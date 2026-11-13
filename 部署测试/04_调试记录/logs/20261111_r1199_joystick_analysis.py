from __future__ import annotations

import csv
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

root = Path(__file__).parent / "field_sessions" / (sys.argv[1] if len(sys.argv)>1 else "20261111-233644_joystick")
protect = root / "low_protection.log"
capture = root / "low_capture_fast.log"
pub = root / "publisher.log"

rows = 0
warning = Counter()
motorstate = Counter()
boardstate = Counter()
max_current = (0.0, 0.0)
min_motor_v = (math.inf, 0.0)
for line in protect.open(encoding="utf-8", errors="replace"):
    if not line.startswith("PROTECT,"):
        continue
    parts = line.strip().split(",")
    sec = float(parts[1]) / 1000
    kv = dict(p.split("=", 1) for p in parts[2:] if "=" in p)
    rows += 1
    warning[kv.get("warning_or", "?")] += 1
    motorstate[kv.get("motorstate_or", "?")] += 1
    boardstate[kv.get("board_state0", "?")] += 1
    if kv.get("board_count", "0") != "0":
        cur = float(kv.get("motor_a", "0"))
        voltage = float(kv.get("motor_v", "0"))
        if cur > max_current[0]:
            max_current = cur, sec
        if 0 < voltage < min_motor_v[0]:
            min_motor_v = voltage, sec
print("PROTECTION", rows, "warning", dict(warning), "motorstate", dict(motorstate),
      "boardstate", dict(boardstate), "max_current", max_current, "min_motor_v", min_motor_v)

events = []
track = []
walk = []
for line in pub.open(encoding="utf-8", errors="replace"):
    if line.startswith("FIELD_SAFETY_") or line.startswith("REMOTE_TIMEOUT") or line.startswith("[") or "Passive ready" in line:
        events.append(line.strip())
    if line.startswith("POLICY_TRACK,"):
        f = list(map(float, line.strip().split(",")[1:]))
        track.append(f)
    if line.startswith("WALK_CMD "):
        walk.append(line.strip())
print("EVENTS", *events, sep="\n")
print("POLICY_TRACK", "n", len(track), "max_abs_error", max(abs(v) for r in track for v in r[1:]),
      "first", track[0], "last", track[-1])
print("WALK", "n", len(walk), "forward", sum("vx=0." in w and "vx=0 vy" not in w for w in walk),
      "back", sum("vx=-" in w for w in walk), "yaw_nonzero", sum("wz=0 " not in w for w in walk))

bucket = defaultdict(list)
active_first = None
active_last = None
max_leg_dq = (0.0, 0.0, -1)
max_wheel_dq = (0.0, 0.0, -1)
max_leg_tau = (0.0, 0.0, -1)
max_wheel_tau = (0.0, 0.0, -1)
for line in capture.open(encoding="utf-8", errors="replace"):
    if not line.startswith("LOW_SAMPLE,"):
        continue
    f = line.strip().split(",")
    if len(f) < 14 + 16 * 6:
        continue
    try:
        sec = float(f[1]) / 1000
        q = [float(f[14 + 6 * i]) for i in range(16)]
        dq = [float(f[15 + 6 * i]) for i in range(16)]
        tau = [float(f[17 + 6 * i]) for i in range(16)]
        modes = [int(f[18 + 6 * i]) for i in range(16)]
        qw,qx,qy,qz = map(float, f[7:11])
        pitch = math.degrees(math.asin(max(-1.0,min(1.0,2*(qw*qy-qz*qx)))))
    except ValueError:
        continue
    if all(m == 1 for m in modes):
        active_first = sec if active_first is None else active_first
        active_last = sec
        for i in range(12):
            if abs(dq[i]) > max_leg_dq[0]: max_leg_dq = abs(dq[i]), sec, i
            if abs(tau[i]) > max_leg_tau[0]: max_leg_tau = abs(tau[i]), sec, i
        for i in range(12,16):
            if abs(dq[i]) > max_wheel_dq[0]: max_wheel_dq = abs(dq[i]), sec, i
            if abs(tau[i]) > max_wheel_tau[0]: max_wheel_tau = abs(tau[i]), sec, i
        bucket[int(sec)].append((q, dq, pitch))
print("ACTIVE", active_first, active_last, "MAX", max_leg_dq, max_wheel_dq, max_leg_tau, max_wheel_tau)
print("SECOND,hip_abs,thigh_mean,calf_mean,leg_dq_rms,leg_dq_max,wheel_dq_max,pitch")
for second in sorted(bucket):
    samples = bucket[second]
    q = samples[-1][0]
    all_leg_dq = [x for _, v, _ in samples for x in v[:12]]
    leg_dq_rms = math.sqrt(sum(x*x for x in all_leg_dq) / len(all_leg_dq))
    leg_dq_max = max(map(abs, all_leg_dq))
    wheel_dq_max = max(abs(x) for _, v, _ in samples for x in v[12:])
    if second < 105 and second % 2 == 0:
        print(second, round(sum(abs(q[i]) for i in (0,3,6,9))/4,3),
              round(sum(q[i] for i in (1,4,7,10))/4,3),
              round(sum(q[i] for i in (2,5,8,11))/4,3),
              round(leg_dq_rms,3), round(leg_dq_max,3), round(wheel_dq_max,3),
              round(samples[-1][2],2), sep=",")

for lo,hi,name in [(10,13,"fixed_stand"),(14,18,"policy_zero_initial"),
                   (19,21,"first_motion_posture_change"),(22,72,"walking"),
                   (75,88,"returned_fixed_stand")]:
    ss = [sample for second in range(lo,hi) for sample in bucket.get(second, [])]
    if not ss: continue
    leg_dq = [abs(v) for _,vel,_ in ss for v in vel[:12]]
    wheel_dq = [abs(v) for _,vel,_ in ss for v in vel[12:]]
    q0,q1 = ss[0][0],ss[-1][0]
    print("WINDOW", name, "samples", len(ss), "leg_dq_peak",max(leg_dq),
          "leg_dq_rms",math.sqrt(sum(v*v for v in leg_dq)/len(leg_dq)),
          "wheel_dq_peak",max(wheel_dq),
          "thigh_start_end",round(sum(q0[i] for i in (1,4,7,10))/4,3),
          round(sum(q1[i] for i in (1,4,7,10))/4,3),
          "calf_start_end",round(sum(q0[i] for i in (2,5,8,11))/4,3),
          round(sum(q1[i] for i in (2,5,8,11))/4,3),
          "pitch_start_end",round(ss[0][2],2),round(ss[-1][2],2))
