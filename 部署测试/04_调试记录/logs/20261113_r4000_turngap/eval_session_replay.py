#!/usr/bin/env python3
"""MuJoCo session-replay comparison for the R4000 turn-gap investigation.

Replays the REAL session's command waveform (20261113-114335) on the flat
model from the measured start, with the original training-contract wrapper,
and records the sim-side measured wheel differential for comparison with the
field data. Single-variable knobs:

  R4000_REPLAY_SESSION   session dir (debug_policy.csv)
  R4000_REPLAY_T0_TICK   first policy tick of the window
  R4000_REPLAY_SECONDS   window length (sim seconds)
  R4000_WHEEL_SOURCE     wrapper | recorded   (wheel targets)
  R4000_LEG_SOURCE       policy | fixed       (leg targets)
  R4000_FRICTION_SCALE   sliding-friction multiplier on ground+wheels
  R4000_WHEEL_KD_SCALE   wheel velocity damping multiplier (native PD)
  R4000_TURN_GAIN        yaw-injection gain multiplier (default 1)

Outputs mujoco-rolling-diagnostic.json (standard fields) plus
session-replay-trace.json with per-frame wheel cmd/meas/yaw/rear posture.
Offline only; no robot access.
"""
import bisect
import copy
import csv
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, "/tmp/opencode/r1199_eval_work")
sys.path.insert(1, "/tmp/opencode/rob2nav_fetch/training/as2w-backup/as2w-current/code")
sys.path.insert(2, "/tmp/opencode/omni/runtime")
sys.path.insert(0, "/tmp/opencode/r4000_turngain")  # gain-patched wrapper module

import mujoco
from as2w_rolling_fixed_exit import (rolling_fixed_exit, rolling_precalibrated_stand,
                                     rolling_wheel_hold)
from as2w_rolling_filtered import filter_leg_residual
from as2w_mujoco_pd import configure_native_pd
from as2w_zero_memory import ZeroWheelMemory
from train_stair_low_speed_course import OmniEnvironment
from export_as2w_candidate_onnx import actor_from_state

SESSION = Path(os.environ["R4000_REPLAY_SESSION"])
T0 = int(os.environ["R4000_REPLAY_T0_TICK"])
DUR = float(os.environ.get("R4000_REPLAY_SECONDS", "11.6"))
WHEEL_SOURCE = os.environ.get("R4000_WHEEL_SOURCE", "wrapper")
LEG_SOURCE = os.environ.get("R4000_LEG_SOURCE", "policy")
FRICTION_SCALE = float(os.environ.get("R4000_FRICTION_SCALE", "1"))
WHEEL_KD_SCALE = float(os.environ.get("R4000_WHEEL_KD_SCALE", "1"))
TURN_GAIN = float(os.environ.get("R4000_TURN_GAIN", "1"))
OUT = Path(sys.argv[1])
CKPT = Path(sys.argv[2])
ASSETS = Path(sys.argv[3])


def load_session_window():
    rows = []
    with (SESSION / "debug_policy.csv").open(newline="", encoding="utf-8", errors="replace") as f:
        next(f)
        for r in csv.reader(f):
            if not (r and r[0] == "DEBUG_POLICY" and r[2] == "WALK"):
                continue
            n = int(r[57]); st = int(r[58 + n]); raw_s = 59 + n + st
            app_s = raw_s + 96
            tick = int(r[3])
            if T0 <= tick <= T0 + DUR * 1000:
                rows.append({
                    "dt_ms": tick - T0,
                    "cmd": (float(r[5]), float(r[6]), float(r[7])),
                    "app_dq": [float(r[app_s + 4 * (12 + i) + 1]) for i in range(4)],
                    "app_q": [float(r[app_s + 4 * i]) for i in range(12)],
                })
    return rows


