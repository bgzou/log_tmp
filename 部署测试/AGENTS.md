# AS2-W / CPRO 现场协作规则

**2026-11-13 网络地址迁移提示：** 路由器重分过地址，本文件与更早条目里写死的 `192.168.10.61`（工作站）、`192.168.10.180`（CPRO）等均为当时快照——当前以实测为准，恢复流程与路径映射见**根目录 `AGENTS.md` 文末常设节「双机拓扑与网络变更」**。当前：工作站 `192.168.10.34`、CPRO WiFi 暂 Offline（USB 正常）。

**2026-11-12 22:43 Debug/低通候选现行状态：** R1199 40ms 腿目标低通已完成15秒和30秒两轮获当次许可的实机摇杆测试；最终 LowCmd 25013+30886行无丢，完整保护流10681+12952行无保护位，软件守卫未触发。现场认为前后比无滤波丝滑，但转向仍几乎不动；第二轮实测输入约±0.09rad/s，IMU偏航角速度均值仅约±0.02–0.025rad/s。当前仅独立 R1199 `-Debug -LowPassMs 40` 候选可在新的当次许可后有界运行：前后≤0.2m/s、yaw≤0.1rad/s、PolicyWalk≤30秒、轮速不滤；其他滤波配置仍锁定。转向性能/长期运行未验收，不能直接提高yaw上限。详见`04_调试记录/INDEX.md`最新节及`logs/20261112_r1199_lp40_field_summary.txt`。

**2026-11-12 训练策略交付清单现行版：** `02_现场操作/AS2-W训练到部署交付清单_v3_通用核心与按需模块.md`。所有策略交可复现接口和版本核心；行走、停车、起身、楼梯等专项按实际技能启用。不适用写原因，未测试写 `not_run`，不强求训练方完成第二仿真器；v1/v2 为历史版。

**2026-11-12 训练合同对齐硬规则（长期）：任何策略的运行时开关、动作包装、腿/轮增益必须与训练 `actual_runtime_flags` 逐项一致；仿真（MuJoCo/Isaac）与实机验收、部署 C++ 编译宏必须用同一份合同，禁止默认关闭/手工挑开关，任何差异即新版本。** 权威合同 `06_训练协作/R1199_real_robot_feedback_20261112/docs/policy_delivery_contract.md`。

2026-11-12 上午：R1199训练合同修复候选离线验收完成（覆盖01:30“尚未编译”旧状态）。静态审查通过并修一处（锁存轮覆盖→叠加`+=`），x86编译/CTest9/9/offline-audit PASS、950帧parity`1.192e-7`、仅新候选实测站姿MuJoCo前进后退×3种子10s全stable/tracked/held、无非轮接触、前进中段最大单帧腿目标步进0.063rad；并复现了停走姿态跳步（旧诊断分支首推0.124–0.127rad，新候选无起步跳步）。**尚未ARM64/同步CPRO/真机**；详见`02_现场操作/R1199训练合同修复候选离线验收_20261112.md`。P2/P3每次动作仍须现场当次明确同意。

2026-11-12 01:30：用户要求停止旧版故障复演，转为R1199训练合同修复。默认OFF的`AS2W_R1199_TRAINING_CONTRACT`源码候选已修正站姿补偿与停车四项，**尚未编译/仿真/同步/实机**。旧joystick入口仍阻断，CPRO旧远端脚本不可绕过。当前执行书`05_OpenCode交接/给OpenCode_R1199训练合同修复与明日实机接续_20261112.md`；每次可能动作仍先明确告知并获现场当次同意。

2026-11-12 01:15：R1199 真实训练合同补证 `continuous/straight=true/true`、`odometry/settle=false/false`，与实机旧C++不一致；较早550权重合同不再用于R1199。两轮**前后滚动时**现场可闻抖动，第二轮10ms状态量化运动段 `dq/tau_est` 波动；见`02_现场操作/R1199训练服务器与实机包装对齐审计_20261112.md`及独立外发包`06_训练协作/R1199_real_robot_feedback_20261112.zip`。明日仅离线同条件复演，旧joystick阻断不变。

2026-11-12：R1199旧摇杆入口两次实机均出现停走姿态切换及单帧腿目标warn，工作站一键脚本已阻断旧`joystick`，不影响`joystick-dry-run`。第二轮四份CPRO日志已拉回本机并核SHA；CPRO远端可能仍开旧脚本，禁止绕过工作站入口。正式连续补偿C++源码候选未编译/仿真/同步，不能上狗。权威分析与交付要求见`02_现场操作/R1199二次实机抖动与停走姿态切换分析_20261112.md`、`AS2-W策略交付合同_v1_20261112.md`及INDEX最新节。

