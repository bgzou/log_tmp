"""Offline kinematic analysis of the 2026-11-09 20 Hz LowState capture (600 frames).

Read-only analysis of an existing field capture; no robot access. Goal: derive
evidence-ranked hypotheses for the 16-axis DDS slot mapping and IMU conventions,
for config/hardware_contract.md. This does NOT verify a calibrated map.

Capture phases (field notes): prone -> stand up -> slow walk ~0.3 m -> stop ->
lie down -> prone. 20 Hz samples of the latest ~1 kHz HG LowState message.
"""
import json
import sys
from pathlib import Path

import numpy as np

LOG = Path(sys.argv[1] if len(sys.argv) > 1 else
           "/home/caolin/as2w_workstation/部署测试/04_调试记录/logs/20261109-100054_windows_LowCapture.log")

rows = []
for line in LOG.read_text(encoding="utf-8", errors="replace").splitlines():
    if not line.startswith("LOW_SAMPLE,"):
        continue
    f = line.split(",")
    rows.append({
        "t": float(f[1]) / 1000., "age": float(f[3]), "tick": int(f[4]),
        "mode_pr": int(f[5]), "mode_machine": int(f[6]),
        "quat": np.array([float(x) for x in f[7:11]]),
        "gyro": np.array([float(x) for x in f[11:14]]),
        "q": np.array([float(x) for x in f[14:84:2]]),   # 35 slots m0..m34
        "dq": np.array([float(x) for x in f[15:85:2]]),  # 35 slots
    })
assert rows and len(rows[0]["q"]) == 35, "expected 35 motor slots"
n = len(rows)
t = np.array([r["t"] for r in rows])
q = np.array([r["q"] for r in rows])
dq = np.array([r["dq"] for r in rows])
quat = np.array([r["quat"] for r in rows])
gyro = np.array([r["gyro"] for r in rows])
print(f"frames={n} t=[{t[0]:.2f},{t[-1]:.2f}]s slots={q.shape[1]}")
print(f"age_ms max {max(r['age'] for r in rows):.0f}  槽16-34 全程为0: {bool(np.all(q[:,16:]==0) and np.all(dq[:,16:]==0))}")

# ---------- IMU ----------
norms = np.linalg.norm(quat, axis=1)
print(f"\nquat norm mean {norms.mean():.7f} (单位四元数)")


def quat_to_R(qr):
    w, x, y, z = qr
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
        [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
        [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
    ])


up = np.array([quat_to_R(r["quat"])[2, 2] for r in rows])
yaw = np.degrees(np.unwrap(np.array([2 * np.arctan2(r["quat"][3], r["quat"][0]) for r in rows])))
print(f"up_cosine(body_z vs world_z): mean {up.mean():.5f} min {up.min():.5f}")
print(f"yaw: start {yaw[0]:.1f}° end {yaw[-1]:.1f}° 漂移 {yaw[-1]-yaw[0]:+.1f}°")

# 陀螺仪 vs 四元数差分一致性 (角速度应在机体系)
dt = 0.05
gyro_from_quat = []
for i in range(n - 1):
    R1, R2 = quat_to_R(rows[i]["quat"]), quat_to_R(rows[i + 1]["quat"])
    dR = R2 @ R1.T
    w_world = np.array([dR[2, 1] - dR[1, 2], dR[0, 2] - dR[2, 0], dR[1, 0] - dR[0, 1]]) / (2 * dt)
    gyro_from_quat.append(R1.T @ w_world)
gq = np.array(gyro_from_quat)
corr = [np.corrcoef(gq[:, k], gyro[:-1, k])[0, 1] for k in range(3)]
scale = [np.polyfit(gq[:, k], gyro[:-1, k], 1)[0] for k in range(3)]
print(f"gyro vs quat差分相关系数 (x,y,z): {np.round(corr,3)}  斜率: {np.round(scale,3)}")
print("  -> 相关≈1且斜率≈1 则陀螺为机体系角速度且符号一致 (采样20Hz,仅过渡段有信号)")

# ---------- 分段 ----------
moving = np.abs(dq[:, 12:16]).max(axis=1) > 0.02
qdot_leg = np.abs(dq[:, 0:12]).max(axis=1)
walk = moving.copy()
stand = (~moving) & (qdot_leg < 0.02)
print(f"\n分段: 运动帧 {walk.sum()}  静止帧 {stand.sum()}")
# 依据腿运动把时间轴切成阶段
leg_act = qdot_leg > 0.05
seg_bound = []
in_seg = False
for i, a in enumerate(leg_act):
    if a and not in_seg:
        seg_bound.append(t[i]); in_seg = True
    elif not a and in_seg and (i == n - 1 or not leg_act[i:i+5].any()):
        seg_bound.append(t[i]); in_seg = False
