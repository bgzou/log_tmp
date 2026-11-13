# 给 Codex：AS2-W LowCmd 发布启动序列深度调试（2026-11-09 23:40）

## 紧急程度与任务性质

**这是真机安全关键任务。** 现场已因错误的 LowCmd 发布序列触发两次机器人保护报警（喇叭巨响），现场人员按急停后冷启动恢复。狗未受损但被吓到。**在你给出经过严谨论证的修复方案并通过离线审查前，禁止任何 LowCmd 真机发布。**

你的任务：**深度 debug 为什么我们的 LowCmd 发布会触发 AS2-W 保护报警，参照官方例程设计正确的启动序列，给出可编译的 C++ 修复代码和离线验证方法。** 不要直接运行到狗上——方案先交现场人员审查。

## 项目环境与入口

- **唯一权威目录**：`D:\Projects\Athena\运动控制\Collie\AS2-W_CPRO`（Windows 工作站），SSHFS 挂载为服务器 `/home/caolin/as2w_workstation`。
- 先 `mountpoint -q ~/as2w_workstation`，确认挂载后才读写。
- 源码主目录：`部署参考/cpp_deploy-as2w/`。
- 调试总账：`部署测试/04_调试记录/INDEX.md`（按时间倒序读最新节，事故记录在 22:10、22:50、23:10、23:30 四节）。
- 官方资料：`部署测试/03_官方资料/`（HTML 文档，底层服务接口 / DDS通信接口 / 运控切换服务接口最相关）。
- GO2 参考例程：`部署参考/unitree_cpp_deploy-go2/`（带轮的 RL deploy，FSM 架构可借鉴）。
- 官方 go2w stand example：`部署参考/unitree_sdk2/example/go2w/go2w_stand_example.cpp`（**关键参考**）。
- CPRO 上 Ubuntu rootfs：`/data/ubuntu_in_hm/ubuntu_rootfs`，工程在 `/root/as2w_deploy`，SDK 安装前缀 `/root/unitree_sdk2_install`，ONNX Runtime 在 `/root/ort122`。
- HDC 管理：WiFi via `192.168.10.180:10178`（hdcrelay），从工作站 `ssh -i ~/.ssh/as2w_workstation zoubu@192.168.10.61` 后 `powershell.exe` → `hdc.exe -t 192.168.10.180:10178 shell /data/local/tmp/as2w_field/cpro_ubuntu.sh /bin/bash -lc '...'`。
- 只读诊断可用 `field.sh` 的 `low-state`/`low-capture`/`low-crc`/`motion-mode`/`sport-state` 等阶段。

## 两次事故经过（精确事实）

### 第一次（22:07）
- **程序**：`r214_publish.cpp` 旧版（有两个 bug）。
- **Bug 1**：确认门槛 `std::getline(std::cin, dummy)` 被 stdin EOF（nohup `< /dev/null`）跳过，程序未经用户确认就开跑。
- **Bug 2**：writer 线程在 `latest_count==0`（没收到 LowState）时仍每 2ms 盲发 LowCmd，`mode_machine` 发成 0（空 LowState 的默认值），全 q=0/kp=0/kd=5。
- **结果**：喇叭巨响，现场按急停。

### 第二次（22:35）
- **程序**：修复版——writer 在 `latest_count==0` 时不发（`continue`）；确认门槛改为输入 `GO`。
- **日志**：`SAFETY: LowState age 62ms → 10561ms`（age 从 62ms 起匀速增长）。`latest_count > 0`（age 非 epoch 级别），证明**收到了至少一个 LowState 包**，writer **确实发了 LowCmd**。
- **结果**：第一帧 LowCmd 就触发喇叭，LowState 随后停止。说明修复后的 LowCmd 内容仍有问题。
- **排除的错误根因假设**：不是盲发 mode_machine=0（已收到有效 LowState，mode_machine 正确回显为 2）。

## 根因确认（23:10–23:30 实验）

### 关键实验：ReleaseMode 前后 LowState motor_state mode 对比

