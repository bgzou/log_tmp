#!/usr/bin/env python3
"""Summarize R1199 training-contract MuJoCo runs and quantify the sustained
forward mid-section: target-step changes, wheel dq, pitch, wheel load."""
import json
from pathlib import Path

import numpy as np

logdir = Path("/home/caolin/as2w_workstation/部署测试/04_调试记录/logs")

rows = []
for case in ("forward", "back"):
    for seed in (101, 202, 303):
        d = logdir / f"r1199_training_contract_{case}005_10s_seed{seed}"
        diag = json.loads((d / "mujoco-rolling-diagnostic.json").read_text())[0]
        rows.append(diag)

print("=== SUMMARY (stable/tracked/held/nonwheel/unload) ===")
for r in rows:
    pl = r.get("park_lock") or {}
    print(f"{r['scenario']:8s} seed={r['seed']:3d} stable={r['stable']!s:5s} "
          f"tracked={r['tracked']!s:5s} held={r['held']!s:5s} nonwheel={r['nonwheel']!s:5s} "
          f"mean_vx={r['mean_velocity'][0]:+.4f} "
          f"first_nonwheel={r['first_nonwheel_contact']} "
          f"max_unload_s={r['max_wheel_unload_s']:.3f} "
          f"effort_ratio={r['max_sim_effort_ratio']:.3f} "
          f"hold_drift={r['hold_displacement_m']:.4f} "
          f"hold_p95={r['hold_speed_p95_m_s']:.4f} "
          f"stop_s={r['stop_s']}")

print()
print("=== SUSTAINED FORWARD MID-SECTION (trace t in [3.0, 9.0]s of motion) ===")
for seed in (101, 202, 303):
    d = logdir / f"r1199_training_contract_forward005_10s_seed{seed}"
    tr = json.loads((d / "compare-forward-trace.json").read_text())
    q_target = np.array([f["q_target_rad"] for f in tr])
    q_actual = np.array([f["q_actual_rad"] for f in tr])
    wheel_dq = np.array([f["wheel_dq_actual_rad_s"] for f in tr])
    wheel_load = np.array([f["wheel_load_n"] for f in tr])
    pitch = np.array([f["pitch_rad"] for f in tr])
    t = np.array([f["t_s"] for f in tr])
    wrapped = np.array([f["wrapped_action"] for f in tr])
    # single-frame leg-target step (rad), mid-section only
    mid = (t >= 3.0) & (t <= 9.0)
    leg_step = np.abs(np.diff(q_target, axis=0)).max(axis=1)
    wheel_target = 16.0 * wrapped[:, 12:]
    wheel_step = np.abs(np.diff(wheel_target, axis=0)).max(axis=1)
    print(f"seed={seed:3d} n_trace={len(tr)} mid_frames={int(mid.sum())} "
          f"max_leg_step_mid={leg_step[mid[:-1]].max():.5f}rad "
          f"max_wheel_step_mid={wheel_step[mid[:-1]].max():.4f}rad/s "
          f"wheel_dq_rms_mid={np.sqrt((wheel_dq[mid]**2).mean()):.4f}rad/s "
          f"wheel_dq_peak_mid={np.abs(wheel_dq[mid]).max():.4f}rad/s "
          f"pitch_span_mid={np.ptp(pitch[mid]):.4f}rad "
          f"min_wheel_load_mid={wheel_load[mid].min():.2f}N "
          f"max_wheel_load_mid={wheel_load[mid].max():.2f}N")