# 给 OpenCode：AS2-W × CPRO R214 FSM 与趴下增益续作（2026-11-09 晚间）

你现在接手 Windows 工作站上 AS2-W × CPRO 的 R214 部署开发。**项目唯一权威目录**是 `D:\Projects\Athena\运动控制\Collie\AS2-W_CPRO`，在服务器通过已验证 SSHFS 挂载为 `/home/caolin/as2w_workstation`。先 `mountpoint -q ~/as2w_workstation`，确认挂载后才读写；断线或空挂载点绝对不要继续编辑。项目源码、交接、原始日志和调试总账均写回工作站；服务器本地仅放仿真依赖/缓存。服务器入口详见 `部署测试/05_OpenCode交接/README.md`。

## 必读顺序

1. 根 `AGENTS.md`、`部署测试/AGENTS.md`。其中旧 R41/R152 主线是历史；本文件和 INDEX 最新节覆盖策略选择。**每阶段无论成败立刻追加 `部署测试/04_调试记录/INDEX.md`，原始输出保存 `logs/`。**
2. `部署测试/04_调试记录/INDEX.md` 最新的 R214、增益、原厂力可观测性、WiFi 链路各节；以及 19:00 原厂 P10、19:40 ReleaseMode、19:49 固定 PD 失败、20:0x FixSquat 纠错。
3. `部署参考/cpp_deploy-as2w/config/hardware_contract.md`、`部署参考/cpp_deploy-as2w/config/r41_measured_identity_sign.md`、`部署测试/02_现场操作/实机事实与命令.md`。
4. `部署参考/cpp_deploy-as2w/models/r214/README.md`、`部署参考/Rob2Nav-r214-source/deliveries/as2w-deploy/omni-blind-stairs-r214/` 交付说明；`部署参考/cpp_deploy-as2w/deploy/robots/as2w/r214/` 只读 C++ 实现。
5. `部署参考/cpp_deploy-as2w/deploy/robots/as2w/r152/r152_publish.cpp` **只当 FSM 架构和已发现问题的参考，不可运行到狗上**；`部署参考/as2w-flat-rerun/r214_fsm_squat_rehearsal.py` 与 `results/r214_*.json` 是当前仿真事实。GO2 FSM 可借鉴 enter/run/exit 架构，不能照搬轴映射或增益。

## 设备、管理链和已做验收

- 工作站 WiFi `192.168.10.61`，服务器 `192.168.10.163`，CPRO wlan0 `192.168.10.180`，CPRO eth0 `192.168.123.100/24` 连接机器人。USB 已拔；HDC 使用 `192.168.10.180:10178` 的设备端 hdcrelay。通常现有 tconn 已连接；只在 HDC 服务器重启后 `hdc tconn 192.168.10.180:10178`。目标丢失先 `hdc list targets`。不可执行 `hdc tmode`、不可改 eth0/ip rule。CPRO 整机重启后 relay 需插回 USB、按 `logs/20261109-1952_opencode_wifi_hdc_link.md` 恢复。若 USB 与 WiFi 双目标并存，所有 hdc 命令必须加 `-t`。`hdc file send` 本机源必须绝对路径。
- 用户指定 Rob2Nav 分支 `codex/as2w-deploy` 的 `omni-blind-stairs-r214`，源提交 `b5b4add5b2ce9fe18690c0dee047dbc8eb2f7ea5`。模型 SHA-256 `b13ed59864fbcde46a6a4d986c2a3552edf2cc9523cfd136a0cf60091aa8f746`；obs 41、递归 state 1196、action 16、50 Hz；需 ONNX Runtime **1.22.0**。不要把 R152 的 844 维隐藏状态接到 R214。
- 已在 `部署参考/cpp_deploy-as2w/` 实现独立 R214 replay 和只读 shadow，CMake 选项 `AS2W_R214` 默认 OFF。服务器基础 CTest 7/7、工作站 `Sync`、CPRO ARM64 `R214Build`/CTest 7/7、1050 帧 `R214Replay` 最大误差 `9.53674e-07`、10 秒 `R214Shadow` 均通过。对应日志 INDEX 最新 R214 节。**尚无 R214 LowCmd 发布程序，也从未在这一阶段给狗发 LowCmd。**
- 16 轴已现场手动测得：DDS FR 腿 0,1,2；FL 3,4,5；RR 6,7,8；RL 9,10,11；轮 FR12、FL13、RR14、RL15。策略 contract 序 DDS 槽位 `[3,0,9,6,4,1,10,7,5,2,11,8,13,12,15,14]`；状态符号 hip 四轴 -1，其余 +1。hip/thigh 零位由限位法实测近 0；calf/轮相关合同逐条看 `hardware_contract.md`。**LowState 状态映射不等于 LowCmd 命令方向已验证。**
- 原厂遥控器已解码：A bit8，B bit9，X bit10，Y bit11；左摇杆 ly 前正。首测只允许 vx 0..0.2 m/s，vy=wz=0。只使用原厂遥控器，不使用 Xbox/键盘输入。遥控器接入的可观测性已验证，不等于低层模式下急停有效。
- `ReleaseMode()` 从趴下释放运控无动作；`SelectMode("ai")` 从趴下恢复会**直接令狗起立**。站立时 SelectMode 行为未验证，绝不能假设。轮命令语义、LowCmd 方向、断流行为、急停、退出/控制权回收均未做最小真机验收。