用只读 `low-capture` 抓帧：

| 时机 | 槽位 0–15 mode | 槽位 16–34 mode | LowState 流量 |
|---|---|---|---|
| ReleaseMode 前（ai_sports 趴下） | **1 (FOC)** | 0 | ~1kHz |
| ReleaseMode 后（不发 LowCmd） | **0 (待机)** | 0 | ~1kHz（持续流动） |

**根因**：`MotionSwitcherClient::ReleaseMode()` 使所有 16 个电机从 FOC(mode=1) 切到待机(mode=0)。我们的 `fill_passive` 设 `mode=0x01` 要求电机切回 FOC，**同时带 q/kp/kd 命令**。电机从待机突然被要求切 FOC + 执行控制命令，**第一帧就触发保护报警**。

**不发 LowCmd 时 ReleaseMode 后安全**：LowState 持续流动，狗趴着不动。报警只在发 LowCmd 时发生。

### 已排除的假设
- 19 个空槽位（16–34 mode=0）：不是原因，固件自己也设 mode=0。
- CRC 算法：验证 3208/3208 匹配，正确。
- mode_machine 回显：正确（=2）。
- LowState 类型/topic：`unitree_hg::msg::dds_::LowState_` on `rt/lowstate`，正确。
- HG LowCmd 没有 head/level_flag 字段（官方底层服务接口文档 + IDL 确认），不能照搬 GO2 的 head/level_flag。

## 官方 go2w_stand_example.cpp 的启动序列（关键参考）

文件：`部署参考/unitree_sdk2/example/go2w/go2w_stand_example.cpp`。这是官方轮足低层接管例程，关键步骤：

1. **`InitLowCmd()` 初始化**（构造时一次）：
   ```cpp
   low_cmd.head()[0] = 0xFE; low_cmd.head()[1] = 0xEF;
   low_cmd.level_flag() = 0xFF; low_cmd.gpio() = 0;
   for(int i=0; i<20; i++) {
     low_cmd.motor_cmd()[i].mode() = 0x01;      // FOC
     low_cmd.motor_cmd()[i].q() = PosStopF;     // 2.146E+9 特殊停止值
     low_cmd.motor_cmd()[i].kp() = 0;
     low_cmd.motor_cmd()[i].dq() = VelStopF;    // 16000.0 特殊停止值
     low_cmd.motor_cmd()[i].kd() = 0;
     low_cmd.motor_cmd()[i].tau() = 0;
   }
   ```
2. **`Init()` 中先 ReleaseMode**（循环直到成功）。
3. **`Start()` 启动 2ms 周期写线程** `LowCmdWrite()`。
4. **`LowCmdWrite()` 前 500 tick（1 秒）只读传感器不运动**——持续发布上面的停止命令让电机稳定。
5. **500 tick 后**：记录当前位置 `_startPos[i] = low_state.motor_state()[i].q()`，开始从当前位置插值到目标（`_percent_1` 线性插值，duration 500 tick = 0.5 秒）。
6. **轮电机（12–15）**：用速度模式 `q=0, kp=0, dq=速度, kd=Kd`，不是位置模式。
7. `Kp=70, Kd=5` 是 GO2 的 FixStand 增益；Passive 用 `kd=3`（见 `unitree_cpp_deploy-go2/config/config.yaml`）。

**注意**：这是 `unitree_go` 类型（20 motor_cmd，有 head/level_flag）。AS2-W 用 `unitree_hg` 类型（35 motor_cmd，**无 head/level_flag**）。PosStopF/VelStopF 机制在 HG 上是否有效**未验证**——这是你要调查的重点之一。

## GO2 RL deploy 对比（unitree_cpp_deploy-go2）

文件：`部署参考/unitree_cpp_deploy-go2/deploy/robots/go2/main.cpp` + `FSM/State_Passive.h`。关键差异：