def main():
    win = load_session_window()
    assert win, "empty window"
    state = torch.load(CKPT, map_location="cpu", weights_only=True)["actor_state_dict"]
    actor = actor_from_state(state, 6.)

    env = OmniEnvironment(ASSETS, 1, stop_training=True, flat_command_max=.40)
    obs, _ = env.reset(seed=101, options={"scene_seed": 101, "target": (0., 0., 0.)})
    # measured start (same as all gates)
    measured = np.loadtxt("/home/caolin/as2w_workstation/部署测试/04_调试记录/logs/20261111_r1199_fresh_fixed_q.txt")
    pitch = -0.08640587718296669
    q0 = env.data.qpos.copy()
    qa = env.qa
    q0[qa] = measured
    q0[2] = 0.3766868133544923
    quat = env.data.qpos[3:7].copy()
    quat[0] = np.cos(pitch / 2); quat[1] = 0.; quat[2] = np.sin(pitch / 2); quat[3] = 0.
    q0[3:7] = quat
    env.data.qpos[:] = q0; env.data.qvel[:] = 0
    mujoco.mj_forward(env.model, env.data)
    obs = env.observe()
    env.apply_motion_prior = False
    env.next_command_tick = 10 ** 9
    center = env.defaults[:12]
    env.leg_low = center + .90 * (env.leg_low - center)
    env.leg_high = center + .90 * (env.leg_high - center)
    env.torque_low = .90 * env.torque_low
    env.torque_high = .90 * env.torque_high
    # wheel velocity damping scale
    env.kd = np.array(env.kd, dtype=float)
    env.kd[12:] = env.kd[12:] * WHEEL_KD_SCALE
    configure_native_pd(env.model, env.motors, env.kp, env.kd,
                        np.r_[env.leg_low, -env.wheel_limit], np.r_[env.leg_high, env.wheel_limit],
                        env.torque_high, velocity_axes=4)
    if FRICTION_SCALE != 1.:
        env.model.geom_friction[:, 0] *= FRICTION_SCALE

    wheel_bodies = sorted(env.wheel_index, key=env.wheel_index.get)
    stand_bias = torch.zeros((1, 12)); filtered_legs = torch.zeros(12)
    previous_legs = np.zeros(12, dtype=np.float32)
    wheel_reference = torch.zeros((1, 4)); hold_frames = torch.zeros(1, dtype=torch.long)
    fixed_q = measured[:12]
    memory = ZeroWheelMemory()
    history = np.zeros(16, dtype=np.float32)
    trace = []
    max_unload = 0; nonwheel = False; min_surface = 1e9
    wheel_slots = [13, 12, 15, 14]   # contract FL FR RL RR -> LowState slots (sim order = env order)
    W_PI = 2 * np.pi
    for tick in range(int(DUR / env.dt)):
        elapsed = tick * env.dt
        i = bisect.bisect_right([w["dt_ms"] for w in win], elapsed * 1000) - 1
        rec = win[max(i, 0)]
        env.target_goal = np.array(rec["cmd"])
        env.update_flat_command()
        sampled = obs.copy()
        sampled[42:58] = history
        frame = torch.from_numpy(memory.push(sampled))
        cmd = frame[:3].clone(); cmd[0] += .4
        cmdb = cmd[None]
        raw = actor(frame).detach()
        current = raw.numpy().copy()
        if TURN_GAIN != 1.:
            import as2w_rolling_fixed_exit as _m
            _m._TURN_GAIN = .66 * TURN_GAIN
        filtered_legs = filter_leg_residual(filtered_legs, torch.from_numpy(current[:12]), env.dt, 5.0)
        action = torch.cat((filtered_legs, torch.from_numpy(current[12:])))
        legs, wheels = rolling_fixed_exit(action[None], cmdb, pure_turn_common_scale=0.)
        wheel_reference, hold_frames, hold = rolling_wheel_hold(
            wheel_reference, hold_frames, cmdb, frame[None, 22:26], frame[None, 38:42],
            frame[None, 3:6], env.dt, common_feedback=False, leg_speed=None)
        wheels = wheels + hold  # (batched)
        stand_bias, stand = rolling_precalibrated_stand(
            stand_bias, cmdb, frame[None, 10:22], frame[None, 3:6], -frame[None, 8],
            frame[None, 38:42], hold_frames, frame.new_tensor([elapsed + 4.]), env.dt,
            continuous=True, straight_only=True)
        legs = legs + stand
        step_limit = .9 * env.dt / .35
        previous_legs += np.clip(legs[0].numpy() - previous_legs, -step_limit, step_limit)
        legs = previous_legs
        wheel_target_norm = wheels[0].numpy()
        if WHEEL_SOURCE == "recorded":
            wheel_target_norm = np.array(rec["app_dq"]) / 16.
        if LEG_SOURCE == "fixed":
            legs = (np.asarray(fixed_q) - env.defaults[:12]) / .35
        applied = np.concatenate((legs, wheel_target_norm))
        history = np.clip(applied.copy(), -6., 6.)
        blend = np.clip(elapsed / 2., 0., 1.)
        q_ref = np.r_[(env.data.qpos[env.qa[:12]] - center) / .35, np.zeros(4)]
        command = (1. - blend) * q_ref + blend * applied
        obs, done, peak = env.step_native(command, monitor=None) if hasattr(env, "step_native") else (None, None, None)
        if obs is None:
            data = env.data
            data.ctrl[env.motors] = np.r_[
                np.clip(env.defaults[:12] + .35 * command[:12], env.leg_low, env.leg_high),
                np.clip(16. * command[12:], -env.wheel_limit, env.wheel_limit)]
            env.previous = command.copy()
            env.tick += 1
            env.update_flat_command()
            for _ in range(env.substeps):
                mujoco.mj_step(env.model, data)
            obs = env.observe()
            done = data.xmat[env.base, 8] < .80 or data.qpos[2] < .20
        meas_w = env.data.qvel[env.va[12:]]
        rotation = env.data.xmat[env.base].reshape(3, 3)
        yaw = env.data.qvel[5]
        rear = env.data.qpos[[env.qa[7], env.qa[10]]].mean()
        loads = np.zeros(4)
        for contact in env.data.contact:
            if env.ground not in contact.geom:
                continue
            link = env.model.geom_bodyid[contact.geom[1] if contact.geom[0] == env.ground else contact.geom[0]]
            if link in env.wheel_index:
                loads[env.wheel_index[link]] += 1
            else:
                nonwheel = True
        max_unload = max(max_unload, int((loads < 2).sum()))
        if tick % 5 == 0:
            trace.append({
                "t_s": elapsed, "wz_cmd": float(cmd[2]),
                "wheel_cmd_diff": float((wheel_target_norm[[1, 3]].mean() - wheel_target_norm[[0, 2]].mean()) * 16.),
                "wheel_meas_diff": float(meas_w[[1, 3]].mean() - meas_w[[0, 2]].mean()),
                "wheel_meas_common": float(meas_w.mean()),
                "yaw_rate": float(yaw), "rear_thigh": float(rear),
                "leg_mode": LEG_SOURCE, "wheel_mode": WHEEL_SOURCE,
            })
        if done:
            trace.append({"terminated": True, "t_s": elapsed})
            break
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "session-replay-trace.json").write_text(json.dumps(trace))
    summary = {
        "config": {"wheel_source": WHEEL_SOURCE, "leg_source": LEG_SOURCE,
                   "friction_scale": FRICTION_SCALE, "wheel_kd_scale": WHEEL_KD_SCALE,
                   "turn_gain": TURN_GAIN, "t0_tick": T0, "dur_s": DUR},
        "frames": len(trace), "terminated": any("terminated" in t for t in trace),
        "nonwheel_contact": nonwheel,
        "meas_diff_mean_1s": float(np.mean([t["wheel_meas_diff"] for t in trace if t["t_s"] <= 1])) or None,
        "meas_diff_mean_3_5s": float(np.mean([t["wheel_meas_diff"] for t in trace if 3 <= t["t_s"] <= 5])) or None,
        "meas_diff_mean_last5": float(np.mean([t["wheel_meas_diff"] for t in trace if t["t_s"] >= DUR - 5])) or None,
        "yaw_mean": float(np.mean([t["yaw_rate"] for t in trace])),
    }
    (OUT / "session-replay-summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
