# R41 盲爬楼/平地联合策略（2026-11-09 接入；15:00 起降级为离线对照，部署目标已切换为 R152，见 ../r152/README.md）

来源：`YuTaoV5/Rob2Nav` main 分支 `deliveries/as2w-deploy/omni-blind-stairs`（R41 代际），
工作站完整副本在 `部署参考/omni-blind-stairs/`（SHA256SUMS 校验通过）。

## 文件

- `policy.onnx`：ONNX 模型（obs[1,41] + state[1,835] → actions[1,16] + next_state[1,835]，50 Hz）
- `deploy.yaml`：关节序/默认姿态/限位/指令限幅（vx 0.6、vy 0.35、wz 0.8）。**本树内已把
  `policy_file: ../exported/policy.onnx` 改为同目录 `policy.onnx`**（适配 `models/r41/` 布局），其余与交付一致
- `r41-trace.csv`：750 帧参考轨迹，用于 C++ 回放逐帧校验

## 接口（与旧 .bin 58 维路径完全不同）

- 观测 41 维：机体系 vx/vy/wz 指令、IMU 角速度、投影重力、16 绝对位置、16 速度
- 递归历史 `state`[835]：模式进入清零，逐帧 `next_state` 回传
- 输出 16 维：12 腿位置目标 + 4 轮速度目标，关节序=contract 序（按关节类型分组）
- 无需官方基座线速度：由轮端运动学与历史观测估计平面速度

## 2026-11-09 验证记录（服务器 x86）

- 平地 MuJoCo（`evaluate_omni_joint.py`）：固定集 **41/52、零跌倒**（forward 0.2/0.4 m/s、
  倒退、左右转、停车全部 4/4；0.6 快进 2/4、纯侧移 1-2/4）；独立集 20/52、零跌倒——
  与交付 README 完全一致。本体感受审计 67,200 帧动作一致。
- C++ 回放（本树 `deploy/robots/as2w/r41/`，`-DAS2W_R41=ON -DONNXRUNTIME_ROOT=<ORT-1.22.0>`）：
  **750 帧 max_abs_error=0**，与交付 `cpp-replay.txt` 一致；根 CMake 原 7/7 测试无回归。
- **ONNX Runtime 必须为 1.22.0**：1.24.2 报 `TopK ShapeInferenceError` 拒载该模型。
- 楼梯边缘种子数值敏感：独立集 6 cm 我方 8/21 vs 同事 10/21（torch 版本差异；平地不受影响）。

## 待办（CPRO 侧，尚未开始）

1. ORT 1.22.0 aarch64 CPU 包经 HDC 传入 CPRO；yaml-cpp 需可用（或源码静态构建入现场包）
2. CPRO 上 `AS2W_R41=ON` 构建 + 回放校验；SDK2 只读 shadow（`shadow.cpp`）接线 field.sh/Windows 入口
3. R41 映射表：关节序=contract，DDS 槽位按 11:41 会话证据填（腿三元组+轮 12–15、侧别已定、
   前后 A/B 未定、零位未标定）——shadow 数值在 A/B 判定与零位标定前仅作链路观察
