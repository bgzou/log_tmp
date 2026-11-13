# 给 caolin 服务器 OpenCode：R1199 直接修复与明日实机接续

日期：2026-11-12。项目唯一权威根目录在 Windows 工作站 `D:\Projects\Athena\运动控制\Collie\AS2-W_CPRO`；caolin 上通常经 SSHFS 挂到 `/home/caolin/as2w_workstation`。**用户已明确：旧故障两次实机复现足够，不要再花时间重跑旧版 MuJoCo 故障。直接修复并验证新候选。**你现在负责后续代码、离线验收、到实验室后的分阶段实机调试与记录，直到可判断抖动和停走姿态是否改善。本文是新的当前任务书，覆盖之前 A/B/C 旧故障复演计划。

## 必须先读及判定优先级

1. 项目根 `AGENTS.md`、`部署测试/AGENTS.md` 的最上方新状态；`部署测试/04_调试记录/INDEX.md` 最后两节。旧时间戳表述一律让位于新节。
2. `部署测试/02_现场操作/R1199二次实机抖动与停走姿态切换分析_20261112.md`、`R1199训练服务器与实机包装对齐审计_20261112.md`、`AS2-W训练到部署交付清单_v3_通用核心与按需模块.md`。
3. `部署测试/06_训练协作/R1199_real_robot_feedback_20261112.zip` 的 `README.md`、`MANIFEST.sha256`、两次实机日志和两张图。该包在没有工作站挂载时仍可独立读取；但包内源码可能早于本任务书下面列出的最新本地修复，以挂载工作站**唯一维护源码**为准。
4. 源码 `部署参考/cpp_deploy-as2w/deploy/robots/as2w/r1199/{r1199_controller.cpp,CMakeLists.txt,r1199_replay.cpp}`、`tools/r1199_training_forward_parity.py`、共享发布端 `deploy/robots/as2w/r214/r214_publish.cpp`、会话入口 `tools/run_r1199_field_session.sh`、Windows `部署测试/运行现场策略会话.ps1`。上游 Python 动作包装位于 `部署参考/Rob2Nav-R1199-trainserver-readonly-snapshot/as2w_rolling_fixed_exit.py`；实际训练合同本地副本是 `部署测试/04_调试记录/logs/20261112_r1199_actual_training_contract_readonly.json`。

## 已经查明，不要重新争论

- 用户两次在**前后滚动过程中**听到真实关节抖动；不是只在 B 交接或首次推杆。第二轮 10ms 状态流：前进窗口 12腿 `dq` RMS 0.1113rad/s（安静零速0.0066），估算力矩去0.2s慢变化 RMS 0.6799Nm（安静0.0181）。前进中途 FR 髋 `dq/tau_est` 连续正负交替。两轮硬件保护位全0，仅各一次首次推杆目标跳步软件warn（0.272911/0.254249rad）；无保护报警不能否定抖动。
- **正确权重溯源**：release `model_1199.pt` SHA `bb5c9735b5bd37ef4bdd2bd13f9d45395d8dc9b4c888c36955de1a345d55776d`，对应同事训练服务器 `rolling-knee-margin-formal/model_1199.pt`。实际训练合同明确 `park_continuous_bias=true, park_straight_bias=true, park_odometry=false, park_settle_joints=false`。早前看的 `rolling-fixed-exit-formal` 是较早 `model_550.pt`，**禁止再当作 R1199 合同**。
- 旧实机 C++/950帧 parity 走的是站姿补偿 false/false、停车 odometry/settle true/true，故虽然 parity 误差小，却没有对齐这版训练。真实训练及部署腿PD标称都为55/2；这不证明真实执行器动力学一致。训练服务器作业 `git/` 为空，当前源码在训练结束后修改；精确训练时源码快照仍缺，但四个开关的运行实值有合同直接证据。
- `hold_frames` 首次非零命令清零，使旧分支站姿补偿可一帧撤掉；松杆再渐入，能解释停走时整机升降。**运动中成串抖动是否也由该失配导致，尚未证实**，必须用修复版实机日志判断。不要盲改所有 `kp/kd` 或直接把声音归因于训练。
- 当前工作站旧 R1199 `-Mode joystick` 被硬阻断；CPRO 上此前同步的旧远端脚本可能仍可直接运行，**绝不可绕过工作站阻断调用**。本地源码已有修复候选，但**未编译、未 MuJoCo/ARM64 验收、未同步 CPRO、未上狗**。

