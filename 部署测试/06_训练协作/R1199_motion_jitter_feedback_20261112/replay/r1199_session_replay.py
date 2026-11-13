#!/usr/bin/env python3
"""Convert a recorded R1199 field session into a replay fixture.

Reads the session's low_capture_fast.log (sensor side, 10 ms or faster) and
policy_diag.log (publisher side, 50 Hz POLICY_DIAG with the applied command
and the LowState tick of each policy frame), aligns them by tick, and emits a
fixture for as2w_r1199_joystick_replay / r1199_training_forward_parity.py.

Offline only. The replay reproduces observation construction -> ONNX ->
wrapper -> targets frame by frame on the recorded sensor stream; compare its
R1199_TARGET lines against the recorded POLICY_DIAG targets, or run what-if
experiments with changed runtime switches."""
import argparse
import bisect
import sys
from pathlib import Path


def parse_capture(path):
    rows = []
    for line in path.read_text(errors="replace").splitlines():
        if not line.startswith("LOW_SAMPLE,"):
            continue
        f = line.split(",")
        if len(f) < 14 + 35 * 6:
            continue
        try:
            tick = int(f[4])
            quat = [float(x) for x in f[7:11]]
            gyro = [float(x) for x in f[11:14]]
            q = [float(f[14 + i * 6]) for i in range(16)]
            dq = [float(f[15 + i * 6]) for i in range(16)]
        except ValueError:
            continue
        rows.append((tick, quat, gyro, q, dq))
    return rows


def parse_diag(path):
    rows = []
    for line in path.read_text(errors="replace").splitlines():
        if not line.startswith("POLICY_DIAG,"):
            continue
        f = line.split(",")
        # POLICY_DIAG,phase,t_since_walk_s,cmd_vx,cmd_vy,cmd_wz,tick,raw_0..15,
        # wrapped_0..15,target_q_0..11,target_dq_12..15,stand_bias_0..11,
        # bias_scale,hold_frames  (69 fields)
        if len(f) < 69:
            continue
        try:
            phase = f[1]
            cmd = [float(x) for x in f[3:6]]
            tick = int(float(f[6]))
        except ValueError:
            continue
        rows.append((phase, tick, cmd))
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("session_dir", type=Path,
                   help="field session dir with low_capture_fast.log and policy_diag.log")
    p.add_argument("fixture_out", type=Path)
    p.add_argument("--max-tick-skew", type=int, default=3,
                   help="max tick distance accepted for sensor alignment (default 3)")
    a = p.parse_args()
    cap = parse_capture(a.session_dir / "low_capture_fast.log")
    diag = parse_diag(a.session_dir / "policy_diag.log")
    if not cap:
        sys.exit("no LOW_SAMPLE rows in capture log")
    if not diag:
        sys.exit("no POLICY_DIAG rows (need a session run with the diag build)")
    ticks = [r[0] for r in cap]
    out = []
    unmatched = 0
    for i, (phase, tick, cmd) in enumerate(diag):
        j = bisect.bisect_left(ticks, tick)
        best, best_skew = None, None
        for k in (j - 1, j):
            if 0 <= k < len(cap):
                skew = abs(cap[k][0] - tick)
                if best is None or skew < best_skew:
                    best, best_skew = k, skew
        if best is None or best_skew > a.max_tick_skew:
            unmatched += 1
            continue
        _, quat, gyro, q, dq = cap[best]
        out.append(" ".join([f"{(i + 1) * 20}"] + [f"{x:.9g}" for x in quat] +
                            [f"{x:.9g}" for x in gyro] + [f"{x:.9g}" for x in q] +
                            [f"{x:.9g}" for x in dq] + [f"{x:.9g}" for x in cmd]))
    a.fixture_out.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"SESSION_REPLAY_FIXTURE frames={len(out)} diag_frames={len(diag)} "
          f"unmatched={unmatched} out={a.fixture_out}")
    print("next: as2w_r1199_joystick_replay deploy.yaml fixture | "
          "r1199_training_forward_parity.py --training-runtime <replay> <onnx> <snapshot>")


if __name__ == "__main__":
    main()
