from pathlib import Path
import numpy as np
sess = Path("/home/caolin/as2w_workstation/部署测试/04_调试记录/logs/field_sessions/20261112-105937_training-contract")
THIGH=[1,4,7,10]; CALF=[2,5,8,11]
rows=[]
for line in (sess/"low_capture_fast.log").read_text(errors="replace").splitlines():
    if not line.startswith("LOW_SAMPLE,"): continue
    f=line.split(",")
    if len(f)<14+35*6: continue
    try:
        t=float(f[1]); q=[float(f[14+i*6]) for i in range(16)]
        dq=[float(f[15+i*6]) for i in range(16)]; tau=[float(f[17+i*6]) for i in range(16)]
    except ValueError: continue
    rows.append((t,q,dq,tau))
t0=rows[0][0]
def th(q): return float(np.mean([q[i] for i in THIGH]))
def cf(q): return float(np.mean([q[i] for i in CALF]))
def wheel(q): return float(np.mean([abs(q[i]) for i in (12,13,14,15)]))
# 找运动段：轮速明显(用wheel dq) — 用轮角变化率代替: 直接看thigh时间线
print("t_s     thigh   calf    maxlegdq maxtau  (每1s)")
last=-99999
for t,q,dq,tau in rows:
    if t-last>=1000:
        print(f"{(t-t0)/1000:7.2f} {th(q):+.3f} {cf(q):+.3f} {max(abs(dq[i]) for i in range(12)):7.3f} {max(abs(tau[i]) for i in range(12)):7.2f}")
        last=t