- **`main.cpp` 顺序**：`ChannelFactory::Init` → `init_fsm_state()`（先订阅 `rt/lowcmd` 检查通道占用 `isTimeout()`，再创建 publisher，再创建 subscriber 并 `wait_for_connection()` 阻塞等首包）→ 启动 FSM。
- **`LowCmd` publisher 构造时**：`for (auto & m : msg_.motor_cmd()) m.mode(1)`——全部 20 槽 mode=1。
- **`State_Passive`**：`mode=[1]×12, kp=0, kd=3, dq=0, tau=0, q=跟随 LowState`。
- **`RealTimePublisher`**：后台线程 1ms 间隔持续发布，即使无新数据也重发上一帧。
- 用 `wait_for_connection()` 等 LowState 首包 + 100ms 稳定期后才启动 FSM。

## 当前代码状态（你要改的文件）

**主文件**：`部署参考/cpp_deploy-as2w/deploy/robots/as2w/r214/r214_publish.cpp`

当前状态（已推送两次修复到 CPRO 并编译，但仍有问题）：
- writer 线程在 `latest_count==0` 时不发（`continue`）——已修。
- 确认门槛改为输入 `GO`——已修。
- **缺 wait_for_connection**：已加等待首包逻辑（5 秒超时 + 200ms 稳定期）。
- **缺安全停止帧阶段**：这是核心待修项。
- `fill_passive`：`mode=0x01, q=st.q(), dq=0, kp=0, kd=5, tau=0`（kd 应降为 3）。
- `finish()`：只算 CRC（HG 无 head/level_flag）。
- 35 个 motor_cmd 只填 16 个（map 对应槽 0–15），其余 19 个保持默认 mode=0。

**构建**：CMake 选项 `AS2W_R214_PUBLISH=ON`，CPRO 上 `AS2W_R214_ROOT=/root/ort122 AS2W_SDK2_PREFIX=/root/unitree_sdk2_install bash tools/build_on_cpro.sh`。

**CMake/构建脚本**：`deploy/robots/as2w/r214/CMakeLists.txt`、`tools/build_on_cpro.sh`、`tools/field.sh`（有 `r214-publish-build` 阶段）。

## AS2-W 16 轴实测身份（只读 LowState 验证）

- 腿槽 0–11 = (hip,thigh,calf)×4，轮槽 12–15。
- FR 腿 0,1,2；FL 3,4,5；RR 6,7,8；RL 9,10,11。
- 轮 FR=12、FL=13、RR=14、RL=15。
- R214 contract 序 → DDS 槽：`[3,0,9,6,4,1,10,7,5,2,11,8,13,12,15,14]`。
- hip 四轴状态符号 −1，thigh/calf/wheel +1（**状态解码符号，非 LowCmd 命令方向，未验证**）。
- 零位、LowCmd 命令方向、轮速模式、急停有效性**均未验证**。
- 当前 `ai_damping` 趴下态实测 q：hip≈±0.56, thigh≈1.0, calf≈−2.75 rad。

## 官方文档关键点（底层服务接口）

- `rt/lowstate` 类型 `unitree_hg::msg::dds_::LowState_`，`rt/lowcmd` 类型 `unitree_hg::msg::dds_::LowCmd_`。
- **"要使用底层服务接口控制 As2，需要先关闭 Unitree 内置的运动控制服务（ai_sports）。"** 用运控切换服务接口或 App。
- `LowCmd_` 结构：`mode_pr, mode_machine, motor_cmd[35], reserve[4], crc`。**无 head/level_flag**。
- `mode_machine` 必须和 lowstate 对齐，否则不响应。
- `MotorCmd_`：`mode(0x00=待机/0x01=FOC), q, dq, tau, kp, kd, reserve`。
- 官方文档只列了 As2 的 12 个腿电机（0–11），**没有说明 As2W 的 4 个轮电机在 35 槽位中的位置**——但只读 LowState 实测确认 12–15 是轮。

## 你要交付的东西

