"""Full analysis of the 2026-11-09 11:41 field session (100 Hz capture + sport FSM + shadow).

User's actual sequence (ground truth):
  1. stand up, long pause          (mode 0->1->2)
  2. walk RIGHT a short distance   (mode 3)
  3. walk LEFT a short distance    (mode 3)
  4. turn LEFT, pause              (mode 3, then 2)
  5. turn RIGHT, pause             (mode 3, then 2)
  6. lie down                      (mode ->0)
  7. stand up                      (mode 1->2)
  8. lie down                      (mode ->0)

Read-only analysis; no robot access.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

LOG = Path("/home/caolin/as2w_workstation/部署测试/04_调试记录/logs/20261109-114107_windows_LowCaptureFast.log")
SPORT = Path("/tmp/opencode/session_logs/sportstate.out")
SHADOW = Path("/tmp/opencode/session_logs/shadow.out")

# ---------- parse sport FSM timeline ----------
mode_seg = []
for line in SPORT.read_text(errors="replace").splitlines():
    m = re.search(r"packets=(\d+) mode=(\d+)", line)
    if m:
        mode_seg.append((int(m.group(1)) / 20., int(m.group(2))))  # (approx t, mode)
# 压缩为分段
segs = []
for t, mode in mode_seg:
    if segs and segs[-1][2] == mode:
        segs[-1][1] = t
    else:
        segs.append([t, t, mode])
print("=== Sport FSM 分段 (t_s, 模式) ===")
for a, b, mode in segs:
    print(f"  {a:6.1f}-{b:6.1f}s mode={mode}")

# ---------- parse 100 Hz capture ----------
rows = []
for line in LOG.read_text(errors="replace").splitlines():
    if not line.startswith("LOW_SAMPLE,"):
        continue
    f = line.split(",")
    if len(f) < 14:  # count==0 的首帧无后续字段
        continue
    rows.append((float(f[1]) / 1000., int(f[4]),
                 np.array([float(x) for x in f[7:11]]),   # quat wxyz
                 np.array([float(x) for x in f[11:14]]),  # gyro
                 np.array([float(x) for x in f[14:84:2]]),  # q 35
                 np.array([float(x) for x in f[15:85:2]])))  # dq 35
t = np.array([r[0] for r in rows])
gyro = np.array([r[3] for r in rows])
q = np.array([r[4] for r in rows])
dq = np.array([r[5] for r in rows])
print(f"\n采样 {len(rows)} 帧  t=[{t[0]:.1f},{t[-1]:.1f}]s  (100 Hz)")

# yaw 时序(用于运动方向核对)
yaw = np.degrees(np.unwrap(np.array([2 * np.arctan2(r[2][3], r[2][0]) for r in rows])))
quat = np.array([r[2] for r in rows])

# ---------- 用运动能量定位活动段 ----------
wdq = np.abs(dq[:, 12:16]).max(axis=1)
ldq = np.abs(dq[:, 0:12]).max(axis=1)
active = (wdq > 0.05) | (ldq > 0.05)
# 连续活动段
idx = np.where(active)[0]
bounds = []
if len(idx):
    start = prev = idx[0]
    for i in idx[1:]:
        if i - prev > 10:  # >100ms 静默 => 分段
            bounds.append((start, prev))
            start = i
        prev = i
    bounds.append((start, prev))
print("\n=== 活动段 (t, 时长, gyro_z均值°/s, yaw变化°, 轮dq均值[12..15]) ===")
for a, b in bounds:
    if b - a < 8:  # <80ms 忽略
        continue
    gz = np.degrees(gyro[a:b + 1, 2].mean())
    dy = yaw[b] - yaw[a]
    w = dq[a:b + 1, 12:16].mean(axis=0)
    vx_proxy = quat_v = None
    print(f"  [{t[a]:6.1f}-{t[b]:6.1f}]s dur={t[b]-t[a]:5.1f}s gyro_z={gz:+7.2f}°/s dyaw={dy:+7.2f}° "
          f"wheel_dq=[{w[0]:+.2f},{w[1]:+.2f},{w[2]:+.2f},{w[3]:+.2f}]")

# ---------- 转向段: 左右轮判定 ----------
print("\n=== 转向段轮槽符号分析 (判据: 左转 ωz>0 -> 右侧轮 dq>0, 左侧 dq<0; 前向=全正已证) ===")
turn_segs = [(a, b) for a, b in bounds
             if abs(np.degrees(gyro[a:b + 1, 2].mean())) > 3.0 and (b - a) > 10]
for a, b in turn_segs:
    gz = np.degrees(gyro[a:b + 1, 2].mean())
    w = dq[a:b + 1, 12:16].mean(axis=0)
    side = ["R" if x > 0.3 else "L" if x < -0.3 else "?" for x in w]
    print(f"  [{t[a]:6.1f}-{t[b]:6.1f}]s gyro_z={gz:+7.2f}°/s -> {'左转' if gz>0 else '右转'}: "
          f"dq=[{w[0]:+.2f},{w[1]:+.2f},{w[2]:+.2f},{w[3]:+.2f}] 槽12-15 侧别={side}")

# ---------- 侧移段: 腿(尤其hip)运动 ----------
print("\n=== 非转向活动段 (侧移/过渡) hip dq 均值 [槽0,3,6,9] ===")
for a, b in bounds:
    if (a, b) in turn_segs or b - a < 8:
        continue
    gz = np.degrees(gyro[a:b + 1, 2].mean())
    hips = dq[a:b + 1][:, [0, 3, 6, 9]].mean(axis=0)
    w = dq[a:b + 1, 12:16].mean(axis=0)
    print(f"  [{t[a]:6.1f}-{t[b]:6.1f}]s gyro_z={gz:+6.2f}°/s hip_dq=[{hips[0]:+.3f},{hips[1]:+.3f},"
          f"{hips[2]:+.3f},{hips[3]:+.3f}] wheel_dq=[{w[0]:+.2f},{w[1]:+.2f},{w[2]:+.2f},{w[3]:+.2f}]")

# ---------- 过渡次序: 100 Hz 分前后腿 ----------
print("\n=== 起立/趴下过渡: 每腿 thigh|dq|>0.2 首次时刻 (100 Hz, 10ms 分辨) ===")
# 过渡段 = mode 0/1/2 切换附近的腿活跃段
trans_bounds = [(a, b) for a, b in bounds
                if np.abs(dq[a:b + 1, 12:16]).max() < 0.1 and (b - a) > 15]  # 腿动轮不动
for a, b in trans_bounds:
    print(f"  过渡段 [{t[a]:6.1f}-{t[b]:6.1f}]s:")
    for leg in range(4):
        s = np.abs(dq[a:b + 1, 3 * leg + 1]) > 0.2
        calf = np.abs(dq[a:b + 1, 3 * leg + 2]) > 0.2
        if s.any():
            print(f"    腿{leg}(槽{3*leg}-{3*leg+2}): thigh 起动 t={t[a]+10*np.argmax(s):7.2f}s  "
                  f"calf 起动 t={t[a]+10*np.argmax(calf) if calf.any() else float('nan'):7.2f}s")
        else:
            print(f"    腿{leg}: thigh 未超阈值")

# ---------- 站立段姿态 ----------
print("\n=== 站立静止段关节均值 ===")
# Exclude prone samples. The old filter mixed both static postures and its mean
# (calf ~-2.09) was incorrectly reported as a standing anchor.
stand_idx = np.where((wdq < 0.02) & (ldq < 0.02) & (np.abs(gyro[:, 2]) < 0.005)
                     & (q[:, [2, 5, 8, 11]].mean(axis=1) > -2.3))[0]
if len(stand_idx) > 50:
    qs = q[stand_idx].mean(axis=0)
    for leg in range(4):
        print(f"  腿{leg}: hip {qs[3*leg]:+.3f} thigh {qs[3*leg+1]:+.3f} calf {qs[3*leg+2]:+.3f}")
    print(f"  轮 q: {qs[12:16].round(2)}")

# ---------- 影子分析 ----------
print("\n=== 影子: 回合与预演 ===")
ep_lines = []
cur = None
for line in SHADOW.read_text(errors="replace").splitlines():
    m = re.search(r"SHADOW_ONLY tick=(\d+) age_ms=([\d.]+) RR_foot_slot=\d+ RR_foot_sdk_dq=([-\d.]+)", line)
    if m:
        if cur is None or len(cur["dq"]) > 40:
            if cur: ep_lines.append(cur)
            cur = {"tick": int(m.group(1)), "age": [], "dq": []}
        cur["age"].append(float(m.group(2)))
        cur["dq"].append(float(m.group(3)))
    e = re.search(r"shadow episode (\d+) ended", line)
    if e and cur:
        ep_lines.append(cur)
        cur = None
if cur: ep_lines.append(cur)
print(f"影子样本行数 {len(ep_lines)} 组")
for i, ep in enumerate(ep_lines[:12]):
    print(f"  组{i}: tick={ep['tick']} n={len(ep['dq'])} RR_foot预演dq: "
          f"mean {np.mean(ep['dq']):+.2f} min {np.min(ep['dq']):+.2f} max {np.max(ep['dq']):+.2f} rad/s")

out = {"turn_segments": len(turn_segs), "capture_frames": len(rows)}
Path("/tmp/opencode/session_analysis.json").write_text(json.dumps(out, indent=1))