## 本机已做的直接修复候选（请审查后接续）

只改 `AS2W_R1199_TRAINING_CONTRACT=ON` 的**独立 joystick 构建**；选项默认 OFF，不改变已验收旧二进制。`r1199_controller.cpp` 中该分支现按正确训练合同：`continuous/straight=true/true`、轮停车参考用原始轮角（不做 park odometry）、停车安静条件不再加腿速、锁存时间0.12s、停车轮速用逐轮 `-6*error` 限幅±1.5再除16（无 common feedback）。`tools/r1199_training_forward_parity.py` 新增 `--training-runtime` 对照这四项。旧实机入口本地脚本保持硬阻断；新候选必须新建单独 build/launcher，**不得覆盖 `build-r1199-joystick` 或重开旧 `-Mode joystick`**。

请先做静态审查，特别检查 Python `rolling_wheel_hold` 的跨阈值捕获帧、原始/包装动作回填到 previous-action、轮角回绕、`rolling_precalibrated_stand` 的直行插值、所有16轴增益与符号。发现不匹配就修此候选；保留默认 OFF 和旧构建隔离。代码改动后必须编译。不要把`AS2W_R1199_TRAINING_CONTRACT`误当作只改站姿补偿的开关，它同时修正停车三项。

## 明天执行顺序（旧故障不复演）

### P0：访问与只读盘点

- 先检查 `mountpoint -q /home/caolin/as2w_workstation`。若空挂载目录或掉线，停止写入；按`部署测试/05_OpenCode交接/README.md`恢复 SSHFS。不要在空目录造一份新项目。若工作站暂不可达，可先用上面的独立 ZIP 阅读和计算，但最终源码/日志必须回到 Windows 项目。
- caolin 上 `opencode` 用 `/home/caolin/as2w_workstation` 启动，服务器本地 `/tmp/opencode/` 只放**隔离编译/仿真缓存**。不要 `git add -A`，不要在 SSHFS 上执行全库递归拷贝/删除。工作站与 CPRO 的管理链走 Windows `hdc.exe`；服务器不能直接运行 Windows HDC。默认 HDC 目标是 `192.168.10.180:8710`，`10178` 仅为已核实的回退；IP/网口以现场只读检查为准。
- 明日狗若已上电，可先只读确认 CPRO `eth0` 载波、LowState 约1kHz、mode_machine=2、原厂FSM/16轴mode、保护位、无残留发布端。此步**不执行 ReleaseMode、SelectMode 或 LowCmd**。把环境/设备状态写 INDEX。

### P1：直接修复版离线验收

- 从唯一维护源码构建**独立** x86 候选目录（例如 `/tmp/opencode/r1199_training_contract_build`），配置 `AS2W_R1199_JOYSTICK_CANDIDATE=ON`、`AS2W_R1199_TRAINING_CONTRACT=ON`、`AS2W_R1199_PUBLISH=ON`，使用实际可用的 ORT/SDK2 路径；增量编译、CTest、`--offline-audit`。不要删历史 `build-r1199-joystick/forward/zero-b`。编译失败就修编译，不得以源码审阅替代编译。
- 用新构建 `as2w_r1199_joystick_replay` 产生覆盖零速、`+0.05→0→−0.05→0` 的 65维观测/最终动作记录；用 `tools/r1199_training_forward_parity.py --training-runtime` 与训练 Python 包装逐帧比对，报告最大动作误差、上一动作历史误差、最差帧。目标至少达到既有1e-5数量级；若不达，定位第一处分歧再修。**不跑旧版故障仿真作为门槛。**
- 只跑**新修复版**的 MuJoCo：实测 FixedStand `q/dq/quat` 起步，B交接→零速→+0.05m/s持续至少5–10s→松杆→−0.05→松杆→Brake/ReturnStand→Y；保持同一资产、增益、摩擦及随机种子，记录完整50Hz raw ONNX/包装后16轴/最终目标、物理子步轮载/非轮接触、机身高度、关节q/dq/tau和最大单帧目标变化。重点单列**持续前进中段**，不能只看起步与通过率。若候选仍出现明显周期振荡、轮卸载/非轮触地、停车长尾或目标跳步，继续修候选；不可把其宣布可真机。
- 必须区分仿真与实机：仿真没有声音/高频电流模型，仿真平顺只能进入**有界实机首测**，不证明抖动根因已经消失。每阶段原始命令/配置/模型/源码SHA和结果写 Windows `部署测试/04_调试记录/logs/`，完成即追加 INDEX。

