#!/usr/bin/env python3
"""R4000 turn-gap independent recomputation, stage 2: window chain analysis.

Produces, for the right/left long-turn windows, short-turn and straight
controls:
  * per-stage chain statistics (first 1 s / 3-5 s / last 5 s),
  * applied->published verification,
  * per-wheel servo error vs tau_est (linearity / ceiling / dead zone),
  * collapse-vs-rear-sink timing,
  * a synchronized multi-panel figure,
  * a machine-readable CSV.

Run after recompute.py step-0 checks. Usage:
  analyze_windows.py <session_dir> <out_dir>
"""
import bisect
import csv
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SESS = Path(sys.argv[1])
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
W_PI = 2.0 * np.pi
SIDE = np.array([1.0, -1.0, 1.0, -1.0])  # contract wheels FL, FR, RL, RR
WHEEL_SLOTS = [13, 12, 15, 14]          # contract FL, FR, RL, RR (self-derived)
LEFT_SLOTS = [13, 15]; RIGHT_SLOTS = [12, 14]
WINDOWS = {
    "turnR_long": (1978, 2560), "turnL_long": (2921, 3557),
    "turnR_short": (3871, 3943), "turnL_short": (2630, 2732),
    "straight_0.37": (5194, 5257),
}
SUBWIN = {"first_1s": (0.0, 1.0), "t3_5s": (3.0, 5.0), "last_5s": None}


def wrap4pi(x):
    return (x + W_PI) % (4 * np.pi) - W_PI


def load_policy():
    fr = []
    with (SESS / "debug_policy.csv").open(newline="", encoding="utf-8", errors="replace") as f:
        next(f)
        for r in csv.reader(f):
            if not (r and r[0] == "DEBUG_POLICY"):
                continue
            n = int(r[57]); st = int(r[58 + n]); raw_s = 59 + n + st
            req_s, app_s = raw_s + 32, raw_s + 96
            fr.append({
                "phase": r[2], "tick": int(r[3]), "age": float(r[4]),
                "vx": float(r[5]), "wz": float(r[7]), "rx": float(r[11]),
                "gyro_z": float(r[17]),
                "q": np.array([float(x) for x in r[25:41]]),
                "dq": np.array([float(x) for x in r[41:57]]),
                "obs": np.array([float(x) for x in r[58:58 + n]]),
                "raw": np.array([float(x) for x in r[raw_s:raw_s + 16]]),
                "req_dq": np.array([float(r[req_s + 4 * (12 + i) + 1]) for i in range(4)]),
                "app_dq": np.array([float(r[app_s + 4 * (12 + i) + 1]) for i in range(4)]),
            })
    return fr


def load_lowcmd():
    rows = []
    with (SESS / "debug_lowcmd.csv").open(newline="", encoding="utf-8", errors="replace") as f:
        next(f)
        for r in csv.reader(f):
            if not (r and r[0].startswith("DEBUG_LOWCMD")):
                continue
            per = {}
            for j in range(16):
                b = 5 + 7 * j
                per[int(r[b])] = (int(r[b + 1]), float(r[b + 2]), float(r[b + 3]),
                                  float(r[b + 4]), float(r[b + 5]), float(r[b + 6]))
            rows.append((int(r[2]), per))
    return rows


def load_capture():
    ticks, age, dq, q, tau, gyro = [], [], [], [], [], []
    with (SESS / "low_capture_fast.log").open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.startswith("LOW_SAMPLE,"):
                continue
            r = line.rstrip("\n").split(",")
            if len(r) < 14 + 16 * 6:
                continue
            ticks.append(int(r[4])); age.append(float(r[3])); gyro.append(float(r[13]))
            dq.append([float(r[15 + 6 * i]) for i in range(16)])
            q.append([float(r[14 + 6 * i]) for i in range(16)])
            tau.append([float(r[17 + 6 * i]) for i in range(16)])
    return (np.array(ticks), np.array(age), np.array(dq), np.array(q),
            np.array(tau), np.array(gyro))


