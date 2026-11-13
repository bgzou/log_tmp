#!/usr/bin/env python3
"""Focused MuJoCo reproduction of the R1199 FixedStand->zero-speed handoff and
the first-motion posture drop. Compares old diagnostic wrapper vs the training
contract (continuous/straight bias). Offline only; no robot/DDS."""
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, "/tmp/opencode/r1199_eval_work")
sys.path.insert(0, "/tmp/opencode/omni/runtime")

import mujoco
from as2w_mujoco_pd import configure_native_pd
from as2w_zero_memory import ZeroWheelMemory
from export_as2w_candidate_onnx import actor_from_state
from train_stair_low_speed_course import OmniEnvironment
from as2w_rolling_fixed_exit import (parking_odometry, rolling_fixed_exit,
                                     rolling_precalibrated_stand, rolling_wheel_hold)

ASSETS = Path("/tmp/opencode/omni/assets")
CKPT = Path("/home/caolin/as2w_workstation/部署参考/Rob2Nav-rolling-1199-preview/deliveries/as2w-deploy/rolling-1199-simulation-preview/model_1199.pt")
QFILE = Path("/home/caolin/as2w_workstation/部署测试/04_调试记录/logs/20261111_r1199_fresh_fixed_q.txt")
PITCH = -0.08640587718296669


def advance_native_pd(env, action):
    data = env.data
    env.previous = action.copy()
    data.ctrl[env.motors] = np.r_[
        np.clip(env.defaults[:12] + .35 * action[:12], env.leg_low, env.leg_high),
        np.clip(16. * action[12:], -env.wheel_limit, env.wheel_limit)]
    for _ in range(env.substeps):
        mujoco.mj_step(env.model, data)
    env.tick += 1
    env.update_flat_command()
    done = data.xmat[env.base, 8] < .80 or data.qpos[2] < .20
    return env.observe(), done


