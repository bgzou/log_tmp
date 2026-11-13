#!/usr/bin/env python3
"""R1199 unfiltered vs 40 ms leg-target low-pass: matched-window field-log comparison.

Offline, read-only analysis of the three archived R1199 training-contract field
sessions of 2026-11-12 (joystick trajectories differ, so windows are matched by
actual command before comparing):

  NF     20261112-220051  -Debug -LowPassMs 0   (no filter, ~21 s walk, no yaw input)
  LP15   20261112-223732  -Debug -LowPassMs 40  (15 s walk, no yaw input)
  LP30   20261112-224151  -Debug -LowPassMs 40  (30 s walk, fwd/bwd + yaw inputs)

Clocks are aligned through the LowState tick (1 tick = 1 ms). The policy ran at
50 Hz; debug_lowcmd.csv and low_capture_fast.log are ~500 Hz.

Usage: python3 20261112_r1199_filter_compare_analysis.py [sessions_root] [out_dir]
Defaults: sessions_root = <script_dir>/field_sessions, out_dir = script_dir.
No robot/DDS/CPRO access. Requires numpy+scipy.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import numpy as np
from scipy.signal import welch

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent / "field_sessions"
OUT = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else Path(__file__).resolve().parent

SESSIONS = [
    ("NF", "20261112-220051_training-contract", "no filter (LowPassMs 0)"),
    ("LP15", "20261112-223732_training-contract", "40 ms leg-target LP, 15 s walk"),
    ("LP30", "20261112-224151_training-contract", "40 ms leg-target LP, 30 s walk"),
]

# Contract axis order (deploy.yaml joint_names): FL/FR/RL/RR hip(0-3), thigh(4-7),
# calf(8-11), wheels(12-15)=FL,FR,RL,RR. Slots: FR=(0,1,2) FL=(3,4,5) RR=(6,7,8)
# RL=(9,10,11), wheels FR=12 FL=13 RR=14 RL=15 (config/r152_measured.map).
CONTRACT_TO_SLOT = [3, 0, 9, 6, 4, 1, 10, 7, 5, 2, 11, 8, 13, 12, 15, 14]
SLOT_TO_CONTRACT = {s: i for i, s in enumerate(CONTRACT_TO_SLOT)}
THIGH_AXES, CALF_AXES, HIP_AXES = [4, 5, 6, 7], [8, 9, 10, 11], [0, 1, 2, 3]
WHEEL_AXES = [12, 13, 14, 15]
LEFT_WHEELS, RIGHT_WHEELS = [12, 14], [13, 15]        # contract FL,RL / FR,RR
WHEEL_SLOTS_LEFT, WHEEL_SLOTS_RIGHT = [13, 15], [12, 14]

# Matched motion windows as WALK-frame ranges (20 ms/frame), chosen by the rule
# "continuous |vx|>=0.08 m/s for >=0.5 s, longest per direction" (candidates are
# listed in the integrity output). All three sessions clamp to the same policy
# command (obs planar clamp 0.10 m/s, see report), so the small slewed-command
# differences do not change what the policy sees in steady state.
WINDOWS = {
    ("NF", "fwd"): (833, 862), ("NF", "bwd"): (572, 642), ("NF", "quiet"): (957, 1053),
    ("LP15", "fwd"): (252, 355), ("LP15", "bwd"): (533, 735), ("LP15", "quiet"): (0, 174),
    ("LP30", "fwd"): (1061, 1131), ("LP30", "bwd"): (1161, 1244), ("LP30", "quiet"): (902, 961),
}
SLICE, STEP = 500, 250   # 1 s sliding spectral slices at 500 Hz, 50% overlap


def pct(x, q):
    return float(np.percentile(x, q)) if len(x) else float("nan")


def segments(mask, min_len):
    idx = np.flatnonzero(mask)
    if len(idx) == 0:
        return []
    breaks = np.flatnonzero(np.diff(idx) > 1)
    starts = np.r_[idx[0], idx[breaks + 1]]
    ends = np.r_[idx[breaks], idx[-1]]
    return [(int(a), int(b)) for a, b in zip(starts, ends) if b - a + 1 >= min_len]


def load_policy(d: Path):
    frames, bad = [], 0
    with (d / "debug_policy.csv").open(newline="", encoding="utf-8", errors="replace") as f:
        next(f)
        for row in csv.reader(f):
            try:
                if not row or row[0] != "DEBUG_POLICY":
                    continue
                obs_count = int(row[57])
                state_count = int(row[58 + obs_count])
                if len(row) != 58 + obs_count + 1 + state_count + 16 + 16 + 64 + 64 \
                        or obs_count != 65 or state_count != 0:
                    bad += 1
                    continue
                raw_s = 59 + obs_count + state_count
                req_s, app_s = raw_s + 32, raw_s + 96
                g = lambda i: float(row[i])
                frames.append({
                    "mono": int(row[1]), "phase": row[2], "tick": int(row[3]),
                    "vx": g(5), "vy": g(6), "wz": g(7), "rx": g(11), "ly": g(14),
                    "gyro_z": g(17), "quat": np.array([g(i) for i in range(18, 22)]),
                    "sensor_q": np.array([g(i) for i in range(25, 41)]),
                    "sensor_dq": np.array([g(i) for i in range(41, 57)]),
                    "obs": np.array([g(i) for i in range(58, 58 + obs_count)]),
                    "raw": np.array([g(i) for i in range(raw_s, raw_s + 16)]),
                    "wrapped": np.array([g(i) for i in range(raw_s + 16, raw_s + 32)]),
                    "req_q": np.array([g(req_s + 4 * i) for i in range(16)]),
                    "req_dq": np.array([g(req_s + 4 * i + 1) for i in range(16)]),
                    "req_kp": np.array([g(req_s + 4 * i + 2) for i in range(16)]),
                    "req_kd": np.array([g(req_s + 4 * i + 3) for i in range(16)]),
                    "app_q": np.array([g(app_s + 4 * i) for i in range(16)]),
                    "app_dq": np.array([g(app_s + 4 * i + 1) for i in range(16)]),
                    "app_kp": np.array([g(app_s + 4 * i + 2) for i in range(16)]),
                    "app_kd": np.array([g(app_s + 4 * i + 3) for i in range(16)]),
                })
            except (ValueError, IndexError):
                bad += 1
    return frames, bad


def load_lowcmd(d: Path):
    rows, bad = [], 0
    with (d / "debug_lowcmd.csv").open(newline="", encoding="utf-8", errors="replace") as f:
        next(f)
        for row in csv.reader(f):
            try:
                if not row or row[0] != "DEBUG_LOWCMD" or len(row) != 5 + 16 * 7:
                    bad += 1
                    continue
                q = np.zeros(16); dq = np.zeros(16); kp = np.zeros(16); kd = np.zeros(16)
                for j in range(16):
                    b = 5 + 7 * j
                    c = SLOT_TO_CONTRACT[int(row[b])]
                    q[c], dq[c], kp[c], kd[c] = float(row[b + 2]), float(row[b + 3]), float(row[b + 4]), float(row[b + 5])
                rows.append({"mono": int(row[1]), "tick": int(row[2]), "state": int(row[3]),
                             "q": q, "dq": dq, "kp": kp, "kd": kd})
            except (ValueError, IndexError):
                bad += 1
    return rows, bad


def load_capture(d: Path):
    ticks, ms, gyro, quat, q, dq, tau = [], [], [], [], [], [], []
    short = 0
    with (d / "low_capture_fast.log").open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.startswith("LOW_SAMPLE,"):
                continue
            row = line.rstrip("\n").split(",")
            if len(row) < 14 + 16 * 6:
                short += 1
                continue
            try:
                ticks.append(int(row[4])); ms.append(float(row[1]))
                gyro.append([float(row[11]), float(row[12]), float(row[13])])
                quat.append([float(x) for x in row[7:11]])
                q.append([float(row[14 + 6 * i]) for i in range(16)])
                dq.append([float(row[15 + 6 * i]) for i in range(16)])
                tau.append([float(row[17 + 6 * i]) for i in range(16)])
            except ValueError:
                short += 1
    return {"tick": np.array(ticks, dtype=np.int64), "ms": np.array(ms), "gyro": np.array(gyro),
            "quat": np.array(quat), "q": np.array(q), "dq": np.array(dq), "tau": np.array(tau)}, short


def load_protection(d: Path):
    n = nz = 0
    with (d / "low_protection.log").open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.startswith("PROTECT,") or "low_count=" not in line:
                continue
            n += 1
            for field in ("warning_or", "motorstate_or"):
                m = re.search(rf"{field}=0x([0-9a-fA-F]+)", line)
                if m and int(m.group(1), 16):
                    nz += 1
                    break
    return n, nz


def load_policy_diag(d: Path):
    rows = []
    with (d / "policy_diag.log").open(encoding="utf-8", errors="replace") as f:
        next(f)
        for line in f:
            if not line.startswith("POLICY_DIAG,"):
                continue
            r = line.rstrip("\n").split(",")
            try:
                rows.append({"phase": r[1], "t": float(r[2]), "vx": float(r[3]), "wz": float(r[5]),
                             "tick": int(r[6]), "hold": float(r[-1]), "bias_scale": float(r[-2]),
                             "bias": np.array([float(x) for x in r[-14:-2]])})
            except (ValueError, IndexError):
                pass
    return rows


def band_power(x, fs, bands, nperseg=None):
    n = len(x)
    if n < 64:
        return {b: np.full(x.shape[1], np.nan) for b in bands}
    if nperseg is None:
        nperseg = min(2048, n)
    f, p = welch(x - x.mean(axis=0), fs=fs, window="hann", nperseg=nperseg,
                 noverlap=nperseg // 2, axis=0)
    out = {}
    for lo, hi in bands:
        sel = (f >= lo) & (f <= hi)
        out[(lo, hi)] = np.trapz(p[sel], f[sel], axis=0) if sel.any() else np.full(x.shape[1], np.nan)
    return out


def yaw_of(quat_wxyz):
    w, x, y, z = (quat_wxyz[:, i] for i in range(4))
    return np.arctan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))


def main():
    R = []          # report lines
    INTEG = []      # integrity lines
    win_rows, hf_rows, turn_rows, bandtime, slice_rows = [], [], [], [], []

    def say(*a):
        R.append(" ".join(str(x) for x in a))

    data = {}
    # ── pass 1: load + integrity + filter-scope verification ──────────────
    for label, name, desc in SESSIONS:
        d = ROOT / name
        if not d.is_dir():
            raise SystemExit(f"missing session dir {d}")
        pol, bad_pol = load_policy(d)
        lcm, bad_lcm = load_lowcmd(d)
        cap, short_cap = load_capture(d)
        prot_n, prot_nz = load_protection(d)
        diag = load_policy_diag(d)
        walk = [p for p in pol if p["phase"] == "WALK"]
        data[label] = {"dir": d, "name": name, "desc": desc, "pol": pol, "walk": walk,
                       "lcm": lcm, "cap": cap, "diag": diag}

        wmono = np.array([p["mono"] for p in walk], dtype=np.int64)
        wdt = np.diff(wmono) / 1e6
        lmono = np.array([r["mono"] for r in lcm], dtype=np.int64)
        ldt = np.diff(lmono) / 1e6
        ct = cap["tick"]
        cover = int(((ct >= walk[0]["tick"]) & (ct <= walk[-1]["tick"])).sum())
        span = walk[-1]["tick"] - walk[0]["tick"]
        il = [
            f"== {label}  {name}  ({desc})",
            f"debug_policy: valid={len(pol)} bad={bad_pol} phases="
            f"{ {k: sum(p['phase'] == k for p in pol) for k in sorted(set(p['phase'] for p in pol))} }",
            f"walk: frames={len(walk)} tick=[{walk[0]['tick']}..{walk[-1]['tick']}] "
            f"dt_ms p50={pct(wdt,50):.3f} p99={pct(wdt,99):.3f} max={wdt.max():.3f} gaps>40ms={(wdt>40).sum()}",
            f"debug_lowcmd: valid={len(lcm)} bad={bad_lcm} dt_ms p50={pct(ldt,50):.3f} "
            f"p99={pct(ldt,99):.3f} max={ldt.max():.3f} gaps>40ms={(ldt>40).sum()}",
            f"low_capture: valid={len(ct)} short_ignored={short_cap} tick=[{ct[0]}..{ct[-1]}] "
            f"rows_in_walk={cover} ({cover/max(1,span)*1000:.0f} Hz over {span} ms walk span)",
            f"low_protection: complete_rows={prot_n} nonzero_warn_or_motorstate={prot_nz}",
            f"policy_diag rows={len(diag)}",
        ]
        # numerical filter-scope verification
        req_dq_w = np.array([p["req_dq"][WHEEL_AXES] for p in walk])
        app_dq_w = np.array([p["app_dq"][WHEEL_AXES] for p in walk])
        d_wheel = float(np.max(np.abs(req_dq_w - app_dq_w)))
        d_kp = float(np.max(np.abs(np.array([p["req_kp"] for p in walk]) - np.array([p["app_kp"] for p in walk]))))
        d_kd = float(np.max(np.abs(np.array([p["req_kd"] for p in walk]) - np.array([p["app_kd"] for p in walk]))))
        d_leg = float(np.max(np.abs(np.array([p["req_q"][:, ] if False else p["req_q"][:12] for p in walk])
                                    - np.array([p["app_q"][:12] for p in walk]))))
        pa_err = [float(np.max(np.abs(b["obs"][42:58] - np.clip(a["wrapped"], -6, 6))))
                  for a, b in zip(walk[:-1], walk[1:]) if b["tick"] - a["tick"] <= 40]
        il.append(f"filter-scope check: max|req-app| wheel dq={d_wheel:.2e} kp={d_kp:.2e} kd={d_kd:.2e}; "
                  f"leg-q |req-app| max={d_leg:.4f} rad; obs previous-action vs wrapped(k-1) max err={max(pa_err):.2e}")
        vx = np.array([p["vx"] for p in walk]); wz = np.array([p["wz"] for p in walk])
        pcmd = np.array([p["obs"][0] + 0.4 for p in walk])
        cands = []
        for nm, mask in (("fwd", vx >= 0.08), ("bwd", vx <= -0.08),
                         ("quiet", (np.abs(vx) < 0.005) & (np.abs(wz) < 0.005)),
                         ("yaw+", wz >= 0.03), ("yaw-", wz <= -0.03)):
            for a, b in segments(mask, 20):
                cands.append(f"{nm}[{a}:{b}] n={b-a+1} vx={vx[a:b+1].mean():+.3f} wz={wz[a:b+1].mean():+.3f}")
        il.append("candidate segments (rule |vx|>=0.08 or |wz|>=0.03, >=0.4 s): " + "; ".join(cands))
        il.append(f"command clamp: slewed vx range [{vx.min():+.3f},{vx.max():+.3f}] but obs-filtered "
                  f"(policy-visible) physical_cmd range [{pcmd.min():+.3f},{pcmd.max():+.3f}] "
                  f"(planar clamp 0.10 m/s in as2w r284_observations.hpp Observations::push)")
        INTEG.append("\n".join(il))

    # ── pass 2: matched-window chain metrics ──────────────────────────────
    say("=" * 104)
    say("R1199 field-log comparison: NF (no filter) vs LP15/LP30 (40 ms leg-target low-pass, wheels unfiltered)")
    say("sessions: NF=20261112-220051, LP15=20261112-223732, LP30=20261112-224151; WALK-frame windows,")
    say("tick ranges quoted for the 2 ms logs; policy command visible to ONNX is clamped to 0.10 m/s planar,")
    say("so all |vx|>=0.10 windows present the same command to the policy in steady state.")
    say("=" * 104)
    for label, name, desc in SESSIONS:
        walk = data[label]["walk"]
        cap = data[label]["cap"]
        ct = cap["tick"]
        for wname in ("fwd", "bwd", "quiet"):
            a, b = WINDOWS[(label, wname)]
            seg = walk[a:b + 1]
            t0, t1 = seg[0]["tick"], seg[-1]["tick"]
            raw = np.array([p["raw"] for p in seg])
            reqq = np.array([p["req_q"] for p in seg])
            appq = np.array([p["app_q"] for p in seg])
            sensq = np.array([p["sensor_q"] for p in seg])
            steps = lambda arr: np.max(np.abs(np.diff(arr, axis=0)), axis=1)
            s_req, s_app = steps(reqq[:, :12]), steps(appq[:, :12])
            s_raw = steps(raw[:, :12])
            lag = np.abs(appq[:, :12] - reqq[:, :12])
            track = np.abs(appq[:, :12] - sensq[:, :12])
            lt = np.array([r["tick"] for r in data[label]["lcm"]])
            sel = (lt >= t0) & (lt <= t1)
            lq = np.array([data[label]["lcm"][i]["q"] for i in np.flatnonzero(sel)])
            s_lcm = steps(lq[:, :12]) if len(lq) > 2 else np.array([np.nan])
            sgn = np.sign(raw[:, :12])
            flip = float(np.mean((sgn[1:] != sgn[:-1]) & (sgn[1:] != 0) & (sgn[:-1] != 0)))
            pcmd = np.array([p["obs"][0] + 0.4 for p in seg])
            cmdw = np.array([p["req_dq"][12:16] for p in seg])
            selc = (ct >= t0) & (ct <= t1)
            measw = cap["dq"][selc][:, WHEEL_SLOTS_LEFT + WHEEL_SLOTS_RIGHT] \
                if selc.any() else np.zeros((1, 4))
            row = {
                "session": label, "window": wname, "frames": b - a + 1, "tick0": t0, "tick1": t1,
                "vx_slewed_mean": float(np.mean([p["vx"] for p in seg])),
                "physical_cmd_mean": float(pcmd.mean()),
                "wz_mean": float(np.mean([p["wz"] for p in seg])),
                "raw_leg_step_p50": pct(s_raw, 50), "raw_leg_step_p99": pct(s_raw, 99),
                "raw_sat_frac_ge5.9": float(np.mean(np.abs(raw[:, :12]) >= 5.9)),
                "raw_signflip_rate": flip,
                "req_step_p50": pct(s_req, 50), "req_step_p95": pct(s_req, 95),
                "req_step_p99": pct(s_req, 99), "req_step_max": float(np.max(s_req)),
                "app_step_p50": pct(s_app, 50), "app_step_p95": pct(s_app, 95),
                "app_step_p99": pct(s_app, 99), "app_step_max": float(np.max(s_app)),
                "lowcmd_step_p99": pct(s_lcm, 99), "lowcmd_step_max": float(np.max(s_lcm)),
                "lag_mean_rad": float(lag.mean()), "lag_max_rad": float(lag.max()),
                "track_applied_mean_rad": float(track.mean()), "track_applied_max_rad": float(track.max()),
                "wheel_cmd_common_rad_s": float(cmdw.mean()),
                "wheel_meas_common_rad_s": float(measw.mean()) if selc.any() else float("nan"),
            }
            win_rows.append(row)
            say(f"[{label} {wname}] frames={b-a+1} tick={t0}..{t1} "
                f"vx_slewed={row['vx_slewed_mean']:+.3f} physical_cmd={row['physical_cmd_mean']:+.4f} "
                f"wz={row['wz_mean']:+.4f}")
            say(f"    raw leg step p50/p99={row['raw_leg_step_p50']:.2f}/{row['raw_leg_step_p99']:.2f} "
                f"(actuator limit 12); |raw|>=5.9 frac={row['raw_sat_frac_ge5.9']:.3f}; "
                f"sign-flip rate={row['raw_signflip_rate']:.2f}/frame")
            say(f"    requested leg-q step rad p50/p95/p99/max = {row['req_step_p50']:.4f}/"
                f"{row['req_step_p95']:.4f}/{row['req_step_p99']:.4f}/{row['req_step_max']:.4f}")
            say(f"    applied  leg-q step rad p50/p95/p99/max = {row['app_step_p50']:.4f}/"
                f"{row['app_step_p95']:.4f}/{row['app_step_p99']:.4f}/{row['app_step_max']:.4f}")
            say(f"    final LowCmd q step (500 Hz) p99/max = {row['lowcmd_step_p99']:.4f}/"
                f"{row['lowcmd_step_max']:.4f}; |applied-req| mean/max = {row['lag_mean_rad']:.4f}/"
                f"{row['lag_max_rad']:.4f}; |applied-meas q| mean = {row['track_applied_mean_rad']:.4f}")
            say(f"    wheel cmd common={row['wheel_cmd_common_rad_s']:+.3f} measured={row['wheel_meas_common_rad_s']:+.3f} "
                f"rad/s (body-speed proxy {0.086*row['wheel_meas_common_rad_s']:+.3f} m/s)")
            say("")

    # ── pass 3: 2 ms feedback HF on matched windows + slice classification ─
    say("=" * 104)
    say("2 ms LowState feedback, matched windows and 1 s sliding slices (Welch, Hann, fs=500 Hz,")
    say("detrend=mean; dq quantization 2*pi/2048 = 0.00307 rad/s dominates the quiet floor).")
    say("=" * 104)
    BANDS = [(40, 120), (120, 250)]
    for label, name, desc in SESSIONS:
        walk = data[label]["walk"]
        cap = data[label]["cap"]
        ct = cap["tick"]
        t0w = walk[0]["tick"]
        vx = np.array([p["vx"] for p in walk]); wz = np.array([p["wz"] for p in walk])
        wtick = np.array([p["tick"] for p in walk])
        selw = (ct >= t0w) & (ct <= walk[-1]["tick"])
        dq_all = cap["dq"][selw][:, CONTRACT_TO_SLOT]
        tau_all = cap["tau"][selw][:, CONTRACT_TO_SLOT]
        tw = ct[selw]
        # per-window full-range Welch on middle 1 s
        for wname in ("fwd", "bwd", "quiet"):
            a, b = WINDOWS[(label, wname)]
            t0, t1 = walk[a]["tick"], walk[b]["tick"]
            sel = (ct >= t0) & (ct <= t1)
            dq = cap["dq"][sel][:, CONTRACT_TO_SLOT]
            tau = cap["tau"][sel][:, CONTRACT_TO_SLOT]
            n = len(dq)
            if n < 64:
                continue
            mid = n // 2
            lo, hi = max(0, mid - 250), min(n, mid + 250)
            bp = band_power(dq[lo:hi], 500.0, BANDS)
            bp2 = band_power(tau[lo:hi], 500.0, BANDS)
            for group, axes in (("thigh", THIGH_AXES), ("calf", CALF_AXES), ("hip", HIP_AXES), ("wheel", WHEEL_AXES)):
                for blo, bhi in BANDS:
                    hf_rows.append({"session": label, "window": wname, "group": group,
                                    "band": f"{blo}-{bhi}Hz", "n": hi - lo,
                                    "dq_band_power_mean": float(np.mean(bp[(blo, bhi)][axes])),
                                    "dq_band_power_max_axis": float(np.max(bp[(blo, bhi)][axes])),
                                    "tau_band_power_mean": float(np.mean(bp2[(blo, bhi)][axes])),
                                    "dq_rms_mean": float(np.sqrt(np.mean(dq[lo:hi][:, axes] ** 2))),
                                    "dq_peak": float(np.max(np.abs(dq[lo:hi][:, axes]))),
                                    "tau_rms_mean": float(np.sqrt(np.mean(tau[lo:hi][:, axes] ** 2))),
                                    "tau_peak": float(np.max(np.abs(tau[lo:hi][:, axes])))})
            say(f"[{label} {wname}] n={n} (middle 1 s): thigh dq 40-120Hz={np.mean(bp[(40,120)][THIGH_AXES]):.3e}, "
                f"120-250Hz={np.mean(bp[(120,250)][THIGH_AXES]):.3e}; calf 40-120Hz={np.mean(bp[(40,120)][CALF_AXES]):.3e}; "
                f"wheel 40-120Hz={np.mean(bp[(40,120)][WHEEL_AXES]):.3e} (rad^2/s^3)")
            say(f"    thigh dq RMS={np.sqrt(np.mean(dq[lo:hi][:, THIGH_AXES]**2)):.4f} rad/s "
                f"peak={np.max(np.abs(dq[lo:hi][:, THIGH_AXES])):.4f}; thigh tau RMS="
                f"{np.sqrt(np.mean(tau[lo:hi][:, THIGH_AXES]**2)):.3f} Nm, tau 40-120Hz={np.mean(bp2[(40,120)][THIGH_AXES]):.3e} (Nm^2/s)")
        # sliding-slice classification over the whole walk
        buckets = {}
        for s in range(0, max(0, len(dq_all) - SLICE + 1), STEP):
            ta, tb = tw[s], tw[s + SLICE - 1]
            fa, fb = np.searchsorted(wtick, ta), np.searchsorted(wtick, tb)
            if fb - fa < 20:
                continue
            svx, swz = vx[fa:fb + 1], wz[fa:fb + 1]
            if np.abs(svx).max() < 0.005 and np.abs(swz).max() < 0.005:
                cls = "quiet"
            elif np.abs(svx).min() >= 0.08 and np.abs(svx).max() <= 0.21 and np.abs(swz).max() < 0.02:
                cls = "steady"
            else:
                cls = "transient"
            bp = band_power(dq_all[s:s + SLICE], 500.0, [(40, 120)])
            bp2 = band_power(tau_all[s:s + SLICE], 500.0, [(40, 120)])
            buckets.setdefault(cls, []).append({
                "t_start_s": (ta - t0w) / 1000.0, "vx_mean": float(svx.mean()),
                "thigh": float(np.mean(bp[(40, 120)][THIGH_AXES])),
                "calf": float(np.mean(bp[(40, 120)][CALF_AXES])),
                "wheel": float(np.mean(bp[(40, 120)][WHEEL_AXES])),
                "thigh_tau": float(np.mean(bp2[(40, 120)][THIGH_AXES]))})
        say(f"[{label}] sliding 1 s slices (0.5 s step):")
        for cls in ("steady", "transient", "quiet"):
            if cls not in buckets:
                say(f"    {cls:9s}: none")
                continue
            b = buckets[cls]
            th = np.array([x["thigh"] for x in b]); tt = np.array([x["thigh_tau"] for x in b])
            worst = b[int(np.argmax(th))]
            say(f"    {cls:9s}: n={len(b):2d} thigh 40-120Hz median={np.median(th):.3e} "
                f"max={th.max():.3e} | tau median={np.median(tt):.3e} | worst slice t={worst['t_start_s']:.1f}s vx={worst['vx_mean']:+.3f}")
            for x in b:
                slice_rows.append({"session": label, "class": cls, **x})
        # bandtime for the plot
        for s in range(0, max(0, len(dq_all) - SLICE + 1), STEP):
            bp = band_power(dq_all[s:s + SLICE], 500.0, [(40, 120)])
            tm = tw[min(s + SLICE // 2, len(tw) - 1)]
            fa = np.searchsorted(wtick, tm)
            bandtime.append({"session": label, "t_ms": int(tm - t0w),
                             "vx": float(vx[fa]), "wz": float(wz[fa]),
                             "thigh_dq_40_120": float(np.mean(bp[(40, 120)][THIGH_AXES])),
                             "calf_dq_40_120": float(np.mean(bp[(40, 120)][CALF_AXES])),
                             "thigh_dq_rms": float(np.sqrt(np.mean(dq_all[s:s + SLICE][:, THIGH_AXES] ** 2)))})
        say("")

    # ── pass 4: turning chain (LP30) ─────────────────────────────────────
    say("=" * 104)
    say("Turning chain (LP30; NF/LP15 had no yaw input): rx -> wz cmd -> wrapper wheel injection ->")
    say("requested wheel dq -> measured wheel dq (2 ms) -> gyro_z / integrated yaw. URDF track=0.331 m;")
    say("if wheels tracked the injected differential and rolled, yaw would be 2*0.66*wz/0.331 = 3.99*wz.")
    say("=" * 104)
    label = "LP30"
    walk = data[label]["walk"]
    cap = data[label]["cap"]
    ct = cap["tick"]
    vx = np.array([p["vx"] for p in walk]); wz = np.array([p["wz"] for p in walk])
    rx = np.array([p["rx"] for p in walk])
    say(f"joystick rx range [{rx.min():+.3f},{rx.max():+.3f}]; wz cmd range [{wz.min():+.3f},{wz.max():+.3f}]")
    for nm, mask in (("yaw+", wz >= 0.03), ("yaw-", wz <= -0.03)):
        for a, b in segments(mask, 20):
            if abs(vx[a:b + 1].mean()) > 0.05:
                continue
            t0, t1 = walk[a]["tick"], walk[b]["tick"]
            sel = (ct >= t0) & (ct <= t1)
            cmdL = np.array([p["req_dq"][LEFT_WHEELS] for p in walk[a:b + 1]])
            cmdR = np.array([p["req_dq"][RIGHT_WHEELS] for p in walk[a:b + 1]])
            cmd_diff = float((cmdR.mean(axis=1) - cmdL.mean(axis=1)).mean())
            measL = cap["dq"][sel][:, WHEEL_SLOTS_LEFT]
            measR = cap["dq"][sel][:, WHEEL_SLOTS_RIGHT]
            meas_diff = float((measR.mean(axis=1) - measL.mean(axis=1)).mean())
            gz = float(np.mean([p["gyro_z"] for p in walk[a:b + 1]]))
            yaw = yaw_of(cap["quat"][sel])
            dyaw = float(np.rad2deg(yaw[-1] - yaw[0]))
            dur = (t1 - t0) / 1000.0
            wtauL = float(cap["tau"][sel][:, WHEEL_SLOTS_LEFT].mean())
            wtauR = float(cap["tau"][sel][:, WHEEL_SLOTS_RIGHT].mean())
            raw = np.array([p["raw"] for p in walk[a:b + 1]])
            wr = np.clip(raw[:, 12:16], -1, 1)
            side = np.array([1.0, -1.0, 1.0, -1.0])
            appq = np.array([p["app_q"] for p in walk[a:b + 1]])
            asym = float(np.mean(np.abs(appq[:, [0, 2, 4, 6, 8, 10]].mean(axis=0)
                                        - appq[:, [1, 3, 5, 7, 9, 11]].mean(axis=0))))
            turn_rows.append({"seg": f"{nm}[{a}:{b}]", "dur_s": dur,
                              "wz_cmd_mean": float(wz[a:b+1].mean()), "cmd_wheel_diff": cmd_diff,
                              "meas_wheel_diff": meas_diff, "gyro_z_mean": gz,
                              "yaw_deg_total": dyaw, "yaw_rate_deg_s": dyaw / dur,
                              "wheel_tau_left_mean": wtauL, "wheel_tau_right_mean": wtauR,
                              "leg_target_LR_asym": asym,
                              "onnx_wheel_common": float(wr.mean()),
                              "onnx_wheel_steering": float((wr * side).mean(axis=1).mean())})
            say(f"[{nm} {a}:{b}] dur={dur:.2f}s wz_cmd={wz[a:b+1].mean():+.4f} rad/s")
            say(f"    wheel dq diff cmd(R-L)={cmd_diff:+.3f} measured={meas_diff:+.3f} rad/s "
                f"(tracking gain {meas_diff/cmd_diff:.2f}); wheel tau L={wtauL:+.2f} R={wtauR:+.2f} Nm")
            say(f"    gyro_z mean={gz:+.4f} rad/s ({gz/wz[a:b+1].mean()*100:.0f}% of cmd); "
                f"integrated yaw={dyaw:+.2f} deg ({dyaw/dur:+.2f} deg/s)")
            say(f"    ONNX wheel common={wr.mean():+.3f} steering={np.mean((wr*side).mean(axis=1)):+.3f} "
                f"(no differential signal from policy); leg-target L/R asym={asym:.4f} rad")
    # fwd/bwd asymmetry reference
    for wname, a, b in (("fwd", *WINDOWS[("LP30", "fwd")]), ("bwd", *WINDOWS[("LP30", "bwd")])):
        appq = np.array([p["app_q"] for p in walk[a:b + 1]])
        asym = float(np.mean(np.abs(appq[:, [0, 2, 4, 6, 8, 10]].mean(axis=0)
                                    - appq[:, [1, 3, 5, 7, 9, 11]].mean(axis=0))))
        say(f"    reference {wname} leg-target L/R asym={asym:.4f} rad (straight-motion gait asymmetry)")

    # ── pass 5: posture / transitions ────────────────────────────────────
    say("")
    say("=" * 104)
    say("Posture and phase transitions")
    say("=" * 104)
    for label, name, desc in SESSIONS:
        walk = data[label]["walk"]
        pol = data[label]["pol"]
        lcm = data[label]["lcm"]
        diag = data[label]["diag"]
        vx = np.array([p["vx"] for p in walk]); wz = np.array([p["wz"] for p in walk])
        appq = np.array([p["app_q"] for p in walk])
        sensq = np.array([p["sensor_q"] for p in walk])
        steps_all = np.max(np.abs(np.diff(appq[:, :12], axis=0)), axis=1)
        nz = np.flatnonzero((np.abs(vx) > 0.01) | (np.abs(wz) > 0.01))
        first = int(nz[0]) if len(nz) else -1
        lo, hi = max(0, first - 50), min(len(walk) - 1, first + 50)
        say(f"[{label}] first nonzero cmd at walk frame {first} (t={first*0.02:.2f}s); max applied leg-q step "
            f"within +/-1 s = {steps_all[lo:hi].max():.4f} rad; whole-walk applied step p99/max = "
            f"{pct(steps_all,99):.4f}/{steps_all.max():.4f} rad")
        thf = sensq[:, [4, 5]].mean(axis=1); thr = sensq[:, [6, 7]].mean(axis=1)
        say(f"    posture F/R thigh mean over walk = {thf.mean():.3f}/{thr.mean():.3f}; "
            f"quiet-start settled F-thigh (frames 100-170) = {thf[100:170].mean():.3f}; "
            f"ranges F [{thf.min():.3f},{thf.max():.3f}] R [{thr.min():.3f},{thr.max():.3f}]")
        hand = [p for p in pol if p["phase"] == "HANDOFF"]
        hq = np.array([p["sensor_q"] for p in hand])
        say(f"    handoff thigh F {hq[0][4]:.3f}->{hq[-1][4]:.3f}, calf F {hq[0][8]:.3f}->{hq[-1][8]:.3f} "
            f"(identical 2 s interpolation in all sessions)")
        post = [r for r in lcm if r["tick"] > walk[-1]["tick"]]
        if post:
            pq = np.array([r["q"] for r in post])
            brake0 = pq[0][4:6].mean()
            say(f"    post-walk (Brake/ReturnStand/FixSquat): F-thigh mean {brake0:.3f} -> min "
                f"{pq[:, 4:6].mean(axis=1).min():.3f} -> final {pq[-1][4:6].mean():.3f} "
                f"(sink below brake-start level = {brake0 - pq[:, 4:6].mean(axis=1).min():+.3f} rad)")
        wd = [r for r in diag if r["phase"] == "WALK"]
        hs = np.array([r["hold"] for r in wd]); bs = np.array([r["bias_scale"] for r in wd])
        b150 = wd[150]["bias"] if len(wd) > 150 else wd[-1]["bias"]
        say(f"    stand-bias frozen values (frame 150) thigh F/L={b150[4]:+.3f} F/R={b150[5]:+.3f} "
            f"R/L={b150[6]:+.3f} R/R={b150[7]:+.3f}; bias_scale range [{bs.min():.3f},{bs.max():.3f}]")

    # ── write outputs ────────────────────────────────────────────────────
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "20261112_r1199_filter_compare_integrity.txt").write_text("\n\n".join(INTEG) + "\n", encoding="utf-8")
    (OUT / "20261112_r1199_filter_compare_analysis.txt").write_text("\n".join(R) + "\n", encoding="utf-8")
    for fname, rows in (("20261112_r1199_filter_compare_windows.csv", win_rows),
                        ("20261112_r1199_filter_compare_hf_bands.csv", hf_rows),
                        ("20261112_r1199_filter_compare_turning.csv", turn_rows),
                        ("20261112_r1199_filter_compare_bandtime.csv", bandtime),
                        ("20261112_r1199_filter_compare_slices.csv", slice_rows)):
        with (OUT / fname).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
    print("wrote outputs to", OUT)


if __name__ == "__main__":
    main()
