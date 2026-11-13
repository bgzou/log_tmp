#!/usr/bin/env python3
"""R4000 field-session turn/forward analysis (offline, from the package data).

Reproduces every number quoted in report/R4000_0.4m与转向实机分析_20261113.md
from data/20261113-114335_r4000/debug_policy.csv and the 2 ms capture
extracts. Usage: python3 turn_analysis.py [package_root]
"""
import csv
import re
import sys
from pathlib import Path

import numpy as np

PKG = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
SESS = PKG / "data/20261113-114335_r4000"

CONTRACT_LEFT = [13, 15]   # LowState wheel slots FL, RL
CONTRACT_RIGHT = [12, 14]  # FR, RR


def load_policy():
    frames = []
    with (SESS / "debug_policy.csv").open(newline="", encoding="utf-8", errors="replace") as f:
        next(f)
        for r in csv.reader(f):
            if not (r and r[0] == "DEBUG_POLICY" and r[2] == "WALK"):
                continue
            obs_n = int(r[57]); st_n = int(r[58 + obs_n]); raw_s = 59 + obs_n + st_n
            req_s, app_s = raw_s + 32, raw_s + 96
            frames.append({
                "tick": int(r[3]), "vx": float(r[5]), "wz": float(r[7]),
                "raw": np.array([float(x) for x in r[raw_s:raw_s + 16]]),
                "req_dq": np.array([float(r[req_s + 4 * (12 + i) + 1]) for i in range(4)]),
                "app_q": np.array([float(r[app_s + 4 * i]) for i in range(12)]),
                "sensor_q": np.array([float(x) for x in r[25:41]]),
            })
    return frames


def load_capture():
    ticks, dq, qs, tau, gz = [], [], [], [], []
    for name in sorted(SESS.glob("capture_extract_*.log")):
        with name.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                if not line.startswith("LOW_SAMPLE,"):
                    continue
                row = line.rstrip("\n").split(",")
                if len(row) < 14 + 16 * 6:
                    continue
                ticks.append(int(row[4])); gz.append(float(row[13]))
                dq.append([float(row[15 + 6 * i]) for i in range(16)])
                qs.append([float(row[14 + 6 * i]) for i in range(16)])
                tau.append([float(row[17 + 6 * i]) for i in range(16)])
    order = np.argsort(np.array(ticks))
    return (np.array(ticks)[order], np.array(dq)[order], np.array(qs)[order],
            np.array(tau)[order], np.array(gz)[order])