## 用户希望的 FSM 交互和目前设计判断

用户的按键意图：**A** 从趴下起立到 Stand，行走时按 A 回 Stand；**B** 从 Stand 开放策略行走；**Y** 从 Stand 受控趴下；**X** 紧急退控。用户强调 A 的 Stand 原想固定 PD，但质疑从策略姿态插值到固定 PD 导致下沉；并追问 Y 的 FixSquat 起点是否平滑。我们已经实际跑了 MuJoCo：`r152_publish.cpp` 当前 `Passive/FixStand/Stand/R152/ReturnStand/FixSquat` 结构中的固定 PD Stand/ReturnStand **6 组有 5 组非轮接触 >50 N、最高约 152 N，机身下沉**。它的 FixSquat 还有 F1 calf `start*0.5` 在负角上实际伸腿的方向错误；原旧轨迹完整下放甚至 253–1006 N、向下 1.35–1.82 m/s。因此这份 C++ 是**失败离线骨架，不可启动实机发布**。

下一版建议保留用户的按键含义，状态定义为：`Passive` → A → `FixStand`（两段预冲/起升）→ `PolicyStand`（R214 运行但 vx=vy=wz=0，持续平衡）→ B → `PolicyWalk`（R214，首测仅左摇杆前进限 0.2 m/s）→ A → `Brake`（R214 零速，实测轮速稳定）→ `PolicyStand`；从 `PolicyStand` 按 Y → `FixSquat`（从上一策略目标/轮速/增益**连续**接入，F1/F2 折叠下放）→ `Passive`；X 或全局故障 → `EmergencyDamping`。`PolicyStand` 是用户操作意义上的站立，**不是固定 PD 姿态**。Y 只从轮速稳定的 PolicyStand 允许。按钮事件按上升沿，阶段不得凭定时自动跨越用户预期的 Stand/Walk/趴下门槛。自动完成 FixStand 和 FixSquat 的内部阶段可以按轨迹时序推进。

X 的紧急阻尼可能导致站立的狗下沉，不能写成“无风险急停”。失联/遥控器异常的发布和模式回收规则必须取证、仿真并与现场人员按步骤约定；现有 `r152_publish.cpp` 的 watchdog→Passive/持续阻尼只是未经真机验证的候选。初期不得自动在退出时调用 `SelectMode("ai")`，因为从趴下可能突然起立。FSM 完成后也要明确退出控制权怎么回原厂服务，不能仅令进程退出/停发。

## FixSquat 仿真现状与当前要解决的增益问题

- 新 MuJoCo 脚本 `部署参考/as2w-flat-rerun/r214_fsm_squat_rehearsal.py` 已用 R214 ONNX 复演：FixStand→零速策略 Stand→0.2m/s 前行 4s→零速策略→FixSquat；F1 calf `start−0.3 rad`、thigh `start+0.2 rad`，F1 1.5s、F2 2.5s，从上一策略输出目标和增益平滑交接。初始 T1/T2×3 6/6 趴下、无翻倒，非轮接触峰约 42–76N、最大下落速度约 0.37m/s。末态静置接触峰约 7–11N。
- 单纯把 F2 拉到 3.5s，最坏约 75.8N；F1/F2 拉到 2.0/3.0s，最坏约 70N，无稳定优势。把 F1 末/F2 kp 提到 55/35、45/45、55/55 大多变差或趴下高度过高。初始 6 例腿 kd=3 比 kd=2 平均峰值 52.6 vs 61.3N、向下速度 0.30 vs 0.37m/s；独立 12 例 kd=3 平均 54.5 vs 58.5N、下落 0.29 vs 0.36m/s，但**最坏峰值 69.4 vs 66.2N 反而略高**。kd=3 是离线候选，不是安全定论。逐例 JSON、日志详 INDEX 最新节。另 `r214_gain_kd3_f2kp25.json` 已跑但尚未汇总。
- **最新用户关切**：原厂起立/趴下接触力峰到底多少，50N 是否过保守。已核对 HG `LowState_` 定义和 P10 `LOW_SAMPLE_SCHEMA`：只有 IMU 和电机 q/dq/ddq/tau/mode/temp，没有足端/机身或地面接触力列。因此**无法从现有原厂实测日志算出真实 N 峰值**；`tau_est` 27Nm hip 等也不能直接当接触力。50N 来自平地行走时非轮接触的严格步态评分，不能直接套在“故意趴下”的阶段。请先对当前 R214 仿真记录接触**部位、单点/总反力、持续时间/冲量、垂直速度、最小高度、力矩峰**，再对照原厂 P10 的 q/dq/ddq/tau 时序包络。可在同一 MuJoCo 模型**按明确假设**重演原厂轨迹做模型内相对比较，但不得标为“原厂实测地面反力”。如果有设备内可读的接触力话题可只读探索；没有就承认需外部测力设备。不要臆造原厂峰值或因为 50N 单阈值把当前方案一票否决。

