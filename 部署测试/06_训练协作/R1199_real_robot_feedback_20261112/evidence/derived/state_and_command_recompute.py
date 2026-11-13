"""Read-only R1199 field-log extraction; never opens DDS or a device."""
from __future__ import annotations

import csv
import math
import re
from pathlib import Path

base = Path(__file__).parent
session = base / "field_sessions" / "20261112-000114_joystick"
walk_re = re.compile(r"WALK_CMD vx=([-+0-9.e]+) vy=([-+0-9.e]+) wz=([-+0-9.e]+) requested=([-+0-9.e]+),([-+0-9.e]+),([-+0-9.e]+) ly=([-+0-9.e]+) lx=([-+0-9.e]+) rx=([-+0-9.e]+)")
pending = None
walk = []
for line in (session / "publisher.log").open(encoding="utf-8", errors="replace"):
    m = walk_re.match(line)
    if m:
        pending = [float(x) for x in m.groups()]
    elif line.startswith("POLICY_TRACK,") and pending is not None:
        t, *errors = map(float, line.strip().split(",")[1:])
        walk.append([t, *pending, *errors])
        pending = None
walk_out = base / "20261112_r1199_joystick_walk_5hz.csv"
with walk_out.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["policy_elapsed_s", "applied_vx_m_s", "applied_vy_m_s", "applied_wz_rad_s",
                "requested_vx", "requested_vy", "requested_wz", "remote_ly", "remote_lx", "remote_rx",
                "target_minus_actual_FL_hip", "FR_hip", "RL_hip", "RR_hip",
                "FL_thigh", "FR_thigh", "RL_thigh", "RR_thigh",
                "FL_calf", "FR_calf", "RL_calf", "RR_calf"])
    w.writerows(walk)

capture = []
for line in (session / "low_capture_fast.log").open(encoding="utf-8", errors="replace"):
    if not line.startswith("LOW_SAMPLE,"):
        continue
    f = line.strip().split(",")
    if len(f) < 14 + 16*6:
        continue
    try:
        t = float(f[1]) / 1000
        q = [float(f[14+i*6]) for i in range(16)]
        dq = [float(f[15+i*6]) for i in range(16)]
        tau = [float(f[17+i*6]) for i in range(16)]
        mode = [int(f[18+i*6]) for i in range(16)]
        qw,qx,qy,qz = map(float,f[7:11])
    except ValueError:
        continue
    if not all(x == 1 for x in mode):
        continue
    pitch = math.degrees(math.asin(max(-1.,min(1.,2*(qw*qy-qz*qx)))))
    capture.append([t,
                    sum(abs(q[i]) for i in (0,3,6,9))/4,
                    sum(q[i] for i in (1,4,7,10))/4,
                    sum(q[i] for i in (2,5,8,11))/4,
                    max(abs(x) for x in dq[:12]),
                    max(abs(x) for x in dq[12:]),
                    max(abs(x) for x in tau[:12]),
                    pitch, *q[:12], *dq[:12], *tau[:12]])
capture_out = base / "20261112_r1199_joystick_capture_10ms.csv"
with capture_out.open("w", newline="", encoding="utf-8") as f:
    w=csv.writer(f)
    w.writerow(["capture_elapsed_s", "mean_abs_hip_q", "mean_thigh_q", "mean_calf_q",
                "max_abs_leg_dq", "max_abs_wheel_dq", "max_abs_leg_tau_est", "pitch_deg",
                *[f"m{i}_q" for i in range(12)], *[f"m{i}_dq" for i in range(12)],
                *[f"m{i}_tau_est" for i in range(12)]])
    w.writerows(capture)

print("walk rows",len(walk),"file",walk_out)
print("capture rows",len(capture),"file",capture_out)
print("policy command intervals and mean absolute hip target error:")
last_active=None
for i,row in enumerate(walk):
    t,vx,vy,wz=row[:4]
    active=abs(vx)>0.001 or abs(wz)>0.001
    if last_active is None or active != last_active:
        hip=sum(abs(x) for x in row[10:14])/4
        print(f"  t={t:.2f}s {'MOVE' if active else 'ZERO'} vx={vx:.4f} hip_err={hip:.3f}")
    last_active=active

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    ar=np.array(walk)
    cap=np.array(capture)
    fig,axes=plt.subplots(3,1,figsize=(13,9),sharex=False)
    axes[0].plot(ar[:,0],ar[:,1],label="applied vx (m/s)",lw=1)
    axes[0].set_ylabel("vx m/s"); axes[0].grid(True); axes[0].legend()
    axes[1].plot(ar[:,0],np.abs(ar[:,10:14]).mean(axis=1),label="mean |hip target - actual| (rad)",lw=1)
    axes[1].set_ylabel("hip error rad"); axes[1].grid(True); axes[1].legend()
    axes[2].plot(cap[:,0],cap[:,2],label="mean thigh q (rad)",lw=.8)
    axes[2].plot(cap[:,0],cap[:,3],label="mean calf q (rad)",lw=.8)
    axes[2].set_ylabel("leg joint q rad"); axes[2].set_xlabel("capture elapsed s (separate clock from upper panels)")
    axes[2].grid(True); axes[2].legend()
    fig.suptitle("R1199 real robot joystick retest: command, target tracking and leg pose")
    fig.tight_layout()
    plot=base/"20261112_r1199_joystick_retest_trace.png"
    fig.savefig(plot,dpi=150)
    print("plot",plot)
except ImportError:
    print("matplotlib unavailable; CSV files retained")