### P2：准备独立现场包，不自动让狗动作

- 离线通过后才同步**新候选**到 CPRO，用独立 `build-r1199-training-contract`（ARM64 ORT1.22/SDK2），重新编译、CTest、audit、核源码/模型/二进制 SHA。修改源码后按项目规则重新`部署测试/准备现场包.ps1`；不得手工改现场压缩包。
- 新建或扩展**独立命名**的现场入口，复用现有 `run_r1199_field_session.sh` 已验证的预检（binary/SHA/audit→LowState→趴下→控制权→16轴mode0→双监测→Passive唤醒）；新入口指向**新构建**。不要取消 Windows `-Mode joystick`旧版阻断、不要直接运行 `run_r1199_joystick_trial.sh`、不要跳过 ReleaseMode/16轴mode/监测门槛。新增原始/包装动作、补偿系数、最终目标和安全守卫的时间戳诊断，优先限频并确保发布周期不受阻塞影响。
- 在**狗不会动作**的 dry-run/只读阶段验证新入口和日志归档，然后报告现场人员：候选哈希、离线结果、下一次具体动作和风险。此处停止等待本次动作许可；先前任何同意都不覆盖明天的试验。

### P3：经现场人员逐次明确同意的修复版实机验收

按从小到大逐次进行，每一步都**提前说明具体会执行的动作、可能下沉/抖动/告警/失撑、现场急停方式，等用户对该次明确同意才调用动作命令**。确认场地平整、狗趴下、人员握原厂遥控器和物理急停。Ctrl+C经Windows→HDC不可靠，不能作为运动急停；异常使用 X/物理急停并停止继续试验。

1. 新候选 `A固定站→B强制零速短接管→自动Brake/回站→Y趴下`。先确认无新的腿目标跳步、姿态突降、保护告警和可闻抖动。
2. 新候选有界 `+0.05m/s` 前进约2秒、自动零速/刹轮/回站/Y；检查真实移动、腿/轮dq、tau、保护、接触观感及停车后滑动。只这一步通过才考虑后退。
3. 新候选**短时**前后轻推/松杆（例如10–15秒总策略窗），不要直接重开60秒自由摇杆；为比较“停走抬升”至少做一次`前进→松杆`，为比较“运动中抖动”保留数秒稳定前进窗口。运动中若仍听到明显抖动，即刻停止推进，回收会话并按 raw ONNX→包装→最终目标→实际 q/dq/tau 顺序定位；不重复试旧版本。转向另行逐次验收，不能与前后结果混写。

每次动作后优先回收 CPRO `field_sessions/<时间>_<模式>/` 四份原始日志到 Windows `部署测试/04_调试记录/logs/field_sessions/`，核大小/SHA；记录现场人员描述、机器当前姿态/控制权、Publisher RC、保护位和软守卫。即使失败/急停也立即追加 INDEX。`SelectMode("ai")` 可能让狗从趴下直接起立，恢复原厂控制也须当次许可。

## 修复后仍抖时的分流

- raw ONNX 动作在稳态已周期变化：保留可重跑夹具交同事训练侧，检查低速命令分布、动作变化奖励、执行器随机化和观测噪声；不要用“仿真通过”解释现场声音。
- raw平顺、包装后目标振荡：修包装/停车状态机，重做 parity、MuJoCo 和编译。
- 目标平顺、实际关节/估算力矩振荡：比对PD增益、延迟、编码器/速度滤波、轮地接触，必要时同步录音/高频电流。调 `kp/kd` 必须是独立受控候选并重做离线门槛，不得以其他策略增益当通用值。

最终交付：最新修复源码/构建哈希、可复现离线证据、每次实机会话原始日志和量化对照图、INDEX各阶段条目、是否可继续扩大运动范围的明确结论，以及给训练同事缺失材料的清单。**现在没有授权任何新实机动作；不要因为看到本任务书就自动 ReleaseMode 或发布 LowCmd。**
