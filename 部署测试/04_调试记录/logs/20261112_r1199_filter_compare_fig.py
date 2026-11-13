#!/usr/bin/env python3
"""Compact figure for the R1199 filter-comparison report.

Row 1: sliding 1 s thigh-dq 40-120 Hz band power vs time for the three walks,
       with the slewed vx command overlaid; matched windows shaded.
Row 2: FR-thigh requested vs applied q and measured q over the matched backward
       windows (NF vs LP15), showing the 0.126 rad alternation and its removal.
Row 3: LP30 turning chain: wz command vs gyro_z; commanded vs measured wheel
       differential (right minus left).
Axes carry units; no robot access. Usage: fig.py [sessions_root] [out.png]
"""
import sys
import importlib.util
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_here = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "r1199_filter_compare_analysis",
    _here / "20261112_r1199_filter_compare_analysis.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
SESSIONS, WINDOWS = _mod.SESSIONS, _mod.WINDOWS
load_policy, load_capture, band_power = _mod.load_policy, _mod.load_capture, _mod.band_power
THIGH_AXES = _mod.THIGH_AXES

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent / "field_sessions"
OUTPNG = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else Path(__file__).resolve().parent / "20261112_r1199_filter_compare_fig.png"
SLICE, STEP = 500, 250

fig = plt.figure(figsize=(13.5, 10.5))
gs = fig.add_gridspec(3, 3, height_ratios=[1.0, 1.0, 1.0], hspace=0.45, wspace=0.30)
colors = {"NF": "tab:red", "LP15": "tab:blue", "LP30": "tab:green"}

