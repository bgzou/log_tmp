from pathlib import Path
import numpy as np
sess = Path("/home/caolin/as2w_workstation/部署测试/04_调试记录/logs/field_sessions/20261112-114347_training-contract")
THIGH=[1,4,7,10]; CALF=[2,5,8,11]
# --- capture (2ms) ---
rows=[]
for line in (sess/"low_capture_fast.log").read_text(errors="replace").splitlines():
    if not line.startswith("LOW_SAMPLE,"): continue
    f=line.split(",")
    if len(f)<14+35*6: continue
    try:
        t=float(f[1]); q=[float(f[14+i*6]) for i in range(16)]; dq=[float(f[15+i*6]) for i in range(16)]
    except ValueError: continue
    rows.append((t,q,dq))
t0=rows[0][0]
def th(q): return float(np.mean([q[i] for i in THIGH]))
def cf(q): return float(np.mean([q[i] for i in CALF]))
print("=== 姿态每2s (t相对capture) ===")
last=-99999
for t,q,dq in rows:
    if t-last>=2000:
        print(f"t={(t-t0)/1000:6.1f}s thigh={th(q):+.3f} calf={cf(q):+.3f} maxlegdq={max(abs(dq[i]) for i in range(12)):.3f}")
        last=t
# --- POLICY_DIAG ---
diag=[]
for line in (sess/"policy_diag.log").read_text(errors="replace").splitlines():
    if not line.startswith("POLICY_DIAG,"): continue
    f=line.split(",")
    diag.append((f[1], float(f[2]), float(f[3]), int(f[7]),
                 [float(x) for x in f[8:24]], [float(x) for x in f[24:40]]))
print(f"\nPOLICY_DIAG frames={len(diag)} phases={set(d[0] for d in diag)}")
tq=[d[1] for d in diag]; vx=[d[2] for d in diag]
print(f"运动段: vx>0 帧={sum(1 for v in vx if v>0.001)} 峰值vx={max(vx):.3f} t跨度={tq[-1]:.1f}s")
# raw vs wrapped 平滑性: 运动段单帧 raw/wrapped 步进
import math
def maxstep(vals): return max(abs(vals[i]-vals[i-1]) for i in range(1,len(vals))) if len(vals)>1 else 0
mv=[i for i,d in enumerate(diag) if d[2]>0.001]
if mv:
    rsteps=[max(abs(diag[i][4][j]-diag[i-1][4][j]) for j in range(16)) for i in mv[1:] if i>0]
    wsteps=[max(abs(diag[i][5][j]-diag[i-1][5][j]) for j in range(16)) for i in mv[1:] if i>0]
    print(f"运动段 单帧步进: raw最大={max(rsteps):.4f} wrapped最大={max(wsteps):.4f}")
    # raw 抖动 vs wrapped: 高频能量对比(去均值逐帧差分的std)
    raw_leg=[d[4][j] for d in diag for j in range(12)]
print(f"bias_scale范围: {min(d[5][0]*0+d for d in diag) if diag else 0}")