def main():
    frames = load_policy()
    ct, dq, qs, tau, gz = load_capture()
    vx = np.array([f["vx"] for f in frames]); wz = np.array([f["wz"] for f in frames])
    app = np.array([f["app_q"] for f in frames])
    s = np.max(np.abs(np.diff(app, axis=0)), axis=1)
    straight = (np.abs(vx[1:]) >= .05) & (np.abs(wz[1:]) < .03)
    turning = np.abs(wz[1:]) >= .03
    print(f"walk frames={len(frames)} cmd vx[{vx.min():+.3f},{vx.max():+.3f}] wz[{wz.min():+.3f},{wz.max():+.3f}]")
    print(f"applied leg-q step straight p50/p99/max = {np.percentile(s[straight],50):.4f}/"
          f"{np.percentile(s[straight],99):.4f}/{s[straight].max():.4f} (slew limit 0.018 rad)")
    print(f"applied leg-q step turning p50/p99/max = {np.percentile(s[turning],50):.4f}/"
          f"{np.percentile(s[turning],99):.4f}/{s[turning].max():.4f}")

    print("\nFORWARD >=0.30 m/s segments (2 ms capture extracts):")
    def segments(mask, min_len):
        idx = np.flatnonzero(mask)
        if not len(idx): return []
        br = np.flatnonzero(np.diff(idx) > 1)
        st = np.r_[idx[0], idx[br + 1]]; en = np.r_[idx[br], idx[-1]]
        return [(int(a), int(b)) for a, b in zip(st, en) if b - a + 1 >= min_len]
    for a, b in segments(np.abs(vx) >= .30, 15):
        t0, t1 = frames[a]["tick"], frames[b]["tick"]
        sel = (ct >= t0) & (ct <= t1)
        if not sel.any(): continue
        common = (dq[sel][:, CONTRACT_LEFT].mean(axis=1) + dq[sel][:, CONTRACT_RIGHT].mean(axis=1)) / 2
        print(f"  [{a}:{b}] {(t1-t0)/1000:4.1f}s cmd={vx[a:b+1].mean():+.3f} -> body ~{0.086*np.abs(common).mean():.3f} m/s "
              f"({0.086*np.abs(common).mean()/abs(vx[a:b+1].mean())*100:.0f}%)")

    print("\nTURN segments (wz cmd, gyro_z, wheel differential, rear posture):")
    segs = [(1792,1882),(1978,2560),(2630,2732),(2740,2891),(2921,3557),(3871,3943),(5733,5768),(5785,5999)]
    for a, b in segs:
        t0, t1 = frames[a]["tick"], frames[b]["tick"]
        sel = (ct >= t0) & (ct <= t1)
        cmdL = np.mean([f["req_dq"][[0,2]].mean() for f in frames[a:b+1]])
        cmdR = np.mean([f["req_dq"][[1,3]].mean() for f in frames[a:b+1]])
        if sel.any():
            meas = dq[sel][:, CONTRACT_RIGHT].mean() - dq[sel][:, CONTRACT_LEFT].mean()
            g = gz[sel].mean()
        else:
            meas, g = float("nan"), float("nan")
        rear_t = np.mean([f["sensor_q"][[6,7]].mean() for f in frames[a:b+1]])
        rear_c = min(f["sensor_q"][[10,11]].min() for f in frames[a:b+1])
        print(f"  [{a}:{b}] {(t1-t0)/1000:5.1f}s wz={wz[a:b+1].mean():+.3f} gyro_z={g:+.4f}"
              f"({abs(g)/max(abs(wz[a:b+1].mean()),1e-9)*100:3.0f}%) cmdDdq={cmdR-cmdL:+.2f} measDdq={meas:+.2f}"
              f" rearThigh={rear_t:.3f} rearCalfMin={rear_c:.3f}")

    print("\nLong-turn time evolution (1 s bins):")
    for a, b, nm in ((1978, 2560, "wz=-0.097"), (2921, 3557, "wz=+0.092")):
        t0, t1 = frames[a]["tick"], frames[b]["tick"]
        sel = np.flatnonzero((ct >= t0) & (ct <= t1))
        print(f"  --- {nm} ---")
        for k in range(0, len(sel), 500):
            idx = sel[k:k+500]
            wl = dq[idx][:, CONTRACT_LEFT].mean(); wr = dq[idx][:, CONTRACT_RIGHT].mean()
            print(f"    t={(ct[idx[0]]-t0)/1000:5.1f}s measDdq={wr-wl:+.2f} gyro_z={gz[idx].mean():+.4f} "
                  f"rearThigh={qs[idx][:,[7,10]].mean():.3f} rearCalf={qs[idx][:,[8,11]].mean():.3f} "
                  f"tau_L={tau[idx][:,CONTRACT_LEFT].mean():+.2f} tau_R={tau[idx][:,CONTRACT_RIGHT].mean():+.2f}")

    print("\nONNX wheel outputs on ALL moving frames (from replay report if present):")
    rep = PKG / "replay/fixture_replay_report.json"
    if rep.exists():
        import json
        j = json.loads(rep.read_text())
        c = j["moving_action_response"]["candidate"]
        print(f"  wheel clip fraction = {c['wheel_clip_fraction']:.3f}; "
              f"steering range = {c['wheel_steering_range']}; "
              f"leg clip fraction = {c['leg_clip_fraction']:.4f}")
    nz = 0
    with (SESS / "low_protection.log").open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.startswith("PROTECT,"):
                continue
            w = re.search(r"warning_or=0x([0-9a-fA-F]+)", line)
            m = re.search(r"motorstate_or=0x([0-9a-fA-F]+)", line)
            if (w and int(w.group(1), 16)) or (m and int(m.group(1), 16)):
                nz += 1
    print(f"  protection nonzero rows = {nz}")


if __name__ == "__main__":
    main()