2026-11-11 夜：现场人员明知首次摇杆推杆出现姿态下降、0.273rad单帧软件warn及可闻抖动，要求解除入口锁自行复测；R1199 `joystick`会话按原控制器恢复，预检/监测/60秒策略上限不变。复测仍需现场看护、记录观感并更新INDEX。此条覆盖下方入口硬阻断旧状态，其他禁令不变。

2026-11-11 23:40：R1199摇杆首试完成（前后、无转向），一次腿目标步进软件warn，主板/电机硬件保护位全程0；现场报告姿态下降和可闻关节抖动。`joystick`现场入口现硬阻断，暂停复测，详见INDEX最新节和`04_调试记录/logs/20261111_r1199_joystick_review.md`。Ctrl+C不作为运动急停；发布端结束后的监测空等已修为5秒尾段。

2026-11-11 23:13：R1199在当次许可下完成一次B后自动0.05m/s两秒前进、自动刹轮回站及Y趴下，发布端RC0，保护流34,176有效行无告警/电机错误；现场有小幅实际移动、回站时下移、无报警，最后稳定趴下。此条覆盖下方“前进真机尚未执行”旧状态。只验收有界一次，**未开放摇杆自由行走**，继续动作须另获当次许可。见INDEX23:10和`04_调试记录/logs/20261111_r1199_forward_review.md`。

2026-11-11 23:06：R1199前进0.05m/s、2秒自动有界候选已独立编译/离线验收并完成只读dry-run，**尚无前进真机LowCmd**。三种子MuJoCo均稳定无非轮触地，但停车评分失败，可能额外移动3.4–3.8cm；现场动作前必须说明风险并获当次明确同意。详细见`02_现场操作/R1199前进0.05有界首测准备.md`和 INDEX 23:06。已验收zero-B仍是另一独立零速二进制。

2026-11-11 22:34 R1199 更新：项目独立候选已在当次明确许可下完成 A→B 2秒交接+2秒强制零速→自动回站→Y 真机试验，现场认为正常、轻微滑动；保护流无新增告警，发布端RC0。**仅零速短接管已验收，非零速度仍编译锁定。** 上游 release 仍是 simulation_diagnostic；任何后续运动或控制权动作需重新具体告知并获当次明确同意。证据见`04_调试记录/INDEX.md` 22:34；此条覆盖较早的“R1199未绑定B”说法，不改变R284等其他禁令。

2026-11-11：`rolling-fixed-exit-preview` 上游MuJoCo gate=false（1/120）；本项目压力复演完整0通过，转向/弧线有倾倒/非轮接触，全部Policy→FixedStand门槛失败。注入真机FixedStand实测初态后零速可站，但B进入腿dq峰约2.6rad/s、前后滚动横漂且退出失败；vy明确不支持。当前禁止绑定B、开发/同步launcher或任何实机试跑。详情见`02_现场操作/rolling-fixed-exit-preview离线评估.md`及INDEX最新节。

2026-11-11 20:46：CPRO 重启（20:41）后管理链更正——**无线可直连，不再需要 hdcrelay**。实测 `hdcd` 监听 `0.0.0.0:8710`，`hdc tconn 192.168.10.180:8710` → `Connect OK`、root shell 正常；旧中继地址 `192.168.10.180:10178` 已失效，仅留作回退。USB 在重启后**自动恢复正常**（`hdcd` 重建 gadget，`0123456789ABCDEF USB Connected`），证实 11-11 上午那次 USB 故障是控制器/gadget 卡死，重启即清。由此 **“CPRO 重启会永久失去管理通道”的旧结论作废**：只要 `persist.hdc.mode=tcp` 仍在（现在是），8710 会自启，本机只需重新 `tconn`。双通道并存时所有命令仍须带 `-t`（USB `0123456789ABCDEF` / 无线 `192.168.10.180:8710`）。

