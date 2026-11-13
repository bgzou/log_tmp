# 给服务器 OpenCode 的 R152 续作提示词（2026-11-09 下午）

你接续 AS2-W × CPRO 实机策略部署。**Windows 工作站项目根** `D:\Projects\Athena\运动控制\Collie\AS2-W_CPRO` 是源码、现场包、原始日志和调试总账的唯一权威位置。你在服务器 `192.168.10.163` 的 `caolin` 账号运行，Windows 项目通过 SSHFS 挂载在 `/home/caolin/as2w_workstation`。**每次开始先 `mountpoint -q ~/as2w_workstation`，挂载失效时不得向空目录写文件。**不要将任何密码写入文件或输出。

## 首先读取

1. `~/as2w_workstation/AGENTS.md` 与 `部署测试/AGENTS.md`：安全规则、阶段日志规则。
2. `部署测试/04_调试记录/INDEX.md` 的 14:07–14:56 G1 六节和最新 R152 节；`部署测试/02_现场操作/G1关节手动标定记录.md`。
3. `部署参考/cpp_deploy-as2w/config/r41_measured_identity_sign.md` 和 `hardware_contract.md`：16 轴**状态**映射已实测，零位与 LowCmd 仍未实测。
4. `部署参考/Rob2Nav-r152-source/deliveries/as2w-deploy/omni-blind-stairs-r152/README.md`、`runtime/audit_flat_geometry.py`、`unitree_cpp_deploy/robots/as2w` 相关源码与 `deploy.yaml`。
5. 旧交接书 `部署测试/05_OpenCode交接/给Codex的交接提示词.md` 的 G2–G5 顺序；**R41 已被用户明确替换为 R152**，所有状态维度/模型文件/回放轨迹必须改用 R152，不能混用。

## 现在状态与硬规则

- 用户刚明确把部署策略换成 GitHub `YuTaoV5/Rob2Nav` main 的 `deliveries/as2w-deploy/omni-blind-stairs-r152`，要求先复测 MuJoCo，服务器可用于仿真。源码已 sparse clone 在 Windows `部署参考/Rob2Nav-r152-source/`，HEAD 固定 `40c80f0e07362b0a8e38528379076355d50ecbf5`；R152 交付本身约 3 MB，包含 `weights/policy.pt`、ONNX、`state[1,844]`、C++ replay/shadow、trace、评估 JSON。旧 R41 是 `state[1,835]`，不得混合。
- 现场人员已在狗 `ai_damping` 下完成 12 腿关节+4 轮逐项手动标定；六段原始 100 Hz 日志都在本机 `部署测试/04_调试记录/logs/`，CPRO 全量归档 `cpro_field_logs_20261109_G1_complete.tar.gz`。实测物理轴：FR=(0,1,2)、FL=(3,4,5)、RR=(6,7,8)、RL=(9,10,11)；轮 FR=12、FL=13、RR=14、RL=15。R41 contract 序的槽位 `[3,0,9,6,4,1,10,7,5,2,11,8,13,12,15,14]`。R152 `deploy.yaml` 关节序目前看与 R41 相同，仍请逐行核对。模型几何结合人工动作推得 LowState 状态 `sign` 为 hip 四轴 −1，其余 12 轴 +1。**这不证明 LowCmd 命令方向。**
- 站姿旧报告 calf −2.09 rad 是把趴下/站立样本混合平均的错误；11:41 长静止原厂站姿实际 calf ≈−1.23、thigh≈0.60、hip≈±0.12。原厂站姿是否等于训练默认姿态未证实，`zero_DDS` 全部未定。`calibrated.map` 保持 UNVERIFIED。
- **任何可能让狗动作的命令，先告知现场人员具体动作并等待其当次明确同意。**此前突然起立吓到用户，绝不能重犯。只读查询/离线仿真可继续。用户只用原厂遥控器，不用 Xbox/键盘。未补齐 `hardware_contract.md` 的零位、LowCmd 模式/CRC、接管/恢复、急停/失联前，**绝不发布 LowCmd**。厂商不会提供缺项，必须自主按只读/隔离取证，不以等待厂商作为结论。
- 每完成阶段或失败，立刻追加 Windows 本机 `部署测试/04_调试记录/INDEX.md`，原始日志放 `logs/`。不要覆盖旧条目。CPRO `field_logs/` 要回收到 Windows。C++ 改动必须编译检查；HDC 传文件本机源用绝对路径；`现场入口.ps1 -Seconds` 最大 300。

## R152 MuJoCo 复测：Codex 已完成，需据此继续

