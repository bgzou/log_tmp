from pathlib import Path
import numpy as np

sess = Path("/home/caolin/as2w_workstation/部署测试/04_调试记录/logs/field_sessions/20261112-103110_training-contract")

# LowState raw slots: per-leg grouped (hip,thigh,calf)x4 then wheels
# FL=(m0,m1,m2) FR=(m3,m4,m5) RL=(m6,m7,m8) RR=(m9,m10,m11), wheels m12-15
THIGH = [1,4,7,10]; CALF = [2,5,8,11]
rows = []
for line in (sess/"low_capture_fast.log").read_text(errors="replace").splitlines():
    if not line.startswith("LOW_SAMPLE,"): continue
    f = line.split(",")
    if len(f) < 14+35*6: continue
    try:
        t = float(f[1]); pc = int(f[2]); age = int(f[3]); tick = float(f[4]); machine = f[6]
        q  = [float(f[14+i*6])   for i in range(16)]
        dq = [float(f[15+i*6])   for i in range(16)]
        tau= [float(f[17+i*6])   for i in range(16)]
        mm = [f[14+i*6+4]        for i in range(16)]
    except ValueError:
        continue
    rows.append((t, pc, age, tick, machine, q, dq, tau, mm))
t0 = rows[0][0]
print(f"capture n={len(rows)} span {(rows[-1][0]-t0)/1000:.1f}s")
print("=== posture timeline (every 2s + all transitions) ===")
def th(q): return float(np.mean([q[i] for i in THIGH]))
def cf(q): return float(np.mean([q[i] for i in CALF]))
prev_key=None; last=-10
for t, pc, age, tick, machine, q, dq, tau, mm in rows:
    key = "".join(mm)
    if key != prev_key:
        print(f"t={(t-t0)/1000:7.2f}s MODE-SET {key}  thigh={th(q):+.3f} calf={cf(q):+.3f}")
        prev_key = key
    if t - last >= 2000:
        print(f"t={(t-t0)/1000:7.2f}s thigh={th(q):+.3f} calf={cf(q):+.3f} maxlegdq={max(abs(dq[i]) for i in range(12)):.3f} maxtau={max(abs(tau[i]) for i in range(12)):.2f} age_ms={age} pc={pc}")
        last = t
print("\n=== fine timeline t=30..50s (every 0.5s) ===")
last=-10
for t, pc, age, tick, machine, q, dq, tau, mm in rows:
    if 30000 <= (t-t0) <= 50000 and t-last >= 500:
        print(f"t={(t-t0)/1000:7.2f}s thigh={th(q):+.3f} calf={cf(q):+.3f} maxlegdq={max(abs(dq[i]) for i in range(12)):.3f} maxtau={max(abs(tau[i]) for i in range(12)):.2f} modes={''.join(mm)} age={age}")
        last = t
print("\n=== LowState staleness check: any age_ms>0 or pc gaps in capture? ===")
bad_age = [(t-t0, age) for t,pc,age,_,_,_,_,_,_ in rows if age > 0]
print(f"samples with age_ms>0: {len(bad_age)}"); print(bad_age[:10])
pcs = [pc for _,pc,_,_,_,_,_,_,_ in rows]
gaps = [(rows[i][0]-t0, pcs[i]-pcs[i-1]) for i in range(1,len(pcs)) if pcs[i]-pcs[i-1] not in (0, pcs[i]-pcs[i-1] if pcs[i]>=pcs[i-1] else 0) and pcs[i]-pcs[i-1] < 0]
print(f"negative pc jumps: {len(gaps)}")
# per-100ms packet rate around t=43..46s
print("\n=== packet rate per 1s window t=40..48 ===")
import collections
w = collections.defaultdict(int)
for t,pc,age,_,_,_,_,_,_ in rows:
    w[int((t-t0)//1000)] += 1
for k in sorted(w):
    if 38 <= k <= 49: print(f"t={k}s samples={w[k]}")