2026-11-11 10:30：管理链路 USB HDC 已修复并双通道并存。症状：CPRO 侧插线但 Windows 无任何枚举、`hdc list targets -v` 只有 `0123456789ABCDEF USB Offline`、设备端 `udc state=not attached`，`dmesg` 报 `udc ea100000.hiusbc: failed to start g1: -22`。根因：gadget 配置 `/config/usb_gadget/g1/configs/b.1/f1 → functions/ffs.hdc` 链接缺失，配置内无任何 function，绑定恒失败、pull-up 不拉，故 PC 看不到设备（线材与 `extcon1 USB=1` 均正常）。修复：`ln -s /config/usb_gadget/g1/functions/ffs.hdc /config/usb_gadget/g1/configs/b.1/f1` 后 `echo ea100000.hiusbc > /config/usb_gadget/g1/UDC`，得 `state=configured` 与 Windows `HDC Device`。现 `0123456789ABCDEF USB Connected` 与 `192.168.10.180:10178 TCP Connected` 并存，**所有 hdc 命令必须带 `-t`**；不执行 `hdc tmode`。规则见末尾“管理链路：USB HDC 与 WiFi 双通道”。

2026-11-10 19:47：R284真机B接管剧烈振荡，已急停终止并重启恢复；R284 launcher已锁死，禁止再次LowCmd。2秒handoff温和，但全量PolicyWalk后0.5秒腿dq跳至7.44rad/s，峰腿11.49/轮14.38rad/s、腿tau73.4Nm。轮角无首帧回绕跳变，属真实闭环不稳/仿真假阴性。重启后原厂ai_damping正常。详见INDEX最新节。

2026-11-10 19:3x：R284-500 离线适配通过，可在上电后准备有界zero-B，但尚无动作许可。官方65维轮角记忆、ORT1.22 16000帧回放、MuJoCo 2秒/10秒零速、x86/ARM64 9/9和audit均过；2秒零速几乎不位移，10秒0–2cm。运动后停车仍滑6–7cm，首次不得开放摇杆。断电一键会话在LowState0包处正确FATAL。INDEX最新节为准。

2026-11-10 17:0x：R270 2秒有界zero-B试验版已完成x86/ARM64 9/9与audit，尚未运行。MuJoCo预测2秒策略段位移0.24–0.25m，随后显式刹轮另滑0.15m，总漂移可能0.4–0.45m；自动回固定站，Y/15秒超时趴下。CPRO只读当前ReleaseMode、趴下、约1kHz、16轴mode0、无发布。真机须当次许可。

2026-11-10 16:3x：R270-preview 当前禁止落地按B。上游8个stop段全部held=false、零命令平均速度约0.14–0.15m/s；独立MuJoCo三种子零速3s轮dq峰2.77–2.89rad/s、机身速度峰0.20–0.21m/s、位移0.42–0.44m。交付缺策略kp/kd明确合同；独立复演按55/2仅作基线。未接入cpp_deploy、未同步CPRO、无真机LowCmd。INDEX最新节为准。

2026-11-10 15:3x：R249 当前禁止落地按B。补跑三种子显示零速3s轮dq峰6.07–9.19rad/s、机身速度峰0.17–0.63m/s、净位移0.15–0.75m，存在碰撞风险。x86/CPRO ARM64构建与离线审计已完成但尚无真机LowCmd；下一步先只读shadow/核查零命令语义，必要动作测试先稳定支架轮子离地并另获许可。INDEX 15:25节为准。

2026-11-10 10:15：修复版第三次A→Y真机通过，现场确认Y趴下较平顺、无报警；采样小腿峰速下降，保护流无新增告警。发布端RC0，当前ReleaseMode趴下、无发布。B/策略未真机测试，T2固定站实测最大位置误差约0.2705rad高于当前B门槛0.25rad，不能直接宣称B可进入。INDEX 10:12–10:15为准；后续动作每次单独说明并获许可。

2026-11-10 10:08：第二次 A→Y 完整采样确认Y后F1→F2边界小腿突降，现场认为趴下不平顺；保护流无新增硬件告警。修复版已使F2目标/kp连续，CPRO stand/full ARM64各CTest8/8、MuJoCo T2三种子接触峰下降；尚未真机复测。当前ReleaseMode趴下、无发布，B暂禁。需另行取得修复版A→Y的当次许可；INDEX 10:00–10:08有证据。

2026-11-10 09:58：新版 A→固定 PD 站立首试完成，15秒超时自动趴下，发布端RC0；Y未验收，现场认为趴下不够受控。50秒只读采样结束于动作前，不能量化下沉或动作期告警。当前 ReleaseMode、无发布、已趴下。下一次动作须当次明确许可并完整覆盖只读监测；暂不进入B。INDEX 09:54–09:58有原始日志。