- 服务器 Python `mujoco==3.17.0`、`torch==2.15.0+cpu`、`onnxruntime==1.31.1`；**R152 ONNX 已在此 ORT 版本成功加载**，输入 `[1,41] + [1,844]`。R152 README 报告 ONNX 固定集跟踪/停车 44/52、严格接触/步态 21/52；独立集 25/52、严格 9/52；104 例零跌倒/前轮换边。需要独立复跑并检查失败类型，不能仅复述 README。
- 服务器本地仿真资产缓存 `/home/caolin/as2w_r152_assets/`，由 Windows 项目已有官方 AS2-W mesh/URDF、R41 交付的相同 XML/contract 复制；两份 XML/contract 的 SHA-256 分别 `2bf148d8e0e5722db4a581c7cf7834611121025cc1c95c14f892b83bc0fdfa01`、`1e4e3fb76806e83dbe3541979fa0cb40f4b3150f5bf4de298224bf9baa9b0490`，与 GitHub main 上 R152 旁的原始资产一致。缓存是计算用，**结果必须写 Windows 挂载项目**。
- Codex 已完成 `runtime/audit_flat_geometry.py`：Python 与 ONNX 各跑固定 52 + 独立 52（共 208 次），退出码 0。输出目录 `部署测试/04_调试记录/logs/r152_verify_20261109/`，原始终端日志 `部署测试/04_调试记录/logs/20261109-r152_audit_server.log`。**ONNX 完全复现交付的逐例布尔标记（104/104、mismatch_count=0）**：固定跟踪/停车 44/52、严格接触/步态 21/52；独立 25/52、严格 9/52；零跌倒、零前轮换边。Python 复测固定 44/52、严格 22/52；独立 28/52、严格 10/52，与交付 Python 的逐例标记有 10 个小差异，见 `logs/20261109-r152_compare_published.log`。**以导出 ONNX 闭环为部署依据。**
- 严格失败类型已经分解：ONNX 固定集 44 个跟踪通过者中有 23 个因**非轮部位触地峰值 ≥50 N**而严格不通过；独立集 25 个跟踪通过者中有 16 个同理；自碰撞 ≥1 N 和前轮换边在通过跟踪者中均为 0。逐命令统计见 `logs/20261109-r152_failure_breakdown.log`。这表明策略有平地运动能力，但**严格接触表现不足以把 44/52 直接视为安全通过**。继续接入前先审查这些接触峰值的身体部位、时段和幅度，以及是否是模型/接触阈值问题；不要简单忽略严格指标。
- 首次非轮触地部位统计：固定集不合格 23 例中 `RL_calf` 11、`RR_calf` 8、`RL_thigh` 2、`RR_thigh` 2；独立集不合格 16 例中 `RR_thigh` 5、`RR_calf` 5、`RL_calf` 5、`RL_thigh` 1。固定峰值约 50.4–122.3 N（中位 59.1），独立约 53.6–167.3 N（中位 84.2），原始汇总 `logs/20261109-r152_contact_bodies.log`。
- 如需手动复跑，工作目录 `~/as2w_workstation/部署参考/Rob2Nav-r152-source/deliveries/as2w-deploy/omni-blind-stairs-r152/runtime`，命令：`python3 -u audit_flat_geometry.py /home/caolin/as2w_r152_assets ../weights/policy.pt ../unitree_cpp_deploy/logs/as2w/r152/exported/policy.onnx ~/as2w_workstation/部署测试/04_调试记录/logs/r152_verify_20261109`。所有命令/版本/哈希/输出须入 INDEX。

## 复测后的顺序

1. **先复核 R152 严格接触失败**：读取 `r152_verify_20261109/onnx-flat.json` 与交付 `evidence/onnx-flat.json`，按命令/身体部位/时间/峰值列出失败模式，重点检查 `first_ground_hit`，并考虑与 R41 的相同严格判据作可比复测。给用户明确解释“跟踪/停车通过”与“接触/步态严格通过”的区别；不把 44/52 说成 44/52 全部动作安全。实机闭环须由合同和受控门槛决定。
2. 经仿真证据决定接入后，把 R152 ONNX、YAML、750 帧 trace、C++ controller/replay/shadow 和来源/哈希系统地迁入唯一源码 `部署参考/cpp_deploy-as2w/`。R152 应成为新 stairs 主线，旧 R41 保留离线对照并更新 README/manifest/阶段入口；不要只改模型名。C++ `state` 必须 844。先在服务器 x86 用 ORT **1.22.0** 对照交付 `evidence/cpp-replay.txt` 跑 750 帧，再考虑 CPRO ARM64 构建；目前服务器 ORT 1.31.1 可载 ONNX，但交付 C++ 验证版本是 1.22.0。
3. G2 CPRO 环境/离线回放/只读 shadow。CPRO Ubuntu 22.04.5 aarch64、SDK2 DDS 链路已通，仍需 ORT 1.22.0 ARM64 CPU 包、yaml-cpp，并把 `field.sh` 和 Windows `现场入口.ps1` 增加 R152 阶段，重打包/Sync/ARM 编译。任何 C++ 改动先编译检查；只读 shadow 在零位未定时数值只供观察。
4. G3–G5 仍按旧交接的低层合同→MuJoCo 起身整链→逐步实机顺序，但**不能把目前的 LowState 状态 sign、原厂 stand 姿态或假设 map 直接变成 LowCmd 写入**。每条物理动作必须提前逐条获同意。

服务器可从 Windows 工作站用密钥 SSH 登录；密钥路径在 Windows 用户 `.ssh/as2w_server`，不在项目内，勿复制私钥入项目。服务器→Windows 的 SSHFS 原有密钥仍保留。项目所有日志与 handoff 文档只存 Windows 路径。