# ── row 1: band power over time ──
for col, (label, name, desc) in enumerate(SESSIONS):
    ax = fig.add_subplot(gs[0, col])
    pol, _ = load_policy(ROOT / name)
    cap, _ = load_capture(ROOT / name)
    walk = [p for p in pol if p["phase"] == "WALK"]
    ct = cap["tick"]; t0w = walk[0]["tick"]
    selw = (ct >= t0w) & (ct <= walk[-1]["tick"])
    dq = cap["dq"][selw][:, [3, 0, 9, 6, 4, 1, 10, 7, 5, 2, 11, 8, 13, 12, 15, 14]]
    tw = ct[selw]
    wtick = np.array([p["tick"] for p in walk])
    vx = np.array([p["vx"] for p in walk])
    ts, es, vxs = [], [], []
    for s in range(0, len(dq) - SLICE + 1, STEP):
        bp = band_power(dq[s:s + SLICE], 500.0, [(40, 120)])
        ts.append((tw[min(s + SLICE // 2, len(tw) - 1)] - t0w) / 1000.0)
        es.append(float(np.mean(bp[(40, 120)][THIGH_AXES])))
        vxs.append(float(vx[np.searchsorted(wtick, tw[min(s + SLICE // 2, len(tw) - 1)])]))
    ts, es, vxs = np.array(ts), np.array(es), np.array(vxs)
    ax.semilogy(ts, es, color=colors[label], lw=1.4, label="thigh dq 40–120 Hz power")
    for wname, shade in (("fwd", "0.85"), ("bwd", "0.7")):
        if (label, wname) in WINDOWS:
            a, b = WINDOWS[(label, wname)]
            ax.axvspan(a * 0.02, b * 0.02, color="orange" if wname == "fwd" else "purple",
                       alpha=0.15, label=f"{wname} window")
    ax2 = ax.twinx()
    ax2.plot(ts, vxs, color="gray", lw=0.8, alpha=0.7, label="vx cmd (m/s)")
    ax2.set_ylabel("vx cmd (m/s)", color="gray")
    ax2.set_ylim(-0.25, 0.25)
    ax.set_xlabel("time since PolicyWalk start (s)")
    ax.set_ylabel("band power (rad$^2$/s$^3$)")
    ax.set_title(f"{label}: {desc}")
    ax.grid(True, which="both", alpha=0.25)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=7, loc="upper right")

# ── row 2: FR-thigh target chain in the matched backward windows ──
pairs = [("NF", "20261112-220051_training-contract", "bwd", 0), ("LP15", "20261112-223732_training-contract", "bwd", 1)]
for label, name, wname, col in pairs:
    ax = fig.add_subplot(gs[1, col])
    pol, _ = load_policy(ROOT / name)
    cap, _ = load_capture(ROOT / name)
    walk = [p for p in pol if p["phase"] == "WALK"]
    a, b = WINDOWS[(label, wname)]
    n = min(b - a, 60)  # 1.2 s view inside the window, skip onset
    a2 = a + 5
    seg = walk[a2:a2 + n]
    t = np.arange(n) * 0.02
    req = np.array([p["req_q"][5] for p in seg])   # FR thigh (contract axis 5)
    app = np.array([p["app_q"][5] for p in seg])
    ct = cap["tick"]
    sel = (ct >= seg[0]["tick"]) & (ct <= seg[-1]["tick"])
    tq = (ct[sel] - seg[0]["tick"]) / 1000.0
    meas = cap["q"][sel][:, 1]  # slot 1 = FR thigh
    ax.step(t, req, where="post", color="tab:orange", lw=1.0, label="requested (pre-filter) q")
    ax.step(t, app, where="post", color="tab:blue", lw=1.2, label="applied (post-filter) q")
    ax.plot(tq, meas, color="k", lw=0.7, alpha=0.7, label="measured q (500 Hz)")
    ax.set_xlabel("time in window (s)")
    ax.set_ylabel("FR thigh angle (rad)")
    ax.set_title(f"{label} backward window: FR-thigh target chain")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.25)
axc = fig.add_subplot(gs[1, 2]); axc.axis("off")
axc.text(0.0, 0.95,
         "Reading guide (backward windows):\n"
         "• NF: requested q alternates ~0.126 rad\n"
         "  every 20 ms (raw ONNX saturating);\n"
         "  applied = requested (no filter);\n"
         "  measured q lags/rings.\n"
         "• LP15: same requested alternation,\n"
         "  applied q smoothed to ≤0.05 rad steps\n"
         "  (τ=40 ms ≈ 2 frames lag),\n"
         "  measured q tracks closely.",
         va="top", fontsize=9, family="monospace")

# ── row 3: LP30 turning chain ──
label, name, _ = SESSIONS[2]
pol, _ = load_policy(ROOT / name)
cap, _ = load_capture(ROOT / name)
walk = [p for p in pol if p["phase"] == "WALK"]
wtick = np.array([p["tick"] for p in walk])
t0w = walk[0]["tick"]
t = (wtick - t0w) / 1000.0
wz = np.array([p["wz"] for p in walk])
gz = np.array([p["gyro_z"] for p in walk])
cmdL = np.array([p["req_dq"][[12, 14]] for p in walk]).mean(axis=1)
cmdR = np.array([p["req_dq"][[13, 15]] for p in walk]).mean(axis=1)
cmd_diff = cmdR - cmdL
ct = cap["tick"]
selw = (ct >= t0w) & (ct <= walk[-1]["tick"])
tc = (ct[selw] - t0w) / 1000.0
mL = cap["dq"][selw][:, [13, 15]].mean(axis=1)
mR = cap["dq"][selw][:, [12, 14]].mean(axis=1)
ax = fig.add_subplot(gs[2, 0])
ax.plot(t, wz, color="tab:blue", lw=1.2, label="wz command (rad/s)")
ax.plot(t, gz, color="tab:red", lw=0.9, alpha=0.8, label="gyro_z (rad/s)")
ax.set_xlabel("time since PolicyWalk start (s)")
ax.set_ylabel("yaw rate (rad/s)")
ax.set_title("LP30: yaw command vs measured gyro_z")
ax.legend(fontsize=8); ax.grid(True, alpha=0.25)
ax = fig.add_subplot(gs[2, 1])
ax.plot(t, cmd_diff, color="tab:blue", lw=1.2, label="commanded wheel Δdq (R−L, rad/s)")
ax.plot(tc, mR - mL, color="tab:red", lw=0.9, alpha=0.8, label="measured wheel Δdq (rad/s)")
ax.set_xlabel("time since PolicyWalk start (s)")
ax.set_ylabel("wheel dq differential (rad/s)")
ax.set_title("LP30: wheel differential cmd vs measured")
ax.legend(fontsize=8); ax.grid(True, alpha=0.25)
ax = fig.add_subplot(gs[2, 2])
yaw = np.unwrap(np.arctan2(2 * (cap["quat"][selw][:, 0] * cap["quat"][selw][:, 3]
                                 + cap["quat"][selw][:, 1] * cap["quat"][selw][:, 2]),
                           1 - 2 * (cap["quat"][selw][:, 2] ** 2 + cap["quat"][selw][:, 3] ** 2)))
ax.plot(tc, np.degrees(yaw - yaw[0]), color="k", lw=1.1, label="integrated yaw (deg)")
ax.set_xlabel("time since PolicyWalk start (s)")
ax.set_ylabel("yaw angle (deg)")
ax.set_title("LP30: accumulated body yaw")
ax.legend(fontsize=8); ax.grid(True, alpha=0.25)

fig.suptitle("R1199 2026-11-12 field sessions: no-filter (NF) vs 40 ms leg-target low-pass (LP15/LP30) — offline log analysis",
             fontsize=11)
fig.savefig(OUTPNG, dpi=140, bbox_inches="tight")
print("wrote", OUTPNG)