2026-11-10 09:51：狗开机后 CPRO eth0 已恢复；现场当次许可 ReleaseMode 成功，16轴 mode0、状态流正常、无新增保护位。新版独立 A/Y build 已 ARM64 8/8、T2离线审计通过，B锁；A固定PD，Y手动趴下，15秒没按Y自动趴下。**ReleaseMode 许可不等于 A/Y 动作许可**；启动程序前须单独说明并取得现场当次明确同意。INDEX 09:50–09:51 节有日志。

2026-11-10 09:46：CPRO `eth0` 物理 `NO-CARRIER/state DOWN`，只读 LowState 0包、MotionMode rc3104；WiFi HDC 正常。新版 A/B/Y/X ARM64 stand/full 各8/8、现场包已重建，但**不能进行任何真实动作试验**。先核实狗电源/网线、恢复 eth0 carrier，再重跑只读基线并对 A 单项取得现场当次明确同意。INDEX 09:46 节有原始日志。

2026-11-10 上午：R214 正式 A/B/Y/X FSM 已写入唯一源码并同步 CPRO，A 固定 PD Stand、B 才接策略、Y 两段 FixSquat、X 紧急 Passive；策略中 A 回站冻结最后策略腿目标。T2 服务器 MuJoCo 三条关键路线各3种子未翻，CPRO ARM64 新独立 stand/full 构建各8/8，离线审计和回放通过；**新版尚未真机发布 LowCmd 或验收任何 A/B/Y 动作**。旧 `build-r214-standtrial` 二进制仍是 A 自动进策略的历史版，禁用；新脚本指向 `build-r214-ab-fsm`/`build-r214-ab-fsm-full`。下一次只读基线后，先独立 A 固定站、再 Y 趴下、B 零速、行走和 A 回站；每次动作仍需现场人员当次明确同意。详情见 `02_现场操作/R214实机遥控与策略递进验收.md` 顶部和 INDEX 最新节。本条覆盖下面旧“未重构”描述。

2026-11-10 上午更新：正式按键目标为 A→FixStand→**固定 PD Stand**，B 才交 R214。00:30 通过的 A 临时试验自动进入策略零速，B 未测试，不能当作正式 FSM 通过。完整 FSM 源码与全方向脚本尚未按正式语义重构/ARM64 验收，不得真机运行；见 `02_现场操作/R214实机遥控与策略递进验收.md` 顶部现行合同和 INDEX 最新节。旧报警的单一原因未隔离，无报警仅证明现行分段 Passive 唤醒组合在已测姿态下通过。各动作仍需现场人员当次明确同意。

2026-11-10 00:33：当次许可的 R214 A 首试完成：FixStand→R214零速约2s→FixSquat→Passive，发布端真实RC0，现场无报警；T1目标没有完全追到，策略交接时收腿，可能略降但无法量化机身高度。当前 ReleaseMode/趴下/无发布，B仍锁住。详见 INDEX 00:28–00:33。任何 B 行走/原厂模式恢复须另行告知并获当次明确同意。

2026-11-10 00:27：用户今晚接受 A→FixStand→R214 零速策略临时方案。独立 `build-r214-standtrial` ARM64全构建/CTest8/8，只开放 A/Y，B 编译锁；A 后零速保持2秒自动 FixSquat 趴下并停发。当前机器人仍 ReleaseMode/趴下，未运行此试验。每次真机动作必须先说明并获现场人员当次明确同意；详见 INDEX 00:20–00:27。

2026-11-10 00:01：现场只读 `MotionMode/GetState` 已确认狗在原厂 `ai_damping` 趴下；R214 后续遥控和策略阶段须按 `02_现场操作/R214实机遥控与策略递进验收.md` 逐项验收。R214 FSM 的 FixSquat 方向及阻塞末段已改并通过 CPRO ARM64 编译/CTest 8/8，但**未进行新版 FSM 仿真/实机动作验收，A/B/Y 仍锁住**。现有方向工具自动使用旧 `kd=5` 连做多项动作，仍禁止运行。两次 Passive-only 成功仅覆盖趴下态；各动作仍须事先说明并获当次明确同意。

2026-11-09 23:50：现场已按当次同意恢复原厂 `ai` 运控，GetState=`ai_free_walk`，现场确认稳定站立、原厂遥控正常。后续低层测试须先重新 ReleaseMode 并逐次获明确同意；INDEX 最新节有证据。

