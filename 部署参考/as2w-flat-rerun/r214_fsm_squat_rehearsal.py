"""R214 offline A/B/A/Y rehearsal with policy-target handoff and calf folding.

Phase A only establishes the initial condition (dog lies prone, held by firmware
damping in reality); the sim starts at the prone pose at exact touch height with
zero velocity and goes straight into FixStand position control (S3).
Model = training-equivalent (self-collision disabled) since R214 was evaluated
under that contact configuration and the folded prone pose is outside the
model's valid self-collision domain (convex-hull artifacts).

Usage: python3 r214_fsm_squat_rehearsal.py <assets> <r152_runtime> <r214_onnx> <out.json> [T1|T2 ...]
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

ASSETS = Path(sys.argv[1]).resolve()
R152RT = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(R152RT))
import mujoco_screen as sim  # noqa: E402
from export_r41_onnx import session_for  # noqa: E402

class OnnxActor:
    """R214 uses the same 41 observation fields but 1196 recurrent state values."""
    def __init__(self, session, defaults):
        self.session = session
        self.defaults = defaults
        state_size = session.get_inputs()[1].shape[1]
        self.state = np.zeros((1, state_size), dtype=np.float32)

    def plan(self, model, data, obs, command, tick, advance):
        observation = np.r_[command, obs[3:9], obs[10:26] + self.defaults,
                            obs[26:42]].astype(np.float32)
        actions, self.state = self.session.run(
            ["actions", "next_state"],
            {"obs": observation.reshape(1, 41), "state": self.state})
        return actions[0]

ONNX = Path(sys.argv[3]).resolve()
OUT = Path(sys.argv[4]).resolve()
VARIANTS = sys.argv[5:] or ["T1", "T2"]

sim.ROOT = ASSETS
mj = sim.mj
contract = json.loads((ASSETS / "fall-baseline/fall-recovery-contract.json").read_text())
defaults = np.asarray(contract["default_joint_pos"])
NAMES = contract["joint_names"]
LIMITS_LO = np.array([-0.785] * 4 + [-2.0, -2.0, -1.3, -1.3] + [-2.7677] * 4 + [0] * 4)
LIMITS_HI = np.array([0.785] * 4 + [3.492, 3.492, 4.19, 4.19] + [-0.8133] * 4 + [0] * 4)

# 趴下 (sim 坐标, G1 实测 sign 换算; DDS 腿序 FR,FL,RR,RL = 槽 0,3,6,9)
PRONE = np.zeros(16)
PRONE[0], PRONE[1], PRONE[2], PRONE[3] = -0.5676, +0.5725, -0.5930, +0.6040  # FL,FR,RL,RR hip (sim)
PRONE[4:8] = 1.00
PRONE[8:12] = -2.75


def make_stand(variant):
    q = np.zeros(16)
    if variant == "T1":   # 原厂站立实测 (11:41 DDS -> sim, 轻微外展)
        q[0], q[1], q[2], q[3] = +0.1298, -0.1213, +0.1215, -0.1308  # FL,FR,RL,RR
        q[4:8] = 0.60
        q[8:12] = -1.23
    else:                 # T2: R152 训练默认
        q[4:8] = 0.8
        q[8:12] = -1.6
    return q


def build_model():
    return sim.load_flat_model(True, True, seed=0)


def place_prone(model, q_legs, noise):
    """二分法求精确贴地高度 (最大接触间距 ≈ 0)。"""
    data = mj.MjData(model)
    joints = [model.joint(n) for n in NAMES]
    qa = np.array([j.qposadr[0] for j in joints])
    data.qpos[qa] = np.clip(q_legs + noise, LIMITS_LO, LIMITS_HI)
    lo, hi = 0.05, 0.60
    for _ in range(18):
        mid = (lo + hi) / 2
        data.qpos[2] = mid
        mj.mj_forward(model, data)
        if data.ncon and min(c.dist for c in data.contact) <= 0:
            lo = mid
        else:
            hi = mid
    data.qpos[2] = hi
    mj.mj_forward(model, data)
    return data


def contact_peak(model, data, wheels, force):
    peak = 0.
    for i, c in enumerate(data.contact):
        a, b = (int(model.geom_bodyid[g]) for g in c.geom)
        if a and b:
            continue
        body = a or b
        if body not in wheels and body != 0:
            mj.mj_contactForce(model, data, i, force)
            peak = max(peak, float(force[0]))
    return peak


def run_case(variant, seed, session, dt=0.02):
    rng = np.random.default_rng(seed)
    model = build_model()
    joints = [model.joint(n) for n in NAMES]
    qa = np.array([j.qposadr[0] for j in joints])
    va = np.array([j.dofadr[0] for j in joints])
    motors = np.array([model.actuator(n).id for n in NAMES])
    wheels = [model.body(n).id for n in NAMES[12:]]
    base = model.body("base_link").id
    model.geom_friction[model.geom("ground").id, 0] = rng.uniform(.55, .85)
    substeps = round(dt / model.opt.timestep)
    force = np.zeros(6)
    data = place_prone(model, PRONE, rng.uniform(-.02, .02, 16))
    metrics = {"variant": variant, "seed": seed, "prone_height": float(data.qpos[2])}
    actor = OnnxActor(session, defaults)
    prev_action = np.zeros(16)
    last_policy_leg = np.zeros(12)
    last_policy_wheel = np.zeros(4)

    def step_ctrl(leg, wheel, kp=55., kd=2., wheel_kd=2.):
        for _ in range(substeps):
            torque = np.r_[kp * (leg - data.qpos[qa[:12]]) - kd * data.qvel[va[:12]],
                           wheel_kd * (wheel - data.qvel[va[12:]])]
            data.ctrl[motors] = np.clip(torque, *model.actuator_ctrlrange[motors].T)
            mj.mj_step(model, data)

    def policy_tick(command):
        nonlocal prev_action, last_policy_leg, last_policy_wheel
        rot = data.xmat[base].reshape(3, 3)
        q = data.qpos[qa].copy()
        q[12:] = (q[12:] + 2 * np.pi) % (4 * np.pi) - 2 * np.pi
        obs = np.r_[command - (.4, 0., 0.), data.qvel[3:6], -rot[2], .4,
                    q - defaults, data.qvel[va], prev_action]
        frame = obs.copy()
        frame[3:9] = frame[3:9].astype(np.float32)
        frame[10:26] = (frame[10:26] + defaults).astype(np.float32).astype(np.float64) - defaults
        frame[26:42] = frame[26:42].astype(np.float32)
        prev_action = actor.plan(None, None, frame, command, 0, None)
        leg = np.clip(defaults[:12] + .35 * prev_action[:12], LIMITS_LO[:12], LIMITS_HI[:12])
        wheel = np.clip(16. * prev_action[12:], -98.47, 98.47)
        last_policy_leg = leg.copy()
        last_policy_wheel = wheel.copy()
        step_ctrl(leg, wheel)

    # Phase B: Two-segment FixStand (P10 official trajectory pattern)
    # B1 Pre-load (~1.2s): thigh overshoot +0.25 rad, calf/hip stay; low gains kp=20
    # B2 Explosive lift (~1.0s): hip swing + thigh drop + calf extend; kp=55
    start_q = data.qpos[qa].copy()
    stand = make_stand(variant)
    preload = start_q.copy()
    preload[4:8] = np.clip(start_q[4:8] + 0.25, LIMITS_LO[4:8], LIMITS_HI[4:8])
    max_dq = 0.
    heights = []
    # B1: slow pre-load
    n_a = int(1.2 / dt)
    for i in range(n_a):
        alpha = (i + 1) / n_a
        target = start_q + alpha * (preload - start_q)
        leg = np.clip(target[:12], LIMITS_LO[:12], LIMITS_HI[:12])
        step_ctrl(leg, np.zeros(4), kp=20.)
        max_dq = max(max_dq, np.abs(data.qvel[va[:12]]).max())
        if i % 25 == 0:
            heights.append(round(float(data.qpos[2]), 3))
    # B2: fast lift
    preload_q = data.qpos[qa].copy()
    n_b = int(1.0 / dt)
    for i in range(n_b):
        alpha = (i + 1) / n_b
        target = preload_q + alpha * (stand - preload_q)
        leg = np.clip(target[:12], LIMITS_LO[:12], LIMITS_HI[:12])
        step_ctrl(leg, np.zeros(4), kp=55.)
        max_dq = max(max_dq, np.abs(data.qvel[va[:12]]).max())
        if i % 25 == 0:
            heights.append(round(float(data.qpos[2]), 3))
    metrics.update(interp_max_leg_dq=float(max_dq), interp_heights=heights,
                   handoff_height=float(data.qpos[2]),
                   handoff_upright=float(data.xmat[base, 8]),
                   handoff_pose_err_max=float(np.abs(data.qpos[qa] - stand).max()))

    # Phase C: R152 接管, 指令 0, 2 s (S4)
    peak_nonwheel = 0.
    ups = []
    for _ in range(int(2.0 / dt)):
        policy_tick(np.zeros(3))
        ups.append(float(data.xmat[base, 8]))
        peak_nonwheel = max(peak_nonwheel, contact_peak(model, data, wheels, force))
    metrics.update(hold_upright_min=float(min(ups)), hold_height=float(data.qpos[2]))

    # Phase D: forward_slow 0.2 m/s, 4 s (S5)
    x0 = float(data.qpos[0])
    for _ in range(int(4.0 / dt)):
        policy_tick(np.array([0.2, 0., 0.]))
        peak_nonwheel = max(peak_nonwheel, contact_peak(model, data, wheels, force))
    metrics["walk_forward_m"] = float(data.qpos[0] - x0)

    # Phase E: stop 2 s (S6)
    vs = []
    for _ in range(int(2.0 / dt)):
        policy_tick(np.zeros(3))
        peak_nonwheel = max(peak_nonwheel, contact_peak(model, data, wheels, force))
        rot = data.xmat[base].reshape(3, 3)
        vs.append(np.linalg.norm((rot.T @ data.qvel[:3])[:2]))
    metrics.update(stop_speed=float(np.mean(vs)), stop_upright=float(data.xmat[base, 8]),
                   fallen=bool(data.qpos[2] < .20 or data.xmat[base, 8] < .80),
                   peak_nonwheel_n=float(peak_nonwheel))

    # Phase F: Two-segment FixSquat / lie-down (S7, P10 pattern)
    # F1 Unload+fold (~50% of squat_sec): thigh to fold overshoot, calf folds, hip opens
    # F2 Settle+close (~50%): hip closes to prone, thigh retracts to prone
    f1_sec = float(os.environ.get("AS2W_F1_SEC", "1.5"))
    f2_sec = float(os.environ.get("AS2W_F2_SEC", "2.5"))
    f2_kp = float(os.environ.get("AS2W_F2_KP", "35"))
    f1_kp_start = float(os.environ.get("AS2W_F1_KP_START", "55"))
    f1_kp_end = float(os.environ.get("AS2W_F1_KP_END", "35"))
    squat_kd = float(os.environ.get("AS2W_SQUAT_KD", "2"))
    squat_wheel_kd = float(os.environ.get("AS2W_SQUAT_WHEEL_KD", "2"))
    metrics.update(f1_sec=f1_sec, f2_sec=f2_sec, f1_kp_start=f1_kp_start,
                   f1_kp_end=f1_kp_end, f2_kp=f2_kp,
                   squat_kd=squat_kd, squat_wheel_kd=squat_wheel_kd)
    squat_sec = f1_sec + f2_sec
    prone_target = PRONE.copy()
    squat_start = data.qpos[qa].copy()
    squat_start_target = last_policy_leg.copy()
    squat_start_wheel = last_policy_wheel.copy()
    squat_entry_height = float(data.qpos[2])
    early_heights = []
    early_vz = []
    early_contact_peak = 0.
    squat_all_heights = []
    squat_all_vz = []
    squat_all_contact_peak = 0.
    f1_contacts, f2_contacts, settle_contacts = [], [], []
    # Fold overshoot: thigh goes past prone value (official: 1.53 from stand 0.60)
    fold_pose = squat_start.copy()
    # Interpolate toward a mid-fold pose (thigh high, calf folding)
    fold_pose[4:8] = squat_start[4:8] + 0.2
    fold_pose[8:12] = squat_start[8:12] - 0.3  # negative calf = toward prone fold
    n_f1 = int(f1_sec / dt)
    for i in range(n_f1):
        alpha = (i + 1) / n_f1
        target = squat_start_target + alpha * (fold_pose[:12] - squat_start_target)
        leg = np.clip(target[:12], LIMITS_LO[:12], LIMITS_HI[:12])
        blend = min(alpha / 0.4, 1.)
        wheel = squat_start_wheel * max(0., 1.-alpha/0.2)
        step_ctrl(leg, wheel, kp=f1_kp_start +
                  (f1_kp_end-f1_kp_start)*blend,
                  kd=squat_kd, wheel_kd=squat_wheel_kd)
        squat_all_heights.append(float(data.qpos[2]))
        squat_all_vz.append(float(data.qvel[2]))
        peak = contact_peak(model, data, wheels, force)
        f1_contacts.append(peak)
        squat_all_contact_peak = max(squat_all_contact_peak, peak)
        if i < int(0.5/dt):
            early_heights.append(float(data.qpos[2]))
            early_vz.append(float(data.qvel[2]))
            early_contact_peak = max(early_contact_peak,
                contact_peak(model, data, wheels, force))
        if i % 25 == 0:
            heights.append(round(float(data.qpos[2]), 3))
    # F2: close hips + settle to prone
    fold_q = data.qpos[qa].copy()
    n_f2 = int(f2_sec / dt)
    for i in range(n_f2):
        alpha = (i + 1) / n_f2
        target = fold_q + alpha * (prone_target - fold_q)
        leg = np.clip(target[:12], LIMITS_LO[:12], LIMITS_HI[:12])
        step_ctrl(leg, np.zeros(4), kp=f2_kp,
                  kd=squat_kd, wheel_kd=squat_wheel_kd)
        squat_all_heights.append(float(data.qpos[2]))
        squat_all_vz.append(float(data.qvel[2]))
        peak = contact_peak(model, data, wheels, force)
        f2_contacts.append(peak)
        squat_all_contact_peak = max(squat_all_contact_peak, peak)
        if i % 25 == 0:
            heights.append(round(float(data.qpos[2]), 3))
    # Phase G: settle 1s, check prone achieved
    for _ in range(int(1.0 / dt)):
        step_ctrl(np.clip(prone_target[:12], LIMITS_LO[:12], LIMITS_HI[:12]), np.zeros(4), kp=10.)
        squat_all_heights.append(float(data.qpos[2]))
        squat_all_vz.append(float(data.qvel[2]))
        peak = contact_peak(model, data, wheels, force)
        settle_contacts.append(peak)
        squat_all_contact_peak = max(squat_all_contact_peak, peak)
    prone_err = np.abs(data.qpos[qa] - prone_target).max()
    metrics.update(
        squat_entry_height=squat_entry_height,
        squat_first_target_jump_rad=float(np.abs(
            np.clip(squat_start_target + (fold_pose[:12]-squat_start_target)/n_f1,
                    LIMITS_LO[:12], LIMITS_HI[:12])-squat_start_target).max()),
        squat_height_0p1=float(early_heights[int(0.1/dt)-1]),
        squat_height_0p2=float(early_heights[int(0.2/dt)-1]),
        squat_height_0p5=float(early_heights[-1]),
        squat_first_0p5_min_vz=float(min(early_vz)),
        squat_first_0p5_contact_peak_n=float(early_contact_peak),
        squat_min_vz=float(min(squat_all_vz)),
        squat_contact_peak_n=float(squat_all_contact_peak),
        squat_f1_contact_peak_n=float(max(f1_contacts)),
        squat_f2_contact_peak_n=float(max(f2_contacts)),
        squat_settle_contact_peak_n=float(max(settle_contacts)),
        squat_settle_contact_mean_n=float(np.mean(settle_contacts[-25:])),
        squat_height_trace=squat_all_heights[::5],
        squat_final_height=float(data.qpos[2]),
        squat_upright=float(data.xmat[base, 8]),
        squat_prone_err_max=float(prone_err),
        squat_heights=heights[-10:],
    )
    return metrics


if __name__ == "__main__":
    session = session_for(ONNX)
    rows = []
    seeds = [int(x) for x in os.environ.get("AS2W_SEEDS", "101,202,303").split(",")]
    for variant in VARIANTS:
        for seed in seeds:
            r = run_case(variant, seed, session)
            rows.append(r)
            print(f"{variant} seed={seed}: prone_h={r['prone_height']:.3f} "
                  f"interp_dq={r['interp_max_leg_dq']:.2f} h_path={r['interp_heights']} "
                  f"handoff(h={r['handoff_height']:.3f},up={r['handoff_upright']:.3f},"
                  f"err={r['handoff_pose_err_max']:.3f}) hold_up={r['hold_upright_min']:.3f} "
                  f"fwd={r['walk_forward_m']:+.2f}m stop_v={r['stop_speed']:.3f} "
                  f"fallen={r['fallen']} peak={r['peak_nonwheel_n']:.1f}N", flush=True)
    OUT.write_text(json.dumps(rows, indent=1))
    print("saved", OUT)