def load_protection():
    out = []
    with (SESS / "low_protection.log").open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.startswith("PROTECT,") or "warning_or=" not in line:
                continue
            m = re.search(r"tick=(\d+)", line)
            w = re.search(r"warning_or=0x([0-9a-fA-F]+)", line)
            ms = re.search(r"motorstate_or=0x([0-9a-fA-F]+)", line)
            if m:
                out.append((int(m.group(1)),
                             int(w.group(1), 16) if w else 0,
                             int(ms.group(1), 16) if ms else 0))
    return out


import re  # noqa: E402  (used above)


def recompute_wheel(raw, pcmd, latched, obs_wheel, park_ref):
    vx, wz = pcmd[0], pcmd[2]
    turning = min(abs(wz) / .20, 1.)
    motion = min(max(abs(vx) / .10, turning), 1.)
    wheel = np.clip(raw[12:16], -1., 1.)
    common = wheel.mean(); steering = (wheel * SIDE).mean()
    linear = vx + .10 * turning * (common * min(abs(vx) / .04, 1.)) \
        - .66 * (1. + .25 * steering) * wz * SIDE
    out = np.clip(linear / (.086 * 16.) + .035 * motion * (1. - turning) * (wheel - common), -6., 6.)
    hold = np.clip(-6. * wrap4pi(obs_wheel - park_ref), -1.5, 1.5) / 16. if latched else np.zeros(4)
    return out + hold