2026-11-09 23:46：现场当次同意下 R214 Passive-only 启动序列连续两次通过，狗均稳定趴下、无报警；这**不授权** FixStand/策略或其他 LowCmd 试验。现保持 ReleaseMode、16轴反馈mode0。详见 `04_调试记录/INDEX.md` 最新两节；任何下一次可能动作命令仍须单独告知并获当次同意。

2026-11-09 夜间：两次 LowCmd 保护报警后**禁止真机 LowCmd 发布**，直到现场审查并对具体实验当次同意。R214 发布端候选已修复启动时序并完成 x86/ARM64 离线编译与帧审计，**没有完成实机验收**。见 `02_现场操作/LowCmd启动事故复核与离线审查.md`、`04_调试记录/INDEX.md` 最新节。以下 R152/R214 旧状态仅为历史。

2026-11-09 晚间：当前主线已切换 R214。R214 已完成 CPRO ARM64 构建、回放和只读 shadow；无 R214 LowCmd 发布端。R152 发布 FSM 仍是离线失败候选，禁止真机运行。详见 `05_OpenCode交接/给OpenCode_R214_FSM增益续作提示词.md` 与 `04_调试记录/INDEX.md` 最新节。下面 R152 主线表述仅为历史记录。

2026-11-09 15:12：用户指定 R152 为新策略目标；G1 16 轴状态身份/符号已由现场逐项手动验证，R152 ONNX MuJoCo 平地复测完成但严格接触仍有较多失败。服务器续作先读 `05_OpenCode交接/给OpenCode_R152续作提示词.md` 和 `04_调试记录/INDEX.md` 最新节。R41 保留离线对照，低层闭环门槛不变。

本目录是现场执行与交接区，源码唯一维护位置是 `../部署参考/cpp_deploy-as2w/`。修改源码、模型或打包文档后运行 `准备现场包.ps1`，验证 SHA-256，再更新现场手册涉及的命令。不要直接修改归档内部文件。

个人 PC 的一键阶段入口是 `现场入口.ps1`，说明见 `02_现场操作/现场入口使用.md`。它不发实体动作；涉及动作的命令仍须先获得现场人员当次明确同意。

按 `02_现场操作/明日bringup手册.md` 的阶段和门槛推进；现场已确认的 CPRO 入口、路由和库问题以 `02_现场操作/实机事实与命令.md` 为准。**【硬规则】每完成一个阶段——包括收包验收、离线对齐/parity、sim2sim、编译/CTest/audit、打包、CPRO 同步、实机会话（成功或失败）、重构/改名/文档整理、故障分析——必须立即在 `04_调试记录/INDEX.md` 追加日期、设备/环境、原始命令、实际输出摘要、原始日志路径、判断与下一步；不要覆盖旧记录。** `field_logs/` 原始日志拷进 `04_调试记录/logs/`。敏感凭据、序列号等不入库。

**CPRO 数据同步与远程操作已固化为标准流程**：唯一操作手册 `02_现场操作/策略交付到实机全流程/05_CPRO数据同步与远程操作.md`（tconn 恢复、scp+file send 两跳、base64 脚本法、整包/定点同步选择、ARM64 远端构建、日志回收、坑清单）。caolin 不直接碰 CPRO，一切经工作站中转，命令一律 `-t 192.168.10.180:8710`；旧 hdcrelay `10178` 仅极端回退。新策略全流程入口 `02_现场操作/策略交付到实机全流程/README.md`。

把官方 AS2 和 AS2-W 资料区分；不能由 AS2 的 12 轴表、URDF 顺序或 GO2 参数推断 AS2-W 16 轴 DDS 映射。交付模型 fixture、纯计算 benchmark、DDS 收包、原厂高层动作、只读影子推理、低层真机闭环是不同验收级别，不混写结论。

（历史行，11-10 已被实际进度覆盖）gated LowCmd 发布端 `deploy/robots/as2w/r214/` 已存在并按逐次许可完成多轮真机验收（A/Y 三次、B 零速、行走取证）；硬件合同权威文件是 `../部署参考/cpp_deploy-as2w/config/hardware_contract.md`（02 目录的旧版合同已归档至 `02_现场操作/archive/`）。低层失联/急停语义、轮速精确标定、平地行走塌陷修复（T2 混合托底）仍待验证后才可开放对应动作。原厂遥控器已通过 HG LowState 内嵌 40 字节解码使用（P6）。

