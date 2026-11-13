#!/usr/bin/env python3
"""R4000 turn-gap independent recomputation (offline, read-only).

Session: 20261113-114335_r4000 (AS2-W, rolling-4000-stage020-research).

Chain audited per policy frame (50 Hz) and final publish (500 Hz):
  stick -> slewed cmd -> obs-filtered physical cmd -> ONNX raw wheels
  -> clip/common/steering -> wrapper mixed wheels (recomputed from source
  math) -> recorded requested/applied targets -> published LowCmd
  (debug_lowcmd, per-slot) -> measured dq / tau_est (2 ms LowState)
  -> IMU gyro_z.

The wheel slot mapping is derived from the session's own published stream
(explicit slot fields) plus forward/backward sign checks and capture
correlation; no external mapping table is trusted.

Usage: recompute.py <session_dir> <out_prefix>
"""
import bisect
import csv
import re
import sys
from pathlib import Path

import numpy as np

SESS = Path(sys.argv[1])
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("turngap")
OUT.mkdir(parents=True, exist_ok=True)
W_PI = 2.0 * np.pi

# ─────────────────────────── loaders ────────────────────────────────────────

def load_policy():
    fr = []
    with (SESS / "debug_policy.csv").open(newline="", encoding="utf-8", errors="replace") as f:
        next(f)
        for r in csv.reader(f):
            if not (r and r[0] == "DEBUG_POLICY"):
                continue
            n = int(r[57]); st = int(r[58 + n])
            raw_s = 59 + n + st
            req_s, app_s = raw_s + 32, raw_s + 96
            fr.append({
                "phase": r[2], "tick": int(r[3]), "age": float(r[4]),
                "vx": float(r[5]), "wz": float(r[7]), "rx": float(r[11]),
                "gyro_z": float(r[17]),
                "quat": np.array([float(x) for x in r[18:22]]),
                "q": np.array([float(x) for x in r[25:41]]),
                "dq": np.array([float(x) for x in r[41:57]]),
                "obs": np.array([float(x) for x in r[58:58 + n]]),
                "raw": np.array([float(x) for x in r[raw_s:raw_s + 16]]),
                "wrap": np.array([float(x) for x in r[raw_s + 16:raw_s + 32]]),
                "req_dq": np.array([float(r[req_s + 4 * (12 + i) + 1]) for i in range(4)]),
                "app_dq": np.array([float(r[app_s + 4 * (12 + i) + 1]) for i in range(4)]),
                "app_q_legs": np.array([float(r[app_s + 4 * i]) for i in range(12)]),
            })
    return fr


def load_lowcmd():
    """Published LowCmd frames: tick + per-slot (mode,q,dq,kp,kd,tau)."""
    rows = []
    with (SESS / "debug_lowcmd.csv").open(newline="", encoding="utf-8", errors="replace") as f:
        next(f)
        for r in csv.reader(f):
            if not (r and r[0] == "DEBUG_LOWCMD" or (r and r[0].startswith("DEBUG_LOWCMD"))):
                continue
            tick = int(r[2])
            per = {}
            ok = True
            for j in range(16):
                b = 5 + 7 * j
                per[int(r[b])] = (int(r[b + 1]), float(r[b + 2]), float(r[b + 3]),
                                  float(r[b + 4]), float(r[b + 5]), float(r[b + 6]))
            if ok and len(per) == 16:
                rows.append((tick, per))
    return rows


def load_capture():
    ticks, age, dq, q, tau, gyro, quat = [], [], [], [], [], [], []
    with (SESS / "low_capture_fast.log").open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.startswith("LOW_SAMPLE,"):
                continue
            r = line.rstrip("\n").split(",")
            if len(r) < 14 + 16 * 6:
                continue
            ticks.append(int(r[4])); age.append(float(r[3]))
            gyro.append(float(r[13])); quat.append([float(x) for x in r[7:11]])
            dq.append([float(r[15 + 6 * i]) for i in range(16)])
            q.append([float(r[14 + 6 * i]) for i in range(16)])
            tau.append([float(r[17 + 6 * i]) for i in range(16)])
    return (np.array(ticks), np.array(age), np.array(dq), np.array(q),
            np.array(tau), np.array(gyro), np.array(quat))


def wrap4pi(x):
    return (x + W_PI) % (4 * np.pi) - W_PI


# ───────────────────── wrapper math recomputed from source ────────────────
# r4000_controller.cpp / as2w_rolling_fixed_exit.rolling_fixed_exit with
# pure_turn_common_scale=0; wheel hold per rolling_wheel_hold
# (latch 0.12 s, per-wheel -6*err clamp +-1.5 /16, no odometry, no settle).