## 现在按顺序执行

补充最新增益结果：`results/r214_gain_kd3_f2kp25.json` 6 例，F2 kp25、腿 kd3 峰最大 68.8N、均值 53.4N、最大下落速度 0.342m/s、末态高度平均 0.154m；相较 F2 kp35/kd3 初始 6 例的 63.7N、52.6N、约 0.30m/s，并未降低冲击。原始 `logs/20261109-2050_r214_gain_kd3_f2kp25.log`。

1. 先验证 SSHFS 挂载、读取上述事实，检查当前源码/测试状态。检查 `r214_gain_kd3_f2kp25.json` 和现有所有结果字段，汇总一张“真实原厂可观测量 vs 模型估计量”表，明确哪些不能比较。
2. 在服务器离线仿真补充原厂 P10 与 R214 趴下的**同类可比较量**（关节 q/dq/ddq/tau 及阶段时间；若仿真接触力与原厂轨迹重演比较，严格注明模型假设）。对 R214 kd=2/3 与 kp 变体做接触位置/持续时间、峰值和冲量、多种子对照。优先控制落地速度和有害碰撞；不要盲目仅拉长时间或提高增益。
3. 用明确的可复验离线验收条件定稿 `PolicyStand→FixSquat` 的连续控制。然后在独立 `r214_publish.cpp` 实现上述 R214 FSM，不把 R152 模型维数或错误 F1 带入。发布目标 CMake 默认 OFF，不纳入 `field.sh` 可直接启动阶段；显式确认参数与物理操作人确认门槛仍保留。先用 mock/no DDS 和 MuJoCo 验证状态迁移、按钮上升沿、policy state 保持、超时/紧急阻尼、站立到趴下的目标与增益连续性、CRC 与 mode_machine。C++ 改动**必须编译检查并过 7/7 CTest**，然后经工作站 `Sync` 和 CPRO `R214Build`/显式发布目标构建；记录真实日志。不要把编译成功当作真机通过。
4. 在 `hardware_contract.md` 和现场链方案列出剩余最小实机取证门槛：LowCmd 命令方向/单轴幅度、轮速度正向、原厂遥控器低层急停、断流/失联、SelectMode 站立行为、退出回收。厂商不会提供，设计可控、一次一项的现场测试。**任何可能使狗动作的命令，每一次都先向现场人员说明具体动作与退出手段，并等当次明确同意；未同意只做离线/只读工作。**目前不要运行发布端或触发原厂动作。
5. 每个阶段完成或失败立刻追加 INDEX，归档原始命令/输出；必要时更新本交接提示词和 AGENTS 顶部状态，确保下一位代理能继续。

## 重要坑

- `现场入口.ps1 -Seconds` 上限 300；HDC file send 本机源必须绝对路径；ONNX Runtime 固定 1.22.0；脚本中 `AS2W_R214` 默认 OFF。
- 旧 C++ 曾因模糊替换引入 `src.q()` 笔误，编辑后必须本地/ARM64 编译检查。
- AS2、GO2-W、B2-W、URDF 轴序不能代替现场 AS2-W 16 轴实测；不能把只读 shadow 说成闭环控制。
- 2026-11-09 19:25 的“FixSquat 6/6 全绿”只验证最终姿态，没检查完整接触力，已被后续详细仿真纠错。

开始时先简短告诉现场人员：你已经读到的当前状态、接下来只做哪些离线/只读工作、不会发动作；完成一个阶段就写日志。不要询问厂商资料，也不要把上面作为未经核对的事实照抄到发布代码。
