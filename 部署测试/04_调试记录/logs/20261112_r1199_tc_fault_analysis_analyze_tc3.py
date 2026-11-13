from pathlib import Path
import math

sess = Path("/home/caolin/as2w_workstation/部署测试/04_调试记录/logs/field_sessions/20261112-103110_training-contract")
rows = []
for line in (sess/"low_capture_fast.log").read_text(errors="replace").splitlines():
    if not line.startswith("LOW_SAMPLE,"): continue
    f = line.split(",")
    if len(f) < 14+35*6: continue
    try:
        t = float(f[1]); pc = int(f[2]); age = int(f[3]); tick = float(f[4])
        mode_pr = f[5]; machine = f[6]
        vals = []
        for i in range(16):
            q=float(f[14+i*6]); dq=float(f[15+i*6]); tau=float(f[17+i*6])
            vals.append((q,dq,tau))
    except ValueError:
        rows.append((t,pc,age,tick,mode_pr,machine,None,None)); continue
    rows.append((t,pc,age,tick,mode_pr,machine,vals,"".join(f[14+i*6+4] for i in range(16))))
t0 = rows[0][0]
print("=== every sample t=44.0..44.8s ===")
prev_tick = None
for t,pc,age,tick,mode_pr,machine,vals,mm in rows:
    if 44000 <= (t-t0) <= 44800:
        dt = (tick-prev_tick) if prev_tick else 0
        nonfinite = ""
        if vals:
            nf = [i for i,(q,dq,tau) in enumerate(vals) if not (math.isfinite(q) and math.isfinite(dq) and math.isfinite(tau))]
            if nf: nonfinite = f" NONFINITE_SLOTS={nf}"
        print(f"t={(t-t0)/1000:7.3f} pc={pc} age={age} tick={tick:.0f} dtick={dt:.0f} mode_pr={mode_pr} machine={machine} modes={mm}{nonfinite}")
        prev_tick = tick
# tick continuity across whole session
print("\n=== tick anomalies (jump != ~10 per 10ms) whole session ===")
prev=None; anomalies=[]
for t,pc,age,tick,mode_pr,machine,vals,mm in rows:
    if prev is not None:
        dt = tick - prev[1]; dtm = t - prev[0]
        if dtm>0 and abs(dt - dtm) > 15:
            anomalies.append(((t-t0)/1000, dt, dtm))
    prev=(t,tick)
print(f"count={len(anomalies)}"); print(anomalies[:15])
# mode_pr values seen
print("\nmode_pr distinct:", set(r[4] for r in rows))
print("machine distinct:", set(r[5] for r in rows))
# quat sanity around fault
print("\n=== quat/gyro t=44.3..44.7 ===")
for t,pc,age,tick,mode_pr,machine,vals,mm in rows:
    if 44300 <= (t-t0) <= 44700:
        f=None
print("(see raw below)")
