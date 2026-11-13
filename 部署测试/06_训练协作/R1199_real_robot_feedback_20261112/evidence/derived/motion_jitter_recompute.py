"""Read-only motion-vs-quiet analysis of the second R1199 robot capture.

Requires numpy and matplotlib. Reads only the exported 10 ms CSV; no DDS/HDC.
The selected windows are in the capture clock, not the publisher clock.
"""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

base = Path(__file__).resolve().parent
source = base / "20261112_r1199_joystick_capture_10ms.csv"
if not source.is_file():
    source = base / "robot_state_10ms.csv"  # standalone teammate package
with source.open(encoding="utf-8", newline="") as handle:
    rows = list(csv.DictReader(handle))

t = np.array([float(r["capture_elapsed_s"]) for r in rows])
dq = np.array([[float(r[f"m{i}_dq"]) for i in range(12)] for r in rows])
tau = np.array([[float(r[f"m{i}_tau_est"]) for i in range(12)] for r in rows])
q = np.array([[float(r[f"m{i}_q"]) for i in range(12)] for r in rows])


def highpass20(x):
    # Subtract a centered 0.20 s average to show rapid changes, not slow gait/pose.
    n = 21
    kernel = np.ones(n) / n
    trend = np.column_stack([np.convolve(x[:, j], kernel, mode="same") for j in range(x.shape[1])])
    return x - trend


def segment(lo, hi):
    mask = (t >= lo) & (t < hi)
    st, sq, sdq, stau = t[mask], q[mask], dq[mask], tau[mask]
    # Trim moving-average edge artifacts before computing the metrics.
    qhp = highpass20(sq)[21:-21]
    tauhp = highpass20(stau)[21:-21]
    return st, sq, sdq, stau, qhp, tauhp


def metrics(label, lo, hi):
    st, sq, sdq, stau, qhp, tauhp = segment(lo, hi)
    values = {
        "window_capture_s": f"{lo}-{hi}",
        "n": len(st),
        "leg_dq_rms_rad_s": float(np.sqrt(np.mean(sdq ** 2))),
        "leg_dq_peak_rad_s": float(np.max(np.abs(sdq))),
        "leg_q_hp_rms_rad": float(np.sqrt(np.mean(qhp ** 2))),
        "leg_tau_hp_rms_Nm": float(np.sqrt(np.mean(tauhp ** 2))),
        "leg_tau_hp_rms_by_motor_Nm": [float(v) for v in np.sqrt(np.mean(tauhp ** 2, axis=0))],
    }
    print(label, values)
    return st, sq, sdq, stau, qhp, tauhp, values


quiet = metrics("quiet_zero", 27, 35)
forward = metrics("sustained_forward", 53, 67)
print("tau_hp_rms_forward_over_quiet", forward[-1]["leg_tau_hp_rms_Nm"] / quiet[-1]["leg_tau_hp_rms_Nm"])

print("sustained_forward 1s windows (capture clock; FR hip and all-leg peaks):")
for start in range(53, 67):
    mask = (t >= start) & (t < start + 1)
    if not mask.any():
        continue
    print(start, "FR_hip_dq_rms", round(float(np.sqrt(np.mean(dq[mask, 0] ** 2))), 4),
          "all_leg_dq_peak", round(float(np.max(np.abs(dq[mask]))), 4),
          "FR_hip_tau_range", round(float(np.ptp(tau[mask, 0])), 4))

# A visible transient oscillation near capture 59.4 s, wholly inside the forward window.
osc = (t >= 59.35) & (t < 59.95)
print("forward_oscillation_capture_59.35_59.95", {
    "FR_hip_dq_peak_rad_s": float(np.max(np.abs(dq[osc, 0]))),
    "FR_hip_tau_range_Nm": float(np.ptp(tau[osc, 0])),
    "all_leg_dq_peak_rad_s": float(np.max(np.abs(dq[osc]))),
})

fig, axs = plt.subplots(3, 1, figsize=(12, 8), sharex=False)
for col, (label, data) in enumerate((("quiet zero", quiet), ("forward rolling", forward))):
    st, sq, sdq, stau, _, _, _ = data
    # Keep the full continuous windows for time-domain inspection.
    sample = (st >= 29) & (st < 33) if col == 0 else (st >= 56) & (st < 60)
    x = st[sample] - st[sample][0]
    color = "tab:blue" if col == 0 else "tab:red"
    axs[0].plot(x, sdq[sample, 0], color=color, alpha=.8, label=label)
    axs[1].plot(x, stau[sample, 0], color=color, alpha=.8, label=label)
    axs[2].plot(x, highpass20(stau)[sample, 0], color=color, alpha=.8, label=label)

axs[0].set_ylabel("FR hip dq (rad/s)")
axs[1].set_ylabel("FR hip tau_est (Nm)")
axs[2].set_ylabel("FR hip tau_est - 0.2s mean (Nm)")
axs[2].set_xlabel("seconds since start of each 4s window")
for ax in axs:
    ax.grid(True, alpha=.3)
    ax.legend()
fig.suptitle("R1199 second robot trial: quiet zero vs sustained forward (10ms LowState)")
fig.tight_layout()
out = base / "20261112_r1199_motion_jitter_evidence.png"
fig.savefig(out, dpi=160)
print("plot", out)
