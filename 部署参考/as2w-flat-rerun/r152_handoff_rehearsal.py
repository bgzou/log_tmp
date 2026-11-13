"""P8 handoff rehearsal: stand pose (T1/T2) -> R152 takeover -> forward_slow -> stop.

Answers the S4-S6 question the sim can faithfully model: given the robot standing
at the FixStand target pose (T1 = measured factory stand, T2 = R152 training
default), can the R152 ONNX policy take over (state zeroed, zero commands),
hold, track forward_slow 0.2 m/s, and stop — with contact peaks audited.

The prone->stand interpolation dynamics (S3) are NOT rehearsed here: the folded
prone pile cannot be faithfully simulated with this model (convex-hull contacts,
no static friction, no firmware damping); S3 must be validated on hardware with
minimal gains, slow ramp and abort path.

Usage: python3 handoff_rehearsal.py <assets> <r152_runtime> <r152_onnx> <out.json> [T1|T2 ...]
"""
import json
import sys
from pathlib import Path

import numpy as np

ASSETS = Path(sys.argv[1]).resolve()
R152RT = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(R152RT))
import mujoco_screen as sim  # noqa: E402
from export_r152_onnx import OnnxActor, session_for  # noqa: E402

ONNX = Path(sys.argv[3]).resolve()
OUT = Path(sys.argv[4]).resolve()
VARIANTS = sys.argv[5:] or ["T1", "T2"]

sim.ROOT = ASSETS
mj = sim.mj
contract = json.loads((ASSETS / "fall-baseline/fall-recovery-contract.json").read_text())
defaults = np.asarray(contract["default_joint_pos"])
NAMES = contract["joint_names"]


def make_stand(variant):
    q = np.zeros(16)
    if variant == "T1":
        q[0], q[1], q[2], q[3] = +0.1298, -0.1213, +0.1215, -0.1308
        q[4:8] = 0.60
        q[8:12] = -1.23
    else:
        q[:] = defaults
    return q


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
    model = sim.load_flat_model(True, True, seed=0)
    joints = [model.joint(n) for n in NAMES]
    qa = np.array([j.qposadr[0] for j in joints])
    va = np.array([j.dofadr[0] for j in joints])
    motors = np.array([model.actuator(n).id for n in NAMES])
    wheels = [model.body(n).id for n in NAMES[12:]]
    base = model.body("base_link").id
    model.geom_friction[model.geom("ground").id, 0] = rng.uniform(.55, .85)
    substeps = round(dt / model.opt.timestep)
    force = np.zeros(6)

    # 放置: 站立目标姿态 + 噪声, 精确贴地, 零速度
    data = mj.MjData(model)
    data.qpos[qa] = make_stand(variant) + rng.uniform(-.03, .03, 16)
    lo, hi = 0.05, 0.60
    for _ in range(18):
        mid = (lo + hi) / 2
        data.qpos[2] = mid
        mj.mj_forward(model, data)
        if data.ncon and min(c.dist for c in data.contact) <= 0:
            lo = mid
        else:
            hi = mid
    data.qpos[2] = hi + 0.002
    mj.mj_forward(model, data)

    actor = OnnxActor(session, defaults)
    prev_action = np.zeros(16)
    metrics = {"variant": variant, "seed": seed, "start_height": float(data.qpos[2])}

    def policy_tick(command):
        nonlocal prev_action
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
        leg = np.clip(defaults[:12] + .35 * prev_action[:12],
                      [-0.785]*4 + [-2.0, -2.0, -1.3, -1.3] + [-2.7677]*4,
                      [0.785]*4 + [3.492, 3.492, 4.19, 4.19] + [-0.8133]*4)
        wheel = np.clip(16. * prev_action[12:], -98.47, 98.47)
        for _ in range(substeps):
            torque = np.r_[55. * (leg - data.qpos[qa[:12]]) - 2. * data.qvel[va[:12]],
                           2. * (wheel - data.qvel[va[12:]])]
            data.ctrl[motors] = np.clip(torque, *model.actuator_ctrlrange[motors].T)
            mj.mj_step(model, data)

    # Phase C: R152 接管, 指令 0, 2 s
    peak = 0.
    ups = []
    for _ in range(int(2.0 / dt)):
        policy_tick(np.zeros(3))
        ups.append(float(data.xmat[base, 8]))
        peak = max(peak, contact_peak(model, data, wheels, force))
    metrics.update(hold_upright_min=float(min(ups)), hold_height=float(data.qpos[2]),
                   hold_peak_n=float(peak))

    # Phase D: forward_slow 4 s
    x0 = float(data.qpos[0])
    vxs = []
    for _ in range(int(4.0 / dt)):
        policy_tick(np.array([0.2, 0., 0.]))
        peak = max(peak, contact_peak(model, data, wheels, force))
        rot = data.xmat[base].reshape(3, 3)
        vxs.append(float((rot.T @ data.qvel[:3])[0]))
    metrics.update(walk_forward_m=float(data.qpos[0] - x0),
                   walk_vx_mean=float(np.mean(vxs)), walk_peak_n=float(peak))

    # Phase E: stop 2 s
    vs = []
    for _ in range(int(2.0 / dt)):
        policy_tick(np.zeros(3))
        peak = max(peak, contact_peak(model, data, wheels, force))
        rot = data.xmat[base].reshape(3, 3)
        vs.append(np.linalg.norm((rot.T @ data.qvel[:3])[:2]))
    metrics.update(stop_speed=float(np.mean(vs)), stop_upright=float(data.xmat[base, 8]),
                   fallen=bool(data.qpos[2] < .20 or data.xmat[base, 8] < .80),
                   peak_nonwheel_n=float(peak))
    return metrics


if __name__ == "__main__":
    session = session_for(ONNX)
    rows = []
    for variant in VARIANTS:
        for seed in (101, 202, 303):
            r = run_case(variant, seed, session)
            rows.append(r)
            print(f"{variant} seed={seed}: hold(up_min={r['hold_upright_min']:.3f},h={r['hold_height']:.3f},"
                  f"peak={r['hold_peak_n']:.1f}N) fwd={r['walk_forward_m']:+.2f}m vx={r['walk_vx_mean']:+.3f} "
                  f"stop_v={r['stop_speed']:.3f} fallen={r['fallen']} peak_total={r['peak_nonwheel_n']:.1f}N",
                  flush=True)
    OUT.write_text(json.dumps(rows, indent=1))
    print("saved", OUT)