1. **根因深度分析报告**：为什么从 mode=0（待机）直接发 mode=1 + q/kp/kd 会触发保护。是 mode 切换本身的问题，还是 q/kp/kd 和 mode 切换同时发生的问题？是否需要先发若干帧"纯 mode 唤醒"（mode=1 但 kp=0/kd=0/q=0/dq=0/tau=0）让电机稳定切到 FOC，再渐进加增益？
2. **正确的启动序列设计**：参照 go2w_stand_example，设计 AS2-W HG 类型的安全启动序列。明确每一阶段的 mode/q/dq/kp/kd/tau 值和持续时间。处理 HG 无 PosStopF/VelStopF 的问题。
3. **可编译的 C++ 修复代码**：修改 `r214_publish.cpp`，实现新启动序列。保持现有 FSM 架构（Passive/FixStand/PolicyStand/PolicyWalk/Brake/FixSquat/EmergencyDamping），但 Passive 进入时先走"安全唤醒"子阶段。
4. **离线验证方法**：如何在不上狗的情况下验证 LowCmd 字节内容正确（比如构造一帧打印十六进制、对比官方例程）。
5. **真机测试方案**：分步骤的安全测试计划，每步预期结果和回退方案。首测只做 Passive（kp=0/kd=3/q 跟随），狗不动。

## 约束与安全规则

- **禁止真机 LowCmd 发布**，直到方案通过现场人员审查。
- 任何可能使狗动作的代码改动，编译后先离线验证字节内容。
- `ReleaseMode()` 后狗趴着不动是安全的（已验证），但发 LowCmd 会触发保护（已验证两次）。
- 急停是锁存式，重启前必须解除；急停锁存时重启不会正常上电。
- 修改源码后需重新 `hdc file send` 推送到 CPRO `/data/ubuntu_in_hm/ubuntu_rootfs/root/as2w_deploy/...` 并 ARM64 编译（`AS2W_R214_ROOT=/root/ort122`）。
- x86 离线编译可用工作站 `/tmp/opencode/` 下的 ONNX Runtime x64 和 sdk2 install。
- 每次实验无论成败追加 `部署测试/04_调试记录/INDEX.md`，原始日志存 `logs/`。

## 已有的调试日志和证据文件

- `部署测试/04_调试记录/INDEX.md` 22:10/22:50/23:10/23:30 四节（完整事故和分析）。
- `/tmp/opencode/session_logs/r214_passive2.out`（第二次事故程序输出，`SAFETY: LowState age 62ms→10561ms`）。
- `/tmp/opencode/before_release.txt`、`/tmp/opencode/after_release.txt`（ReleaseMode 前后 LowState 抓帧对比）。
- `/tmp/opencode/lowstate_scan.txt`（35 槽位 mode 扫描，16 active/19 inactive）。
- `部署参考/cpp_deploy-as2w/config/r41_measured_identity_sign.md`（16 轴身份标定）。
- `部署参考/cpp_deploy-as2w/config/hardware_contract.md`（硬件合同，待填项）。

## 建议的调查路径（非强制，供参考）

1. 仔细读 `go2w_stand_example.cpp` 的 `InitLowCmd` + 前 500 tick 空转逻辑。
2. 研究 HG `MotorCmd_` 的 mode 字段语义：mode=0→1 的切换是否需要"纯唤醒帧"（mode=1 但全零增益）先发若干帧？
3. 检查 HG LowCmd 是否有类似 PosStopF 的特殊值机制，或是否可以直接 mode=0 + 全零保持待机，再渐进切 mode=1。
4. 考虑 kd 从 5 降到 3（对齐 GO2 Passive）。
5. 设计一个"离线 LowCmd 字节检查工具"：构造一帧 Passive LowCmd，打印全部字段，和 go2w_stand_example 的字段逐项对比。
6. 如果 HG 类型确实不支持 PosStopF，设计替代方案：比如先发 N 帧 mode=0（保持待机）+ mode_pr=0，让 DDS 链路稳定，再切 mode=1 + kp=0/kd=0/q=0（纯 FOC 无控制），再渐进加 kd。

交付后请明确标注：哪些部分是已验证事实，哪些是推断，哪些需要真机实验确认。
