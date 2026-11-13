# R152 盲爬楼/平地联合策略（2026-11-09 接入，当前 stairs 部署目标）

来源：GitHub `YuTaoV5/Rob2Nav` main @ `40c80f0e07362b0a8e38528379076355d50ecbf5`
`deliveries/as2w-deploy/omni-blind-stairs-r152`；工作站 sparse clone 在
`部署参考/Rob2Nav-r152-source/`（同 HEAD）。

## 文件与哈希

- `policy.onnx` SHA-256 `fdc661f936a08a96d8db7ae34bb26933f6c34ed980dae8a5119283812a80f5d1`
- `r152-trace.csv` SHA-256 `9e31a294305c8b6f24211f45d5ab2c4acdc0af54f31c34dfcaad33a7a642945a`
- `deploy.yaml`：与 R41 逐字一致（关节序/默认姿态/限位/指令限幅 vx 0.6、vy 0.35、wz 0.8）。
  **本树内 `policy_file` 改为同目录 `policy.onnx`**，其余与交付一致

## 接口（与 R41 唯一关键差异：state 尺寸）

- 观测 `obs`[1,41]：机体系 vx/vy/wz 指令、IMU 角速度、投影重力、16 绝对位置、16 速度（同 R41）
- 递归历史 **`state`[1,844]**：模式进入清零，逐帧 `next_state` 回传——**不得与 R41 的 [1,835] 混用**
- 输出 16 维：12 腿位置目标 + 4 轮速度目标，关节序与 R41 完全一致
- 50 Hz；无官方基座线速度依赖（轮端运动学估速）

## 2026-11-09 验证记录

- **MuJoCo 平地（服务器复跑，ONNX 闭环）**：固定集跟踪/停车 **44/52**、严格接触/步态
  **21/52**；独立集 25/52、严格 9/52；104 回合零跌倒、零前轮换边；与交付 evidence 逐例
  完全一致（mismatch 0/104）。原始：`../../部署测试/04_调试记录/logs/r152_verify_20261109/`
- **严格失败模式**：全部为后腿非轮部位触地峰值 ≥50 N——固定集 23/44（RL_calf 11、RR_calf 8、
  RL/RR_thigh 4）、独立集 16/25；峰值中位 ~60–84 N、最大 167 N；发生在加速段(8)、跟踪段(10)、
  停车段(5)。**速度越激进越差：stop 与 forward_slow 4/4 全严格通过；forward 1/4、
  forward_fast 0/4、纯侧移/斜移 0–2/4。**
- **R41 相同判据可比复测**（`r41_audit_strict.py`，同一 harness/种子/判据）：R41 python/onnx
  固定集严格仅 13/12 of 52、独立 4/5 of 52，且 41 个跟踪通过者中 18 个**前轮换边**
  （R41 stop 姿态前腿内收交叉 ~12 cm 过中线，292/300 tick）；R152 在跟踪、净严格率、几何
  检查上全面优于 R41。注意：后腿触地是两代共性，R152 触地频率反而更高（52% vs 24%），
  由零换边与更高跟踪率补偿。原始：`部署测试/04_调试记录/logs/r41_strict_verify_20261109/`
- **C++ 回放（本树 `deploy/robots/as2w/r152/`，`-DAS2W_R152=ON -DONNXRUNTIME_ROOT=<ORT-1.22.0>`）**：
  750 帧 `max_abs_error=0`，与交付 cpp-replay 一致；根项目 7/7 CTest 无回归。
- **ONNX Runtime 必须 1.22.0**（1.24.2 报 TopK ShapeInferenceError；服务器 ORT 1.31.1 可载但
  交付 C++ 验证基准是 1.22.0）。

## 判据说明（不混淆验收级别）

"跟踪/停车通过"（44/52）= 指令跟踪误差与停车达标且不倒；"严格通过"（21/52）= 另加
前轮不换边、自碰撞 <1 N、非轮触地 <50 N。**44/52 不是安全通过**；实机起步建议只使用
仿真中全严格通过的指令域（stop、forward_slow≈0.2 m/s）。

## 待办（CPRO 侧）

ORT 1.22.0 aarch64 CPU 包传入 → `AS2W_R152=ON` ARM 构建 + 回放 → `shadow.cpp` 只读探针接线
（映射表用 G1 实测：contract 序槽位 `[3,0,9,6,4,1,10,7,5,2,11,8,13,12,15,14]`、hip sign −1
其余 +1；zero 未定，shadow 数值仅作链路观察）→ field.sh/现场入口阶段 → Sync 重打包。
