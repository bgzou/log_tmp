#!/usr/bin/env python3
"""MuJoCo closed-loop sim2sim for the delivered as2w_mlp57_flat_model2700.

Reproduces the colleague's 156-case PhysX matrix (39 commands x 4 initial
states, 2 s zero + 8 s motion + 2 s stop) with their exact rng initial states
(np.random.default_rng(81200+repeat)) and their five scoring criteria, using
the delivery's own reference.hpp observation/target mapping and ONNX policy.

Same official AS2-W URDF source as their Isaac model (26 kg, torque limits
60/60/90/15). MuJoCo replaces PhysX as the second simulator. Offline only."""
import csv
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import mujoco
import onnxruntime as ort

PKG = Path("/home/caolin/as2w_workstation/部署参考/as2w_mlp57_flat_model2700_v1_20261112")
OMNI = Path("/tmp/opencode/omni/assets")
OUT = Path("/home/caolin/as2w_workstation/部署测试/04_调试记录/logs/mlp57_2700_mujoco156")

# their policy joint order (per-leg grouped, FR/FL/RR/RL then wheels)
POLICY_ORDER = ["FR_hip", "FR_thigh", "FR_calf",
                "FL_hip", "FL_thigh", "FL_calf",
                "RR_hip", "RR_thigh", "RR_calf",
                "RL_hip", "RL_thigh", "RL_calf",
                "FR_foot", "FL_foot", "RR_foot", "RL_foot"]
Q0 = np.array([0, .65, -1.3] * 4 + [0, 0, 0, 0], dtype=np.float64)
LEG_SCALE = np.array([.125, .25, .25] * 4, dtype=np.float64)
KP_LEG, KD, WHEEL_SCALE = 40.0, 1.0, 5.0

COMMANDS = []  # (name, label, vx, vy, wz) — filled from their cases.csv
def load_commands():
    rows = list(csv.DictReader(open(PKG / "simulation/evidence156/cases.csv")))
    seen = {}
    for r in rows:
        key = r["profile"]
        if key not in seen:
            seen[key] = (r["label"], float(r["command_vx"]), float(r["command_vy"]), float(r["command_wz"]))
    for name, (label, vx, vy, wz) in seen.items():
        COMMANDS.append((name, label, vx, vy, wz))

def initial_condition(repeat):
    """Exact reproduction of their evaluate.py lines 93-98."""
    if repeat == 0:
        return [0.0, 0.0, 0.0], np.zeros(12)
    rng = np.random.default_rng(81200 + repeat)
    rpy = [*rng.uniform(-math.radians(.25), math.radians(.25), 2), rng.uniform(-math.pi, math.pi)]
    delta = rng.uniform(-.005, .005, 12)
    return rpy, delta