print(f"腿活跃时间边界: {[round(x,1) for x in seg_bound]}")

# ---------- 腿槽三元组 ----------
print("\n=== 腿槽 0-11: (hip,thigh,calf)x4 三元组 ===")
def phase_mean(mask, label):
    if mask.sum() < 3: return
    print(f"[{label} t={t[mask][0]:.1f}-{t[mask][-1]:.1f}s]")
    for leg in range(4):
        print(f"  腿{leg}(槽{3*leg}-{3*leg+2}): hip {q[mask,3*leg].mean():+.3f}  thigh {q[mask,3*leg+1].mean():+.3f}  calf {q[mask,3*leg+2].mean():+.3f}")

phase_mean(stand & (t < 15), "站立(前半)")
phase_mean(stand & (t >= 15), "站立(后半)")
if (t < 1.5).any(): phase_mean(t < 1.5, "起始趴下")
if (t > 28.5).any(): phase_mean(t > 28.5, "结束趴下")

# 站立窗口轮与腿的URDF限位一致性
URDF_HIP = (-0.785, 0.785); URDF_CALF = (-2.7677, -0.8133)
ok = all(URDF_HIP[0] <= q[:, 3*l].max() and q[:, 3*l].min() <= URDF_HIP[1] for l in range(4))
ok2 = all(URDF_CALF[0] <= q[:, 3*l+2].max() and q[:, 3*l+2].min() <= URDF_CALF[1] for l in range(4))
print(f"\nhip 全帧在 URDF ±0.785: {ok};  calf 全帧在 URDF [-2.7677,-0.8133]: {ok2}")

# 同腿 thigh-calf 相关性 (过渡段), 支持三元组归属
trans = (leg_act) & (~moving)
if trans.sum() > 5:
    print("过渡段 thigh-calf 相关系数(同腿 / 跨腿对照):")
    for l in range(4):
        c_same = np.corrcoef(q[trans, 3*l+1], q[trans, 3*l+2])[0, 1]
        c_cross = np.corrcoef(q[trans, 3*l+1], q[trans, ((3*(l+1))%12)+2])[0, 1]
        print(f"  腿{l}: 同腿 thigh-calf r={c_same:+.2f}  vs 相邻腿 thigh-calf r={c_cross:+.2f}")

# 步态相位: 行走窗口腿 dq 互相关 (对角对假设)
mw = np.where(walk)[0]
if len(mw) > 20:
    print("\n行走窗口 thigh dq 互相关矩阵 (4腿):")
    dqs = dq[mw][:, [1, 4, 7, 10]]
    for a in range(4):
        print("   " + " ".join(f"{np.corrcoef(dqs[:,a], dqs[:,b])[0,1]:+.2f}" for b in range(4)))

# ---------- 轮槽 ----------
print("\n=== 轮槽 12-15 ===")
if len(mw):
    for s in (12, 13, 14, 15):
        d = dq[mw, s]
        print(f"槽{s}: dq均值 {d.mean():+.3f}  活跃帧 {np.mean(np.abs(d)>0.1):.2f}  q总变化 {q[mw[-1],s]-q[mw[0],s]:+.2f} rad")
    # 轮 dq 对偏航率回归: 转向时左右轮差速
    print("行走窗口轮dq ~ gyro_z 回归斜率 (b>0 与 b<0 分两侧):")
    for s in (12, 13, 14, 15):
        b = np.polyfit(gyro[mw, 2], dq[mw, s], 1)[0]
        print(f"  槽{s}: b={b:+.3f}")
    # 与机体系前向速度代理(轮dq均值)的相关
    fwd = dq[mw][:, 12:16].mean(axis=1)
    print(f"轮dq与各自时延0互相关: " + " ".join(f"{np.corrcoef(fwd, dq[mw, s])[0,1]:+.2f}" for s in (12,13,14,15)))

print("\n结论要点已生成; JSON 摘要写出")
Path("/tmp/opencode/capture_analysis.json").write_text(json.dumps({
    "frames": n, "slots_active": "0-15", "slots_zero": "16-34",
    "leg_triples": "slot 3k,3k+1,3k+2 = (hip,thigh,calf) of leg k",
    "hip_side_split": {"legs_negative": [0, 2], "legs_positive": [1, 3]},
    "wheel_forward_sign": {str(s): float(dq[mw, s].mean()) for s in (12, 13, 14, 15)},
    "imu": {"quat": "wxyz unit, body-to-world", "yaw_drift_deg": float(yaw[-1] - yaw[0]),
            "gyro_quat_corr": [float(c) for c in corr]},
}, indent=1, ensure_ascii=False))
