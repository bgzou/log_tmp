#!/usr/bin/env python3
"""Compare factory stand and low-level FixedStand from LOW_SAMPLE logs.

This is offline-only: it reads recorded HG LowState CSV lines and never opens DDS.
"""

from __future__ import annotations

import math
import statistics
import sys
from pathlib import Path


NAMES = [
    "FL_hip", "FR_hip", "RL_hip", "RR_hip",
    "FL_thigh", "FR_thigh", "RL_thigh", "RR_thigh",
    "FL_calf", "FR_calf", "RL_calf", "RR_calf",
]
SLOTS = [3, 0, 9, 6, 4, 1, 10, 7, 5, 2, 11, 8]
SIGNS = [-1, -1, -1, -1, 1, 1, 1, 1, 1, 1, 1, 1]
T1 = [0.1298, -0.1213, 0.1215, -0.1308, 0.60, 0.60, 0.60, 0.60,
      -1.23, -1.23, -1.23, -1.23]
T2 = [0.0, 0.0, 0.0, 0.0, 0.8, 0.8, 0.8, 0.8,
      -1.6, -1.6, -1.6, -1.6]


def parse(path: Path):
    rows = []
    with path.open(errors="replace") as stream:
        for raw in stream:
            pos = raw.find("LOW_SAMPLE,")
            if pos < 0:
                continue
            f = raw[pos:].strip().split(",")
            if len(f) < 14 + 35 * 6:
                continue
            motors = []
            for i in range(35):
                j = 14 + i * 6
                motors.append({
                    "q": float(f[j]), "dq": float(f[j + 1]),
                    "tau": float(f[j + 3]), "mode": int(float(f[j + 4])),
                })
            q = [SIGNS[i] * motors[SLOTS[i]]["q"] for i in range(12)]
            dq = [SIGNS[i] * motors[SLOTS[i]]["dq"] for i in range(12)]
            tau = [SIGNS[i] * motors[SLOTS[i]]["tau"] for i in range(12)]
            quat = [float(f[7 + i]) for i in range(4)]
            rows.append({
                "t": float(f[1]) / 1000.0, "q": q, "dq": dq, "tau": tau,
                "mode": [motors[SLOTS[i]]["mode"] for i in range(12)],
                "quat": quat,
            })
    return rows


def upright(row):
    w, x, y, z = row["quat"]
    return 1.0 - 2.0 * (x * x + y * y)


def pitch_deg(row):
    w, x, y, z = row["quat"]
    value = 2.0 * (w * y - z * x)
    return math.degrees(math.asin(max(-1.0, min(1.0, value))))


def factory_stable(row):
    q = row["q"]
    return (
        all(mode == 1 for mode in row["mode"])
        and max(abs(v) for v in row["dq"]) <= 0.08
        and upright(row) >= 0.98
        and max(abs(v) for v in q[:4]) <= 0.30
        and 0.45 <= statistics.mean(q[4:8]) <= 0.75
        and -1.45 <= statistics.mean(q[8:12]) <= -1.05
    )


def fixed_stable(row):
    q = row["q"]
    return (
        all(mode == 1 for mode in row["mode"])
        and max(abs(v) for v in row["dq"]) <= 0.15
        and upright(row) >= 0.96
        and max(abs(v) for v in q[:4]) <= 0.50
        and 0.50 <= statistics.mean(q[4:8]) <= 1.00
        and -2.10 <= statistics.mean(q[8:12]) <= -1.35
        and max(abs(T2[i] - q[i]) for i in range(12)) <= 0.40
    )


def longest_contiguous(rows, gap=0.05):
    groups = []
    current = []
    for row in rows:
        if current and row["t"] - current[-1]["t"] > gap:
            groups.append(current)
            current = []
        current.append(row)
    if current:
        groups.append(current)
    groups = [group for group in groups if group[-1]["t"] - group[0]["t"] >= 0.5]
    return max(groups, key=lambda group: group[-1]["t"] - group[0]["t"]) if groups else []


def summarize(label, rows):
    if not rows:
        raise SystemExit(f"no rows selected for {label}")
    q = [statistics.median(r["q"][i] for r in rows) for i in range(12)]
    tau = [statistics.median(r["tau"][i] for r in rows) for i in range(12)]
    std = [statistics.pstdev(r["q"][i] for r in rows) for i in range(12)]
    pitch = statistics.median(pitch_deg(r) for r in rows)
    return {"label": label, "rows": len(rows), "q": q, "tau": tau,
            "std": std, "pitch": pitch, "t0": rows[0]["t"], "t1": rows[-1]["t"]}


def error(q, target):
    values = [target[i] - q[i] for i in range(12)]
    return max(abs(v) for v in values), math.sqrt(sum(v * v for v in values) / 12), values


def main():
    if len(sys.argv) < 3:
        raise SystemExit("usage: analyze_stand_pose_comparison.py FACTORY_LOG FIXED_LOG [MORE_FIXED_LOG ...]")
    factory_rows = parse(Path(sys.argv[1]))
    fixed_rows = parse(Path(sys.argv[2]))
    factory = summarize("factory", [r for r in factory_rows if factory_stable(r)])
    # Trial-3 has a documented FixedStand window at elapsed 42.5..43.5 s.
    fixed = summarize("fixed_t2", [r for r in fixed_rows if 42.5 <= r["t"] <= 43.5])

    print(f"factory_selected rows={factory['rows']} span={factory['t0']:.2f}..{factory['t1']:.2f}s pitch={factory['pitch']:.3f}deg")
    print(f"fixed_selected rows={fixed['rows']} span={fixed['t0']:.2f}..{fixed['t1']:.2f}s pitch={fixed['pitch']:.3f}deg")
    print("axis,factory_q,factory_tau,fixed_q,fixed_tau,fixed_std,T1,T2,fixed-T1,fixed-T2,kp55_T2_error")
    for i, name in enumerate(NAMES):
        print(f"{name},{factory['q'][i]:.6f},{factory['tau'][i]:.4f},"
              f"{fixed['q'][i]:.6f},{fixed['tau'][i]:.4f},{fixed['std'][i]:.7f},"
              f"{T1[i]:.4f},{T2[i]:.4f},{fixed['q'][i]-T1[i]:+.6f},"
              f"{fixed['q'][i]-T2[i]:+.6f},{55.0*(T2[i]-fixed['q'][i]):+.3f}")
    for label, sample in (("factory", factory), ("fixed", fixed)):
        for target_label, target in (("T1", T1), ("T2", T2)):
            mx, rms, _ = error(sample["q"], target)
            print(f"distance {label}->{target_label}: max={mx:.6f} rms={rms:.6f}")

    print("history: file,rows,span,pitch,max_err_T2,rms_err_T2,max_err_T1,rms_err_T1")
    for name in sys.argv[2:]:
        selected = longest_contiguous([row for row in parse(Path(name)) if fixed_stable(row)])
        if not selected:
            print(f"history {Path(name).name},NO_STABLE_SEGMENT")
            continue
        sample = summarize(Path(name).name, selected)
        t2max, t2rms, _ = error(sample["q"], T2)
        t1max, t1rms, _ = error(sample["q"], T1)
        print(f"history {Path(name).name},{sample['rows']},"
              f"{sample['t0']:.2f}..{sample['t1']:.2f},{sample['pitch']:.3f},"
              f"{t2max:.6f},{t2rms:.6f},{t1max:.6f},{t1rms:.6f}")


if __name__ == "__main__":
    main()