现场人员要求：每次发可能让狗动作的命令前，先说清具体动作，等待现场人员明确回复可以后才执行；只说将要测试不算获得同意。

服务器 OpenCode 接续时先读 `05_OpenCode交接/README.md` 与提示词。工作站目录是源码、现场包、原始日志和阶段总账的唯一权威位置；SSHFS 断开时不得在服务器空挂载点继续写。厂商不会提供低层合同，按 `02_现场操作/低层自测计划.md` 自主取证。stairs 平地能力先仿真/只读验证，recovery 暂缓。

## 服务器 x86 编译流程（2026-11-10 固化，避免每轮冷编译）

- **权威源码**永远是工作站 SSHFS `/home/caolin/as2w_workstation/部署参考/cpp_deploy-as2w/`；服务器本地 `/tmp/opencode/r214_zero_b/` 只是**编译镜像**，最终源码/日志/结果必须写回工作站。编辑始终发生在工作站侧，再同步到镜像（方向不可反）。
- 首次初始化镜像用 rsync 排除构建/日志目录：`rsync -a --exclude='/b/' --exclude='/build*/' --exclude='/field_logs/' --exclude='/dist/' '<SSHFS工程>/' /tmp/opencode/r214_zero_b/`。日常只改 `r214_publish.cpp` 等单文件时用 `cp` 单文件同步；改 CMakeLists/头文件/多文件时再跑 rsync，**保留 `b/` 增量缓存**。
- **禁止**每轮执行 `rm -rf /tmp/opencode/r214_zero_b`、`rm -rf b`、`rm -rf build*` 或跨 SSHFS 全量复制后冷编译。
- CMake 构建目录固定为 `/tmp/opencode/r214_zero_b/b`，仅在首次或改 CMake 选项时重新 `cmake -S . -B b ...`（选项：`-DAS2W_R214=ON -DAS2W_R214_PUBLISH=ON -DAS2W_R214_ZERO_B_TRIAL=ON -DONNXRUNTIME_ROOT=/tmp/opencode/onnxruntime-linux-x64-1.22.0 -DCMAKE_PREFIX_PATH=/tmp/opencode/sdk2_install`）。
- 日常快速编译只构建目标：`cmake --build b --target as2w_r214_publish -j8`（实测增量约 4–6 秒）。只有改公共策略库/控制器/测试时才全量增量 `cmake --build b -j8`。长编译不要只管道 `tail`，需要日志时用 `tee` 存到 `04_调试记录/logs/`。
- **分层验证**：小改动→增量编译+相关离线 audit；一个功能阶段完成→完整增量构建+`ctest --test-dir b`+回放+MuJoCo 复演+同步 CPRO ARM64 增量构建+CTest+三处源码 SHA256 核对。CPRO 已有构建目录直接 `cmake --build build-r214-ab-fsm -j4` 增量，不要删 CMakeCache。
- **上真机前**才另建干净目录（如 `b-clean-zero-b`）做一次全量干净构建+CTest，证明无陈旧缓存，不破坏日常 `b/` 缓存。服务器已确认无 ninja/ccache，不换 Generator。

## 服务器→工作站→CPRO 多层远程命令的转义规则（2026-11-10 固化）

链路是 `ssh → powershell.exe -Command "..." → hdc shell → cpro_ubuntu.sh → bash -lc '...'`，共四层 shell 解析。已踩过的坑与规避：

- **禁止**在这条链上内联复杂命令（shell 变量 `$d`、管道 `|`、`grep -E "a|b"`、`&&` 链、中文输出）。实测症状：`$d` 被 PowerShell 层吃掉导致 ctest 把 `--output-on-failure` 当目录名；`|` 被 PowerShell 解析报"'tests' 不是内部或外部命令"（乱码）。
- **正确做法**：把要在 CPRO Ubuntu 执行的整段命令写成本地脚本文件，`base64 -w0` 编码后单行传过去解码执行，全程只有一层引号：
  `ssh ... "powershell.exe -NoProfile -Command \"& 'hdc.exe路径' shell /data/local/tmp/as2w_field/cpro_ubuntu.sh /bin/bash -lc 'echo <B64> | base64 -d > /tmp/x.sh && bash /tmp/x.sh'\""`。