def main():
    load_commands()
    import os
    if os.environ.get("MLP57_SMOKE"):
        COMMANDS[:] = [c for c in COMMANDS if c[0] in ("stand", "forward_0.30")][:2]
    OUT.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, "/tmp/opencode/omni/runtime")
    import mujoco_screen as sim
    sim.ROOT = OMNI
    model = sim.load_flat_model(True, True, None, 0)
    # Match the colleague's nominal PhysX eval materials (resolved_env.yaml:
    # static/dynamic friction 1.0); the omni loader randomizes ground friction
    # to 0.55-0.85 per scene seed, which makes the wheels slip and the policy
    # collapse. MuJoCo combines per-pair; set both sides explicitly.
    model.geom_friction[:, 0] = 1.0
    data = mujoco.MjData(model)
    base = model.body("base_link").id
    ground = model.geom("ground").id
    wheel_bodies = {model.body(n).id for n in POLICY_ORDER[12:]}
    qadr = np.array([model.joint(n).qposadr[0] for n in POLICY_ORDER], dtype=int)
    vadr = np.array([model.joint(n).dofadr[0] for n in POLICY_ORDER], dtype=int)
    actu = [model.actuator(n).id for n in POLICY_ORDER]
    ctrl_lo = model.actuator_ctrlrange[actu, 0]
    ctrl_hi = model.actuator_ctrlrange[actu, 1]
    substeps = round(0.02 / model.opt.timestep)
    sess = ort.InferenceSession(str(PKG / "model/policy.onnx"),
                                providers=["CPUExecutionProvider"])

    def contact_search():
        lo, hi = 0.30, 0.50
        for _ in range(20):
            mid = (lo + hi) / 2
            data.qpos[2] = mid
            mujoco.mj_forward(model, data)
            if data.ncon and min(c.dist for c in data.contact) <= 0:
                lo = mid
            else:
                hi = mid
        return hi

    results = []
    t_start = time.time()
    for (name, label, vx, vy, wz) in COMMANDS:
        for repeat in range(4):
            rpy, delta = initial_condition(repeat)
            data.qpos[:] = 0
            data.qvel[:] = 0
            r, p, y = rpy
            cr, sr = math.cos(r/2), math.sin(r/2)
            cp, sp = math.cos(p/2), math.sin(p/2)
            cy, sy = math.cos(y/2), math.sin(y/2)
            data.qpos[3:7] = [cr*cp*cy + sr*sp*sy, sr*cp*cy - cr*sp*sy,
                              cr*sp*cy + sr*cp*sy, cr*cp*sy - sr*sp*cy]
            for i in range(12):
                data.qpos[qadr[i]] = Q0[i] + delta[i]
            for i in range(12, 16):
                data.qpos[qadr[i]] = 0.0
            data.qvel[:] = 0
            # Their formal eval starts IN contact (0.42844 is their contact
            # height; the 9 mm sink is soft kp=40 leg loading, not a drop).
            # Our model's contact height for the same pose is ~0.4234; start
            # exactly at contact, no free-fall transient.
            data.qpos[2] = contact_search()
            mujoco.mj_forward(model, data)

            previous = np.zeros(16, dtype=np.float32)
            cmd = np.array([vx, vy, wz], dtype=np.float64)
            rows = []
            failed_t = None
            nonwheel_peak = 0.0
            for step in range(round(12.0 / 0.02)):
                command = np.zeros(3) if step * 0.02 < 2.0 else cmd
                mujoco.mj_objectVelocity(model, data, mujoco.mjtObj.mjOBJ_BODY, base, _vel, 1)
                gyro = _vel[:3].copy()
                lin_b = _vel[3:].copy()
                R = data.xmat[base].reshape(3, 3)
                gravity = R.T @ np.array([0, 0, -1.0])
                q = np.array([data.qpos[a] for a in qadr])
                dq = np.array([data.qvel[a] for a in vadr])
                obs = np.empty(57, dtype=np.float32)
                obs[0:3] = np.clip(gyro, -100, 100) * .25
                obs[3:6] = np.clip(gravity, -100, 100)
                obs[6:9] = np.clip(command, -100, 100)
                obs[9:21] = np.clip(q[:12] - Q0[:12], -100, 100)
                obs[21:25] = 0.0
                obs[25:41] = np.clip(dq, -100, 100) * .05
                obs[41:57] = np.clip(previous, -100, 100)
                raw = sess.run(["raw_action_mean"], {"observation": obs[None]})[0][0]
                previous = raw.astype(np.float32)
                q_des = Q0.copy()
                q_des[:12] = np.clip(raw[:12] * LEG_SCALE + Q0[:12], -100, 100)
                dq_des = np.clip(raw[12:] * WHEEL_SCALE, -100, 100)
                tilt = math.degrees(math.acos(max(-1.0, min(1.0, -gravity[2]))))
                rows.append((step * 0.02, command.copy(), data.xpos[base].copy(),
                             data.qpos[3:7].copy(), q.copy(), lin_b.copy(), gyro.copy(), tilt))
                if failed_t is None and (data.xpos[base][2] < 0.20 or tilt > 60.0):
                    failed_t = step * 0.02
                # Their Isaac actuator PD is re-evaluated EVERY physics step
                # (200 Hz) against the held targets ("zero-order target hold
                # for four physics steps" — the TARGET is held, the torque is
                # recomputed). A 50 Hz torque hold with kd=1 is unstable on
                # the lightly-damped wheel loop (verified against their
                # recorded applied_torque_after: last-substep torques decay/
                # brake, e.g. wheel +0.077 vs first-substep -1.31).
                tau = np.empty(16)
                for _ in range(substeps):
                    q_now = np.array([data.qpos[a] for a in qadr])
                    dq_now = np.array([data.qvel[a] for a in vadr])
                    tau[:12] = KP_LEG * (q_des[:12] - q_now[:12]) - KD * dq_now[:12]
                    tau[12:] = KD * (dq_des - dq_now[12:])
                    data.ctrl[actu] = np.clip(tau, ctrl_lo, ctrl_hi)
                    mujoco.mj_step(model, data)
                    for cidx in range(data.ncon):
                        c = data.contact[cidx]
                        if ground not in c.geom:
                            continue
                        other = c.geom[1] if c.geom[0] == ground else c.geom[0]
                        if model.geom_bodyid[other] in wheel_bodies:
                            continue
                        mujoco.mj_contactForce(model, data, cidx, _wrench)
                        nonwheel_peak = max(nonwheel_peak, abs(_wrench[0] * c.frame[2]))
                if failed_t is None and (data.xpos[base][2] < 0.20):
                    failed_t = (step + 1) * 0.02

            arr_t = np.array([r[0] for r in rows])
            arr_cmd = np.array([r[1] for r in rows])
            arr_pos = np.array([r[2] for r in rows])
            arr_vb = np.array([r[5] for r in rows])
            arr_wb = np.array([r[6] for r in rows])
            arr_tilt = np.array([r[7] for r in rows])
            steady = (arr_t > 4.0) & (arr_t <= 10.0)
            stop_m = arr_t > 11.0
            actual = np.column_stack([arr_vb[:, :2], arr_wb[:, 2]])
            mean = actual[steady].mean(axis=0)
            mae = np.abs(actual[steady] - arr_cmd[steady]).mean(axis=0)
            th = np.array([max(.03, .2 * abs(cmd[i])) if cmd[i] else .05 for i in range(2)]
                          + [max(.05, .2 * abs(cmd[2])) if cmd[2] else .10])
            stop_xy = np.linalg.norm(actual[stop_m][:, :2], axis=1).mean() if stop_m.any() else 9.9
            stop_wz = np.abs(actual[stop_m][:, 2]).mean() if stop_m.any() else 9.9
            min_h = arr_pos[steady, 2].min() if steady.any() else 0.0
            max_tilt = arr_tilt[steady].max() if steady.any() else 99.0
            failed = failed_t is not None
            v_pass = (not failed) and bool(np.all(mae <= th))
            s_pass = (not failed) and stop_xy <= .1 and stop_wz <= .15
            p_pass = min_h >= .28 and max_tilt <= 25
            c_pass = nonwheel_peak < 50
            results.append({
                "case": f"{name}__r{repeat}", "profile": name, "label": label, "repeat": repeat,
                "first_failure_seconds": failed_t,
                "min_base_height_m": float(arr_pos[:, 2].min()),
                "moving_min_height_m": float(min_h), "moving_max_tilt_deg": float(max_tilt),
                "nonwheel_contact_peak_N": float(nonwheel_peak),
                "stop_mean_xy_speed_m_s": float(stop_xy), "stop_mean_abs_yaw_rate_rad_s": float(stop_wz),
                "velocity_pass": v_pass, "stop_pass": s_pass,
                "posture_pass": bool(p_pass), "contact_pass": bool(c_pass),
                "fully_qualified": bool(v_pass and s_pass and p_pass and c_pass),
                "command_vx": vx, "command_vy": vy, "command_wz": wz,
                "actual_vx": float(mean[0]), "actual_vy": float(mean[1]), "actual_wz": float(mean[2]),
                "mae_vx_vy_wz": mae.tolist(),
            })
            print(f"{name}__r{repeat}: v={v_pass} s={s_pass} p={p_pass} c={c_pass} "
                  f"peak={nonwheel_peak:.1f}N minH={min_h:.3f} stop={stop_xy:.3f}/{stop_wz:.3f}",
                  flush=True)

    with open(OUT / "mujoco156.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader()
        w.writerows(results)
    tallies = {k: sum(r[k] for r in results) for k in
               ("velocity_pass", "stop_pass", "posture_pass", "contact_pass", "fully_qualified")}
    summary = {"cases": len(results), **tallies,
               "engine": f"MuJoCo {mujoco.__version__}",
               "model_timestep_s": model.opt.timestep,
               "policy": str(PKG / "model/policy.onnx"),
               "onnx_sha256": __import__("hashlib").sha256((PKG / "model/policy.onnx").read_bytes()).hexdigest(),
               "initial_states": "np.random.default_rng(81200+repeat), exact reproduction of evaluate.py:93-98",
               "criteria": "identical to speed_sweep_native.py criteria",
               "wall_seconds": time.time() - t_start}
    (OUT / "mujoco156_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))

_vel = np.zeros(6)
_wrench = np.zeros(6)

if __name__ == "__main__":
    main()