@torch.inference_mode()
def run(mode, seed, zero_s=6.0, fwd_s=3.0, rel_s=5.0):
    env = OmniEnvironment(ASSETS, 1, stop_training=True, flat_command_max=.10)
    obs, _ = env.reset(seed=seed, options={"scene_seed": seed, "target": (0., 0., 0.)})
    measured = np.loadtxt(QFILE)
    d = env.data
    d.qpos[env.qa] = measured
    d.qpos[3:7] = [np.cos(PITCH / 2.), 0., np.sin(PITCH / 2.), 0.]
    d.qvel[:] = 0.
    low, high = .05, .60
    for _ in range(18):
        mid = (low + high) / 2.
        d.qpos[2] = mid
        mujoco.mj_forward(env.model, d)
        if d.ncon and min(c.dist for c in d.contact) <= 0.:
            low = mid
        else:
            high = mid
    d.qpos[2] = high + .002
    mujoco.mj_forward(env.model, d)
    obs = env.observe()

    env.apply_motion_prior = False
    env.next_command_tick = 10**9
    center = env.defaults[:12]
    env.leg_low = center + .90 * (env.leg_low - center)
    env.leg_high = center + .90 * (env.leg_high - center)
    env.torque_low = .90 * env.torque_low
    env.torque_high = .90 * env.torque_high
    configure_native_pd(env.model, env.motors, env.kp, env.kd,
                        np.r_[env.leg_low, -env.wheel_limit], np.r_[env.leg_high, env.wheel_limit],
                        env.torque_high, velocity_axes=4)

    q_ref = np.r_[(env.data.qpos[env.qa[:12]] - center) / .35, np.zeros(4)]
    memory = ZeroWheelMemory()
    history = np.zeros(16, dtype=np.float32)
    last_obs = obs.copy()
    stand_bias = torch.zeros((1, 12))
    wheel_reference = torch.zeros((1, 4))
    hold_frames = torch.zeros(1, dtype=torch.long)

    actor = actor_from_state(torch.load(CKPT, map_location="cpu", weights_only=True)["actor_state_dict"], 6.)
    dt = env.dt
    start = 4.0          # policy starts moving (command ramps in) after 4 s zero
    release = start + fwd_s
    total = release + rel_s
    trace = []

    old = (mode == "old")
    for tick in range(round(total / dt)):
        elapsed = tick * dt
        # requested command profile: zero until start, then forward, then zero
        if elapsed < start or elapsed >= release:
            amount = max(0., 1. - 1.2 * max(0., elapsed - release) / max(.05, .1)) if elapsed >= release else 0.
        else:
            amount = min(1., 1.2 * (elapsed - start) / max(.05, .1))
        requested = np.array((.05, 0., 0.)) * amount
        env.target_goal = requested

        sampled = last_obs.copy() if (seed >= 47000) else obs.copy()
        sampled[:3] = obs[:3]
        sampled[42:60] = obs[42:60]
        sampled[42:58] = history
        frame = torch.from_numpy(memory.push(sampled))
        current = actor(frame).numpy()

        cmd = torch.from_numpy(obs[:3].copy()).to(torch.float32)
        cmd[0] += .4
        legs, wheels = rolling_fixed_exit(torch.from_numpy(current)[None], cmd[None],
                                          pure_turn_common_scale=1.0)
        wheel_angle = frame[None, 22:26]
        if old:
            wheel_angle = parking_odometry(wheel_angle, frame[None, 10:22], -frame[None, 6:9])
        latch_time = .35 if old else .12
        was_latched = float(hold_frames[0]) * dt >= latch_time
        wheel_reference, hold_frames, hold = rolling_wheel_hold(
            wheel_reference, hold_frames, cmd[None], wheel_angle,
            frame[None, 38:42], frame[None, 3:6], dt,
            common_feedback=old, common_gain_scale=.5,
            leg_speed=(frame[None, 26:38] if old else None))
        wheels = wheels + hold
        stand_bias, stand = rolling_precalibrated_stand(
            stand_bias, cmd[None], frame[None, 10:22], frame[None, 3:6],
            -frame[None, 8], frame[None, 38:42], hold_frames,
            frame.new_tensor([elapsed]), dt,
            continuous=(not old), straight_only=(not old))
        legs = legs + stand
        current = torch.cat((legs, wheels), dim=1)[0].numpy()

        history = current.copy()
        blend = np.clip(elapsed / 2., 0., 1.)
        command = (1. - blend) * q_ref + blend * current
        last_obs = obs.copy()
        obs, done = advance_native_pd(env, command)
        if done:
            break

        q_actual = env.data.qpos[env.qa[:12]].copy()
        q_target = env.data.ctrl[env.motors[:12]].copy()
        trace.append(dict(t=elapsed,
                          cmd_vx=float(obs[0] + .4),
                          q_actual_rad=q_actual.tolist(),
                          q_target_rad=q_target.tolist(),
                          bias_rad=stand_bias[0].tolist(),
                          held_frames=int(hold_frames[0]),
                          thigh_mean=float(q_actual[4:8].mean()),
                          calf_mean=float(q_actual[8:12].mean())))

    # summary metrics
    tt = np.array([f["t"] for f in trace])
    qt = np.array([f["q_target_rad"] for f in trace])
    qa = np.array([f["q_actual_rad"] for f in trace])
    bias = np.array([f["bias_rad"] for f in trace])
    step = np.abs(np.diff(qt, axis=0)).max(axis=1)
    # posture in last 1s of zero-speed vs first 1s after motion starts
    zero_mask = (tt >= start - 1.0) & (tt < start)
    motion_mask = (tt >= start) & (tt < start + 1.0)
    zero_thigh = qa[zero_mask, 4:8].mean() if zero_mask.any() else np.nan
    zero_calf = qa[zero_mask, 8:12].mean() if zero_mask.any() else np.nan
    mot_thigh = qa[motion_mask, 4:8].mean() if motion_mask.any() else np.nan
    mot_calf = qa[motion_mask, 8:12].mean() if motion_mask.any() else np.nan
    bias_at_motion = bias[np.where(tt >= start)[0][0]] if (tt >= start).any() else None
    max_step = step.max()
    max_step_t = tt[step.argmax() + 1]
    return dict(mode=mode, seed=seed,
                zero_posture=dict(thigh=zero_thigh, calf=zero_calf),
                motion_posture=dict(thigh=mot_thigh, calf=mot_calf),
                max_bias_mag=float(np.abs(bias).max()),
                max_single_frame_target_step_rad=float(max_step),
                max_step_at_t=float(max_step_t),
                n_frames=len(trace)), trace


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/opencode/r1199_posture_repro")
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for mode in ("old", "new"):
        for seed in (101, 202, 303):
            r, trace = run(mode, seed)
            rows.append(r)
            (out / f"trace_{mode}_seed{seed}.json").write_text(json.dumps(trace))
            print(f"{mode:4s} seed={seed:3d} "
                  f"zero(thigh={r['zero_posture']['thigh']:.3f},calf={r['zero_posture']['calf']:.3f}) "
                  f"motion(thigh={r['motion_posture']['thigh']:.3f},calf={r['motion_posture']['calf']:.3f}) "
                  f"max_bias={r['max_bias_mag']:.3f} "
                  f"max_step={r['max_single_frame_target_step_rad']:.4f}rad @t={r['max_step_at_t']:.2f}s")
    (out / "summary.json").write_text(json.dumps(rows, indent=2))
    print(json.dumps(rows, indent=2))