#!/usr/bin/env python3
import csv
import math
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: analyze_low_capture_incident.py LOW_CAPTURE_LOG")
rows = []
with open(sys.argv[1], errors="replace") as stream:
    for raw in stream:
        pos = raw.find("LOW_SAMPLE,")
        if pos < 0:
            continue
        f = raw[pos:].strip().split(",")
        if len(f) < 14 + 35 * 6:
            continue
        t = float(f[1]) / 1000.0
        tick = int(f[4])
        motors = []
        for i in range(35):
            j = 14 + i * 6
            motors.append(tuple(float(f[j+k]) for k in range(4)) + (int(f[j+4]), int(float(f[j+5]))))
        rows.append((t, tick, motors))
if not rows:
    raise SystemExit("no LOW_SAMPLE rows")
active = [r for r in rows if any(m[4] == 1 for m in r[2][:16])]
print(f"rows={len(rows)} time={rows[0][0]:.3f}..{rows[-1][0]:.3f}s active_rows={len(active)}")
spans = []
start = prev = None
for row in active:
    if start is None or row[0] - prev[0] > .05:
        if start is not None:
            spans.append((start[0], prev[0]))
        start = row
    prev = row
if start is not None:
    spans.append((start[0], prev[0]))
print("mode1_spans=" + ",".join(f"{a:.3f}-{b:.3f}" for a,b in spans))
for label, subset in (("all", rows), ("mode1", active)):
    if not subset:
        continue
    dq = [(abs(m[1]), r[0], i, m[1]) for r in subset for i,m in enumerate(r[2][:16])]
    tau = [(abs(m[3]), r[0], i, m[3]) for r in subset for i,m in enumerate(r[2][:16])]
    print(label, "top_dq", sorted(dq, reverse=True)[:12])
    print(label, "top_tau", sorted(tau, reverse=True)[:12])
# 0.5 s bins over active control, peak leg/wheel dq and tau.
if active:
    origin = active[0][0]
    bins = {}
    for r in active:
        key = int((r[0] - origin) / .5)
        b = bins.setdefault(key, [0.,0.,0.,0.,r[0],r[0]])
        b[0] = max(b[0], max(abs(m[1]) for m in r[2][:12]))
        b[1] = max(b[1], max(abs(m[1]) for m in r[2][12:16]))
        b[2] = max(b[2], max(abs(m[3]) for m in r[2][:12]))
        b[3] = max(b[3], max(abs(m[3]) for m in r[2][12:16]))
        b[5] = r[0]
    print("bins: rel_s,leg_dq,wheel_dq,leg_tau,wheel_tau")
    for key in sorted(bins):
        b=bins[key]
        print(f"{key*.5:.1f},{b[0]:.4f},{b[1]:.4f},{b[2]:.3f},{b[3]:.3f}")

# Detailed 100 ms samples around the observed R284 handoff/instability.
window = [r for r in rows if 71.5 <= r[0] <= 78.0]
if window:
    reference = min(window, key=lambda r: abs(r[0] - 72.5))[2]
    print("detail: t,leg_dq_max,leg_tau_max,wheel_q[4],wheel_dq[4],wrapped_delta_from_72.5[4]")
    for n, r in enumerate(window):
        if n % 10:
            continue
        leg_dq = max(abs(m[1]) for m in r[2][:12])
        leg_tau = max(abs(m[3]) for m in r[2][:12])
        q = [m[0] for m in r[2][12:16]]
        dq = [m[1] for m in r[2][12:16]]
        delta = [((q[i] - reference[12+i][0] + 2*math.pi) % (4*math.pi)) - 2*math.pi
                 for i in range(4)]
        print(f"{r[0]:.3f},{leg_dq:.4f},{leg_tau:.3f},"
              + ",".join(f"{v:.4f}" for v in q+dq+delta))