def main():
    fr = load_policy()
    lc = load_lowcmd()
    ct, cage, cdq, cq, ctau, cgyro = load_capture()
    prot = load_protection()
    walk = [f for f in fr if f["phase"] == "WALK"]
    lct = np.array([t for t, _ in lc])
    prot_t = np.array([t for t, _, _ in prot])
    prot_w = np.array([w for _, w, _ in prot]); prot_m = np.array([m for _, _, m in prot])

    # ── chain recompute over all WALK frames (source math vs recorded) ─────
    # hold-latch state machine replay (quiet: wheel<0.5, gyro-norm<0.15; latch .12s)
    park_ref = np.zeros(4); hold = 0; latched_prev = False
    recompute_err_req = recompute_err_app = 0.0
    latched_flags = []
    # state machine replays from the session's first HANDOFF frame so the
    # wheel-hold park reference is captured exactly like the deployed arm()
    for f in [x for x in fr if x["phase"] in ("HANDOFF", "WALK")]:
        obs = f["obs"]; pcmd = (obs[0] + .4, obs[1], obs[2])
        gyro = obs[3:6]; gyro_n = float(np.linalg.norm(gyro))
        wheel_dq_meas = f["dq"][12:16]
        quiet = np.abs(wheel_dq_meas).max() < .5 and gyro_n < .15
        was_latched = hold * 0.02 >= .12
        centered = max(abs(pcmd[0]), abs(pcmd[1]), abs(pcmd[2])) < .005
        hold = hold + 1 if (centered and (was_latched or quiet)) else 0
        latched = hold * 0.02 >= .12
        if latched and not was_latched:
            park_ref = obs[22:26].copy()
        rw = recompute_wheel(f["raw"], pcmd, latched, obs[22:26], park_ref)
        if f["phase"] == "WALK":
            recompute_err_req = max(recompute_err_req, float(np.max(np.abs(rw * 16. - f["req_dq"]))))
            recompute_err_app = max(recompute_err_app, float(np.max(np.abs(rw * 16. - f["app_dq"]))))
            latched_flags.append(latched)
    print(f"[chain self-check] source-math recompute vs recorded: "
          f"req max err={recompute_err_req:.3e}, app max err={recompute_err_app:.3e}")
    latched_arr = np.array(latched_flags)
    for name, (a, b) in WINDOWS.items():
        print(f"  {name}: latched frames inside window = {int(latched_arr[a:b+1].sum())}")

    # ── applied vs published (final LowCmd) ────────────────────────────────
    # Backward match: a published row carries the targets of the LATEST
    # policy frame whose tick <= row tick; anything else would be a real
    # applied->published discrepancy.
    pub_err = 0.0; pub_n = 0
    pub_diff_by_tick = {}
    wt = [f["tick"] for f in walk]
    for k in range(0, len(lc), 3):
        tick, per = lc[k]
        j = bisect.bisect_right(wt, tick) - 1
        if j < 0 or tick - wt[j] > 100:
            continue
        f = walk[j]
        dqs = np.array([per[s][2] for s in WHEEL_SLOTS])
        pub_err = max(pub_err, float(np.max(np.abs(dqs - f["app_dq"]))))
        pub_n += 1
        pub_diff_by_tick[f["tick"]] = (dqs,
                                       np.array([per[s][3] for s in WHEEL_SLOTS]),
                                       np.array([per[s][4] for s in WHEEL_SLOTS]),
                                       np.array([per[s][5] for s in WHEEL_SLOTS]))
    print(f"[applied->published] frames matched={pub_n}, wheel dq max |diff|={pub_err:.3e} "
          f"(kp/kd/tau published: kp=0 kd=2 tau=0 expected)")

    # ── window stage tables ─────────────────────────────────────────────────
    rows = []
    for name, (a, b) in WINDOWS.items():
        t0, t1 = walk[a]["tick"], walk[b]["tick"]
        dur = (t1 - t0) / 1000.
        selc = np.flatnonzero((ct >= t0) & (ct <= t1))
        p_mask = (prot_t >= t0) & (prot_t <= t1)
        sub = {"first_1s": (0., 1.), "t3_5s": (3., 5.), "last_5s": (max(dur - 5., 0.), dur)}
        for sub_name, (ts, te) in sub.items():
            fa = bisect.bisect_left([f["tick"] for f in walk], t0 + ts * 1000)
            fb = bisect.bisect_right([f["tick"] for f in walk], t0 + te * 1000) - 1
            fa = max(fa, a); fb = min(fb, b)
            seg = walk[fa:fb + 1]
            if not seg:
                continue
            raw_w = np.array([f["raw"][12:16] for f in seg])
            steering = float((np.clip(raw_w, -1, 1) * SIDE).mean())
            req_d = np.mean([f["req_dq"][[1, 3]].mean() - f["req_dq"][[0, 2]].mean() for f in seg])
            app_d = np.mean([f["app_dq"][[1, 3]].mean() - f["app_dq"][[0, 2]].mean() for f in seg])
            # published + measured from capture slice
            sc = np.flatnonzero((ct >= seg[0]["tick"]) & (ct <= seg[-1]["tick"]))
            measL = cdq[sc][:, LEFT_SLOTS].mean(axis=1) if len(sc) else np.array([np.nan])
            measR = cdq[sc][:, RIGHT_SLOTS].mean(axis=1) if len(sc) else np.array([np.nan])
            meas_d = float((measR - measL).mean()) if len(sc) else np.nan
            common = float(((measL + measR) / 2).mean()) if len(sc) else np.nan
            gz = float(cgyro[sc].mean()) if len(sc) else np.nan
            wzcmd = float(np.mean([f["wz"] for f in seg]))
            vx = float(np.mean([f["vx"] for f in seg]))
            rear_t = float(np.mean([f["q"][[6, 7]].mean() for f in seg]))
            rear_c = float(np.mean([f["q"][[10, 11]].mean() for f in seg]))
            tauL = float(ctau[sc][:, LEFT_SLOTS].mean()) if len(sc) else np.nan
            tauR = float(ctau[sc][:, RIGHT_SLOTS].mean()) if len(sc) else np.nan
            # servo linearity: tau_est vs kd*speed_error on a per-wheel basis
            errs, taus = [], []
            for f in seg:
                j = np.searchsorted(ct, f["tick"])
                if j < len(ct):
                    cmd = f["app_dq"]
                    meas = cdq[j][WHEEL_SLOTS]
                    errs.extend(cmd - meas); taus.extend(ctau[j][WHEEL_SLOTS])
            errs = np.array(errs); taus = np.array(taus)
            tau_max = float(np.nanmax(np.abs(taus))) if len(taus) else np.nan
            slope = float(np.polyfit(errs, taus, 1)[0]) if len(errs) > 10 and np.std(errs) > 1e-6 else np.nan
            rows.append({
                "window": name, "dur_s": round(dur, 1), "sub": sub_name,
                "vx_cmd": round(vx, 3), "wz_cmd": round(wzcmd, 4),
                "raw_wheel_common": round(float(raw_w.mean()), 3),
                "raw_wheel_steering": round(steering, 4),
                "req_diff": round(req_d, 3), "app_diff": round(app_d, 3),
                "pub_diff": np.nan,  # per-frame matching done globally above
                "meas_diff": round(meas_d, 3) if meas_d == meas_d else np.nan,
                "meas_common": round(common, 3) if common == common else np.nan,
                "gyro_z": round(gz, 4) if gz == gz else np.nan,
                "yaw_pct": round(abs(gz) / max(abs(wzcmd), 1e-9) * 100, 1) if gz == gz else np.nan,
                "diff_track_pct": round(abs(meas_d) / max(abs(req_d), 1e-9) * 100, 1) if meas_d == meas_d and req_d else np.nan,
                "rear_thigh": round(rear_t, 3), "rear_calf": round(rear_c, 3),
                "tau_L": round(tauL, 2) if tauL == tauL else np.nan,
                "tau_R": round(tauR, 2) if tauR == tauR else np.nan,
                "tau_absmax": round(tau_max, 2) if tau_max == tau_max else np.nan,
                "servo_slope_tau_per_err": round(slope, 3) if slope == slope else np.nan,
                "prot_nonzero_in_window": int(np.count_nonzero(prot_w[p_mask]) + np.count_nonzero(prot_m[p_mask])),
                "comms_age_ms_p99": round(float(np.nanpercentile(cage[sc], 99)), 1) if len(sc) else np.nan,
            })
    with (OUT / "stage_table.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    for r in rows:
        print(f"{r['window']:>13s} {r['sub']:>9s} wz={r['wz_cmd']:+.3f} | rawsteer={r['raw_wheel_steering']:+.4f} "
              f"reqD={r['req_diff']:+.3f} appD={r['app_diff']:+.3f} measD={r['meas_diff']} "
              f"({r['diff_track_pct']}%) gyro={r['gyro_z']} yaw={r['yaw_pct']}% "
              f"tauLR={r['tau_L']}/{r['tau_R']} slope={r['servo_slope_tau_per_err']} "
              f"rearT={r['rear_thigh']} prot={r['prot_nonzero_in_window']}")

    # ── collapse vs rear-sink timing (long turns) ───────────────────────────
    for name, (a, b) in (("turnR_long", WINDOWS["turnR_long"]), ("turnL_long", WINDOWS["turnL_long"])):
        t0 = walk[a]["tick"]
        selc = np.flatnonzero((ct >= t0) & (ct <= walk[b]["tick"]))
        t = (ct[selc] - t0) / 1000.
        measD = cdq[selc][:, RIGHT_SLOTS].mean(axis=1) - cdq[selc][:, LEFT_SLOTS].mean(axis=1)
        rearT = cq[selc][:, [7, 10]].mean(axis=1)
        base_d = np.abs(measD[:int(1.0 / .002)]).mean() if len(t) > 500 else np.abs(measD).mean()
        collapse_t = next((tt for tt, v in zip(t, np.abs(measD)) if v < base_d * .5 and tt > .5), None)
        base_r = rearT[:int(1.0 / .002)].mean()
        sink_t = next((tt for tt, v in zip(t, rearT) if v < base_r - 0.05 and tt > .5), None)
        tau_abs = np.abs(ctau[selc][:, WHEEL_SLOTS]).mean(axis=1)
        print(f"[timing {name}] wheel-diff 50% collapse at t={collapse_t} s; "
              f"rear-thigh -0.05 rad sink at t={sink_t} s")

    # ── synchronized figure (right turn window) ───────────────────────────
    fig, axes = plt.subplots(8, 1, figsize=(12, 15), sharex=True)
    for wname, (a, b) in (("RIGHT turn 11.6 s", WINDOWS["turnR_long"]),):
        t0, t1 = walk[a]["tick"], walk[b]["tick"]
        wsel = [f for f in walk if t0 <= f["tick"] <= t1]
        wt = np.array([f["tick"] for f in wsel])
        selc = np.flatnonzero((ct >= t0) & (ct <= t1))
        tt = (ct[selc] - t0) / 1000.
        wtt = (wt - t0) / 1000.
        ax = axes[0]
        ax.plot(wtt, [f["wz"] for f in wsel], label="slewed wz cmd")
        ax.plot(wtt, [f["obs"][2] for f in wsel], "--", label="obs-filtered wz")
        ax.plot(tt, cgyro[selc], label="gyro_z (IMU)")
        ax.set_ylabel("rad/s"); ax.legend(fontsize=7); ax.set_title(f"{wname}: command -> IMU")
        ax = axes[1]
        for k, (lab, sl) in enumerate((("FL", 13), ("FR", 12), ("RL", 15), ("RR", 14))):
            ax.plot(wtt, [f["raw"][12 + k] for f in wsel], label=f"raw {lab}", lw=.8)
        ax.set_ylabel("ONNX raw wheels"); ax.legend(fontsize=6, ncol=4)
        ax = axes[2]
        ax.plot(wtt, [f["req_dq"][[1, 3]].mean() - f["req_dq"][[0, 2]].mean() for f in wsel], label="requested diff (R-L)")
        ax.plot(tt, cdq[selc][:, RIGHT_SLOTS].mean(axis=1) - cdq[selc][:, LEFT_SLOTS].mean(axis=1), label="measured diff (R-L)")
        ax.set_ylabel("rad/s"); ax.legend(fontsize=7); ax.set_title("wheel differential: software target vs measured")
        ax = axes[3]
        pub_t = []; pub_d = []
        for f in wsel:
            if f["tick"] in pub_diff_by_tick:
                dqs, *_ = pub_diff_by_tick[f["tick"]]
                pub_t.append((f["tick"] - t0) / 1000.)
                pub_d.append(dqs[[1, 3]].mean() - dqs[[0, 2]].mean())
        ax.plot(wtt, [f["app_dq"][[1, 3]].mean() - f["app_dq"][[0, 2]].mean() for f in wsel], label="applied diff")
        ax.plot(pub_t, pub_d, ".", ms=1, alpha=.4, label="published LowCmd diff")
        ax.set_ylabel("rad/s"); ax.legend(fontsize=7); ax.set_title("applied vs final published LowCmd")
        ax = axes[4]
        ax.plot(tt, cdq[selc][:, LEFT_SLOTS].mean(axis=1), label="measured L wheels")
        ax.plot(tt, cdq[selc][:, RIGHT_SLOTS].mean(axis=1), label="measured R wheels")
        ax.set_ylabel("rad/s"); ax.legend(fontsize=7)
        ax = axes[5]
        ax.plot(tt, ctau[selc][:, LEFT_SLOTS].mean(axis=1), label="tau_est L")
        ax.plot(tt, ctau[selc][:, RIGHT_SLOTS].mean(axis=1), label="tau_est R")
        err2 = []
        for j in selc:
            k = bisect.bisect_left(wt, ct[j])
            if k < len(wt):
                cmd = wsel[k]["app_dq"]; meas = cdq[j][WHEEL_SLOTS]
                err2.append(2.0 * (cmd - meas).mean())
        ax.plot(tt, err2, "k--", lw=.8, label="kd*(cmd-meas) predicted mean")
        ax.set_ylabel("Nm"); ax.legend(fontsize=7); ax.set_title("wheel torque: estimate vs kd*speed-error prediction")
        ax = axes[6]
        ax.plot(tt, cq[selc][:, [7, 10]].mean(axis=1), label="rear thigh mean")
        ax.plot(tt, cq[selc][:, [8, 11]].mean(axis=1), label="rear calf mean")
        ax.set_ylabel("rad"); ax.legend(fontsize=7)
        ax = axes[7]
        ax.plot(tt, cage[selc], lw=.6)
        ax.set_ylabel("ms"); ax.set_xlabel("time in window (s)"); ax.set_title("LowState data age")
        for ax in axes:
            ax.grid(alpha=.3)
    fig.tight_layout()
    fig.savefig(OUT / "chain_sync_turnR.png", dpi=130, bbox_inches="tight")
    print("figure:", OUT / "chain_sync_turnR.png")


if __name__ == "__main__":
    main()
