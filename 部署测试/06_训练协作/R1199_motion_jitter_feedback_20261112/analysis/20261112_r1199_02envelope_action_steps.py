from pathlib import Path
import numpy as np
sess = Path("/home/caolin/as2w_workstation/部署测试/04_调试记录/logs/field_sessions/20261112-114347_training-contract")
diag=[]
for line in (sess/"policy_diag.log").read_text(errors="replace").splitlines():
    if not line.startswith("POLICY_DIAG,"): continue
    f=line.split(",")
    if len(f)<69: continue
    try:
        diag.append((f[1], float(f[2]), float(f[3]),
                     np.array([float(x) for x in f[7:23]]),
                     np.array([float(x) for x in f[23:39]]),
                     np.array([float(x) for x in f[39:51]])))
    except ValueError: continue
tw=np.array([d[1] for d in diag]); vx=np.array([d[2] for d in diag])
raw=np.array([d[3] for d in diag]); wrapped=np.array([d[4] for d in diag]); tq=np.array([d[5] for d in diag])
nz=np.where(vx>0.001)[0]
seq=[i for i in nz if i+1 in nz]
zs=[i for i in range(len(diag)) if vx[i]<0.001 and tw[i]>6 and diag[i][0]=="WALK"]
print(f"运动连续帧={len(seq)} 零速帧={len(zs)}")
def stats(a, idx, sl, name):
    d=np.abs(np.diff(a[idx][:,sl],axis=0))
    print(f"  {name:30s} 步进 mean={d.mean():.4f} p99={np.percentile(d,99):.4f} max={d.max():.4f}")
print("=== 运动段 单帧(20ms)步进 ===")
stats(raw,seq,slice(0,12),"raw ONNX 腿[限幅±6]")
stats(raw,seq,slice(12,16),"raw ONNX 轮[限幅±6]")
stats(wrapped,seq,slice(0,12),"wrapped 腿(动作单位)")
stats(wrapped,seq,slice(12,16),"wrapped 轮(rad/s目标)")
stats(tq,seq,slice(0,12),"最终腿目标 q (rad)")
print("=== 零速段(纯策略保持) 单帧步进 ===")
stats(wrapped,zs,slice(0,12),"wrapped 腿(动作单位)")
stats(tq,zs,slice(0,12),"最终腿目标 q (rad)")
# 目标本身的 40-250Hz 谱(50Hz指令方波谐波会落在这)
def band_rms(x, fs=50.0, lo=40, hi=250):
    xs=x-x.mean(); X=np.fft.rfft(xs*np.hanning(len(xs))); P=np.abs(X)**2/(len(xs)/2)
    fr=np.fft.rfftfreq(len(xs),1/fs); m=(fr>=lo)&(fr<=hi)
    return float(np.sqrt(P[m].sum()))
mot=np.mean(tq[seq][:,:12],axis=1); zer=np.mean(tq[zs][:,:12],axis=1)
print(f"=== 腿目标(50Hz指令流) 高频带RMS ===")
print(f"  运动段 40-250Hz: {band_rms(mot):.5f} rad   零速段: {band_rms(zer):.5f} rad")
print("  (若目标本身就含大量高频 → 指令侧; 若目标平滑 → 硬件/接触侧)")
