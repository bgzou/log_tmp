from pathlib import Path
import numpy as np
sess = Path("/home/caolin/as2w_workstation/部署测试/04_调试记录/logs/field_sessions/20261112-105453_training-contract")
THIGH=[1,4,7,10]; CALF=[2,5,8,11]
rows=[]
for line in (sess/"low_capture_fast.log").read_text(errors="replace").splitlines():
    if not line.startswith("LOW_SAMPLE,"): continue
    f=line.split(",")
    if len(f)<14+35*6: continue
    try:
        t=float(f[1]); q=[float(f[14+i*6]) for i in range(16)]
        dq=[float(f[15+i*6]) for i in range(16)]; tau=[float(f[17+i*6]) for i in range(16)]
        mm="".join(f[14+i*6+4] for i in range(16))
    except ValueError: continue
    rows.append((t,q,dq,tau,mm))
t0=rows[0][0]
def th(q): return float(np.mean([q[i] for i in THIGH]))
def cf(q): return float(np.mean([q[i] for i in CALF]))
print("=== 姿态时间线 每2s ===")
last=-99999
for t,q,dq,tau,mm in rows:
    if t-last>=2000:
        print(f"t={(t-t0)/1000:7.2f}s thigh={th(q):+.3f} calf={cf(q):+.3f} maxlegdq={max(abs(dq[i]) for i in range(12)):.3f} maxtau={max(abs(tau[i]) for i in range(12)):.2f} modes={mm[:4]}")
        last=t
q_ts=[(t,th(q),cf(q),max(abs(dq[i]) for i in range(12)),max(abs(tau[i]) for i in range(12)),mm) for t,q,dq,tau,mm in rows]
stand_i=None
for i in range(len(q_ts)):
    t,T,C,md,mt,mm=q_ts[i]
    if mm=="1"*16 and 0.70<T<0.76:
        if all(0.70<q_ts[j][1]<0.76 for j in range(i,min(i+50,len(q_ts)))):
            stand_i=i; break
ext_i=None
for j in range(stand_i or 0,len(q_ts)):
    if q_ts[j][1]>0.78: ext_i=j; break
print(f"\nFixedStand平台起点 t={(q_ts[stand_i][0]-t0)/1000:.2f}s thigh={q_ts[stand_i][1]:.3f} calf={q_ts[stand_i][2]:.3f}")
print(f"策略伸展起点     t={(q_ts[ext_i][0]-t0)/1000:.2f}s")
print("\n=== B交接窗口 (伸展点-1s .. +6s, 每0.2s) ===")
s=max(0,ext_i-50)
for j in range(s,min(ext_i+300,len(q_ts)),10):
    t,T,C,md,mt,mm=q_ts[j]
    print(f"t={(t-t0)/1000:7.2f}s thigh={T:+.3f} calf={C:+.3f} maxlegdq={md:.3f} maxtau={mt:.2f}")
w0=max(1,ext_i-100); w1=min(len(q_ts),ext_i+400)
seg=q_ts[w0:w1]
peakT=max(x[1] for x in seg); peakC=max(x[2] for x in seg)
maxstep=max(abs(seg[j][1]-seg[j-1][1]) for j in range(1,len(seg)))
maxstepC=max(abs(seg[j][2]-seg[j-1][2]) for j in range(1,len(seg)))
print(f"\n固定站 thigh={q_ts[stand_i][1]:.3f} calf={q_ts[stand_i][2]:.3f}")
print(f"零速策略稳态 thigh={np.mean([x[1] for x in q_ts[ext_i+200:ext_i+350]]):.3f} calf={np.mean([x[2] for x in q_ts[ext_i+200:ext_i+350]]):.3f}")
print(f"交接窗口单帧 thigh 最大步进={maxstep:.4f} rad, calf={maxstepC:.4f} rad (10ms采样)")
print(f"交接窗口 maxlegdq={max(x[3] for x in seg):.3f} rad/s, maxtau={max(x[4] for x in seg):.2f} Nm")