- `ctest --test-dir` 用**绝对路径**（相对路径按当时 shell 工作目录解析，曾在 SSHFS 挂载点上误解析失败）。
- 长编译/长输出不要只管道 `tail -N`：会把真实错误吞掉、且看起来像卡死。需要留档时用 `tee '部署测试/04_调试记录/logs/....log'`；临时查看先看退出码再决定看多少行。
- `hdc file send` 的本机源必须绝对路径；从服务器传文件到 CPRO 是两跳：先 `scp` 到工作站 `zoubu@192.168.10.61:C:/Users/zoubu/`，再在 PowerShell 里 `hdc file send 'C:\Users\zoubu\<file>' <CPRO目标绝对路径>`。目标路径若跨 CMakeLists/脚本/源码多个文件，逐条 send 或打包成脚本循环。
- PowerShell 里 `& '含空格路径.exe'` 单引号形式可靠；把 hdc 路径先赋 `$H` 再多次调用可行但路径含空格时会坏，优先每次显式完整引号。

## 监测会话等待与回收规则（2026-11-10 固化）

- `现场入口.ps1 -Stage LowCaptureFast/LowProtection` 经 SSH 启动后，**采样结束不代表 ssh 会话退出**：PowerShell→hdc 链尾部经常挂住（LowProtection 还偶发 CycloneDDS 退出断言），进程可滞留数分钟。
- **判定"监测完成"以数据为准，不以进程退出为准**：检查日志帧数与末帧时间戳（如 LowCaptureFast 150s 应约 15000 帧、末帧 t≈150000ms；LowProtection 行数与秒数×~190/行 同量级）。数据达标即视为完成。
- 数据达标后直接 `pkill -f 'as2w_field.ps1 -Stage <名字>'` 回收挂住的会话，不要干等进程自然退出；pkill 后用 `ps aux | grep -c '[名字]'` 确认，注意 grep 自身计 1。
- 发布端日志同理：`MOTION/STAND/ZERO_B_TRIAL_REMOTE_RC=` 结尾行出现即会话逻辑已结束，尾部 ssh 挂住可安全 pkill，不影响已写盘数据。

## 管理链路：USB HDC 与 WiFi 双通道（2026-11-11 固化）

链路事实：CPRO 的 HDC 走 `hdcd`（`/system/bin/hdcd`，init 关键服务，`start-mode=condition`），设备端 persist 为 `persist.hdc.mode=tcp`、`persist.hdc.mode.usb=enable`、`persist.hdc.port=8710`。WiFi 侧**优先直连 `192.168.10.180:8710`**：2026-11-11 20:41 CPRO 重启后实测 `hdcd` 监听 `0.0.0.0:8710`，`hdc tconn 192.168.10.180:8710` 直接可用，**不需要 hdcrelay**；`hdcrelay`（`10178 → 127.0.0.1:8710`，源码 `../部署参考/cpp_deploy-as2w/tools/hdcrelay.c`）只在直连不通时作为回退手段。USB 侧由 gadget `/config/usb_gadget/g1` 绑定 UDC `ea100000.hiusbc`（对应 `hiusb-port0` / `extcon1 hisi_usb3_0`）。HDC 客户端固定用 `部署测试/00_HDC工具/hdc_6.1.1.280/hdc.exe`（`hdc` 不在 PATH）。

- **双通道并存时一律带 `-t`**：`-t 0123456789ABCDEF` 走 USB，`-t 192.168.10.180:8710` 走 WiFi（旧中继端口 `10178` 已停用，仅回退时使用）。裸 `hdc shell` 在多目标下会报错或落到非预期目标。
- **禁止 `hdc tmode`**：会重启 `hdcd`（实测约 5 分钟）并可能把当前唯一可用通道切掉；本次故障排查中不要用它做“试探”。
- **禁止 `hdc kill`**：Windows 后台 hdc 服务一死，tconn 全丢；恢复要重新 `hdc tconn 192.168.10.180:8710`。
- **禁止向 `UDC` 写空值**（`echo > UDC` 之类）做试探：那是解绑 gadget。若此时配置里没有 function 链接，再绑会返回 `-EINVAL`，把“能枚举但不 attach”变成“完全绑不上”。

USB HDC 不通时的固定排查顺序（全程只读，除最后修复）：

