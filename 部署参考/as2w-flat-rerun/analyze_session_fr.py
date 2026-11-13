"""Follow-up: front/rear leg identification from 100 Hz transitions + per-leg gait activity.

Turn analysis (previous script) established: wheel slots 12,14 = RIGHT side; 13,15 = LEFT side.
Now:
  A. Per-leg (thigh/calf) onset order in the four stand-up/lie-down transitions.
  B. Per-leg activity during motion segments (which legs step, which roll).
  C. Sport velocity cross-check for the walk segments.
"""
import re
from pathlib import Path

import numpy as np

LOG = Path("/home/caolin/as2w_workstation/部署测试/04_调试记录/logs/20261109-114107_windows_LowCaptureFast.log")
SPORT = Path("/tmp/opencode/session_logs/sportstate.out")

rows = []
for line in LOG.read_text(errors="replace").splitlines():
    if not line.startswith("LOW_SAMPLE,"):
        continue
    f = line.split(",")
    if len(f) < 14:
        continue
    rows.append((float(f[1]) / 1000.,
                 np.array([float(x) for x in f[11:14]]),
                 np.array([float(x) for x in f[14:84:2]]),
                 np.array([float(x) for x in f[15:85:2]])))
t = np.array([r[0] for r in rows])
gyro = np.array([r[1] for r in rows])
q = np.array([r[2] for r in rows])
dq = np.array([r[3] for r in rows])

LEGS = ["腿0(槽0-2)", "腿1(槽3-5)", "腿2(槽6-8)", "腿3(槽9-11)"]

# ---------- A. 过渡次序 ----------
print("=== A. 起立/趴下过渡: 每腿 thigh |dq| 首超 0.3 rad/s 时刻 (100 Hz) ===")
windows = [("T1 起立#1", 74., 80.), ("T2 趴下#1", 219., 226.),
           ("T3 起立#2", 231., 236.), ("T4 趴下#2", 239., 244.)]
for name, a, b in windows:
    mask = (t >= a) & (t <= b)
    idx = np.where(mask)[0]
    if not len(idx):
        continue
    print(f"\n  {name} [{a}-{b}s]:")
    onsets = []
    for leg in range(4):
        s = np.abs(dq[idx, 3 * leg + 1]) > 0.3
        c = np.abs(dq[idx, 3 * leg + 2]) > 0.3
        if s.any():
            t_on = t[idx][np.argmax(s)]
            t_c = t[idx][np.argmax(c)] if c.any() else float("nan")
            onsets.append((t_on, leg))
            print(f"    {LEGS[leg]}: thigh 起动 {t_on:.2f}s  (calf {t_c:.2f}s)")
        else:
            print(f"    {LEGS[leg]}: thigh 未超阈值")
    if len(onsets) >= 3:
        onsets.sort()
        order = [f"腿{leg}" for _, leg in onsets]
        dt = onsets[-1][0] - onsets[0][0]
        print(f"    -> 次序: {' → '.join(order)}  (首末差 {dt*1000:.0f} ms)")

# ---------- B. 运动段逐腿活动 ----------
print("\n=== B. 运动段逐腿活动 (thigh dq RMS) 与轮槽 dq ===")
segs = [("行走段2 (用户:往右)", 168.5, 175.6), ("行走段3 (用户:往左)", 181.6, 185.3),
        ("左转 (4)", 187.3, 191.8), ("右转 (5)", 202.9, 206.4)]
for name, a, b in segs:
    mask = (t >= a) & (t <= b)
    idx = np.where(mask)[0]
    rms = []
    for leg in range(4):
        rms.append(float(np.sqrt(np.mean(dq[idx, 3 * leg + 1] ** 2))))
    w = dq[idx, 12:16].mean(axis=0)
    print(f"  {name}: thigh_dq_rms=[{rms[0]:.2f},{rms[1]:.2f},{rms[2]:.2f},{rms[3]:.2f}] "
          f"轮dq均值=[{w[0]:+.2f},{w[1]:+.2f},{w[2]:+.2f},{w[3]:+.2f}]")

# ---------- C. Sport 速度核对行走段 ----------
print("\n=== C. SportState 速度 (packets/20≈t_s, 与采集差2s) ===")
for line in SPORT.read_text(errors="replace").splitlines():
    m = re.search(r"packets=(\d+) mode=(\d+) velocity=([-\d.e]+),([-\d.e]+),([-\d.e]+)", line)
    if not m:
        continue
    ts = int(m.group(1)) / 20.
    if 166 <= ts <= 210:
        print(f"  t_sport={ts:6.1f}s mode={m.group(2)} v=({float(m.group(3)):+.3f},{float(m.group(4)):+.3f},{float(m.group(5)):+.3f})")

# ---------- D. hip 分组核对 (轮侧 vs 腿侧) ----------
print("\n=== D. 轮侧与腿镜像分组组合一致性 ===")
print("  轮: 12=R, 14=R, 13=L, 15=L (两次转向交叉验证)")
print("  腿 hip 镜像组: {腿0,腿2} vs {腿1,腿3}")
print("  轮-腿配对假设: 轮12↔腿0, 13↔腿1, 14↔腿2, 15↔腿3")
print("  若成立: 腿0,腿2=右侧(轮12,14=R), 腿1,腿3=左侧 -> hip负值组{0,2}=右侧")
