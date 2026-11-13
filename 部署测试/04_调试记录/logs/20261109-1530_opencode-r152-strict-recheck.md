# 2026-11-09 15:2x OpenCode 会话：R152 严格接触复核 + R41 同判据可比复测 + R152 系统迁移

- 执行者：服务器 OpenCode（SSHFS 挂载正常）；本阶段零机器人命令、零 HDC、零 CPRO 写入。
- 环境：服务器 Ubuntu 24.04、Python 3.12.3、MuJoCo 3.17.0、torch 2.15.0+cpu、ORT 1.31.1（Python）/
  ORT 1.22.0 x64（C++ 回放，复用上午缓存）；仿真资产 `/home/caolin/as2w_r152_assets/`（SHA 与交付一致）。

## 一、R152 严格接触失败复核（读 r152_verify_20261109/onnx-flat.json + 交付 evidence）

- 与交付 evidence 逐例核对：`passed/qualified/fallen/front_cross_ticks` mismatch **0/104**。
- 失败结构（跟踪通过而严格不过）：
  - 固定集 23/44；独立集 16/25。**全部由非轮部位触地峰值 ≥50 N 造成**（自碰撞 ≥1 N 与前轮换边在这些回合均为 0）。
  - 部位全部是后腿：固定 RL_calf 11、RR_calf 8、RL_thigh 2、RR_thigh 2；独立 RR_thigh 5、RR_calf 5、RL_calf 5、RL_thigh 1。
  - 时刻：固定集加速段(<1.5s) 8、跟踪段(1.5–4s) 10、**停车段(≥4s) 5**；独立集加速段 9、跟踪段 2、停车段 5。
  - 力：固定首触中位 57.4 N（50.4–122.3）；独立 67.7 N（50.8–147.9）。
- **按命令的剂量效应（固定集，跟踪通过/其中严格通过）**：stop 4/4、forward_slow 4/4、reverse 3/4、
  turn_left 3/4、right 2/2、left 1/2、forward 1/4、turn_right/arc_left/arc_right 1/4、
  forward_fast 0/4、diagonal 0/2+0/2。**慢速域（stop、0.2 m/s 前进）100% 严格干净。**
- 判据澄清（写给用户/后续会话）：跟踪/停车通过（44/52）≠ 安全通过；严格通过（21/52）另要求
  前轮不换边、自碰撞 <1 N、非轮触地 <50 N。后腿刮擦是 gait 质量问题（不倒、能跟踪），
  实机上意味着后腿小腿/大腿以 50–167 N 峰值拍地——真实硬件风险是冲击磨损与姿态扰动。

## 二、R41 相同严格判据可比复测（新脚本 r41_audit_strict.py）

- 方法：在 R41 runtime 树内单进程运行（避免两树同名模块污染），复用与 R152 audit 完全相同的
  filtered 模型（仅排除 FL/FR_thigh–base_link 名义重叠对）、相同 104 种子/命令、相同 capture 与
  qualified 判据；脚本内断言 R41 的 FLAT_COMMANDS/gait_clock 与 R152 逐项一致。
- 自洽性：R41 经该 harness 的跟踪结果 41/52（python）、40/52（onnx）、20/52、20/52，
  与 R41 自己发布的 fixed/confirmation 完全一致 → harness 驱动无失真。
- **结果**：
  | 相同判据 | R41 py | R41 onnx | R152 py | R152 onnx |
  | --- | --- | --- | --- | --- |
  | 固定跟踪 | 41/52 | 40/52 | 44/52 | 44/52 |
  | 固定严格 | **13/52** | **12/52** | 22/52 | **21/52** |
  | 独立跟踪 | 20/52 | 20/52 | 28/52 | 25/52 |
  | 独立严格 | **4/52** | **5/52** | 10/52 | **9/52** |
  | 前轮换边（跟踪通过者，固定） | **18/41** | 18/40 | 0 | **0** |
- 换边机制：R41 的 StopStance 是**前腿内收交叉站姿**——stop 回合 292/300 tick 前轮越过中线
  ~12 cm（front_min≈−0.12 m），forward/forward_slow/forward_fast/reverse 也 4/4 换边。
  R152 完全消除此问题。
- 注意（诚实记录）：后腿触地是**两代共性**，且 R152 在跟踪通过者中的触地比例反而更高
  （固定 23/44=52% vs R41 10/41=24%），但被零换边+更高跟踪/严格率补偿——**净结论：R152
  在相同判据下全面优于 R41，用户切换决策有据**；触地问题不因切换消失，实机起步仍应限制在
  stop/forward_slow 严格干净域。
- 原始：`部署测试/04_调试记录/logs/r41_strict_verify_20261109/{python,onnx}-flat.json`；
  脚本 `部署参考/as2w-flat-rerun/r41_audit_strict.py`。

## 三、R152 系统迁移入唯一源码树（cpp_deploy-as2w）

- 新增 `models/r152/{policy.onnx, deploy.yaml, r152-trace.csv}`（yaml 仅 policy_file 改同目录，
  其余与 R41 逐字一致）+ `deploy/robots/as2w/r152/{r152_controller.cpp/hpp, replay.cpp, shadow.cpp,
  CMakeLists.txt}`（CMake 相对路径 ../../→../../../ 适配子目录；保留交付新增的
  `libonnxruntime.so.1` 库名候选）；根 CMakeLists 加 `AS2W_R152` 选项（与 R41 并列）。
- x86 验证：`-DAS2W_R152=ON -DONNXRUNTIME_ROOT=<ORT-1.22.0>` 构建通过；
  **回放 750 帧 `rows=750 max_abs_error=0 leg_and_wheel_targets=verified stale_state=latched_off`**
  （与交付 evidence/cpp-replay.txt 逐字一致）；根项目 CTest 7/7 无回归。
- manifest.json：`onnx_policies.r152`（status=active deployment target、接口、验证、R41 对比、
  哈希）置顶，r41 标注 superseded；`models/r41/README.md` 与 `models/r152/README.md` 状态已更新。
- SHA-256：policy.onnx `fdc661f9…f5d1`、r152-trace.csv `9e31a294…945a`。

## 四、未解决/下一门槛

- CPRO 侧 R152 部署未开始：ORT 1.22.0 aarch64 CPU 包、yaml-cpp、`AS2W_R152=ON` ARM 构建+回放、
  `shadow.cpp` 只读探针（G1 实测映射表：contract 序槽位 `[3,0,9,6,4,1,10,7,5,2,11,8,13,12,15,14]`、
  hip sign −1 其余 +1；zero 未定）+ field.sh/现场入口 R152 阶段 + Sync 重打包。
- 实机测试链方案文档（passive→fixstand→R152→遥控器行走）另见
  `02_现场操作/实机测试链方案_R152.md`（本阶段产物）；其执行门槛=零位标定+LowCmd 合同+
  看门狗+逐条同意，未全部满足前不发布任何 LowCmd。