1. `hdc list targets -v`：USB 行 `Offline` 且 Windows `Get-PnpDevice -PresentOnly` 查不到 `VID_12D1` → 转设备端取证（若 `TCP` 也掉了，先 `tconn` 再试）。
2. 设备端 `cat /sys/class/udc/ea100000.hiusbc/state`：`configured` 正常，`not attached` 说明没拉起来。
3. `cat /sys/class/extcon/extcon1/state`：`USB=1, USB-HOST=0` 表示端口层已看到线与 VBUS（`hisi-usb-typec` 驱动未绑定任何设备，不要依赖 `typec`/`usb_role` 类目录）。
4. `dmesg | grep -i -E 'HIUSBC|gadget|udc'`：出现 `failed to start g1: -22` 即配置无 function。
5. `ls -l /config/usb_gadget/g1/configs/b.1/`：缺 `f1 -> …/functions/ffs.hdc` 就是本次故障。
6. 修复（root shell）：`ln -s /config/usb_gadget/g1/functions/ffs.hdc /config/usb_gadget/g1/configs/b.1/f1`，再 `echo ea100000.hiusbc > /config/usb_gadget/g1/UDC`；`f1` 已存在时 `ln` 报 File exists 可忽略，直接 bind。
7. 成功判据：`state=configured`，且 Windows 出现 `HDC Device`（`USB\VID_12D1&PID_5000\0123456789ABCDEF`），随后 `hdc -t 0123456789ABCDEF shell id` 返回 root。

注意：手工 relink/bind **不持久**。CPRO 重启后由 `hdcd` 重建 gadget 通常自动恢复；若重启后仍不 attach，按上面第 5–6 步处理。USB 与 WiFi 是两条独立通道，USB 故障不影响 WiFi 管理，排查时不要为了“试试”去动 `eth0`、`ip rule` 或 `hdcrelay`。

### 网络或主机变化后的恢复：只做 tconn，不改任何配置（2026-11-12 固化）

触发场景：本机切换/重连 WiFi、重启本机、CPRO 重启、路由器重启。**结论：不需要重新配置，也不需要动 CPRO 任何文件，只需重连一次目标。**

原因：`tconn` 建立的连接只存在于本机 hdc 服务的内存里，不写任何配置文件；CPRO 侧 `hdcd` 只要 `persist.hdc.mode=tcp` 还在（现在是），就会自己监听 `0.0.0.0:8710`，与 USB 和机主是否重连 WiFi 无关。

```powershell
& "D:\Projects\Athena\运动控制\Collie\AS2-W_CPRO\部署测试\00_HDC工具\hdc_6.1.1.280\hdc.exe" tconn 192.168.10.180:8710
& "…\hdc.exe" list targets -v      # 该行应为 192.168.10.180:8710  TCP  Connected
& "…\hdc.exe" -t 192.168.10.180:8710 shell id    # 返回 uid=0(root) 即恢复
```

- 目标表里的 `Offline` 残留（`0123456789ABCDEF` USB、旧 `10178`）可忽略；**判断链路好坏只看 8710 那行是否 `Connected`**。
- `tconn` 失败时才按序排查：① 本机是否仍在 `192.168.10.x`（`Get-NetIPAddress -InterfaceAlias WLAN`）；② `Test-NetConnection 192.168.10.180 -Port 8710`；③ 8710 不通而 10178 通 → 说明设备端跑着回退中继，改 `tconn 192.168.10.180:10178`；④ 两者都不通 → CPRO 的 WiFi 掉线或 wlan IP 变了，转设备侧排查。
- 实测（2026-11-12 09:05）：重连 WiFi 后 USB/10178/8710 三行全 `Offline`，仅执行一条 `tconn 192.168.10.180:8710` 即恢复 `Connected` 与 root shell；CPRO `uptime` 44656s 表明其间未重启，设备侧零操作。
- 这一恢复过程**不要**用 `hdc kill`、`hdc tmode`，也不需要重启 CPRO。
- **典型“CPRO 断线”其实是本机 WiFi 重关联**（2026-11-12 10:13 实测）：本机 WLAN 在 09:52:20–21 出现 `11004 停止 → 11005 成功 → 11010 启动`，`hdc.log` 同步记录 09:52:55 关闭会话；随后 09:58/09:59 两次自动 `TargetConnect` 均在约 20 秒后 `STATUS_OFFLINE`。设备侧 `uptime` 与 `hdcd` PID（2717）全程未变，wlan0 信号 -54 dBm。**判据：8710 可达 + targets 显示 Offline = 只是会话被打断，hdc 不会自动重连，`tconn` 即恢复。** 减少复发可关闭本机无线网卡的“允许计算关机以节约电源”并避免睡眠；不要因为这种现象去重启 CPRO。
- **不做开机自动 tconn**：用户 2026-11-11 明确表示不需要自动连接，恢复时手工执行上面那条命令即可。