SIDE = np.array([1.0, -1.0, 1.0, -1.0])  # contract wheels FL, FR, RL, RR


def recompute_wheel_targets(raw, physical_cmd, latched, obs_wheel, park_ref):
    vx, wz = physical_cmd[0], physical_cmd[2]
    turning = min(abs(wz) / 0.20, 1.0)
    motion = min(max(abs(vx) / 0.10, turning), 1.0)
    wheel = np.clip(raw[12:16], -1.0, 1.0)
    common = wheel.mean()
    steering = (wheel * SIDE).mean()
    forward_blend = min(abs(vx) / 0.04, 1.0)
    turn_common = common * forward_blend          # pure_turn_common_scale = 0
    linear = vx + 0.10 * turning * turn_common \
        - 0.66 * (1.0 + 0.25 * steering) * wz * SIDE
    wheels = np.clip(linear / (0.086 * 16.0)
                     + 0.035 * motion * (1.0 - turning) * (wheel - common),
                     -6.0, 6.0)
    hold = np.zeros(4)
    if latched:
        err = wrap4pi(obs_wheel - park_ref)
        hold = np.clip(-6.0 * err, -1.5, 1.5) / 16.0
    return wheels + hold, turning, motion, common, steering


def main():
    fr = load_policy()
    lc = load_lowcmd()
    (ct, cage, cdq, cq, ctau, cgyro, cquat) = load_capture()
    walk = [f for f in fr if f["phase"] == "WALK"]
    print(f"policy frames={len(fr)} walk={len(walk)} lowcmd={len(lc)} capture={len(ct)}")

    # ── Step 0a: slot self-derivation from the published stream ────────────
    slot_of_axis = [None] * 16
    slot_mode_kp = {}
    for tick, per in lc[:50] + lc[-50:]:
        for axis in range(16):
            pass
    # contract order -> slot from the first frame
    first = lc[0][1]
    slots_sorted = sorted(first.keys())
    # The 16 entries appear in contract-axis order; map axis i -> slot in entry i
    entries = []
    with (SESS / "debug_lowcmd.csv").open(newline="", encoding="utf-8", errors="replace") as f:
        next(f)
        r = next(csv.reader(f))
        for j in range(16):
            b = 5 + 7 * j
            entries.append((j, int(r[b]), int(r[b + 1])))
    print("published entry order (axis_index_in_file, slot, mode):")
    print("  " + " ".join(f"{j}:s{s}/m{m}" for j, s, m in entries))
    slot_of_axis = {j: s for j, s, _ in entries}  # position j in file -> slot
    # wheels are the last four entries (axis 12..15)
    wheel_slots = [slot_of_axis[j] for j in (12, 13, 14, 15)]
    print(f"wheel entries -> slots: {wheel_slots}")

    # verify: during strong forward frames all four wheel slots' dq > 0
    vt = np.array([f["tick"] for f in walk]); vvx = np.array([f["vx"] for f in walk])
    fwd_i = int(np.argmax(vvx)); bwd_i = int(np.argmin(vvx))
    lct = np.array([t for t, _ in lc])
    for label, ti in (("forward-peak", fwd_i), ("backward-peak", bwd_i)):
        k = bisect.bisect_left(lct, vt[ti])
        per = lc[k][1]
        dqs = {s: per[s][2] for s in wheel_slots}
        print(f"  {label} (vx={vvx[ti]:+.3f}): published wheel dq per slot = "
              f"{ {s: round(v,3) for s,v in dqs.items()} }")

    # capture correlation per wheel slot (published dq vs measured dq)
    pub_by_tick = {t: per for t, per in lc}
    corr = {}
    for s in wheel_slots:
        xs, ys = [], []
        idx = np.searchsorted(ct, lct[:: max(1, len(lct)//4000)])
        for t in lct[:: max(1, len(lct)//4000)]:
            j = np.searchsorted(ct, t)
            if j < len(ct):
                xs.append(pub_by_tick[t][s][2]); ys.append(cdq[j][s])
        if np.std(xs) > 1e-9 and np.std(ys) > 1e-9:
            corr[s] = float(np.corrcoef(xs, ys)[0, 1])
    print(f"  published-vs-measured wheel dq correlation per slot: "
          f"{ {s: round(c,3) for s,c in corr.items()} }")
    return fr, lc, walk, ct, cage, cdq, cq, ctau, cgyro, cquat, wheel_slots


if __name__ == "__main__":
    main()
