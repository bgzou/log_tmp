from pathlib import Path
import numpy as np
sess = Path("/home/caolin/as2w_workstation/部署测试/04_调试记录/logs/field_sessions/20261112-114347_training-contract")
TH=[1,4,7,10]
rows=[]
for line in (sess/"low_capture_fast.log").read_text(errors="replace").splitlines():
    if not line.startswith("LOW_SAMPLE,"): continue
    f=line.split(",")
    if len(f)<14+35*6: continue
    try: rows.append((float(f[1]), int(f[4]), [float(f[15+i*6]) for i in range(16)]))
    except ValueError: continue
t0=rows[0][0]; tt=np.array([(r[0]-t0)/1000 for r in rows]); ticks=np.array([r[1] for r in rows])
dqT=np.array([[r[2][i] for i in TH] for r in rows])  # 4大腿 dq
def rms_band(sig, fs, lo, hi):
    seg=sig[int(len(sig)*0.1):]  # 去头
    x=seg-seg.mean()
    X=np.fft.rfft(x*np.hanning(len(x)))
    P=(np.abs(X)**2)/ (len(x)/2)
    fr=np.fft.rfftfreq(len(x), 1/fs)
    m=(fr>=lo)&(fr<=hi)
    return float(np.sqrt(P[m].sum()))
fs=500.0
# 时间窗: 零速保持段 与 运动段 (相对capture)
# 从上一分析: 起立~96-98s, 交接~102s, 运动~104-118s
w0,w1=104.0,116.0   # 运动窗
z0,z1=99.0,101.5     # 零速窗(站好交接前)
def seg(t0s,t1s): m=(tt>=t0s)&(tt<t1s); return m
mz=seg(z0,z1); mv=seg(w0,w1)
print("=== 大腿 dq 高频带 RMS (2ms=500Hz采样, 可分辨0-250Hz) ===")
for lo,hi,tag in ((0,20,"0-20Hz 全局"),(40,120,"40-120Hz"),(120,250,"120-250Hz")):
    z=rms_band(dqT[mz].mean(axis=1),fs,lo,hi); v=rms_band(dqT[mv].mean(axis=1),fs,lo,hi)
    print(f"  {tag:12s} 零速段={z:.5f} rad/s   运动段={v:.5f} rad/s   比值={v/max(z,1e-9):.1f}x")
print(f"  采样点: 零速{mz.sum()}, 运动{mv.sum()}")
