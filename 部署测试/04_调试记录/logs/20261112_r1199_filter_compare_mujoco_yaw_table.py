#!/usr/bin/env python3
"""Summarize the paired tau=0 vs tau=40 MuJoCo yaw runs (0.10 rad/s command).

tau=40 results are read from the archived turn directories; tau=0 results from
the runs produced by 20261112_r1199_filter_compare_mujoco_yaw.sh. Everything
else (weight, measured start, contract flags, friction, PD, command) is
identical between the two sets.
"""
import json
import sys
from pathlib import Path

LOGS = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/home/caolin/as2w_workstation/部署测试/04_调试记录/logs")
T0ROOT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("/tmp/opencode/r1199_filter_compare/mujoco_tau0")

rows = []
print("Paired MuJoCo yaw, cmd 0.10 rad/s, only R1199_LOWPASS_MS differs:")
print(f"{'case':22s} {'tau_ms':>6s} {'yaw_mean(rad/s)':>15s} {'ratio':>6s} {'tracked':>7s} "
      f"{'stable':>6s} {'nonwheel':>8s} {'hold_disp_m':>11s} {'brake_m':>7s}")
for d in ("left", "right"):
    for s in (101, 202, 303):
        for tau, path in (
            (0, T0ROOT / f"turn_{d}010_10s_seed{s}_tau0" / "mujoco-rolling-diagnostic.json"),
            (40, LOGS / f"r1199_debug_lowpass_turn_{d}010_10s_seed{s}_tau40" / "mujoco-rolling-diagnostic.json"),
        ):
            j = json.load(open(path))[0]
            wz = j["mean_velocity"][2]
            print(f"turn_{d:5s} seed{s}      {tau:6d} {wz:+15.4f} {abs(wz)/0.10:6.2f} "
                  f"{str(j['tracked']):>7s} {str(j['stable']):>6s} {str(j['nonwheel']):>8s} "
                  f"{j['hold_displacement_m']:11.3f} {j['brake_distance_m']:7.3f}")
            rows.append({"case": f"turn_{d}", "seed": s, "tau_ms": tau, "yaw_mean": wz,
                         "ratio": abs(wz) / 0.10, "tracked": j["tracked"], "stable": j["stable"],
                         "nonwheel": j["nonwheel"], "hold_disp_m": j["hold_displacement_m"],
                         "brake_m": j["brake_distance_m"]})
import csv
out = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("20261112_r1199_filter_compare_mujoco_yaw.csv")
with out.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
r0 = [r["ratio"] for r in rows if r["tau_ms"] == 0]
r40 = [r["ratio"] for r in rows if r["tau_ms"] == 40]
print(f"\ntau=0 : ratio mean {sum(r0)/len(r0):.2f} (min {min(r0):.2f} max {max(r0):.2f}), "
      f"tracked {sum(r['tracked'] for r in rows if r['tau_ms']==0)}/6")
print(f"tau=40: ratio mean {sum(r40)/len(r40):.2f} (min {min(r40):.2f} max {max(r40):.2f}), "
      f"tracked {sum(r['tracked'] for r in rows if r['tau_ms']==40)}/6")
print(f"relative yaw cost of the 40 ms filter in sim: "
      f"{(sum(r0)-sum(r40))/sum(r0)*100:.0f}% of the tau=0 response")
print("wrote", out)
