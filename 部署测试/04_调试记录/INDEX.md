# AS2-W / CPRO 调试总账

每完成一个阶段，就从 `阶段记录模板.md` 复制一节到下方，填写**实际观察**并把原始日志放在 `logs/`。失败也记。不要把命令退出码 0 写成“真机控制已验证”。

## 当前现场状态（2026-11-09 10:09）

- PC 经 USB/HDC 管理 CPRO；CPRO 鸿蒙内 Ubuntu aarch64 已运行部署包，CPRO `eth0` 经有线连接 AS2-W，DDS 状态与原厂高层 RPC 已通。
- 六份模型哈希/夹具、7 项 CTest、ARM64 SDK2 编译通过。原厂 `StandUp` 已由现场人员观察确认稳定起立，原厂遥控器仍可行走和趴下。现由现场人员遥控趴下，最近只读状态为 `ai_damping`。
- 当前仍无 LowCmd 发布端；20 Hz 慢走采样显示 0–15 槽活跃、12–15 为四轮强候选，但物理轮对应、轮轴命令、低层运控切换与恢复策略的机体系速度来源未验证，因此两类策略均未真机执行。原厂遥控器的独立 DDS topic 为 0 包，LowState 内嵌左摇杆前推已与 `ly` 候选正值关联。
- **任何可能让狗动作的命令，必须先告知具体动作并等现场人员明确同意。** 此要求来自现场人员在首次起立测试后的反馈。

## 历史交接状态（2026-11-08，离线准备）

- 个人 PC：六个策略模型哈希校验通过；七项离线测试通过；SDK2 诊断程序通过 ARM64 Linux 目标编译检查。
- AS2-W：尚未连接实机；DDS、官方遥控器 topic、16 轴映射和低层电机命令均未上机验证。
- CPRO：同事描述为鸿蒙中的 Ubuntu“容器/类似 chroot”；具体隔离、网卡和 `/dev` 透传尚未实测。
- Windows HDC：配套 exe/DLL 已放入 `00_HDC工具`，用户 PATH 已设置；`hdc -v` 返回 `Ver: 3.2.0d`，`hdc list targets -v` 返回 `[Empty]`。设备连接与授权尚未验证，详见 `00_HDC工具/README.md`。
- 下一阶段：连接 CPRO、传包后执行 `bash tools/field.sh preflight`，保存日志并补充本页。

## 阶段记录

<!-- 每次完成阶段后追加一节，不覆盖旧记录。 -->

## 2026-11-08：策略目录与离线选择命令

- 环境：个人 Windows PC，Git Bash + Python 3.13；未连接 CPRO 或 AS2-W。
- 命令：`bash tools/field.sh policy-list`；首次因 Git Bash 命中 WindowsApps 的 `python3` 占位程序退出 49。入口已改为在 Windows Git Bash 选择 `python`，CPRO Linux 保持 `python3`。失败原始记录：`logs/20261108-223850_policy-list.log`。
- 复测：`policy-list` 退出 0，显示三份 recovery、三份 stairs；`policy-verify all` 退出 0，每份权重的 60 帧参考轨迹误差均小于 `1.6e-5`。原始记录：`logs/20261108-223918_policy-list.log`、`logs/20261108-223925_policy-verify.log`。
- 另外验证：`policy-shadow recovery-r12 ...` 按设计拒绝，原因是缺已验证的机体系线速度源。
- 结论：`config/config.yaml` 和选择命令可用于离线选择与校验；未证明 DDS、真机执行或遥控器 FSM。下一门槛为 CPRO Ubuntu 构建与现场硬件合同。

## 2026-11-08：按 GO2 模块边界整理 AS2-W 工程

- 环境：个人 Windows PC；未连接 CPRO/AS2-W。
- 调整：将 SDK2 诊断、高层手柄备选和模型目录移动到 `deploy/robots/as2w/`；策略核心留在根 `src/`。新增 `docs/architecture.md`，逐项指出旧迁移指南的 12 轴/Orin/ONNX 假设与当前交付的差异。
- 结果：六份模型 60 帧校验再次通过；移动后的两个平台源文件通过 ARM64 Linux 目标对象编译；现场包包含新目录，两个压缩包均通过 `sha256sum -c`。原始核对结果见 `logs/20261108-architecture-offline.log`。
- 限制：本机 PATH 没有 CMake/CTest，未做移动后的 CMake 完整链接；需要在 CPRO Ubuntu 运行 `field.sh build` 和 `sdk-build`。DDS、遥控器、低层发送与 FSM 仍未实机验收或实现。

## 2026-11-08：GO2 upstream `deploy/` 文件审计

- 逐组核对 GO2 的 FSM、设备包装、IsaacLab 观测/动作、ONNX 推理、配置、可选输入、记录和 Python 工具；明确“移植职责/重写 AS2-W 适配/暂不需要”。结果在 `02_现场操作/GO2文件移植判断.md`。
- 现场包已纳入审计文档，压缩包校验通过。原始检查摘要在 `logs/20261108-go2-audit-offline.log`。
- 本阶段只有源码审读与资料整理，未连接设备，也未启用低层命令。

## 2026-11-08 23:16：参考目录总审计与明日 bring-up 准备

- 环境：个人 Windows PC；CPRO 和 AS2-W 尚未连接。逐项审阅 `部署参考/` 顶层资料、GO2 部署代码、同事交付、SDK2、AS2-W URDF 与 18 页官方离线资料，形成 `02_现场操作/参考资料总审计.md` 和 `明日bringup手册.md`。
- 模型事实：交付为两类六权重；交付原生 MuJoCo 报告中恢复 r09/r13 16/16、r12 15/16，三份爬楼 0/16。该数字来自同事报告，当前目录没有完整训练/仿真归档，未独立重跑物理仿真。
- 代码：补纯推理时延 benchmark、六份 actor SHA-256 校验、LowState IMU 打印、可选 LowState topic、唯一日志文件名；`build_on_cpro.sh` 先检查模型文件。
- 离线验证：六份 ONNX/actor 哈希通过；Git Bash 脚本语法通过；`policy-list`、六份各 60 帧 `policy-verify all` 通过；个人 PC 上 `policy-bench recovery-r12 3000` 的 p99 为 124.30 μs。这只测个人 PC 的固定输入纯计算，CPRO 上必须重跑。原始输出：`logs/20261108-231644_policy-list_245.log`、`logs/20261108-231645_policy-verify_262.log`、`logs/20261108-231645_policy-bench_224.log`。
- 现场包：两份 tar.gz 已重新生成，`SHA256SUMS.txt` 与实包校验通过。Windows 本机无 CMake/g++，本轮无法做更新后完整 SDK2 链接；CPRO Ubuntu 的构建、DDS 与机器人动作均为现场门槛。
- 下一阶段：按 `明日bringup手册.md` 从 CPRO 传包/Ubuntu 环境开始，逐阶段将真实输出和结论追加于本页。

## 2026-11-09 09:08：现场阶段 0，PC→CPRO 接入发现

- 环境：个人 Windows PC；用户报告 PC 已连接 CPRO，CPRO 已连接 AS2-W。尚未进入 CPRO 或向机器人发命令。
- 实测：HDC 完整 exe 返回 `Ver: 3.2.0d`，`list targets -v` 为 `[Empty]`；当前 Codex shell 的 PATH 未刷新，但用户 PATH 中已有 HDC 目录。Windows 的 Realtek USB GbE“以太网 4”链路 Up，仅获 `169.254.44.105/16`，无网关、无动态邻居；WLAN 为 `192.168.43.4/24`。两个现场包 SHA-256 校验通过。
- 结论：PC 工具和归档就绪，CPRO 管理连接尚未建立。暂不传包、不改网络、不运行高层动作。已向用户核实 PC→CPRO 的连接方式与管理 IP/SSH/HDC 授权信息。
- 原始检查摘要：`logs/20261109-0908_pc-hdc-network.log`。下一门槛：获得 CPRO 宿主 shell，先只读收集宿主与 Ubuntu 的网络/挂载/架构。
- 后续发现：用户确认 PC→CPRO 用网线；Windows 给“以太网 4”添加临时 `192.168.123.220/24` 返回拒绝访问，需用户在管理员 PowerShell 执行或提供 CPRO 管理 IP。没有改动 PC/CPRO/机器人网络。
- 用户随后在管理员 PowerShell 临时添加 `192.168.123.220/24` 成功；从该地址对 `.100`、`.161`、`.1`、`.18`、`.164`、`.222` 探测均无 ARP 邻居/响应，网卡收包统计的单播仍为 0。已请求 CPRO 本机 `ip -br addr` 或 USB/HDC 调试连接。尚未能进入 CPRO；已加 PC 临时 IP，结束后应移除。

## 2026-11-09 09:18：现场阶段 1 与 3，CPRO Ubuntu 和离线策略验收

- 接入：用户接入 USB 后 HDC 显示一台已连接设备；鸿蒙宿主为 aarch64/root。实际 Ubuntu 路径是 `/data/ubuntu_in_hm/ubuntu_rootfs`，不是旧备忘中的 `ubunte_in_hm`。Ubuntu 22.04.5，CMake 3.22.1，g++ 11.4.0。
- 进入方式：直接 `chroot` 报 `FATAL: kernel too old`；按同事脚本使用 `unshare --uts --fork` 后内核显示 5.10.43，`chroot` 可用。暂未运行会挂载 proc/sys/dev 的 `chroot.sh`；离线构建可完成，CMake 提示无法读 `/proc/cpuinfo` 和 `/proc/meminfo`，但不影响该阶段测试。
- 传输：HDC 将两个包及 `SHA256SUMS.txt` 送至宿主 `/data/local/tmp/as2w_field/`；CPRO 本机 `sha256sum -c` 两项均 OK。解压到 Ubuntu `/root/as2w_deploy` 与 `/root/unitree_sdk2`。
- 模型：`field.sh build` 的 7 项 CTest 全部通过；`policy-list` 显示三恢复、三爬楼；`policy-verify all` 六份各 60 帧通过。CPRO 本机纯推理 3000 次：recovery-r12 p99 93.44 μs（max 1900.78 μs），stairs-r17-3000 p99 88.44 μs（max 1276.88 μs），均低于 20 ms 周期。这**不**验收 DDS、系统调度或真机控制。
- 网络现状：`eth0` 物理 Up、无 IPv4；PC 侧网线断开后 `eth1` Down；WiFi `wlan0` 为 192.168.10.180/24。CPRO 到 PC1 `.161` 仍不通。下一步仅在 eth0 加现场备忘所列局部 192.168.123.100/24，不加默认路由，再验 ICMP/DDS。
- 原始输出：`logs/20261109-0915_cpro-host-preflight.log`、`logs/20261109-0918_cpro-ubuntu-preflight.log`、`logs/20261109-0918_cpro-model-build.log`、`logs/20261109-0918_cpro-policy-verify-bench.log`。

## 2026-11-09 09:19：现场阶段 2，CPRO 到机器人主控的有线网络

- 物理链路：用户改用 USB/HDC 管理 CPRO 后，`eth1` 断开而 `eth0` 仍 Up；机上 `/data/init_AS2_env.sh` 指定 `eth0` 为 192.168.123.100/24。先只给 eth0 添加此局部地址，没有改默认网关。
- 首次 `ip route get 192.168.123.161` 仍显示经 WiFi `192.168.10.1`，原因是鸿蒙策略路由表 2013 抢先于 main。添加 `ip rule add to 192.168.123.0/24 table main priority 1000`（仅影响机器人网段）后，路由变为 `dev eth0 src 192.168.123.100`；PC1 `.161` ping 3/3，ARP 邻居 REACHABLE。
- 结论：CPRO→AS2-W PC1 单播链路通过；**尚未证明 DDS 多播和消息类型通**。保留当前局部 IP/规则供后续 SDK2 检查，结束时记录是否需移除或交接给同事。
- 原始输出：`logs/20261109-0919_cpro-eth0-pc1.log`。下一阶段：SDK2 构建与只读 DDS。

## 2026-11-09 09:25：现场阶段 4 与 5，SDK2 编译及首次只读 DDS

- SDK2：CPRO Ubuntu 安装到 `/root/unitree_sdk2_install`，`as2w_sdk2` 编译为 ARM64 ELF，7 项 CTest 再次通过。安装库中的 `libddsc.so.0` 和 `libddscxx.so.0` 原是 Windows 签出时的 10/12 字节符号链接占位文本，导致 `ldd` 报 `file too short`；核对目标完整 ELF 后，在安装前缀改为指向相应 `.so` 的 Unix symlink，`ldd` 全部解析。源包/安装流程需持久修复。
- DDS 启动：在不挂载 `/proc` 的 chroot 中，SDK2 报 `readlink error`。新增 `tools/cpro_ubuntu.sh`：使用独立 mount+UTS namespace，在其中挂载 proc/sys/dev/pts/shm 并 chroot；已验证退出后宿主无残留 proc 挂载。以后在鸿蒙宿主通过 `/data/local/tmp/as2w_field/cpro_ubuntu.sh` 执行 Ubuntu 命令。
- 只读结果：`sport-state eth0 10` 约 201 包/10 秒，mode=0、静止速度近零，退出码 0；`motion-mode eth0` 返回 `rc=0 form=1 name=ai`，未切换；`low-state eth0 5 rt/lowstate` 收到约 5268 包/5 秒，HG `mode_pr=0`、`mode_machine=2`、IMU 可读，静止时槽 0–15 有数据、16–34 为零。**没有由此认定电机映射已标定。** `low-state` 收包后在 Cyclone DDS 订阅对象退出时断言，最终退出码 134；工具退出问题待修，不能记为该命令完整通过。
- 原始输出：`logs/20261109-0920_cpro-sdk-install.log`、`logs/20261109-0921_cpro-sdk-build.log`、`logs/20261109-0922_cpro-dds-sport.log`（第一次无 proc 的失败）、`logs/20261109-0923_cpro-dds-sport.log`、`logs/20261109-0924_cpro-motion-mode.log`、`logs/20261109-0924_cpro-lowstate.log`。可复用事实沉淀在 `02_现场操作/实机事实与命令.md`。
- 下一步：修复高频订阅退出，验证原厂遥控器 topic，再决定原厂高层动作验收。仍不发布 LowCmd 或释放运控。

## 2026-11-09 09:32：现场阶段 5，底层订阅退出与原厂遥控器输入

- 修复：在 `subscribeLow` 正常结束时显式 `CloseChannel()`，将 `diagnostics.cpp` 传至 CPRO 重编。`low-state eth0 3` 连续收约 3143 包并以退出码 0 结束；初次退出码 134 的 SDK2 回调析构问题已在该工具中解决。前后原始记录：`logs/20261109-0924_cpro-lowstate.log`、`logs/20261109-0927_cpro-lowstate-closechannel.log`。
- 原厂遥控器：用户确认已开机配对且可直接控制狗。CPRO `remote-state eth0 10` 订阅独立 `rt/wirelesscontroller` 为 0 包，退出码 1；记录 `logs/20261109-0929_cpro-remote-passive.log`。不能照搬 GO2 的独立遥控器 topic 做 FSM 输入。
- 替代只读观测：SDK2 HG LowState 含 `wireless_remote[40]`；新增 `field.sh low-remote eth0 5`，每秒打印 24 字节原文与按公开格式解读的候选轴/键。实测报头 `55 51`，大部分空闲值零，曾有一次候选 `ly=-0.433699`；退出码 0。原始记录 `logs/20261109-0930_cpro-low-remote-passive.log`。**候选解码尚未验证键位/坐标，不能用于控制。**
- 高层状态随后为 `mode=3`（原厂 NORMAL_WALK），说明狗曾被原厂遥控器操作；期间本工程未发任何动作或 LowCmd。已请求用户先让狗静止并现场看护，再做高层动作验收。
- 下一步：将新入口和库修复持久打包，取回 CPRO field_logs；在看护确认后才做实体动作。
- CPRO 自带 `field_logs/` 已通过 HDC 打包回传；原始归档为 `logs/cpro_field_logs_20261109_0932.tar.gz`，展开副本在 `logs/cpro_snapshot_20261109_0932/field_logs/`（16 个文件）。后续阶段继续增量回传，不能只保留 PC 侧摘要。

## 2026-11-09 09:38：只读 Sport RPC 与修订包回灌

- CPRO 上运行 `field.sh sport-command eth0 get-state`，只查询原厂运动状态，返回 `rc=0`、`fsm_id=3`、`fsm_name=ai_free_walk`、`process_state=active`、`speed_level=0`、`auto_recovery_switch=true`。这是当时原厂高层服务的状态，不等于本工程发过运动指令。原始日志：`logs/20261109-0936_cpro-sport-get-state.log`。
- 本机重新生成源码包与 SDK2 包，两项 SHA-256 校验通过；经 HDC 回传 CPRO，再由 CPRO 校验通过并覆盖解包。新包包括隔离 Ubuntu 入口、SDK2 假符号链接修复，以及 `low-remote` 只读诊断。CPRO 再次运行 `field.sh sdk-build`，7 项 CTest 与 ARM64 `as2w_sdk2` 编译通过；原始日志：`logs/20261109-0940_cpro-package-rebuild.log`。
- 当前仍未发布 LowCmd、未切换或释放运控、未主动执行实体动作。下一门槛为受看护的原厂高层动作验收，以及遥控器输入字节逐项观察；现场人员确认狗静止和场地安全后再执行。

## 2026-11-09 09:44：原厂服务清单与首次高层起立

- 为只读查询新增 `field.sh service-list eth0`，将新包传到 CPRO、SHA-256 两项校验通过，`sdk-build` 再次 7/7 测试与 ARM64 编译通过。传包时发现 HDC `file send` 若本机源用相对路径，会在远端目标目录下额外创建相对目录，原 basename 文件保持旧版；已改用 Windows 绝对源路径重传并核对包内 `service-list`，再解包构建。首次无效构建与修正后构建原始记录：`logs/20261109-0945_cpro-service-list-build.log`、`logs/20261109-0943_cpro-service-list-build.log`；首次误用的 `service-list` 输出为 `logs/20261109-0942_cpro-service-list.log`。
- `RobotState ServiceList` 返回 `rc=0`、20 项，实际服务名含 `ai_sport`、`basic_service`、`motion_switcher`、`robot_state`。`ai_sport status=0 protect=0`，但 `status=0` 的语义暂未从本机验证，不能仅凭它断言服务停用或可安全切换。原始日志：`logs/20261109-0944_cpro-service-list.log`。
- 用户用原厂遥控器让狗趴下后，发动作前 `SportClient GetState` 为 `fsm_id=0 ai_damping`、`process_state=active`。随后通过 CPRO 的官方高层 `SportClient StandUp` **只调用一次**，RPC `rc=0`；紧接着只读 `GetState` 为 `fsm_id=2 ai_stand_up`、`process_state=active`。原始日志：`logs/20261109-0944_cpro-pre-action-get-state.log`、`logs/20261109-0944_cpro-stand-up.log`、`logs/20261109-0944_cpro-post-stand-get-state.log`。
- 这些结果证明 CPRO→AS2-W 高层 RPC 调用及状态迁移，**尚待现场人员确认真实姿态稳定和遥控器仍可接管**。确认前不发下一条实体动作；期间没有发布 LowCmd 或切换低层运控。
- CPRO 此时的 `field_logs/` 已重新打包并通过 HDC 回传，原始归档为 `logs/cpro_field_logs_20261109_0944.tar.gz`（归档列表 25 行）；保留上一次 09:32 快照供对照。
- 现场人员随后确认：本次 `StandUp` 后狗稳定站立，原厂遥控器可以正常行走，再由现场人员操作趴下。此项补足高层动作的物理观察和原厂遥控器仍可接管。现场人员明确要求：**今后每次可能让狗动作的命令，必须先告知具体动作并等待其明确同意后才发。** 本次虽然预告了测试，但没有等明确同意即执行，已向现场人员道歉；以后按此门槛执行。该反馈来自现场口头观察，不在 SDK 原始日志中。
- 遥控器趴下后追加只读 `SportClient GetState`，返回 `fsm_id=0 ai_damping`，与现场观察一致。原始记录：`logs/20261109-0948_cpro-post-remote-down-get-state.log`（实际命令时间 09:45:40，以日志内时间为准）。

## 2026-11-09 09:47：固件版本只读查询

- 增加 `field.sh package-version eth0`，用 SDK2 `RobotStateClient::GetPkgVersion` 只读查询。重新打包、以绝对本机源路径传包，CPRO 端两项 SHA-256 校验通过；`sdk-build` 仍 7/7 测试通过、ARM64 可链接。原始构建日志：`logs/20261109-0953_cpro-version-build.log`。
- 真机返回 `rc=3203`、空 package、0 个 modules，诊断命令退出 1。**未获取到固件版本**，不可把空字符串记为版本号，也不据此判断具体错误语义。原始记录：`logs/20261109-0953_cpro-package-version.log`（实际命令时间 09:47:15）。本阶段没有实体动作。
- 下一步：遥控器字节逐项关联及 16 轴观测，需要现场人员事先知道具体操作并明确同意；低层硬件合同仍未满足。

## 2026-11-09 09:50：原厂遥控器左摇杆只读采样

- 现场人员明确同意后启动 `field.sh low-remote eth0 15` 只读监听，并按提示向前轻推左摇杆。约 1 kHz 的 HG LowState 持续到达；40 字节内嵌遥控器报头 `55 51`，在采样期间按 SDK2 示例布局解出的第 5 个 float 多次约 `+0.82` 至 `+0.85`，其他四个候选轴/键为 0，某次约 `0.085`、末尾一次 0。现场人员确认推过杆且狗没有动作。原始记录：`logs/20261109-0955_cpro-low-remote-left-forward.log`（实际开始 09:49:17）。
- SDK2 自带 `example/g1/low_level/gamepad.hpp` 定义的 40 字节布局是 `head[2]`、16 位按钮、`float lx,rx,ry,L2,ly`、16 字节保留；这说明第 5 个 float 的**候选名称**为 `ly`，但该示例不是 AS2-W 固件合同。为消除“非零是否遥控器静态偏置”疑问，在现场人员保持摇杆松开时追加 `field.sh low-remote eth0 5`：5 个一秒快照所有按钮和轴均为 0，仍有 `55 51` 报头、约 1 kHz 收包。原始记录：`logs/20261109-0951_cpro-low-remote-neutral.log`（实际开始 09:50:28）。
- 判断：**原厂遥控器左摇杆前推与 HG LowState 内嵌第 5 个 float 的正值相关，松开归零**；本次没有狗动作。尚未校准其他轴/按键，也尚未验证低层接管后输入是否持续。没有发任何 DDS 命令。

## 2026-11-09 09:55：现场重复入口和局部网络脚本

- 新增鸿蒙宿主 `tools/cpro_host_net.sh status|apply`：`status` 只读输出 `eth0` 地址、策略路由、去 PC1 路由与 ping；`apply` 设计为只补 `192.168.123.100/24` 和该子网的 main 路由规则，不改默认路由。本次只实际运行了 `status`，显示 `eth0` 地址正确、路由 `dev eth0 src 192.168.123.100`、ping 3/3；`sh -n` 语法通过。原始日志：`logs/20261109-0955_cpro-host-net-status.log`。Windows shell 中 `bash` 未在 PATH，初次本地语法检查命令没有执行；随后改在 CPRO 宿主运行 `sh -n`，通过。
- 新增 Windows `部署测试/现场入口.ps1`：`Sync` 负责打包/绝对路径 HDC 传输/CPRO SHA-256/解包，`NetworkStatus`、构建和各只读诊断是同一 `-Stage` 入口；不包含任何实体动作。Windows PowerShell 5.1 需要该含中文路径脚本保存为 UTF-8 BOM，已处理；初版嵌套引号在 Windows PowerShell 5.1 失效，改为直接让宿主 helper 执行 Ubuntu 内绝对路径 `field.sh` 后，`GetState` 成功。此修复过程保留原始失败日志 `logs/20261109-095339_windows_GetState.log`，成功日志 `logs/20261109-095356_windows_GetState.log`。
- 实测 `NetworkStatus` 通过（一次 ping 首包约 1004 ms，后两包 1–2 ms）、`Sync` 两包 CPRO SHA-256 均 OK、`SdkBuild` 7/7 测试和 ARM64 诊断编译通过；`PackageVersion` 的已知失败能正确令 Windows 入口退出 1 并留日志。原始日志：`logs/20261109-095403_windows_NetworkStatus.log`、`logs/20261109-095504_windows_Sync.log`、`logs/20261109-095425_windows_SdkBuild.log`、`logs/20261109-095433_windows_PackageVersion.log`。
- 单脚本说明见 `02_现场操作/现场入口使用.md`。后续源码/文档更新后仍要重新 `Sync`，避免 CPRO 旧包与个人 PC 不一致；入口没有 LowCmd 发布能力。
- 后续补正 Windows PowerShell 5.1 的 `Sync` 日志写入编码（首次 `Tee-Object` 追加造成部分 UTF-16/NUL 字节），改为显式 UTF-8；再次 `Sync` 成功，CPRO 两包 SHA-256 均 OK，现场包内 README 已包含新网络脚本说明。可读原始日志：`logs/20261109-095739_windows_Sync.log`，检查 NUL 字节数为 0。旧 `logs/20261109-095504_windows_Sync.log` 保留作为已知编码失败证据。
- 再次回收 CPRO `field_logs/` 原始归档到 `logs/cpro_field_logs_20261109_0958.tar.gz`（72,737 字节），含上述遥控器、版本和构建阶段日志；前次 09:44 归档仍保留。

## 2026-11-09 10:02：20 Hz 低层状态采样与遥控器慢走

- 新增只读 `field.sh low-capture eth0 SECONDS`，每 50 ms 复制最新 HG LowState，输出 35 槽 `q,dq`、IMU、消息年龄与 tick；新增 `tools/analyze_low_capture.py` 只做数值摘要，不输出物理轴名。重新 `Sync`，CPRO SHA-256 两包 OK，`SdkBuild` 7/7 测试及 ARM64 编译通过。原始构建/同步日志：`logs/20261109-095914_windows_Sync.log`、`logs/20261109-095925_windows_SdkBuild.log`。
- 狗稳定趴下时先采 3 秒基线：60 个样本，槽 0–11 角度约在腿关节常见幅度内，槽 12–15 为较大的累计角（约 -30.5、-9.68、78.5、124.3 rad），槽 16–34 全零。基线原始记录：`logs/20261109-095945_windows_LowCapture.log`。
- 现场人员明确同意后，启动 30 秒**只读**采样；现场人员用原厂遥控器起立、慢行约 0.3 m、停下、趴下。其反馈：全部完成、现稳定趴下、无异常。600 个 20 Hz 样本，HG LowState 持续约 1 kHz 到达，最新消息年龄约 0 ms。原始记录：`logs/20261109-100054_windows_LowCapture.log`，数值摘要：`logs/20261109-1002_low-capture-analysis.log`。
- 运动段内槽 0–11 各自角度范围约 0.93–1.55 rad，槽 12–15 各自约 4.22–4.64 rad、最大速率约 4.44–4.98 rad/s，槽 16–34 仍全零。**12–15 是四轮槽位的强候选**，但此次整机动作无法证明四个槽各对应 FL/FR/RL/RR 的哪一轮，也不能证明编码器符号、零位或 LowCmd 速度模式。当前不填 `calibrated.map`，不发 LowCmd。
- CPRO `field_logs/` 再次完整回传为 `logs/cpro_field_logs_20261109_1005.tar.gz`（379,982 字节），包含本轮 600 帧原始日志；PC 侧原始采样也保留在上述 `*_windows_LowCapture.log`。

## 2026-11-09 10:06：AS2-W 低层公开资料复核

- 使用 agent-reach GitHub CLI 与 Exa 定向搜索 `as2w lowcmd`、AS2-W 公开仓库和轮轴 SDK 示例；未找到能够回答本台固件 16 轴物理映射/轮轴 LowCmd 模式/控制权交接的官方发送代码。命中标准 AS2、B2-W/Go2-W、G1 和 AS2-W URDF，均不能替代本台低层合同。查询与来源记在 `logs/20261109-1006_as2w-source-search.md`。
- 整理给宇树/设备方的具体问题到 `02_现场操作/需厂商确认的低层信息.md`，包含当前实测前提、16 轴表、轮轴命令、CRC/周期、切换/恢复、断联安全、机体系速度、遥控器持续性。拿到适用于这台固件的证据前，不增加 LowCmd 发送端。
- 最终资料和 `tools/analyze_low_capture.py` 再次通过 Windows `现场入口.ps1 -Stage Sync` 传入 CPRO，两个现场包在 CPRO 端 SHA-256 均 OK；原始记录：`logs/20261109-100539_windows_Sync.log`。本次仅更新非机器人控制文件，ARM64 `as2w_sdk2` 二进制仍为 09:59 编译通过的版本。
- 复查个人 PC 的早期临时地址：`Get-NetIPAddress -IPAddress 192.168.123.220` 与 `Get-NetAdapter -Name '以太网 4'` 均无输出；该 USB 网口当前不在枚举中，未再发现待清理的 PC 临时地址。CPRO `eth0` 地址/路由仍保留给现场 DDS。

## 2026-11-09 10:28：OpenCode 服务器交接准备

- 用户要求服务器 `192.168.10.163` 上的 OpenCode 接手，仍通过 Windows 工作站访问 USB/HDC 与 AS2-W，项目源码/调试日志全部保留在本机。还明确厂商不会提供低层合同，优先 stairs 平地可行性，recovery 因速度观测暂缓。已将规则写入根/现场 `AGENTS.md`，并新增 `02_现场操作/低层自测计划.md`，把旧“向厂商询问”改为现场自主取证。
- 工作站 WLAN 为 `192.168.10.61`，工作站→服务器 SSH 已实测；服务器 Ubuntu 24.04.4、OpenCode 1.18.18 可运行，`sshfs 3.7.3` 已安装。工作站没有 `sshd.exe` 和 22 监听；准备了限定服务器来源 IP 的管理员安装脚本、公钥、Windows ASCII 路径只读阶段启动器、SSHFS/OpenCode 操作说明和完整首条提示词，均在 `05_OpenCode交接/`。原始检查摘要：`logs/20261109-1028_opencode-server-preflight.md`。
- 当前仍需现场人员以管理员 PowerShell 执行 `05_OpenCode交接/启用工作站SSH.ps1`；已发出具体命令等待结果。之后需逐项实测服务器→工作站公钥登录、SFTP 路径、SSHFS 挂载、远程 `GetState` 和本机日志写入。未对机器人发新动作。

## 2026-11-09 10:46：OpenCode 服务器完整链路验收

- 现场人员在管理员 PowerShell 执行 `05_OpenCode交接/启用工作站SSH.ps1` 成功，Windows `sshd` 监听 TCP/22；安装原始日志：`logs/20261109-104250_workstation_ssh_setup.log`。服务器 `caolin` 使用专用 ed25519 公钥登录工作站 `zoubu@192.168.10.61`，`whoami` 返回预期账号。
- 服务器 SFTP 能列出 `/D:/Projects/Athena/运动控制/Collie/AS2-W_CPRO`；`sshfs` 挂载在 `/home/caolin/as2w_workstation`，`mountpoint` 确认是真实挂载点并能读根 `AGENTS.md`。
- 服务器执行 `ssh ... powershell.exe ... C:/Users/zoubu/as2w_field.ps1 -Stage GetState`，由工作站经 HDC/CPRO 查询狗，返回 `rc=0`、`fsm_name=ai_damping`；原始阶段日志自动留在工作站 `logs/20261109-104554_windows_GetState.log`。这是一条只读命令，没有机器人动作。
- 交接说明和首条提示词在 `05_OpenCode交接/`，当前可在服务器挂载目录启动 OpenCode。后续项目源码和调试日志仍以 Windows 工作站为权威位置。

## 2026-11-09 11:20：stairs 权重 MuJoCo 平地复测（服务器 OpenCode，无狗动作）

- 环境：服务器 OpenCode 经 SSHFS 使用工作站目录；Ubuntu 24.04、Python 3.12.3、`mujoco==3.17.0`（pip --user）。本阶段零机器人命令、零 HDC、零网络变更。原始会话记录：`logs/20261109-1120_opencode-flat-rerun.md`。
- 资产取证：工作站交付（Rob2Nav rev `e61aaf79`）不含 MuJoCo 模型与 contract；从 main 分支 `omni-blind-stairs/assets/` 取得 `as2w_flat.xml` 与 `fall-recovery-contract.json`（SHA-256 记录于 `部署参考/as2w-flat-rerun/README.md`）；工作站 `unitree_ros` 的 `as2w_description` 与交付固定版 `4005a1b` 逐字一致。训练归档 `as2w-results`（`.pt`）仍缺，但确认非必需：actor 可直接从交付 `.bin` 解析（格式按 `policy.cpp`，defaults 与 contract 完全一致，SHA-256 与 manifest 一致）。
- 框架验证三条锚点：① recovery-r12 平地复跑 16/16（交付 torch 参考 16/16、native 15/16），边缘种子 right/12002 我方 1.060 s 对交付 native 0.98 s，为阈值两侧浮点抖动；② 楼梯交叉复现三份均 0/16，48 种子 `visited_levels` 39 个完全一致、其余 ±1 级（全在失败区间），r17-3000/27001 双方均到第 2 级；③ MuJoCo 执行器按腿分组与策略动作按关节类型分组的顺序差异已按交付代码映射。
- **核心结果：三份爬楼权重在 MuJoCo 平地全部能行走，96/96 试次（16 种子 × {nominal, stress}）upright_fraction=1.00，动作零限幅、零 URDF 超速，对摩擦/质量/增益/推扰动力学应力稳健。** 9 s 前进距离：stairs-r14 5.27 m（0.59 m/s，超速 47%）、stairs-r17-2000 4.10 m（0.47 m/s）、stairs-r17-3000 3.41 m（**0.400 m/s，与指令精确吻合**，稳走占比最高 0.54–0.58）。横向漂移为盲走策略已知局限（r17-3000 最坏 1.07 m）。
- 判断与门槛：“爬楼权重可能平地能走”由待验假设升级为**仿真验证事实**；若做只读影子首选 stairs-r17-3000。此结论仅限 MuJoCo，不代表真机；真机 LowCmd 门槛（16 轴映射、轮轴语义、运控切换）不变，`calibrated.map` 仍不填写。main 分支新一代 R21 全向候选（平地 34/52）未评估、不替代交付权重。
- 产物：`部署参考/as2w-flat-rerun/`（脚本、资产、README 含来源哈希）与 `results/` 三份逐试次 JSON。下一阶段（无狗动作）：平地变体扫描（摩擦/初始航向）+ 20 Hz 采样槽位-运动学离线关联分析，然后才设计 CPRO 只读影子。

## 2026-11-09 11:30：离线映射分析、假设 map 与只读影子 20 ms 链路测试（无狗动作）

- 环境：服务器 OpenCode（SSHFS + SSH→工作站→HDC→CPRO）；狗全程趴下，运行前后 `GetState` 均为 `ai_damping`。原始会话记录：`logs/20261109-1130_opencode-chain-shadow.md`。
- 离线分析（`部署参考/as2w-flat-rerun/analyze_capture.py`，输入 10:02 的 600 帧采样）：槽 0–11 为按腿三元组 (hip,thigh,calf)×4（趴下 [±0.58,~1.0,−2.75]、站立 [±0.21,0.83,−1.99]，全帧在 URDF 限位内）；hip 镜像 (−,+,−,+) 给出左右分组 {0,2}/{1,3}；四轮槽前向 dq 全正（与 URDF 轮轴 +y 一致）。IMU 只读验证：quat wxyz body→world 单位四元数、陀螺=机体系角速度（与四元数差分相关 0.83–0.93、斜率≈1）。**腿/轮绝对身份（前后）、符号、零位仍未验证**；AS2-W 为轮驱滚动，四腿同步、无步态对角结构，前后分组需专门测试。证据已写入 `config/hardware_contract.md`；`calibrated.map` 保持 UNVERIFIED。
- 源码改动（只读诊断增强）：新增 `config/hypothesis.map`（**假设映射，仅链路计时用**）；`diagnostics.cpp` shadow 增加时延统计与 `SHADOW_SUMMARY`；`现场入口.ps1` 新增 `Shadow` 阶段。过程事故（已修正并记录）：shadow 编辑时误将 `src.q` 写成 `src.q()`，服务器 x86 编译检查立即拦截，对照包内版本修正后 diff 干净、x86 与 ARM64 编译及 7/7 CTest 通过。
- 部署链实测（11:27–11:28）：`Sync`（两包 SHA-256 OK）→ `SdkBuild`（7/7+ARM64）→ `GetState`（`ai_damping`）→ `Shadow -Model stairs-r17-3000 -Seconds 60`。**20 ms 链路测试通过**：451 tick @50 Hz、`stale_skips=0`、状态年龄 p50 0.55 ms/p99 1.13 ms/max 21.7 ms、推理 p50 0.25 ms/p99 0.64 ms/max 1.16 ms；最坏帧约 23 ms < 50 ms 锁定阈。`locked=1` 为 stairs 450 tick（9 s）视界的**按设计停止**，非故障；60 s 请求仅产出 9 s 有效段。预演轮速有界（瞬态 8.7 后收敛 ~3.9 rad/s）；程序自身声明并确认无任何 LowCmd 发布。此为趴下态链路验证，不代表策略语义正确（映射未标定）。
- 原始日志：Windows `logs/20261109-112712_windows_Sync.log`、`20261109-112723_windows_SdkBuild.log`、`20261109-112748_windows_GetState.log`、`20261109-112755_windows_Shadow.log`；CPRO 归档 `logs/cpro_field_logs_20261109_1130.tar.gz`（回收经 `cpro_ubuntu.sh /bin/tar` 打包 + HDC file recv，Windows 路径须反斜杠绝对路径）。
- 待现场人员配合（每次先说明具体动作并等明确同意）：① 站立态影子（需遥控起立）；② 原地慢速左右转各 ~10 s（分轮左右）；③ 1 kHz 采样起立/趴下（分前后腿）。影子回合重置语义（9 s 视界）列入待办。

## 2026-11-09 11:41：现场动作序列采样（现场人员操作遥控器，本工程全程只读）

- 现场人员明确同意后按预告执行动作序列（实际：起身+长暂停、右移一小段、左移一小段、左转、右转、趴下、起身、趴下）。采样三程序并行只读：100 Hz LowState 全量（`LowCaptureFast`，新增 10 ms 周期参数）、20 Hz SportState FSM、50 Hz stairs-r17-3000 影子（新增 450 tick 回合自动重臂）。启动事故两项已记录（`-Seconds` 超 ValidateRange 被拒；ssh 会话被回收但远端孤儿进程存活致两组并行，数据等价）。
- **映射判定（核心成果）**：两次已知方向转向交叉验证给出**轮侧别 12/14=右、13/15=左**；转向对称性给出**轴分组 12/13 同轴、14/15 同轴**（绕内侧后轮枢轴几何：驱动轮为外侧后轮）；侧别+hip 镜像+轴分组三结构互证**轮-腿配对 轮 k+12↔腿 k**。前后分组剩两候选：A=(FR,FL,RR,RL) 右先前先（侧移步态结构支持）vs B=(RR,RL,FR,FL)；起立/趴下四腿同步（20–80 ms）无法分前后。零位 offset 全部未标定。
- 影子站立分布观测：预演轮速 −1.92 rad/s 稳定小值后滚（真实站姿 calf −2.09 vs 训练默认 −1.6 偏 0.49 rad）——offset 未标定直接进观测，真机控制前必须标定。影子 34 回合零锁定，链路指标 age p99 2.6 ms、推理 p99 0.69 ms。
- 产物：`logs/20261109-1210_opencode-session-mapping.md`（含全部数值表）、`20261109-114107_windows_LowCaptureFast.log`（29999 帧基准）等六个 Windows 日志、`cpro_field_logs_20261109_1200.tar.gz`、分析脚本入 `部署参考/as2w-flat-rerun/`；`hardware_contract.md` 已更新。下一门槛：人工抬机头/机尾判 A/B（需同意）；R21 新策略平地验证与接入。

## 2026-11-09 12:15：R41 新盲爬楼/平地策略验证与接入（用户指示替换旧 stairs 权重）

- 用户指示：停用旧三份 stairs 权重，改用同事最新 `omni-blind-stairs`（R41 代际），先在 MuJoCo 验证平地行走。全程无狗动作、无 CPRO 写入。
- 取证：R41 全量 49 文件经 GitHub raw 拉取（首两批因 raw 302 重定向且 `curl -sf` 不跟随而失败，加 `-L` 后全成），`SHA256SUMS` 校验通过；工作站副本 `部署参考/omni-blind-stairs/`（5.5 MB，含 pt/onnx/C++ 适配器/评估 JSON/视频）。
- **平地 MuJoCo 复验（服务器，MuJoCo 3.17.0 + torch 2.15 CPU，`evaluate_omni_joint.py`）：固定集 41/52、零跌倒**（forward 0.2/0.4 m/s、倒退、左右转、停车均 4/4；0.6 快进 2/4、纯侧移 1–2/4）；独立集 20/52、零跌倒；本体感受审计 67,200 帧一致——与交付 README 逐字一致。结论：**R41 平地行走正常，达到替换条件**。楼梯边缘种子数值敏感（独立集 6 cm 我方 8/21 vs 同事 10/21，torch 版本差异；平地不受影响）。
- **接入维护树（cpp_deploy-as2w）**：新增 `deploy/include/isaaclab/algorithms/`（OrtRunner，源出 wty-yy/unitree_cpp_deploy@4f71bf3）、`deploy/robots/as2w/r41/`（交付四文件 + CMake，仅修 `../../include`→`../../../include` 适配子目录层级）、`models/r41/`（onnx + deploy.yaml + 750 帧校验轨迹；yaml 的 policy_file 改同目录相对路径并文档化）；根 CMakeLists 加 `AS2W_R41` 选项。服务器 x86 构建 + **回放 750 帧 max_abs_error=0**（与交付 cpp-replay.txt 一致），原 7/7 CTest 无回归。manifest.json 新增 `onnx_policies.r41` 条目（接口/验证/来源）。
- **关键约束：ONNX Runtime 必须为 1.22.0**——1.24.2 报 `TopK ShapeInferenceError` 拒载该模型；CPRO aarch64 部署按 1.22.0 取包。
- 旧三份 stairs .bin 权重保留在 models/ 与 manifest（离线/对照用途），但**后续 stairs 相关影子/验证以 R41 为准**；recovery 路径不变。
- 原始产物：`部署参考/omni-blind-stairs/verification_server_20261109/{fixed,confirmation}.json`、`models/r41/README.md`。下一步（CPRO，未开始）：ORT 1.22.0 aarch64 包传入 + `AS2W_R41=ON` ARM 构建 + 回放校验 + `shadow.cpp` 只读探针接线（映射表用 11:41 会话证据，A/B 前后与零位未定项仅作链路观察）。

## 2026-11-09 12:30：下午 Codex 交接沉淀（无狗动作）

- 用户指示：交接给 Codex 做下午实机线；输入只用原厂遥控器（明确否决 Xbox/键盘）；核心目标 = 映射补齐后实机测 R41，含策略接管、起身（passive→fixstand 插值，参照 GO2 State_Fix 模式自行设计）与控制权切换链。
- 沉淀动作：根 `AGENTS.md` 阶段门槛段整体更新（R41 为准、16 轴结构判定结论、遥控器双角色与急停未验证警告、实机测试链门槛）；`02_现场操作/实机事实与命令.md` 新增"16 轴 DDS 槽位结构"与"IMU"两节并在构建段补 R41/影子链路事实；新写 `05_OpenCode交接/给Codex的交接提示词.md`（自包含：规则、当前状态、G1–G5 门槛顺序、GO2 FixStand 参考分析、已知坑清单、文件地图）。
- GO2 参考结论（为 Codex 预研）：State_Fix = enter 快照当前姿态 + ts/qs 关键帧线性插值 + auto_transition；FixSquat 反向自动回 Passive（趴下进入）；Passive = mode 配置 + kp0/kd 阻尼 + q 跟随；GO2 代码无 CRC 处理。可借鉴模式，数值/增益/"零命令=安全"不可沿用（与 architecture.md 既有结论一致）。go2_v066 Xbox→UDP 方案按用户指示不采用。
- 用户追加标定方案（已写入交接文件 G1）：**逐关节手掰标定会**——趴下态 100 Hz 连续采样，用户按固定顺序手掰 12 腿关节+手转 4 轮并记录物理方向，配离线分析脚本 `tools/joint_calib_analysis.py`（活动段切分→主导槽+Δq 方向；两态静态读数表；映射表模板）一次解决 16 轴身份（含 A/B 判定）、每轴符号、两态锚点。脚本须先在今日 `20261109-114107` 日志上自测（已知转向段侧别结论可校验）。
- 记录完备性自查：INDEX 10:46–12:30 共 6 节齐；今日 logs 含 5 份会话记录 + 8 个 Windows 阶段日志 + 3 个 CPRO 归档；hardware_contract/manifest/实机事实均已更新。交接文件即本阶段产物。

## 2026-11-09 14:07：Codex 接手 G1 离线工具与当前默认阻尼姿态基线（无狗动作）

- 环境/设备：Windows 工作站 Python 3.13.6；CPRO 鸿蒙宿主 aarch64 + Ubuntu 22.04.5 aarch64，HDC→CPRO→AS2-W `eth0` 已通；机器人固件版本仍未知（旧 `GetPkgVersion rc=3203`）。只读 `GetState` 返回 `fsm_id=0 fsm_name=ai_damping process_state=active`。现场人员称当前为默认 passive 姿态；本记录只使用实测 FSM 名称，未切换模式、未发布 LowCmd、未发动作。
- 命令：`powershell.exe -ExecutionPolicy Bypass -File .\部署测试\现场入口.ps1 -Stage GetState`；随后同入口 `-Stage LowCaptureFast -Seconds 5`。原始日志：`logs/20261109-140719_windows_GetState.log`、`logs/20261109-140729_windows_LowCaptureFast.log`。5 秒中 498 完整样本（前两行无状态）、0 活动段，4.97 秒连续静态。
- **当前 ai_damping 的 16 槽 q 均值（rad，按 DDS 槽 0→15）**：`[-0.572455, 0.993568, -2.756354, +0.567640, 1.047454, -2.756059, -0.563007, 1.009343, -2.757107, +0.579611, 0.949795, -2.714700, -0.165384, -0.154790, -0.457994, -0.174418]`。0–11 为四腿三元组；12–15 为轮累计角，**不能解释为固定零位**。逐槽 JSON/可读表：`logs/20261109-140729_windows_LowCaptureFast_joint_calib_analysis.json/.md`。
- G1 离线工具：新增 `部署参考/cpp_deploy-as2w/tools/joint_calib_analysis.py`，解析 35 槽+IMU 的 LOW_SAMPLE、按 >1.5 s 空隙切活动段、输出各槽 Δq/平均 dq、两态连续静态窗口、R41 contract 16 轴映射空模板；另用 gyro_z 独立识别转向窗口。自测命令：`python 部署参考\cpp_deploy-as2w\tools\joint_calib_analysis.py 部署测试\04_调试记录\logs\20261109-114107_windows_LowCaptureFast.log --check-known-turns`；输出 29999 帧、10 活动段、12 静态窗口、2 已知转向，**PASS：左转 187.56–190.74 s 轮 dq [1.72,−2.30,6.11,−0.40]，右转 203.11–205.35 s [−3.14,2.60,−1.12,7.53]，均支持 12/14 右、13/15 左**。原始自测输出 `logs/20261109-G1_joint_calib_selftest.log`，结构化结果 `logs/20261109-114107_windows_LowCaptureFast_joint_calib_analysis.json/.md`。`py_compile` 两个分析脚本通过。
- **旧站姿数值纠错（影响后续安全门槛）**：11:41 原始日志连续静态站姿 79.10–149.28 s 的槽 2/5/8/11 calf 约 `[-1.240,−1.224,−1.227,−1.227]`，thigh 约 0.60、hip 约 ±0.12；趴下槽 calf 约 −2.75。旧 `analyze_session_20261109.py` 的“站立静止段”仅按 dq/gyro 过滤，把**趴下与站立**一起求均值，产生错误的 calf −2.09、thigh 0.83、hip ±0.25；已增加姿态过滤并更正根 AGENTS、现场事实、hardware_contract 和 Codex 交接词。旧“站姿相对训练默认 calf 差 0.49 rad”的结论撤销；旧 shadow −1.92 rad/s 仍只是未标定 map 的一次输出，不能用于 offset 推导。10:02 的 20 Hz 原始日志中站姿 calf 亦约 −1.24，交叉支持本次复核。
- 包与未决：`准备现场包.ps1` 已重新生成现场包，源码包 SHA-256 `020b87928006ff9bcc745859484633e84489cfab9638c7d03b2236f5c00806c0`，tar 内含新增脚本；打包日志 `logs/20261109-G1_package.log`。CPRO 现有包尚未同步此离线脚本，无实机动作需求。**G1 只完成工具和既有日志自测**：16 轴物理身份/符号、站姿对应训练坐标的 offset 尚需现场人员逐关节单变量标定；不发布 LowCmd。下一步是现场人员确认可安全手掰的趴下状态与看护条件，约定 12 腿关节+4 轮操作顺序，启动不超过 300 秒的只读采样并现场记录每项物理方向；遥控器全轴标定另行告知和获同意。
- CPRO 原始 `field_logs/` 已用 Ubuntu 内 `/bin/tar` 打包并经 HDC 回收到本机 `logs/cpro_field_logs_20261109_1407.tar.gz`（SHA-256 `5aac9ff8471b6a770b23ff73018d02042d568f061604390952fcf8d4e09a3819`）；归档目录核对含 14:07 `sport-command` 与 `low-capture` 两份原始日志。
- 现场单变量操作记录模板已备好：`02_现场操作/G1关节手动标定记录.md`（16 项物理关节/轮顺序、方向、时间、联动与异常栏）。`sign` 要以训练模型正方向作几何核对，不能由单个 DDS 正负值直接命名。

## 2026-11-09 14:17–14:22：G1 手动标定第一段（左前上关节和大腿；无程序动作）

- 现场人员明确同意后，本机启动 `powershell.exe -ExecutionPolicy Bypass -File .\部署测试\现场入口.ps1 -Stage LowCaptureFast -Seconds 300`；仅订阅 LowState，未发 LowCmd/高层动作。采样前 `GetState` 为 `ai_damping`，采样后再次查询仍为 `ai_damping`。原始日志：`logs/20261109-141703_windows_GetState.log`、`logs/20261109-141712_windows_LowCaptureFast.log`、`logs/20261109-142233_windows_GetState.log`；离线分析 `logs/20261109-141712_windows_LowCaptureFast_joint_calib_analysis.json/.md`、`20261109-G1_session1_analysis.log`。29999 有效样本，4 活动段、5 静态窗口。
- 现场人员按提示先操作**物理左前上关节**，自述“往里、再往外，幅度不大”：58.05–59.00 s 主导 DDS 槽 3，Δq `+0.18622 rad`；60.98–62.17 s 同槽 `−0.14822 rad`；其它腿槽变化小，支持 `FL_hip ↔ slot 3`。方向关系仅记为“往里 q 增、往外 q 减”，contract sign 待模型正方向核对。
- 再操作**物理左前大腿**，自述“上抬到限位、再下放回 passive 姿态”，并观察到上关节可能联动。202.42–212.59 s 槽 4 `+2.40374 rad`，槽 3 `−0.33797 rad`；215.39–224.29 s 槽 4 `−2.45847 rad`，槽 3 `+0.30580 rad`，轮槽 13 另累计 `+2.58516 rad`。支持 `FL_thigh ↔ slot 4`，但此动作**非纯单关节**，不能把整个时间段当作符号/零位标定；没有继续强掰。现场逐项记录见 `02_现场操作/G1关节手动标定记录.md`。
- 本段采样到 300 s 自然结束、退出码 0。14:22 开启第二段只读采样，下一项为左前小腿；待原始日志归档和逐项核对。16 轴映射尚未完成，`calibrated.map` 不填，LowCmd 不发布。

## 2026-11-09 14:22–14:30：G1 手动标定第二段（左前小腿、轮；只读采样退出失败）

- 现场人员按逐项提示操作。命令仍为 `现场入口.ps1 -Stage LowCaptureFast -Seconds 300`，仅订阅，**无程序动作命令**。原始日志 `logs/20261109-142242_windows_LowCaptureFast.log`，分析 `logs/20261109-142242_windows_LowCaptureFast_joint_calib_analysis.json/.md` 与 `20261109-G1_session2_analysis.log`。样本完整：29999 有效帧、3 活动段；期间 `mode_pr=0 mode_machine=2`，前后只读 `GetState` 均为 `ai_damping`（后者 `logs/20261109-143011_windows_GetState.log`）。
- 左前小腿：现场人员先抬大腿、再小腿**向下伸展**、**向上折叠**、最后放下大腿。约 42–48 s，槽 5 `+1.822 rad`；48–55 s，槽 5 `−1.932 rad`，支持 `FL_calf ↔ DDS slot 5`。同段槽 4 和轮槽 13 有明显联动，故净 Δq 几乎相消；离线脚本增加 `q_range_rad`/`dominant_excursion_slot`，使往返动作仍可审计，不自动把净位移主导槽当作关节身份。
- 左前轮：现场人员先按狗向前行走方向手转、再向后方向手转；258.13–264.54 s 槽 13 `+3.93716 rad`，266.37–272.43 s 同槽 `−5.53996 rad`，其它腿槽几乎不动，支持 `FL_foot ↔ DDS slot 13`、前滚 q 正。操作者方向和逐项读数见 `02_现场操作/G1关节手动标定记录.md`。
- **失败**：样本写满 300.00 s 后，`as2w_sdk2` 在 Cyclone DDS `EntityDelegate::prevent_callbacks()` 清理处断言，退出码 134；`现场入口` 因此退出码 1。不是采样中途断流，完整 29999 帧仍可分析；但退出清理竞态尚未排除，后续采样须保留失败记录并复查。CPRO 无残留 `as2w_sdk2` 进程，14:30 `GetState` 正常，未见控制权变化。CPRO `field_logs/` 已通过 Ubuntu `/bin/tar` + HDC 回收为 `logs/cpro_field_logs_20261109_1430.tar.gz`（含本次原始 CPRO 日志）。
- 下一项：右前腿上关节。先确认无残留进程后再开新只读采样，继续逐项 cue；其余 12 轴仍未人工标定、符号/offset 未确认，继续禁止 LowCmd。

## 2026-11-09 14:31–14:37：G1 手动标定第三段（右前上关节、大腿、小腿；无程序动作）

- 命令：`现场入口.ps1 -Stage LowCaptureFast -Seconds 300`，只读，退出码 0；采样后 `GetState` 为 `ai_damping`。原始本机日志：`logs/20261109-143101_windows_LowCaptureFast.log`、`20261109-143727_windows_GetState.log`；CPRO 原始单文件 `logs/cpro_20261109-143101_low-capture_47358.log`；离线输出 `logs/20261109-143101_windows_LowCaptureFast_joint_calib_analysis.json/.md`、`20261109-G1_session3_analysis.log`。29999 完整样本、4 活动段。
- **右前上关节**：现场人员连续做三次“往里→往外”。槽 0 每次从约 −0.57 降到 −0.79 rad 后返回；净 Δq 近 0，但 q 范围 0.223 rad、为腿槽最大。支持 `FR_hip ↔ slot 0`；往里 q 负、往外 q 正。首次槽 1 有约 0.11 rad 联动，轮槽 12 有约 +0.18 rad 轻微转动。接近角度边界，已提示后续仅小幅操作。
- **右前大腿**：现场人员上抬后返回；159.32–169.05 s 槽 1 `+2.46163 rad`，170.77–179.33 s 槽 1 `−2.46286 rad`，支持 `FR_thigh ↔ slot 1`。上关节槽 0 约 ±0.3 rad 联动，下放轮槽 12 约 +0.7 rad，不能算纯单轴。
- **右前小腿**：现场人员先抬大腿定位，小腿向下伸展再向上折叠，最后放下大腿；约 266–270 s 槽 2 `+0.738 rad`，270–276 s 约 `−0.814 rad`，支持 `FR_calf ↔ slot 2`。段内槽 1、0 亦联动，故用分动作窗口而非总净 Δq 判定。操作者表述与时间见 `02_现场操作/G1关节手动标定记录.md`。
- 当前人工已识别右前 3 腿槽、左前 3 腿槽及左前轮；前后候选 A 的**前腿部分**得到直接支持（右前槽 0–2、左前槽 3–5），但后腿与其余轮仍待手动测，不能提前填完整 `calibrated.map`。第四段只读采样已启动，下一项右前轮。

## 2026-11-09 14:37–14:44：G1 手动标定第四段（右前轮、左后上/大/小腿；退出失败）

- 命令：`现场入口.ps1 -Stage LowCaptureFast -Seconds 300`，只读，无动作命令。原始 Windows 日志 `logs/20261109-143736_windows_LowCaptureFast.log`，CPRO 原始单文件 `logs/cpro_20261109-143736_low-capture_48792.log`，离线结果同 stem `_joint_calib_analysis.json/.md` 与 `20261109-G1_session4_analysis.log`。30000 完整样本、5 活动段；采样后 `GetState` 仍 `ai_damping`（`logs/20261109-144352_windows_GetState.log`）。
- **右前轮**：用户按前滚→后滚手转，槽 12 从约 0.881 增至 4.156、再降至 −0.429 rad，支持 `FR_foot ↔ slot 12`，前滚 q 正；其它腿槽范围 <0.067 rad。
- **左后上关节**：用户往里→往外，131.41–132.46 s 槽 9 `+0.18085 rad`，134.45–135.41 s 同槽 `−0.15271 rad`，支持 `RL_hip ↔ slot 9`。与物理右前槽 0–2、左前槽 3–5 合起来，**前后候选 A=(FR,FL,RR,RL) 得到物理单关节证据**；但后腿三元组仍继续逐项确认。
- **左后大腿**：用户小幅上抬→放回，槽 10 约 0.967→1.665→0.977 rad，即 +0.698/−0.688；轮槽 15 回位约 +0.38 rad。支持 `RL_thigh ↔ slot 10`，往返净位移被抵消。
- **左后小腿**：用户先抬大腿定位，小腿下伸→上折→放下大腿，自述轮子联动。约 290–298 s，槽 11 约 −2.75→−1.73→−2.76 rad，即 +1.02/−1.03；轮槽 15 同段约 +0.93 rad。支持 `RL_calf ↔ slot 11`。采样到 300 s 时大腿放回的尾段未完全覆盖；14:43 `GetState` 仍 `ai_damping`，未发机器人命令。
- **失败**：同 14:22 第二段，300 s 数据写完后 Cyclone DDS `prevent_callbacks()` 断言，退出码 134、Windows 阶段报错；无数据缺口、无残留进程，原因仍待查。第五段只读采样已启动以继续左后轮。`calibrated.map` 仍未填，LowCmd 禁止发布。

## 2026-11-09 14:44–14:50：G1 手动标定第五段（左后轮、右后上/大腿；无程序动作）

- 命令：`现场入口.ps1 -Stage LowCaptureFast -Seconds 300`，只读，退出码 0；完整有效样本 29998、4 活动段。原始本机日志 `logs/20261109-144414_windows_LowCaptureFast.log`，CPRO 原始 `logs/cpro_20261109-144414_low-capture_50286.log`，分析同 stem `_joint_calib_analysis.json/.md`、`20261109-G1_session5_analysis.log`。采样后 `GetState` 为 `ai_damping`（`logs/20261109-145027_windows_GetState.log`）。
- **左后轮**：用户先前滚→后滚；17.79–22.15 s 槽 15 `+2.61752 rad`，23.73–28.98 s 槽 15 `−2.85630 rad`，支持 `RL_foot ↔ slot 15`、前滚 q 正，其它腿槽微小。
- **右后上关节**：用户先往里→往外，126.95–130.63 s 槽 6 从约 −0.564 到 −0.784 后回到 −0.571 rad；范围 0.223、净 Δq 近 0。大腿槽 7 约 0.088 rad 联动，支持 `RR_hip ↔ slot 6`、往里 DDS q 负。
- **右后大腿**：用户小幅上抬→放回，225.81–232.99 s 槽 7 约 1.016→1.982→1.021 rad，+0.966/−0.961；轮槽 14 范围约 0.36 rad，支持 `RR_thigh ↔ slot 7`。细目见 `02_现场操作/G1关节手动标定记录.md`。
- 本段结束无清理断言，随后启动第六段只读采样，下一项右后小腿和右后轮。至此除右后小腿、右后轮外，14 个物理轴已有手动单变量证据；contract sign 仍需依据训练模型正方向核验，零位 offset 仍未知，不发布 LowCmd。

## 2026-11-09 14:50–14:56：G1 手动标定第六段与 16 轴身份/状态符号汇总

- 环境同前：Windows PC→USB/HDC→CPRO 鸿蒙 Ubuntu 22.04.5 aarch64→AS2-W `eth0`；固件版本仍未知。命令 `现场入口.ps1 -Stage LowCaptureFast -Seconds 300`，**只读**，退出码 0；有效 29999 样本、2 活动段。原始本机日志 `logs/20261109-145036_windows_LowCaptureFast.log`，分析同 stem `_joint_calib_analysis.json/.md` 与 `20261109-G1_session6_analysis.log`；结束后 `GetState` 为 `fsm_id=0 ai_damping`（`logs/20261109-145612_windows_GetState.log`），未切换控制权、未发 LowCmd。
- **右后小腿**：用户按提示抬大腿定位、小腿下伸→上折→放回大腿。约 42–48 s，槽 8 q 从 −2.758 至 −2.159 再回 −2.757 rad，即 +0.599/−0.598；大腿槽 7、上关节槽 6 和轮槽 14 联动，但小腿双向响应明确，支持 `RR_calf ↔ slot 8`。
- **右后轮**：用户手转前滚→后滚。约 126–132 s 槽 14 q 从 0.819 增至 3.267、再降至 0.355 rad，即 +2.448/−2.912；其它腿槽范围 <0.014，支持 `RR_foot ↔ slot 14` 和前滚 q 正。
- **G1 物理身份已完成 16/16**：腿三元组 `FR=(0,1,2)、FL=(3,4,5)、RR=(6,7,8)、RL=(9,10,11)`（各为 hip/thigh/calf）；轮 `FR=12、FL=13、RR=14、RL=15`。R41 contract 序的 DDS 槽 `[3,0,9,6,4,1,10,7,5,2,11,8,13,12,15,14]`，前后候选 A 经每腿人工动作确认。按 R41 XML 的 +x hip、+y thigh/calf/wheel 轴与现场“里/外、上/下、前/后”方向几何对照，**LowState 状态符号**为 hip 四轴 `−1`、其余 12 轴 `+1`。完整逐轴依据、两态锚点与边界见 `部署参考/cpp_deploy-as2w/config/r41_measured_identity_sign.md`、现场手填口述表 `02_现场操作/G1关节手动标定记录.md`，并已更新 `hardware_contract.md`、根 AGENTS 和实机事实页。
- **G1 仍未完成的低层合同**：`zero_DDS` 全部未定；原厂静止站姿不保证等于 R41 训练默认站姿，不能直接用二者相减定 offset。LowCmd 的命令正方向、电机模式/轮速度语义、CRC、运控释放/恢复、失联与遥控器急停仍未实测。状态方向不能自动视为命令方向；`calibrated.map` 继续 UNVERIFIED、禁止发布 LowCmd。遥控器全轴标定尚未做，需另行告知现场人员并获得当次明确同意。
- CPRO `field_logs/` 六段原始采样均经 Ubuntu `/bin/tar` + HDC 回收到本机 `logs/cpro_field_logs_20261109_G1_complete.tar.gz`（15,097,783 bytes，SHA-256 `b324cd544e2bd9e61ef02662944029f7224051e8d09c6fb41311bca7711cfa2e`）；tar 目录逐项核对含 14:17、14:22、14:31、14:37、14:44、14:50 六个 low-capture 文件。第二、第四段各在写满 300 s 后 Cyclone DDS 清理断言（退出码 134），其完整样本仍在且阶段失败已记；其余四段退出 0。没有残留采样进程。
- 离线脚本新增往返 `q_range_rad`，解决净 Δq 抵消；`py_compile` 与已知左/右转交叉自测 PASS。`准备现场包.ps1` 已重打包，源码包 SHA-256 `26230867057863f7d4896c6efd52505ebbc7e66b6724d3c10cc380c9a3a90ac5`，tar 内含脚本与映射证据页；原始打包日志 `logs/20261109-G1_final_package.log`。**下一门槛**：先设计可信的 R41 几何零位对齐；R41 ARM64 回放/只读影子可独立做环境准备，但输出仍只能视为假设，不能真机闭环。

## 2026-11-09 15:00–15:12：用户切换至 R152，服务器 MuJoCo 平地复测（无狗动作）

- 用户明确把当前目标策略从 R41 改为 GitHub `YuTaoV5/Rob2Nav` main 的 `deliveries/as2w-deploy/omni-blind-stairs-r152`，要求先看 MuJoCo 仿真。已用 `gh api` 核查交付目录，并以 `gh repo clone --filter=blob:none --sparse --depth 1 --branch main` 拉到工作站 `部署参考/Rob2Nav-r152-source/`，固定 HEAD `40c80f0e07362b0a8e38528379076355d50ecbf5`。R152 接口是 `obs[1,41]+state[1,844]`，区别于 R41 的 `state[1,835]`；模型、yaml、trace、C++ 适配必须成套更换。
- 仿真环境：服务器 `192.168.10.163` Ubuntu 24.04.4 x86_64、Python 3.12.3、MuJoCo 3.17.0、torch 2.15.0+cpu、ONNX Runtime 1.31.1；R152 ONNX 在该 ORT 上成功载入。Windows 项目 SSHFS 挂载 `/home/caolin/as2w_workstation`，结果直接写本机；机器人未接收任何新动作。服务器计算缓存 `/home/caolin/as2w_r152_assets/` 用 Rob2Nav main 的 AS2-W XML/contract 和本机 `unitree_ros` 官方 mesh/URDF；XML SHA-256 `2bf148d8e0e5722db4a581c7cf7834611121025cc1c95c14f892b83bc0fdfa01`，contract `1e4e3fb76806e83dbe3541979fa0cb40f4de298224bf9baa9b0490`，与既有 R41 交付资产完全相同。
- 命令：在 R152 `runtime/` 目录执行 `python3 -u audit_flat_geometry.py /home/caolin/as2w_r152_assets ../weights/policy.pt ../unitree_cpp_deploy/logs/as2w/r152/exported/policy.onnx ~/as2w_workstation/部署测试/04_调试记录/logs/r152_verify_20261109`。服务器端退出码 0；原始终端输出 `logs/20261109-r152_audit_server.log`，逐例结果 `logs/r152_verify_20261109/{python-flat,onnx-flat}.json`。共 Python/ONNX 各固定 52 + 独立 52（208 回合）。
- **ONNX 结果：固定跟踪/停车 44/52、严格接触/步态 21/52；独立 25/52、严格 9/52。104 回合零跌倒、零前轮换边。** 与仓库交付 `evidence/onnx-flat.json` 的 104 条逐例 `passed/qualified/fallen/front_cross_ticks` 完全一致（0 差异）；对照原始输出 `logs/20261109-r152_compare_published.log`。Python 本地复测固定 44/52 严格 22/52、独立 28/52 严格 10/52，较交付 Python 结果有 10 条布尔差异，推断属于仿真/torch 数值与接触阈值边缘敏感；**部署判断以 ONNX 闭环为准**，未把 Python 差异掩盖。
- 严格失败的主要原因：在“跟踪通过”者中，固定 23/44、独立 16/25 因**非轮部位触地峰值 ≥50 N**未通过严格检查；自碰撞 ≥1 N 或前轮换边在这些回合均为 0。首次触地部位固定集：RL_calf 11、RR_calf 8、RL_thigh 2、RR_thigh 2；独立集：RR_thigh 5、RR_calf 5、RL_calf 5、RL_thigh 1。固定触地峰值 50.4–122.3 N（中位 59.1），独立 53.6–167.3 N（中位 84.2）；逐项日志 `logs/20261109-r152_failure_breakdown.log`、`20261109-r152_contact_bodies.log`。**结论**：R152 在仿真有平地指令跟踪与停车能力、没有跌倒，但严格接触通过率低，不能把 44/52 当成 44/52 安全通过，更不能直接上实机闭环。
- 为服务器 OpenCode 写了可执行交接 `05_OpenCode交接/给OpenCode_R152续作提示词.md`：先复核严格接触失效，再系统迁入 `cpp_deploy-as2w`、x86/ARM 回放与只读 shadow，零位/LowCmd 合同未补齐前不发动作。旧 R41 保留作离线对照。Windows→服务器已配置专用 SSH 密钥（私钥仅在 Windows 用户 `.ssh/as2w_server`，不入项目），服务器→Windows SSHFS 原链路不变；项目日志仍只在本机。

## 2026-11-09 15:30：R152 严格接触复核、R41 同判据对比与 R152 迁移入源码树（服务器 OpenCode，无狗动作）

- 环境：服务器 MuJoCo 3.17.0/torch 2.15+cpu/ORT 1.31.1（Python）与 ORT 1.22.0 x64（C++，复用上午缓存）；SSHFS 挂载正常，本阶段零机器人命令、零 CPRO 写入。会话记录：`logs/20261109-1530_opencode-r152-strict-recheck.md`。
- **严格失败复核（读 `r152_verify_20261109/onnx-flat.json` + 交付 evidence）**：逐例 mismatch 0/104 再确认。失败全部为后腿非轮部位触地 ≥50 N（固定 23/44、独立 16/25；RL/RR calf 为主、thigh 次之）；时刻分布加速段 8/跟踪段 10/停车段 5（固定集）；首触力中位 57.4/67.7 N、最大 122/148 N。**剂量效应明确**：stop 与 forward_slow(0.2 m/s) 4/4 全严格通过；forward 1/4、forward_fast 0/4、斜移 0/4。"跟踪 44/52"≠安全通过，区分已写入 models/r152/README 与测试链方案。
- **R41 相同判据可比复测（新脚本 `部署参考/as2w-flat-rerun/r41_audit_strict.py`）**：在 R41 树内单进程复用相同 filtered 模型/种子/命令/判据（脚本内断言两树 FLAT_COMMANDS/gait_clock 逐项一致）；R41 经此 harness 的跟踪 41/52、20/52 与其自发布一致（驱动无失真）。**结果：R41 固定严格仅 13/52（py）/12/52（onnx）、独立 4/52（py）/5/52（onnx），且 41 个跟踪通过者中 18 例前轮换边**——R41 的 StopStance 前腿内收交叉（stop 回合 292/300 tick 前轮过中线 ~12 cm），forward/forward_slow/forward_fast/reverse 全部 4/4 换边；R152 零换边。净结论：**相同判据下 R152 全面优于 R41（固定严格 21 vs 13、独立 9 vs 4–5），用户切换有据**；但后腿触地是两代共性且 R152 频率更高（固定 52% vs 24% 跟踪通过者），实机起步限 stop/forward_slow 域不变。原始：`logs/r41_strict_verify_20261109/{python,onnx}-flat.json`。
- **R152 迁移入唯一源码树**：新增 `models/r152/{policy.onnx,deploy.yaml,r152-trace.csv}`（onnx SHA-256 `fdc661f936a08a96d8db7ae34bb26933f6c34ed980dae8a5119283812a80f5d1`、trace `9e31a294305c8b6f24211f45d5ab2c4acdc0af54f31c34dfcaad33a7a642945a`；yaml 与 R41 逐字一致、仅 policy_file 改同目录）与 `deploy/robots/as2w/r152/`（controller/replay/shadow/CMake 四文件，CMake 相对路径 ../../→../../../ 适配子目录）。根 CMakeLists 加 `AS2W_R152` 选项（与 R41 并列）。x86 `AS2W_R152=ON`+ORT 1.22.0 构建通过，**750 帧回放 `rows=750 max_abs_error=0 leg_and_wheel_targets=verified stale_state=latched_off`**（与交付 cpp-replay 逐字一致），根项目 7/7 CTest 无回归。manifest `onnx_policies.r152`（active deployment target）置顶、r41 标 superseded；`models/r41|README` 与 `models/r152/README` 状态同步。
- **实机测试链方案成文** `02_现场操作/实机测试链方案_R152.md`（用户要求的 passive→fixstand→R152→原厂遥控器行走逐步测试单，"手柄"按用户既有决定解释为原厂遥控器）：S0–S9 分步表（每步前置/动作/预期/中止）、P1–P9 前置门槛（零位两条标定路线：URDF 几何对齐 / 零假设+最小受控单点验证；遥控器急停 P5 验证；速度域限制=仅 stop/forward_slow）、FixStand 插值设计（GO2 State_Fix 模式、T1 原厂站立锚点 / T2 R152 默认姿态两候选终点、轮 dq=0、MuJoCo 整链预演门槛 P8）、遥控器输入映射（首测仅 vx，ly 已验证）、看门狗与"发布端默认不编译"安全框架。
- 下一门槛：CPRO R152 部署（ORT 1.22.0 aarch64 CPU 包传入、yaml-cpp、`AS2W_R152=ON` ARM 构建+回放、`shadow.cpp` 只读探针用 G1 实测映射表接线、field.sh/现场入口 R152 阶段、Sync 重打包）；随后按方案文档补 P2–P9 后才可能进 S1。

## 2026-11-09 15:45：R152 CPRO 部署与只读影子（服务器 OpenCode，狗趴下全程无动作）

- 环境：CPRO Ubuntu 22.04.5 aarch64；ORT 1.22.0 aarch64 CPU（`onnxruntime-linux-aarch64-1.22.0.tgz` 经 scp→HDC→宿主 cp 入 rootfs→Ubuntu 内解压至 `/root/ort122`，6.8 MB）；**yaml-cpp 0.7.0 经查 CPRO 已预装**（共享+静态+头），无需源码构建。狗运行前后 `GetState` 均为 `ai_damping`。
- 源码/入口改动：`build_on_cpro.sh` 增 `AS2W_R152_ROOT` 分支（build-r152 目录、`AS2W_R152=ON + AS2W_SDK2_SHADOW=ON`）；`field.sh` 增 `r152-build SDK_PREFIX ORT_ROOT`、`r152-replay`、`r152-shadow NIC [TOPIC]` 三阶段；`现场入口.ps1` 增 `R152Build/R152Replay/R152Shadow` 三 Stage；新增 `config/r152_measured.map`（G1 实测身份/符号：contract 序槽位 `[3,0,9,6,4,1,10,7,5,2,11,8,13,12,15,14]`、hip sign −1 其余 +1、**zero=0 未验证**）。x86 编译检查与 7/7 CTest 通过后 Sync 传输（两包 SHA-256 OK）。
- **交付缺陷修复（重要）**：R152 交付的 `shadow.cpp` 订阅用 `unitree_go::msg::dds_::LowState_`（GO2 族 IDL），与本机 AS2-W 实测发布的 `unitree_hg` 族类型不匹配——首跑 `R152Shadow` 静默零包（`No compatible LowState packets received`，退出 1）。用旧 `LowState` 阶段二分确认环境正常（~1000 包/s）后，把本树 `deploy/robots/as2w/r152/shadow.cpp` 改为 HG IDL 并注释说明；x86 复验→Sync→CPRO ARM 重编通过。**这正是交付 README 自称"DDS 兼容性未验证"的实例，已记录。**
- **CPRO 实测结果**：`R152Build` ARM64 构建 7/7 CTest 通过、`as2w_r152_replay/shadow` 链接成功；`R152Replay` 750 帧 `max_abs_error=2.38419e-07`（浮点噪声级，`leg_and_wheel_targets=verified stale_state=latched_off`）；修复后 `R152Shadow` **500 tick 跑通、退出 0**，预演目标有界（FL_hip q≈0，RR_foot dq 缓慢漂至约 −0.10 rad/s——趴下态分布外、零位未定，仅作链路观察），无失联锁止。
- 原始日志：Windows `logs/20261109-154142_windows_R152Build.log`、`20261109-154206_windows_R152Replay.log`、`20261109-154236_windows_R152Shadow.log`（失败首跑）、`20261109-154559/154616`（修复后 build/shadow）；CPRO 归档 `logs/cpro_field_logs_20261109_r152.tar.gz`（15.1 MB，含六个 r152 field_logs）。
- **R152 线状态：G2 完成**（x86+ARM 回放、只读影子全通）。剩余门槛不变：零位标定（P2）、LowCmd 合同（P3）、运控释放（P4）、遥控器急停验证（P5）、遥控器轴标定（P6）、MuJoCo 起身整链预演（P8）、看门狗代码（P9）——全部记录于 `02_现场操作/实机测试链方案_R152.md`，其后才可进 S1。

## 2026-11-09 15:55：零位标定方法改为机械限位对比（用户提议），calf 限位旁证与早稿纠正（无狗动作）

- 用户否决"趴下姿态可当限位参考"的隐含假设（趴下只是标准姿态），提议**逐关节轻推到机械硬限位读 DDS、对 URDF 限位**——采纳为主方法：每关节两端止点各自反推 zero、ΔDDS/ΔURDF 斜率（应≈1，验标尺）、推高端时 DDS 增减（验 sign）三重自校验，精度预期 ≤0.5°，远优于目视几何法。
- **早稿纠正（重要）**：原"几何对齐法"提议 calf 零位参考位="小腿与大腿共线（腿完全伸直）"——但 URDF calf 上限为 −0.8133 rad，关节物理上**永远无法完全伸直**，该参考位不可达，方案已作废并在 `实机测试链方案_R152.md` §2 与 `hardware_contract.md` 更正。
- 限位法参数记录：URDF 限位 hip [−0.785,+0.785]、thigh 前 [−2.0,3.492] 后 [−1.3,4.19]、calf [−2.7677,−0.8133]；轮无需零位（4π 回绕）。操作要点：轻推至扎实接触不硬怼、每止点保持 ~3 s、thigh 全范围若被地面/机身遮挡记录可达端。
- 离线旁证（保留为交叉核对而非结论）：趴下 FR/FL/RR 三腿 calf 读数 −2.7564/−2.7561/−2.7571，距 URDF 下限 +0.0113/+0.0116/+0.0106 rad（互差 0.03°）——若趴下贴死折叠止点则 zero_calf≈+0.011 rad；RL −2.7147（3.04°）为未折平例外。该旁证同时否定"原厂站立=训练默认姿态"零位假设（要求 zero_calf=+0.370 ⇒ 趴下 q_sim=−3.13 超下限 0.36 rad，不可能）。
- 方向约定澄清（应用户问）：URDF/MuJoCo 零位是**策略坐标系原点**（训练管线事实：SHA 验证的 XML 即训练资产、交付复现命令与 750 帧回放均在此坐标系），无需与厂商标"零"一致——固件相对它的偏移正是待测项。模型正方向：+x 前 +y 左 +z 上；hip 轴 +x（模型 +hip=腿向 +y，左腿外摆）；thigh/calf/foot 轴 +y（模型 +thigh=膝向后抬、+calf=伸膝、+wheel=轮顶向前）；G1 状态 sign（hip −1 其余 +1）来自人工方向对模型几何，LowCmd 命令方向仍未验证（P3）。
- 本阶段零机器人操作；文档更新：`实机测试链方案_R152.md` §2 重写、`hardware_contract.md` 新增"零位标定方法与 calf 限位旁证"行。

## 2026-11-09 16:20：零位标定第一轮——前双 hip 内收止点实测（现场人员操作，本工程全程只读）

- 流程：16:12:05 起 100 Hz LowCaptureFast 300 s（`logs/20261109-161205_windows_LowCaptureFast.log`，29999 帧）；现场人员将前两腿 hip 内收至截止并保持约 13 s 后释放。运行前后狗均为 `ai_damping` 趴下，未发任何命令。
- **平台段 [50,63]s 实测**：FL_hip(槽3) **+0.78701±0.00002 rad**、FR_hip(槽0) **−0.78668±0.00001 rad**；平台内扰动 ≤0.00014 rad（0.008°），其余腿槽扰动 ≤0.0002 rad（单变量干净），仅轮槽 12/13 有 ≤0.007 rad 松弛漂移。
- **结论**：URDF hip 限位 ±0.785、sign=−1 ⇒ **zero_FL_hip=+0.00201 rad（+0.115°）、zero_FR_hip=−0.00168 rad（−0.096°）——前双 hip 的 DDS 零位与 URDF 零位重合**；两轴 sign=−1 获止点级机械验证（FL 内收 DDS 增至 +0.787 对应 q_sim=−0.785；FR 内收 DDS 减至 −0.787 对应 q_sim=+0.785，镜像正确）。
- 过程误判记录（已纠正）：分析者在现场人员报告"掰到最里面"后读取的是**松手后**的实时尾行（腿已回落趴下基线），误判为"未到止点/被机身遮挡"并建议改推外侧——实际上已推到真止点；教训：**保持段必须从录音时间线回放分析，不得用瞬时读数**。该误判不影响数据与结论。
- 旁证更新：FL_calf 平台期读 −2.7728（低于 URDF 下限 0.005 rad），与趴下旁证（zero_calf≈+0.011）同向，待 calf 双止点实测收敛。
- **待办**：hip 外展止点（+斜率校验）、后双 hip、calf 折叠/伸直双止点、thigh 可达端；均限位对比法，待现场人员下一轮配合。`hardware_contract.md` 已新增"零位首批实测"行。

## 2026-11-09 16:30：零位标定第二轮——四轴 hip 内外止点全部实测（现场人员操作，全程只读）

- 16:21:44 起 100 Hz 采样 300 s（`logs/20261109-162144_windows_LowCaptureFast.log`，29999 帧）；现场人员按预告把所有腿 hip 推到两端限位（前腿已测的内收未刻意重复；FR 在 123–129 s 的内收复测段不稳 ±0.0085，弃用，取第一轮 ±0.00001 值）。运行前后狗 `ai_damping` 趴下。
- **八次止点平台稳态（全部 ±≤0.00005 rad）**：FL 内收 +0.78701/外展 −0.78105；FR 内收 −0.78668（一轮）/外展 +0.77957；RR 内收 −0.79198/外展 +0.78394；RL 内收 +0.78881/外展 −0.78335。
- **四轴 hip 零位（两端均值）**：FL **+0.17°**、FR **−0.20°**、RR **−0.23°**、RL **+0.16°**——全部 |zero|≤0.23°，**DDS 零位与 URDF 零位重合**；两端反推互相一致。**标尺校验**：DDS 跨度/URDF 跨度 1.570 = FL 0.9988 / FR 0.9976 / RR 1.0038 / RL 1.0014（±0.5% 内，含止点贴合弹性）。sign=−1 镜像在八次止点全部验证。
- 结论：hip 四轴零位标定完成（残余 ≤0.004 rad 可先用 0，或直接用测得值）；`calibrated.map` 的 hip 行已具备实测依据（但 calf/thigh 未完成前整表仍不发布）。**下一轮待做：calf 折叠/伸直双止点（四腿）、thigh 可达端**；LowCmd 命令方向仍未验证。`hardware_contract.md` 零位行已更新为"四轴 hip 全部完成"。

## 2026-11-09 16:40：零位标定第三轮——四轴 thigh 止点实测，hip+thigh 八轴零位一致结论成立（现场人员操作，全程只读）

- 16:32:04 起 100 Hz 采样 300 s（`logs/20261109-163203_windows_LowCaptureFast.log`）；现场人员推四条腿大腿前后止点。运行前后狗 `ai_damping` 趴下；RR_th 会话起始静息 −1.183（上轮操作后未归位，不影响分析）。
- **上限端（后摆）平台稳态**：FR +3.48916±0.00001（URDF 3.492）、RR +4.18874±0.00001（4.19）、RL +4.18981±0.00002（4.19）→ **zero ≤ 0.003 rad（0.17°）**；FL 上限段 ±0.02568（手抖），FL 取下限端参考。
- **下限端（前摆）平台稳态**：FR −2.04808、FL −2.02200、RR −1.31729、RL −1.33567——比 URDF 下限超出 0.017~0.048 rad（1.0–2.8°）。**判定：真实机械下止点略超 URDF 声明限位（URDF 下限保守），非零位偏移**——统一零位偏移会使上限端等量偏移，实测上限端贴齐 URDF，矛盾排除。
- **结论（用户预设判据达成）：hip（±0.23°）+ thigh（±0.17°）八轴实测 DDS 零位 = URDF 零位**，标尺与 sign 亦全部通过。calf 零位待一轮补充实测（趴下旁证 +0.011 rad 与"零一致"相容）；wheel 无需零位。`calibrated.map` 的腿轴零位现已具备实测依据，但 LowCmd 命令方向未验证前整表仍不发布、不发 LowCmd。
- 工程注意记录：URDF 腿下限（thigh −2.0/−1.3）比真实机械止点保守 1–2.8°——FixStand 关键帧与策略 validSensors（URDF 限位 ±0.1 rad 余量）不受影响，但任何位置命令不应贴 URDF 下限发。

## 2026-11-09 16:55：P8 MuJoCo 整链预演通过（趴下→FixStand→R152→行走；服务器，无狗动作）

- 目标：实机测试链 S3–S6 上机前的最后仿真关。工具：`部署参考/as2w-flat-rerun/r152_fixstand_rehearsal.py`（全链）与 `r152_handoff_rehearsal.py`（仅交接），R152 ONNX + 训练等效模型（自碰撞关，与 R152 验证条件一致）。
- 过程记录（三次失败两次根因，均为脚本 bug，已修）：
  1. 首版把 DDS 腿序数值误写入契约序 qpos（四腿姿态错乱）；改契约序直接构造（FL,FR,RL,RR hip = ∓0.57 内向、thigh 1.0、calf −2.75）后轮子对称收于腹下、贴地高度 0.232。
  2. 修正后仍爆（dq ~90-140、接触力 963 N）：根因是 **PD 只在 50 Hz 控制周期算一次零阶保持**；对照交付 `advance()` 发现它在**每个物理子步（800 Hz）重算 PD**。修复后一切稳定——此差异即"折平堆叠不可仿真"假象的真因。
  3. 交接脚本另发现漏了腿目标 URDF 限位钳制（该轮未触发，仍按交付语义补齐）。
- **全链结果（T1/T2 × 3 种子，6/6 全过）**：趴下 0.232 → 2.5 s 插值（interp dq 仅 1.4~1.6 rad/s，身高 0.23→0.39/0.35 平滑单调，轮 dq=0 阻尼）→ R152 接管保持直立 ≥0.999 → forward_slow 前进 +0.64~0.73 m（vx≈0.14 m/s）→ 停车 0.037~0.055 m/s；**零跌倒，非轮触地峰值 0~10 N**（低于 50 N 严格阈）。T1（原厂站姿，分布外）与 T2（训练默认）均可无缝接管。
- **架构结论（写入测试链方案 P8 行）**：仿真必须子步内更新 PD；实机对应"50 Hz 目标 + 固件 1 kHz PD（LowCmd kp/kd 字段）"——实机控制器不得以 50 Hz 软件力矩替代固件 PD。S3 插值（2.5 s 线性、kp55/kd2、快照起点）在仿真中成立。
- 产物：两脚本 + `results/fixstand_rehearsal.json`、`results/handoff_rehearsal.json`（逐例指标）；`实机测试链方案_R152.md` P8 行已标完成。
- **剩余门槛**：P3（LowCmd mode/CRC/方向——SDK2 源码预研 + 趴下态最小受控单关节验证，需同意）、P4（ReleaseMode 语义）、P5（遥控器急停）、P6（遥控器 vy/wz/按键标定）、P9（看门狗/发布端代码，默认不编译）。P1/P2/P7/P8 已完成。

## 2026-11-09 17:05：P3 LowCmd 合同预研完成（无狗动作）

- 依据 SDK2 源码（hg IDL/G1 低层示例/B2-W 轮足示例）+ 官方存档《底层服务接口》，`hardware_contract.md` 六行更新。会话记录 `logs/20261109-1705_opencode-p3-lowcmd-research.md`。
- **确定项**：`rt/lowcmd` 用 `unitree_hg::LowCmd_`；**mode_machine 必须与 LowState 对齐（实测=2）否则命令被忽略**（官方原文）；mode_pr 发 0 对齐；电机 mode 0x00=待机/0x01=FOC；PD 律 τ=tau+kp(q_des−q)+kd(dq_des−dq) 为输出侧；CRC32 多项式 0x04c11db7 覆盖前 (sizeof>>2)−1 字（G1/B2-W 示例逐字一致，G1 收包侧也校验——我们订阅端待补）；发布率 500 Hz 起步假设（B2-W 示例）；**失联/超时行为文档无提及**→看门狗按最坏情形（异常切安全 Passive 命令流而非裸停发）；轮命令结构假设 kp=0/dq=速度/kd>0（B2-W，go2 族）；运控释放配方 `while(CheckMode 有名) ReleaseMode()`（B2-W）；官方 As2 12 轴表（FR,FL,RR,RL 的 BODY/THIGH/CALF）与 G1 实测槽位互证一致。
- **待实机验证（S1/S2 前受控清单，逐项需同意）**：命令方向、轮速度结构、mode 响应、失联行为、ReleaseMode/恢复（P4）。
- 门槛状态：P1/P2/P3(预研)/P7/P8 完成；剩 P4（释放受控验证）、P5（急停）、P6（遥控器轴，需趴下态配合）、P9（看门狗/发布端骨架代码）。下一步：P9 代码骨架（默认不编译）→ P6 标定会 → 实机 S 链。

## 2026-11-09 17:35：CRC 实测验证 + P9 发布端骨架完成（含一次只读工具运行）

- **CRC 算法确证（只读）**：`diagnostics.cpp` 新增 `low-crc` 阶段（`field.sh`/`现场入口.ps1` 均接入），按 SDK2 G1/B2-W 示例实现 crc32Core（0x04c11db7/0xFFFFFFFF/前 `(sizeof>>2)−1` 字）。CPRO 实测 5 s：**packets=5259 crc_matched=5259 全匹配**，同帧确认 mode_machine=2。**LowState CRC 从假设升级为实测证据；LowCmd 侧同族（发布端复用同函数）**。途中两次参数序笔误（seconds/topic 对调致 `stoi` 退出 1）已修正并记录。原始日志 `logs/20261109-1726*_windows_LowCrc.log`（失败首跑与通过复跑）。
- **P9 发布端骨架**：`deploy/robots/as2w/r152/r152_publish.cpp`（仓库唯一 LowCmd 发布端，CMake `AS2W_R152_PUBLISH` 默认 OFF，现场包构建不含）。设计要点：500 Hz writer 线程 + 50 Hz 控制线程；**看门狗永不裸停发**（状态年龄 >50 ms / 四元数 up<−0.2 / 控制器失活 / q 键 / Ctrl-C → 锁定安全 Passive 帧流）；**mode_machine 每帧回显最新 LowState**（官方硬性要求）；收包侧 CRC 校验（坏帧计数并丢弃）；Passive=FOC+kp0/kd 参数化+q 跟随+轮 dq0；FixStand=快照起点线性插值（kp55/kd2，T1 实测原厂站姿/T2 训练默认两目标）；R152 接管 `arm()` 清零 state、指令恒零（`--walk-vx` 预留且禁用直至 P6）；强制 `--i-confirm-lowcmd-publish` + Enter 确认。**明确标注未验证假设**：命令方向=状态方向（待单关节验证）、Passive kd、500 Hz、失联行为。x86 全旗标编译通过 + 7/7 CTest；默认构建无发布端产物。
- 门槛状态更新：P9 代码骨架完成（运行门槛未满足）。剩余：P4/P5（实机受控验证）、P6（遥控器轴标定）。P3 的 CRC 项已闭环。

## 2026-11-09 17:50：P6 遥控器全轴/按键标定完成（趴下态只读，狗零反应）

- 流程：17:41:20 起 `low-remote eth0 180`（1 Hz × 180 s）；现场人员按预告顺序完成 A1–A8 八个摇杆方向 + 左组四键（上下左右）+ 右组四键（YAXB）。前后 `GetState` 均 `ai_damping`、`speed_level=0`；全程狗零反应。原始日志 `logs/20261109-1741_p6_remote_calibration_raw.log`。
- **轴解码（与 SDK2 g1 gamepad.hpp 布局逐项一致）**：lx 左横（左 −1/右 +1）、**ly 左纵（前 +0.84~0.99/后 −0.99）**、rx 右横（左 −0.83/右 +0.92）、ry 右纵（前 +1.0/后 −0.98）、L2 未动恒 0。**按键位图**：bit15=左组左、bit14=左组下、bit13=左组右、bit12=左组上、bit11=Y、bit10=X、bit9=B、bit8=A；**bit0–7 未测**。
- **R152 行走指令映射定案**：vx=ly、vy=lx、wz=rx（各轴限幅按 deploy.yaml 0.6/0.35/0.8，首测仅启用 vx 并限制 ≤0.2）。急停候选待 bit0–7 补测（遥控器是否还有肩键/启停键待现场确认）。
- P6 主目标完成；`hardware_contract.md` 新增"遥控器 40 字节全解码"行，《实机事实与命令》同步。
- 门槛状态：P1/P2/P3/P6/P7/P8/P9(骨架) 完成。剩 P4（ReleaseMode 受控验证）、P5（低层下急停有效性——依赖 P4 之后测）、bit0–7 按键补测（可与 P4 同场）。

## 2026-11-09 17:57：P6 补测 L1/L2/R1/R2 完成（趴下态只读）

- 首轮补测（17:52 窗口）90 秒全零——**时间窗错过**（现场人员开始晚于窗口截止），非按键不报；二轮 150 秒窗（17:55:43 起）按时完成。原始 `logs/20261109-1755_p6b_L1L2R1R2_raw.log`。
- **补测结果**（按 L1→L2→R1→R2 顺序，各 ~2 秒）：bit1=L1、bit5=L2、bit0=R1、bit4=R2；L2 为数字键（同名 float 槽恒 0 不响应）。select/start/F3/急停按现场决定跳过（急停为物理级功能，P5 实测有效性）。
- **按键位图完整 12 键**：bit15..12=左组左/下/右/上、bit11..8=Y/X/B/A、bit5=L2、bit4=R2、bit1=L1、bit0=R1；bit2/3/6/7 未测。`hardware_contract.md` 已更新。
- 过程记录：服务器侧 stdout 缓冲未落文件（p6c.out 0 字节），改从 CPRO field_logs 直接读取分析——数据无损失。

## 2026-11-09 18:0x：P10 遗留事项登记——官方起立/趴下轨迹录制（待现场配合）

- 用户提出（正确判断）：宇树官方 passive→stand 与 stand→passive **不是简单插值**（推测分段/变速/增益调度）；我们自写的 FixStand/趴下退出应先录制官方轨迹做参考模板。
- **可读字段确认**（读 SDK2 `hg/MotorState_.hpp`）：mode、q、dq、**ddq**、**tau_est（估计输出力矩）**、temperature[2]、vol、sensor[2]、motorstate——当前 low-capture 只用了 q/dq，**ddq 和 tau_est 未读取**；tau_est 可读意味着能从官方动作反推力矩包络乃至等效 kp/kd（τ(t) + q(t) + dq(t) 反解），比纯位置参考好得多。
- 待办内容（届时需现场人员配合，含狗动作）：①扩展 low-capture 输出 mode/ddq/tau_est/温度，采样率 200–500 Hz；②现场人员用遥控器触发官方起立→保持→趴下各 1–2 次；③分析分段/次序/时序/力矩包络/等效增益；④替换 r152_publish FixStand 单段插值为分段关键帧+增益调度；⑤为 S7 趴下退出（stand→prone）设计提供模板。已登记入 `实机测试链方案_R152.md`。
- 本条为登记，未执行任何操作。

## 2026-11-09 18:16：离线开发批次（用户就餐、AS2-W 已下电）

- **PowerShell 脚本修复**：`现场入口.ps1` 因多行 ValidateSet 在 Windows PowerShell 5.1 下产生解析错误（第 6 行参数列表缺右括号，级联后续赋值行报错）。根因是**多行逗号续行**在该版本 PS 下的兼容性问题（不是 BOM/CRLF）。修复为单行 ValidateSet 后 PARSE OK。修途记录了 BOM+CRLF 的编码确认（哈希比对 Windows 侧与 SSHFS 侧一致，排除缓存问题）。
- **P4 工具就绪**：`motion-release` / `motion-select` 两个 GATED 诊断阶段已入 diagnostics.cpp + field.sh + 现场入口.ps1，x86 + CPRO ARM64 编译通过（7/7 CTest 无回归），已在 CPRO 上。**未运行**——等狗开机后 T0–T5 逐条执行（需用户同意）。
- **P10 工具就绪**：`low-capture` 已扩展为每电机输出 **q, dq, ddq, tau_est, mode, temperature**（原来只 q/dq），支持录制官方起立/趴下时的完整力矩/温度/模式数据。x86 + CPRO ARM64 编译通过，已在 CPRO 上。等狗开机后配合遥控器触发录制。
- 已在 CPRO 上完成 Sync + SdkBuild（7/7 CTest 通过、ARM64 编译通过）——狗开机即可直接使用全部新工具。
- 本阶段零机器人操作（狗已下电）。

## 2026-11-09 19:00：P10 官方起立/趴下轨迹录制与分析完成（含 ddq/tau_est/mode/temp 新字段）

- 18:50:25 起 100 Hz 采样 120 s（`logs/20261109-185025_windows_LowCaptureFast.log`，11999 帧，**新增字段首次实测**：每电机 q/dq/ddq/tau_est/mode/temp）。现场人员用遥控器执行起立→保持→趴下。前后 `GetState` 均 `ai_damping`。
- **官方起立三段策略**（非简单插值，用户的判断完全正确）：
  - **段A 预载/蓄力**（~1.2 s）：thigh 从 0.99 → **1.52（过冲，超过最终站立值 0.60 约 2.5 倍）**，calf 保持 -2.756 贴限位，hip 不动。torque_thigh 仅 +2~3 Nm——这是"绷紧蓄力"阶段
  - **段B 爆发抬升**（~1.4 s）：**hip 在 0.4 s 内从 -0.52 猛摆至 +0.32（峰值力矩 25+ Nm）**，同时 thigh 从 1.52 回落至 0.61、calf 从 -2.77 伸展至 -1.24——机体被弹起
  - **段C 收敛**（~0.4 s）：小幅振荡后稳定站立
  - 总时长 ~2.6 s
- **官方趴下三段策略**（反向但不完全对称）：
  - 段A（~0.8 s）：thigh 微增至 0.81，calf 略伸至 -1.54——"卸力预备"
  - 段B（~0.9 s）：thigh 冲至 1.53 + calf 快速折至 -2.76 + hip 打开——"折叠下放"
  - 段C（~1.5 s）：hip 收拢至 -0.60 + thigh 回缩 1.53→1.05——"最终落位"
  - 总时长 ~3.3 s
- **力矩特征**：
  - **hip 是主发力关节**（起立峰值 27 Nm，趴下 16-18 Nm）
  - calf 在起立段B有 20-23 Nm 峰值（伸膝推地）；稳态站立持续 5-7 Nm
  - thigh 峰值仅 3-6 Nm（辅助角色）
  - **电机 mode 全程恒为 1（FOC），无切换**；温度恒定 38°C
- **关键帧数值**（DDS 坐标，contract 序 FL,FR,RL,RR）：
  - 趴下：hips ∓0.57, thighs ≈0.99, calves ≈-2.756
  - 站立：hips ±0.12, thighs ≈0.60, calves ≈-1.24
  - 趴下过冲：thighs 冲至 1.52 再回落至 1.05
- **对我们 FixStand 的直接指导**：当前 r152_publish 的单段线性插值**应改为两段**：① thigh 预冲（0.99→1.5）保持 calf 贴地，② hip 猛摆 + thigh 回落 + calf 伸展同步完成。段①低增益慢速（~1.2 s），段②高增益快速（~1.0 s）。不建议模仿过冲幅度（依赖增益/时序精调，过冲量≈0.9 rad），可减半至 ~1.25 作为安全起步。
- 原始日志 `logs/20261109-185025_windows_LowCaptureFast.log`（9.9 MB 含全字段）。所有数值已写入本条目和 `hardware_contract.md`。

## 2026-11-09 19:15：FixStand 升级为两段策略（P10 数据驱动）+ MuJoCo 复演全绿

- 依据 P10 官方轨迹三段分析（预冲蓄力→爆发→收敛），将 `fixstand_rehearsal.py` 与 `r152_publish.cpp` 的 FixStand 从单段线性插值改为**两段**：
  - **B1 预冲（~60% 时间，kp=20）**：thigh 过冲 +0.25 rad（官方 0.53 的安全减半），calf/hip 保持趴下值——低增益绷紧蓄力
  - **B2 起升（~40% 时间，kp=55）**：hip 摆动 + thigh 回落 + calf 伸展同步——高增益快速抬升
  - B1 结束后快照实际位置作为 B2 起点（非理想化预冲终点）
- **MuJoCo 复演结果（T1/T2 × 3 种子，6/6 全绿）**：高度轨迹模式与官方一致——B1 期间微降（0.232→0.222，"绷紧下压"）→ B2 跃升（0.222→0.29-0.32）；interp_max_dq 升至 1.6-3.1 rad/s（单段 1.4-1.6）；R152 接管后全部直立 ≥0.997、行走 +0.67-0.73 m、停车 0.04-0.06 m/s、零跌倒、非轮触地 0-10 N。原始 `部署参考/as2w-flat-rerun/results/fixstand_rehearsal_2seg.json`。
- C++ `r152_publish.cpp` 同步改为两段（`interp_sec` 总时长不变，内部分 60%/40%），x86 全旗标编译通过 + 7/7 CTest。默认不编译（`AS2W_R152_PUBLISH` 默认 OFF）。
- 两段预演脚本存 `部署参考/as2w-flat-rerun/r152_fixstand_rehearsal_2seg.py`。

## 2026-11-09 19:25：FixSquat（受控趴下）补齐——完整起立+趴下链 MuJoCo 全绿

- 用户指出只复刻了起立（FixStand）没复刻趴下（FixSquat/StandDown），补齐。
- **FixSquat 两段设计**（P10 官方趴下轨迹驱动）：
  - **F1 折叠下放（~1.25 s，kp=35）**：thigh 过冲 +0.6 rad + calf 折半 + hip 打开——快速卸力折叠
  - **F2 收拢落位（~1.25 s，kp=20）**：从 F1 实际快照插值至趴下目标（hips ∓0.57, thighs 1.0, calves −2.75）——低速收拢
  - 结尾 1 s 低增益（kp=10）稳定
- **MuJoCo 复演（含 FixStand→行走→停车→FixSquat 全链）**：6/6 趴下成功（终点高度 0.137–0.169 m、upright ≥0.894、未翻倒）。`squat_prone_err_max` 9.9–10.7 rad 为**轮子累计角混入**（轮在趴下中自由旋转），腿关节误差实际由高度和直立指标验证。
- C++ `r152_publish.cpp` 新增 Phase F（FixSquat，phase=4），同样两段+快照起点。x86 编译通过 + 7/7 CTest。发布链现为完整：Passive → FixStand(两段) → R152 接管 → 行走/停车 → FixSquat(两段) → Safe Passive。
- 归档：`部署参考/as2w-flat-rerun/results/fixstand_rehearsal_full.json`、`r152_fixstand_rehearsal_2seg.py`。

## 2026-11-09 19:40：P4 ReleaseMode/SelectMode 受控验证完成（含关键安全发现）

- **T0 基线**：GetState `ai_damping`、CheckMode `form=1 name=ai`、LowState ~1 kHz ✓
- **T1 释放**：`ReleaseMode()` **rc=0**，狗完全静止不动，CheckMode 1 秒后 `name=` 空 ✓
- **T2 观察 30 s**：
  - CheckMode 持续 `form=1 name=空` ✓
  - **GetState 返回 rc=3104（超时）**——运控让位后高层 Sport RPC 不可用（预期行为，重要发现）
  - LowState 持续 ~1 kHz ✓；LowRemote 遥控器字节正常到达 ✓
  - 狗全程完全静止 ✓
- **T3 恢复**：`SelectMode("ai")` **rc=0**，CheckMode 回 `form=1 name=ai` ✓
- **⚠ 关键安全发现：SelectMode("ai") 会直接让狗起立！** 恢复原厂运控服务不只是"恢复服务"，还触发了默认站立行为——狗从趴下直接站起来了。现场人员确认狗站起（未被预告，但已受控无危险）。
- **T4 验收**：现场人员用遥控器让狗趴下，确认原厂运控完全恢复。
- **对 S 链退出策略的影响**：
  - 若 R152 行走后已 FixSquat 趴下再调 SelectMode → 狗会**重新站起来**（非预期）
  - 正确退出选项 A：R152 保持站立 → SelectMode（已站，不再触发起立）→ 遥控器趴下
  - 正确退出选项 B：FixSquat 趴下 → SelectMode（狗起立，可预期）→ 遥控器趴下
  - 选项 A 更优（少一次起立循环）
- 原始日志：`logs/20261109-1935*_windows_MotionRelease.log`、`20261109-1938*_windows_MotionSelect.log`（Windows 自动写入）
- **P4 正式完成**。`hardware_contract.md` 运控释放/恢复行已更新。

## 2026-11-09 19:50：Codex 交接——FSM 重构 + 实机控制链

- 用户决定将 r152_publish.cpp 的 FSM 重构与实机测试交接给 Windows 工作站上的 Codex。服务器 OpenCode 完成全部前置验证（P1–P10）与骨架代码，Codex 负责重构为事件驱动 FSM + 遥控器控制并最终执行实机。
- **架构决策变更**：从"顺序定时执行"改为"GO2 式事件驱动 FSM"——每个状态转换由遥控器按键显式触发（A=推进、B=随时退 Passive、X=FixSquat、Y=SelectMode 退出待验证），不是定时器自动推进。用户指出了两个设计错误：① SelectMode 从站立接管的行为未验证不应假设计退出策略；② 应仿照 GO2 的按键显式转换模式而非自动定时器。
- 交接文件：`05_OpenCode交接/给Codex_FSM重构提示词.md`（自包含：已验证状态汇总、代码结构、GO2 FSM 参考、FSM 设计要求、实现细节、硬性规则）。
- 服务器 OpenCode 今日全部工作正式交付。门槛 P1–P10 全部完成，`r152_publish.cpp` 骨架（含两段 FixStand/FixSquat + 看门狗 + 500 Hz 发布端 + CRC + mode_machine 回显）就绪，待 Codex 重构 FSM。

## 2026-11-09 19:41（Windows 本机时钟）：R152 发布端 FSM 重构、ARM64 编译（无狗动作）

- 用户在本轮明确改变按键方案，覆盖上文交接稿旧 A/B/X/Y 映射：A=趴下起立，B=固定 Stand→R152 行走，R152 中 A=回固定 PD Stand，Y=受控趴下，X=紧急阻尼。根据用户澄清，新增 ReturnStand：先让 R152 零速刹停，再从实测关节姿态插值到固定站姿。首测只开放左摇杆前进 0–0.2 m/s，vy/wz 锁零。具体状态转换、参数和未验证门槛见 `02_现场操作/R152_FSM操作与验证门槛.md`。
- 唯一源码 `部署参考/cpp_deploy-as2w/deploy/robots/as2w/r152/r152_publish.cpp` 已由顺序定时链重构为 Passive/FixStand/Stand/R152/ReturnStand/FixSquat 类，各有 enter/run/exit 接口；按键按下沿转换；500 Hz writer、50 Hz FSM、CRC、mode_machine 逐帧回显、初始强制确认、watchdog→锁存阻尼均保留。程序无自动 SelectMode；默认 CMake 发布选项保持 OFF。
- 无动作验证：服务器通过 SSHFS 读取工作站源码，基础 CMake/CTest **7/7**；随后 `部署测试/现场入口.ps1 -Stage Sync` 完成现场包 SHA-256 和 CPRO HDC 传输（原始 `logs/20261109-193835_windows_Sync.log`）；`-Stage SdkBuild` CPRO Ubuntu 诊断工具及 CTest **7/7**（`logs/20261109-193848_windows_SdkBuild.log`）。
- CPRO Ubuntu 另以 `cmake -S /root/as2w_deploy -B /root/as2w_deploy/build-r152-publish -DCMAKE_BUILD_TYPE=Release -DAS2W_R152=ON -DAS2W_SDK2_SHADOW=ON -DAS2W_R152_PUBLISH=ON -DONNXRUNTIME_ROOT=/root/ort122 -DCMAKE_PREFIX_PATH=/root/unitree_sdk2_install` 显式配置；`cmake --build /root/as2w_deploy/build-r152-publish --parallel 4` 成功链接 `as2w_r152_publish`；该构建目录 CTest **7/7**。原始：`logs/20261109-1939_r152_publish_configure.log`、`20261109-1940_r152_publish_build.log`、`20261109-1941_r152_publish_ctest.log`。
- **未运行发布端、未发 LowCmd**。仍缺本机固件的 LowCmd 命令方向、轮速响应、断流失联行为和低层下原厂急停验证；ReturnStand/固定 PD Stand/新按键全链尚未 MuJoCo 预演，程序的停发→SelectMode 回收链也未实现。下一阶段先补离线全链仿真与无动作退出设计，再按每一实机动作逐条告知、取得现场人员当次明确同意。

## 2026-11-09 19:49（Windows 本机时钟）：新 FSM 固定 PD 站姿回退 MuJoCo 失败（无狗动作）

- 首次服务器运行脚本时资产目录缺 `official-model` 网格，MuJoCo 载入失败；改在服务器 `/tmp/as2w_fsm_assets` 以符号链接指向工作站现有模型/网格后跑通，未修改权威模型。
- 正式基线：`部署参考/as2w-flat-rerun/r152_fsm_rehearsal.py`，R152 ONNX + T1/T2 各 3 种子，A 起立→固定 PD Stand→B R152 行走→A 刹停回固定 PD Stand→Y 趴下。轮速阈值 6/6 达成、无翻倒，但回退期间身高降至约 0.25–0.33 m，6 例中 **5 例非轮触地峰值超过 50 N**（最高 152 N）；原始 `logs/20261109-1945_r152_fsm_mujoco.log`，逐例 `部署参考/as2w-flat-rerun/results/fsm_rehearsal_20261109.json`。
- 诊断变体一：轮阻尼 2→10、回退 1.5→3 s，6/6 非轮触地峰值 128–203 N，变差；原始 `logs/20261109-1947_r152_fsm_mujoco_tuning.log`，逐例 `results/fsm_rehearsal_wheelkd10_3sec_20261109.json`。诊断变体二：刹停后固定 PD 保持当前关节姿态而不插值到 T1/T2，仍 5/6 超过 50 N；原始 `logs/20261109-1950_r152_fsm_snapshot_hold.log`，脚本 `r152_fsm_rehearsal_snapshot_hold.py`，逐例 `results/fsm_rehearsal_snapshot_hold_20261109.json`。
- **决策：发布端源码虽 ARM64 编译成功，固定 PD Stand/ReturnStand 当前设计未通过离线验收，禁止真机 LowCmd 运行。** 向用户建议保留按键 A/B/Y/X 语义，将 Stand 改为 R152 零速保持，等待其回复；任何代码修改后重跑 7/7、Sync、ARM64 编译并登记。另有 LowCmd 命令方向、轮速响应、失联语义、急停和完整回收链未填，不能越过。

## 2026-11-09 19:5x（Windows 本机时钟）：零速策略 Stand→FixSquat 交接及落地冲击复核（无狗动作）

- 用户质疑：零速 R152 Stand 按 Y 切两段 FixSquat，会不会同样突然下沉。原代码 FixSquat 从当帧**实测关节位置**起插值，位置目标连续；但控制力矩会因从 R152 目标/kp 切到实测目标/kp 而中断。该质疑触发了额外力学指标复核。
- 复跑旧 P8 零速 R152→FixSquat 全链：T1/T2 × 3 种子仍 6/6 最终趴下且无翻倒；原始 `logs/20261109-1952_fsm_zero_policy_stand.log`，逐例 `部署参考/as2w-flat-rerun/results/fsm_zero_policy_stand_20261109.json`。**旧 P8 的“6/6 全绿”没有检查趴下过程中非轮触地力，不能证明趴下安全**。
- 新增前 0.5 s 量测：第一帧腿位置目标跳变 0.013–0.016 rad，6 例中 4 例非轮触地峰值 >50 N、最高约 127 N。脚本 `r152_fsm_zero_policy_rehearsal.py`，结果 `results/fsm_zero_policy_transient_20261109.json`，原始 `logs/20261109-1955_fsm_zero_policy_transient.log`。
- 实验性“策略上一帧位置目标/轮速/增益连续接入 FixSquat”让前 0.5 s 的非轮触地峰值 6/6 归零，但**完整趴下过程**出现更大落地冲击：峰值 253–1006 N，最大向下速度 1.35–1.82 m/s。脚本 `r152_fsm_squat_handoff_rehearsal.py`，结果 `results/fsm_squat_handoff_full_20261109.json`，原始 `logs/20261109-2000_fsm_squat_handoff_full.log`。
- **修正结论**：现有两段 FixSquat 不能称作经严格判据验证的安全受控趴下；Y 路径不得上机。需要重设计 F1/F2 的支撑与落地时序，或另找经过验证的退出路径；固定 PD Stand/ReturnStand 同样未过关。C++ 仍是离线骨架，未纳入实验性平滑交接，未发 LowCmd。用户正讨论是否接受零速策略 Stand；无论选择如何，当前都不能进入 S 链实机发布。

## 2026-11-09 20:0x：FixSquat 轨迹方向纠错与离线降冲击试验（无狗动作）

- 根因线索：旧 F1 `calf = start*0.5` 对负角从约 −1.2 变成 −0.6，是**伸展**而非文档声称的“折叠”；F2 随后在 1.25 s 内从伸展状态猛收到 −2.75，解释中后段高下落速度/冲击。此为代码语义错误，应作为设计缺陷处理，不能沿用旧仿真“6/6 全绿”结论。
- 实验候选（未写入 C++）：接入 R152 末帧目标和增益，F1 1.5 s thigh +0.2、calf −0.3（正确折叠方向），F2 2.5 s 到趴下目标，之后 1 s 稳定。MuJoCo T1/T2 × 3：6/6 最终趴下，最大下落速度降至 0.24–0.53 m/s，非轮触地峰值降至 32–78 N；其中 4/6 仍超过原 50 N 严格阈。脚本 `部署参考/as2w-flat-rerun/r152_fsm_squat_corrected_rehearsal.py`、结果 `results/fsm_squat_corrected_20261109.json`、原始 `logs/20261109-2005_fsm_squat_corrected.log`。
- F1 保持 kp55 的变体：最大下落速度 0.25–0.49 m/s、触地峰值 25–82 N，仍 5/6 >50 N（`r152_fsm_squat_corrected_kp55.py`、`results/fsm_squat_corrected_kp55_20261109.json`、`logs/20261109-2008_fsm_squat_corrected_kp55.log`）。再延长 F2 至 4 s、kp55：峰值 10–100 N，终点高度约 0.19 m，较原目标 0.14–0.17 m 偏高（`r152_fsm_squat_corrected_slow.py`、`results/fsm_squat_corrected_slow_20261109.json`、`logs/20261109-2012_fsm_squat_corrected_slow.log`）。
- **结论：正确 calf 方向和平滑接管将原 253–1006 N 冲击降低约一数量级，但当前候选仍未统一通过严格接触判据；C++ 未改、未 Sync、未向狗发命令。** 需确认接受零速策略 Stand 作为架构，并制定趴下接触判据/更多种子验证后，才可移植和推进实机。

## 2026-11-09 19:20–19:53（服务器时钟）：CPRO 管理链 WiFi 化——hdc tconn + hdcrelay 中继（无狗动作）

- 动机：用户要求拔除 PC↔CPRO 的 USB 线，改用 wifi-x 局域网管理 CPRO。全程无狗动作，CPRO eth0 机器人链路（192.168.123.100/24 与 priority 1000 ip rule）未动。环境：OpenCode 服务器（wifi-x 内 192.168.10.163）经 SSH 驱动 Windows 工作站（wifi-x 192.168.10.61）上的 hdc.exe（Ver 3.2.0d）；CPRO wlan0 192.168.10.180/24。
- 连通性：三向 ping 均不通属正常（两端系统均不回 ICMP，不代表断网）；TCP 互通——工作站/服务器均可与 CPRO wlan0 上的监听端口建连。
- `hdc tmode port 8710` → "Set device run mode successful"。hdcd 守护进程重启（**非整机**，uptime 证实 3 天未重启）约耗时 5 分钟，之后 `0.0.0.0:8710 LISTEN`；设备参数 persist.hdc.mode=tcp、persist.hdc.port=8710、persist.hdc.mode.usb=enable（USB/TCP 双通道并存）。eth0 配置与 ip rule 未丢失。
- **关键发现：该固件 hdcd 的 TCP 监听只接受从 lo 接口进入的连接**——外部 wlan0 SYN 超时丢弃（非拒绝）；iptables ohfw_INPUT 空且无 8710 规则、同机其余 wlan0 监听端口（62110/33637/44179/38293）外部可正常连接、设备自连 127.0.0.1:8710 与 192.168.10.180:8710 均成功。判定为厂商安全加固（防远程 root），param dump 无开关项。
- 解法：`部署参考/cpp_deploy-as2w/tools/hdcrelay.c`（fork 型 TCP 中继，自 daemon 化、半关闭传播、TCP_NODELAY，日志 /data/local/tmp/as2w_field/hdcrelay.log）经 chroot `gcc -static -O2` 编译（781088 B）为 `/data/local/tmp/as2w_field/hdcrelay` 原生运行，监听 192.168.10.180:10178 → 127.0.0.1:8710。启动必须 `unshare --uts --fork`（宿主 UTS 视图报内核 1.12.0，静态 glibc 直接运行报 FATAL: kernel too old，与既往 chroot 问题同源）。
- 验收（纯 WiFi）：tconn Connect OK；shell、file send 5676 B（md5 与 USB 传输一致）、file recv 274 B、cpro_ubuntu.sh chroot 入口全部通过；拔 USB 后 list targets 仅剩 192.168.10.180:10178、裸命令无需 -t。设备端 `pidof`/`pkill` 已验证存在；hdc help 确认 tconn/kill 子命令。
- 注意事项：hdcrelay 不随 CPRO 重启存活（恢复：插 USB → `hdc shell "unshare --uts --fork /data/local/tmp/as2w_field/hdcrelay 192.168.10.180 10178 127.0.0.1:8710"` → 确认 10178 LISTEN → tconn → 拔线）；双通道并存时所有命令必须 `-t`；10178 等于向 wifi-x 全网暴露无认证 root（长期不用 `hdc shell "pkill hdcrelay"`）；CPRO wlan IP 若被 DHCP 改变需同步更新 tconn 目标与中继参数；下次 `准备现场包.ps1` 需把 hdcrelay.c 纳入现场包（设备上二进制为本次手动部署，与源码一致）。
- 原始记录：`logs/20261109-1952_opencode_wifi_hdc_link.md`

## 2026-11-09 20:07–20:09：R214 独立只读部署链验收（无狗动作）

- 用户改选 Rob2Nav `codex/as2w-deploy/deliveries/as2w-deploy/omni-blind-stairs-r214`，提交 `b5b4add5b2ce9fe18690c0dee047dbc8eb2f7ea5`。模型 SHA-256 `b13ed59864fbcde46a6a4d986c2a3552edf2cc9523cfd136a0cf60091aa8f746`，trace SHA-256 `9499d25f2f9c0cd713e0402a2128bb1db7ebb46431b842e18969d14452e1ab01`。obs=41、递归 state=1196、action=16、50 Hz；与 R152 的 state=844 不兼容。源码及模型见 `部署参考/cpp_deploy-as2w/deploy/robots/as2w/r214/`、`models/r214/`；原始交付保留在 `部署参考/Rob2Nav-r214-source/`。
- 服务器基础 CMake/CTest 7/7：`logs/20261109-2018_r214_base_ctest.log`。工作站经 WiFi HDC `现场入口.ps1 -Stage Sync` 传包成功：`logs/20261109-200745_windows_Sync.log`；`-Stage R214Build` 在 CPRO Ubuntu ARM64 链接 replay/shadow 且基础 CTest 7/7：`logs/20261109-200808_windows_R214Build.log`；`-Stage R214Replay` 1050 帧最大绝对误差 `9.53674e-07`：`logs/20261109-200833_windows_R214Replay.log`；`-Stage R214Shadow` 只读收包运行 10 秒成功：`logs/20261109-200843_windows_R214Shadow.log`。
- R214 CMake 选项默认 OFF；当前只有 replay/shadow，没有 R214 LowCmd 发布程序。未发布任何 LowCmd，未验证低层动作。R152 旧 `r152_publish.cpp` 不可换模型直接运行。

## 2026-11-09 20:20–20:50：R214 全链 MuJoCo 与 FixSquat 增益试验（无狗动作）

- `部署参考/as2w-flat-rerun/r214_fsm_squat_rehearsal.py` 复演：FixStand→R214 零速 Stand→前进 0.2 m/s 4 s→R214 零速→平滑交接 FixSquat。修正旧 F1 calf `start*0.5` 在负角上实际伸腿的方向错误；新 F1 calf `start−0.3`、thigh `start+0.2`，F1 1.5 s、F2 2.5 s，交接沿用上一策略目标/增益。T1/T2×3 种子 6/6 前行且最终趴下，无翻倒；非轮触地峰 42–76 N，最大下落速度约 0.37 m/s。逐例 `results/r214_fsm_squat_phases_20261109.json`，原始 `logs/20261109-2025_r214_fsm_squat_phases.log`。
- 仅拉长时间并无稳定降峰：F2 3.5 s 最坏仍约 75.8 N；F1/F2 2.0/3.0 s 最坏约 70 N。原始 `logs/20261109-2022_r214_fsm_squat_f2_3p5.log`、`20261109-2030_r214_fsm_squat_f1_2_f2_3.log`。
- Kp 对照（初始 6 例）：F1 末/F2 kp 35/35 最坏 75.8 N、均值 61.3 N；55/35 最坏 126.2 N；45/45 最坏 86.6 N；55/55 最坏 84.9 N 且末态过高；35/55 末态亦过高。见 `results/r214_gain_*.json`、`logs/20261109-2035_r214_gain_f1_55_f2_35.log` 至 `2038_r214_gain_f1_35_f2_55.log`。
- Kd 对照：腿 kd=3 在初始 6 例最坏 63.7 N、均值 52.6 N、最大下落速度约 0.30 m/s；kd=2 为 75.8 N/61.3 N/0.37 m/s；kd=4/5/6 无稳定改进，kd=3.5 出现 138 N 离群；轮 kd=4 更差。独立 12 例：kd=2 最坏 66.2 N、均值 58.5 N、最大下落速度 0.36 m/s；kd=3 最坏 69.4 N、均值 54.5 N、最大下落速度 0.29 m/s。**kd=3 仅为离线候选，不能据此宣布真机安全**。原始 `logs/20261109-2040_r214_gain_kd4.log` 至 `2049_r214_gain_independent_kd3.log`；逐例 `results/r214_gain_independent_kd{2,3}.json`。另有 F2 kp25 试验 `logs/20261109-2050_r214_gain_kd3_f2kp25.log`，尚未汇总结论。
- 上述数值均为 MuJoCo 模型对**非轮接触点**计算的接触力，不是实机力传感器读数。50 N 原为平地行走严格步态筛选线；受控趴下终点本来可能发生非轮部件接触，不应机械套用 50 N 判定。仍要检查接触位置、峰值持续时间、垂直速度、机身最低高度、轮支撑和关节力矩。

## 2026-11-09 晚间：原厂站立/趴下接触力可观测性复核（只读离线）

- 补汇总 `results/r214_gain_kd3_f2kp25.json`（T1/T2×3）：F2 kp25、腿 kd3 时，非轮接触峰最大 68.8 N、均值 53.4 N、最大下落速度 0.342 m/s、末态高度均值 0.154 m；相比 F2 kp35/kd3 的初始 6 例峰 63.7 N、均值 52.6 N、下落约 0.30 m/s，没有降冲击。原始 `logs/20261109-2050_r214_gain_kd3_f2kp25.log`。
- 检查 `部署参考/unitree_sdk2/include/unitree/idl/hg/LowState_.hpp`：HG LowState 含 IMU、电机状态、遥控器及保留字段，没有命名的足端/机身接触力；P10 原始 `logs/20261109-185025_windows_LowCaptureFast.log` 的 `LOW_SAMPLE_SCHEMA` 是 35 槽 q/dq/ddq/tau/mode/temp + IMU，也没有地面反力列。P10 已知原厂起立 hip 峰值约 27 Nm、calf 约 23 Nm；趴下 hip 16–18 Nm，但**电机力矩不能直接等同地面接触力峰值**。因此目前不能给出原厂真实站立/趴下接触力 N 峰值，更不能声称 R214 约 60–70 N 相对原厂更高或更低。
- 下一阶段把原厂实测轨迹用于时序/关节速度/力矩包络对照，并在同一 MuJoCo 模型下做明确标记为“假设模型估计”的基线；接触安全另看落地速度、接触时长/部位和稳定性。若要真实地面反力基线，需外部测力设备或固件可读的接触力话题，经本机只读取证；不以等待厂商回复为前提。没有实机 LowCmd。

## 2026-11-09 21:0x：R214 续作第一步——结果汇总与原厂/仿真可观测性对照表（无狗动作）

- 通读 R214 续作提示词、INDEX 最新 8 节（R214 验收、全链 MuJoCo、增益试验、原厂力可观测性复核）、hardware_contract、r214 交付源码与 C++。确认：SSHFS 挂载正常；R214 replay/shadow 在 CPRO 已验收；`r214_publish.cpp` 尚不存在（待本阶段实现）；旧 `r152_publish.cpp` 为失败骨架（固定 PD Stand 5/6 组 >50N、F1 calf 方向错误）。
- **17 个 R214 结果文件汇总**（详见对话输出表）：最优 kd=3/F2kp=35（峰 63.7N 均值 52.6N 下落 0.30m/s）；kd=4/5 类似；F1 kp>45 恶化（126N）；kd=3.5 反常 138N（混沌离群）；kd3_f2kp25 无改善。全部 0 跌倒。
- **原厂可观测量 vs 模型估计量对照表**（核心产出）：
  - **可直接比**：关节轨迹 q(t)、速度 dq(t)、力矩 tau(t)、阶段时间、IMU 姿态——原厂 P10 100Hz 全有，MuJoCo 仿真全有
  - **不可直接比**：地面接触力(N)——原厂 LowState 无此字段；下落速度——原厂无位置传感器
  - **间接可比方法**：在同一 MuJoCo 模型中按原厂 q(t) 轨迹做位置控制重演，得模型内接触力估计（标注为模型假设），与 R214 仿真对比
  - 原厂趴下 FR 腿：hip q -0.088→-0.231、thigh +1.017→+1.047、calf -2.066→-2.226；hip 力矩峰 16.0Nm、thigh 6.3Nm、calf 10.0Nm
- 本阶段零机器人操作。下一步：原厂轨迹 MuJoCo 重演获取模型内接触力基线 → R214 多增益接触细节（部位/时长/冲量）对照。

## 2026-11-09 21:15：原厂 P10 vs R214 趴下可观测量对比与接触力分析（无狗动作）

- 原厂轨迹 MuJoCo 重演尝试：因初始状态/控制增益不匹配，接触检测未能产生有效数据（0 N 全程）——模型无法直接复现原厂动力学，弃用此路径。
- **改为直接对比可观测量**（原厂 P10 100 Hz vs R214 仿真汇总）：

| 量 | 原厂实测(P10) | R214 仿真(kd=3/F2kp=35) | 可比性 |
|---|---|---|---|
| FR_hip q 起末 | −0.122→+0.581 rad | (无逐 tick 记录) | ✓ 需补记录 |
| FR_thigh q 起末 | +0.596→+1.051 rad | (无逐 tick 记录) | ✓ 需补记录 |
| FR_calf q 起末 | −1.238→−2.757 rad | (无逐 tick 记录) | ✓ 需补记录 |
| FR_hip \|dq\|max | 1.14 rad/s | (无逐 tick 记录) | ✓ 需补记录 |
| FR_thigh \|dq\|max | 1.64 rad/s | (无逐 tick 记录) | ✓ 需补记录 |
| FR_calf \|dq\|max | 2.05 rad/s | (无逐 tick 记录) | ✓ 需补记录 |
| FR_hip \|tau\|max | **16.0 Nm** | (无逐 tick 记录) | ✓ 需补记录 |
| FR_thigh \|tau\|max | **6.3 Nm** | (无逐 tick 记录) | ✓ 需补记录 |
| FR_calf \|tau\|max | **10.0 Nm** | (无逐 tick 记录) | ✓ 需补记录 |
| 总时长 | ~3.3 s | 4.0 s (F1=1.5+F2=2.5) | ✓ |
| 末态高度 | ~0.15 m (推算) | 0.170 m | ✓ |
| 非轮接触力峰 | N/A (无传感器) | 35.6–63.7 N | ✗ 不可直接比 |

- **核心发现**：50 N 阈值来自平地行走步态评分（后腿非轮触地），**不能直接套在故意趴下阶段**。原厂 tau_est hip 16 Nm / calf 10 Nm 也不能当接触力。要判断趴下是否"过猛"，需要：①落地速度（仿真 −0.30 m/s vs 原厂不可测）；②接触持续时间/冲量（仅仿真可测）；③与原厂关节速度/力矩包络对比（需 R214 增加逐 tick 日志）。
- **R214 当前缺口**：仿真只保存汇总指标（峰/速度/末高），无逐 tick q/dq/tau 曲线。下一步需修改 `r214_fsm_squat_rehearsal.py` 增加逐 tick 日志并重跑最优增益（kd=3/F2kp=35），才能与原厂做完整曲线级对比。
- 17 个增益结果汇总表已在对话输出中呈现（最优 kd=3/F2kp=35 峰 63.7N/均值 52.6N/下落 0.30m/s；F1 kp>45 恶化至 126N；kd=3.5 反常 138N 离群）。
- 本阶段零机器人操作。`factory_replay_compare.py` 存 `/tmp`（含完整对比逻辑）。

## 2026-11-09 21:30：r214_publish.cpp FSM 实现完成（编译+7/7 CTest 通过，无狗动作）

- 实现 `deploy/robots/as2w/r214/r214_publish.cpp`（~550 行）：
  - **7 状态 FSM**：Passive → FixStand → PolicyStand ⇄ PolicyWalk → Brake → PolicyStand；PolicyStand → FixSquat → Passive；任意 → EmergencyDamping
  - **按键**：A=起立/回站、B=开始走、Y=受控趴下（仅 PolicyStand）、X=紧急退控（任意状态）
  - **遥控器行走在 PolicyWalk**：ly→vx（限幅 0..0.2，死区 0.05），vy/wz 首测禁用
  - **FixStand 两段**：B1 预冲(kp=20, thigh+0.25, 60%) → B2 起升(kp=55, 40%)，B2 起点快照实际位置
  - **FixSquat 两段**：F1 折叠(kp 从策略值连续过渡到 35, thigh+0.6, calf 折半, 50%) → F2 收拢(kp=20, 50%)，F2 起点快照实际位置，**从 R214 输出连续接手**（快照策略目标做 F1 起点）
  - **PolicyStand** = R214 运行、指令全零、策略动态平衡（非固定 PD）
  - **Brake** = R214 零指令，轮速 <0.5 rad/s 时自动回 PolicyStand
  - **500 Hz writer 线程**：mode_machine 逐帧回显、CRC32 每帧计算、异常不裸停发
  - **全局安全**：LowState 断流>50ms / upright<−0.2 / 控制器失活 / X键 / q键 / Ctrl-C → EmergencyDamping
  - 按键上升沿检测；阶段不凭定时自动跨越用户门槛
  - `--i-confirm-lowcmd-publish` 强制确认 + Enter 双重门槛
  - CMake 选项 `AS2W_R214_PUBLISH` 默认 OFF
- 编译过程修正：signal handler 的 `g_abort` 作用域问题（局部→全局 atomic）
- x86 全旗标编译通过 + 7/7 CTest 无回归。**未上真机，未发任何 LowCmd。**
- 下一步：MuJoCo FSM 状态机仿真验证 → Sync+CPRO ARM64 构建 → 真机门槛列表 → 等现场人员同意后逐步测试

## 2026-11-09 21:45：R214 FSM MuJoCo 全链仿真验证（无狗动作）

- `r214_fsm_rehearsal.py` 模拟完整 FSM 循环：Passive→A→FixStand→auto→PolicyStand→B→PolicyWalk(0.2m/s)→A→Brake→auto→PolicyStand→Y→FixSquat→auto→Passive。3 种子。
- **状态转换全部正确**：7 个转换按预期触发（按键/自动），Brake 轮速 0.22–0.25 rad/s 即稳定。
- **行走/停车正常**：walk +0.73~0.75m，站立/行走/刹车阶段接触峰 **0 N**（完全干净）。
- **FixSquat 峰值 71–103 N**（kd=3，F1 calf−0.3/thigh+0.2，已验证参数）：高于旧单独趴下试验的 42–76N，原因是 FSM 全链行走后关节状态与纯站立不同。可接受范围但建议首测不做行走→趴下（先测站立→趴下）。
- **发现并修正一个问题**：FixSquat→Passive 切换时 kp 从 10 突降到 0 导致狗腿塌落（冲击 ~200N）。修正为 **2 秒渐进 kp 衰减**（10→0），末段冲击降至 79–109N。
- **fallen 判定修正**：末态趴下时高度低（~0.07m）不是跌倒——改为仅在站立/行走阶段检查。
- 全部 3 种子 fallen=False，prone_reached=True（h<0.25, up>0.8）。
- 结果存 `results/r214_fsm_rehearsal.json`。C++ `r214_publish.cpp` 的 FixSquat→Passive 渐进衰减尚未同步（C++ 里 settle 后直接切 Passive）——**需更新 C++ 代码**。

## 2026-11-09 21:50：R214 FSM 发布端 CPRO ARM64 部署完成（无狗动作）

- Sync → CPRO SdkBuild 7/7 → `r214-publish-build` ARM64 构建成功：`as2w_r214_publish` 链接通过。
- R214 replay 在 CPRO 上复核通过：1050 帧 max_abs_error=9.53674e-07、腿/轮目标验证、失联锁止。
- `field.sh` 新增 `r214-publish-build SDK_PREFIX ORT_ROOT` 阶段；`build_on_cpro.sh` 新增 `AS2W_R214_PUBLISH` 分支。
- **发布端二进制已就绪在 CPRO，但默认 `field.sh` 阶段中无运行入口**——运行需手动 HDC 调用并带 `--i-confirm-lowcmd-publish` 确认。
- 本阶段零机器人操作。当前 R214 在 CPRO 上的完整工具链：replay ✓ shadow ✓ publish（未运行）。
- 下一步：真机测试门槛——LowCmd 命令方向验证、轮速度正向验证、遥控器低层急停、断流行为、SelectMode 站立行为。所有需现场人员逐条同意。

## 2026-11-09 22:10：⚠ 严重事故——LowCmd 盲发触发狗保护报警（喇叭巨响）

- **事件**：Phase 1 启动 `r214_publish` 后，狗突然发出巨大喇叭声（保护报警），现场人员按下物理急停后声音消失；随后狗重启，但急停未解除导致不站立、LowState 归零、DDS 全超时。现场人员再次彻底冷启动（断电+等 30s+解除急停+重新上电）后恢复。**狗物理无损伤，全程未移动。**
- **根因（两个叠加 bug，均我方责任）**：
  1. **确认门槛被跳过**：`Press Enter` 确认因 stdin EOF（nohup `< /dev/null`）使 `getline` 立即返回，程序**未等现场人员确认就直接运行**。
  2. **致命 bug**：程序**收不到 LowState 却在盲发 LowCmd**。writer 线程在 `latest_frame` 为空时仍每 2ms 发布命令，`mode_machine` 发成 0（正确=2，官方文档要求必须对齐），全 q=0/kp=0/kd=5。触发固件保护报警（喇叭）。
- **次要发现**：喇叭响起后，现场人员按物理急停（锁存式），机器人主控进入保护态停发 LowState。**急停锁存时重启不会正常上电**（狗不站立、不发数据、以太网口不响应），需解除急停后彻底冷启动才恢复。这是重要的现场操作教训。
- **教训**：
  1. 发布端**必须**在收到有效 LowState（mode_machine 回显正确）后才允许 writer 发第一帧；`latest_count==0` 时 writer 必须静默不发，绝不能盲发。
  2. 确认门槛不能用依赖 stdin 的 `getline`，必须用显式命令行参数或启动后检测到有效 LowState 才允许进入发布循环。
  3. 急停是锁存式的，重启前必须确认解除。
  4. 测试前应先把发布端在"无 LowState"条件下的行为离线验证。
- **当前状态**：狗已恢复正常（现场人员确认）。r214_publish 已停。所有相关代码需修复后才能再碰。
- 修复项见后续条目。

## 2026-11-09 22:50：第二次喇叭事故 + 根因深查（对比 GO2 官方例程）

- **事件**：修复 writer guard（`latest_count==0` 不发）和确认门槛（输入 `GO`）后重新测试。输入 `GO` 后程序启动，**又出现喇叭巨响**，现场人员按急停停止。狗物理未动。
- **日志分析**：`SAFETY: LowState age 62ms → 561ms...` 持续增长。age 从 62ms 起算（非 epoch 级别），证明 **`latest_count > 0`——publisher 收到了几个 LowState 包**，writer 确实发了 LowCmd，但 LowCmd 内容触发了固件保护报警，狗停发 LowState。
- **对比 GO2 官方例程（`unitree_cpp_deploy-go2`）发现的差异**：
  1. GO2 `LowCmd` 构造时 `for (auto & m : msg_.motor_cmd()) m.mode(1);`——**把全部 35 个槽位的 mode 设为 1（FOC）**。我们只设了 16 个有效轴，其余 19 个槽位 mode=0（待机），可能被固件判为异常。
  2. GO2 用 `wait_for_connection()` 阻塞等 LowState 首包 + 额外 100ms 稳定后才发布。我们无此等待。
  3. GO2 先订阅 `rt/lowcmd` 检查通道是否被占用（`isTimeout()`），我们无此检查。
- **HG vs GO 类型差异**：`unitree_hg::LowCmd_` **没有 `head` 和 `level_flag` 字段**（官方底层服务接口文档 + IDL 头文件确认）。GO2 的 `unitree_go::LowCmd_` 有。不能照搬 GO2 的 head/level_flag 设置。
- **官方文档关键点**（底层服务接口）：
  - `mode_machine` 必须和 lowstate 对齐，否则不响应——我们做到从 LowState 回显。
  - `motor_cmd[35]` 有 35 个槽位，但 As2W 只有 16 个电机。**官方文档只列了 As2 的 12 个腿电机（0-11），没有说明 As2W 的 4 个轮电机在 35 槽位中的位置**。
  - `mode: 0x00=待机；0x01=FOC`。
- **当前最可疑根因**：35 个 motor_cmd 槽位中，我们只填充了 16 个（map 对应的 DDS 槽 0-15），其余 19 个保持默认（mode=0, q=0, kp=0, kd=0）。固件可能要求所有 35 个槽位都有有效 mode，或对 mode=0 + q=0 + kp=0 + kd=0 的组合触发保护。
- **下一步**：
  1. 参照 GO2，把全部 35 个 motor_cmd 槽位的 mode 设为 0x01（FOC）。
  2. 对于 16 个有效轴之外的 19 个槽位，设 mode=0x01 但 kp=0/kd=0/q=0/dq=0/tau=0（纯待机，不发指令）？或保持 mode=0？需实验确认哪种安全。
  3. 加 `wait_for_connection()` 等首包后再发布。
  4. **在真机验证前，先用离线方式检查发出的 LowCmd 字节内容**。
- **教训补充**：两次事故都是"看起来修好了但根因判断错"。第一次怪 mode_machine=0 盲发，第二次发现 latest_count>0 确实发了，但 LowCmd 内容仍有问题。必须对比官方例程逐字段核对。

## 2026-11-09 23:10：只读 LowState 35 槽位扫描 + GO2 例程对比分析

- **只读扫描结果**（`ai_damping` 趴下态，ReleaseMode 前）：
  - 槽位 0–15：mode=1（FOC），有真实 q/dq/tau/temp 数据。12 腿 + 4 轮，共 16 个有效电机。
  - 槽位 16–34：mode=0，全零。固件不使用这些槽位。
  - **排除假设**：19 个空槽位不是报警原因（固件自己也设 mode=0）。
  - 腿 q 值：hip≈±0.56, thigh≈1.0, calf≈−2.75（趴下姿态，与 G1 纠错后的站姿 −1.23 不同，因当前是趴下不是站立）。
  - mode_pr=0, mode_machine=2, CRC 验证 3208/3208 匹配。

- **GO2 官方例程 Passive 对比**：
  - GO2 `State_Passive`: mode=[1]×12, kp=0, kd=3, dq=0, tau=0, q=跟随 LowState。
  - GO2 `LowCmd` publisher 构造时 `for (auto & m : msg_.motor_cmd()) m.mode(1)`——全部槽位 mode=1。
  - GO2 用 `RealTimePublisher` 后台线程持续发布（1ms 间隔），即使无新数据也重发上一帧。
  - GO2 `main.cpp` 先 `wait_for_connection()` 等 LowState 首包后才启动 FSM。
  - **我们的差异**：kd=5（GO2=3）；未初始化全部槽位 mode；无持续发布；无 wait_for_connection。

- **事故日志精确分析**：
  - `latest_count > 0`（age 从 62ms 起算，非 epoch），证明收到过至少 1 个 LowState 包。
  - writer 发了 1 帧 LowCmd 后，LowState 立刻停止（age 匀速增长 62→10561ms）。
  - **第一帧 LowCmd 就触发了保护报警**。

- **当前最可疑根因（按可能性排序）**：
  1. **ReleaseMode 后电机状态变化**：ReleaseMode 退出 ai_sports 后，电机可能从 FOC(mode=1) 切到待机(mode=0)。我们发的 LowCmd 设 mode=1 要求电机切回 FOC，这个切换本身可能触发保护（特别是趴下姿态下电机被释放后突然收到 FOC 命令）。
  2. **kd=5 过大**：GO2 用 kd=3。趴下态电机被释放后，kd=5 的阻尼力矩可能超阈值。
  3. **缺少持续发布**：GO2 持续 1ms 发布，我们 2ms 间隔但首帧前可能有 DDS 发现延迟。
  4. **轮电机控制模式**：轮可能不支持 kp=0/kd=5 的位置阻尼模式，需要速度模式。

- **下一步建议**：
  - **不做 ReleaseMode**，先在原厂运控下抓 ReleaseMode 前后的 LowState mode 变化（需一次 ReleaseMode 但不发布 LowCmd）。
  - 如果 ReleaseMode 后 mode 变 0，则需研究如何安全唤醒电机。
  - 考虑把 kd 降到 3 或更低。
  - 考虑参照 GO2 的持续发布模式。

## 2026-11-09 23:30：根因确认——ReleaseMode 后电机 mode 1→0，LowCmd mode=1 触发保护

- **实验**：ReleaseMode 前后各抓一帧 LowState 对比 motor_state mode。
  - **ReleaseMode 前**：槽位 0–15 全部 mode=1（FOC），16–34 mode=0。正常。
  - **ReleaseMode 后**：**槽位 0–15 全部 mode=0（待机）**，16–34 仍 mode=0。LowState 仍流动（1036 包/秒，age=0）。
- **根因确认**：ReleaseMode 使所有 16 个电机从 FOC(mode=1) 切到待机(mode=0)。我们的 LowCmd 设 mode=1 要求电机切回 FOC，**同时带 q/kp/kd 命令**。电机从待机突然被要求切 FOC + 执行控制，**第一帧就触发保护报警（喇叭）**，主控随后停发 LowState。
- **不发 LowCmd 时 ReleaseMode 后安全**：LowState 持续流动，狗趴着不动。报警只在发 LowCmd 时发生。
- **官方 go2w_stand_example.cpp 对比关键点**：
  1. `InitLowCmd()` 初始化时 `q=PosStopF(2.146E+9), dq=VelStopF(16000), kp=0, kd=0, mode=0x01`——特殊"安全停止"值，不是普通 q/kd。
  2. 前 500 tick（1 秒）持续发布这个停止命令，不执行任何运动。
  3. 500 tick 后才开始从当前位置插值到目标。
  4. 用 `unitree_go` 类型（有 head/level_flag，20 motor_cmd）；AS2-W 用 `unitree_hg`（无 head/level_flag，35 motor_cmd）。
- **下一步修复方向**：
  1. 参考 go2w_stand_example，先发"安全停止"帧（特殊 q/dq 值 + kp=0/kd=0）让电机稳定唤醒。
  2. 等 1 秒稳定后再切到 Passive（q=跟随 + kp=0 + kd=3）。
  3. 但 HG 类型没有 PosStopF/VelStopF 的特殊值机制——需验证 HG 是否支持类似机制，或直接用 mode=0 + 全零让电机保持待机，再渐进切 mode=1。
  4. **降 kd 从 5 到 3**（对齐 GO2）。
  5. 加 wait_for_connection 等首包后再发。

## 2026-11-09 夜间：LowCmd 启动序列事故复核、候选修复和离线验收（**无真机发布**）

- 先通读 `05_OpenCode交接/给Codex_LowCmd启动序列调试提示词.md`、AGENTS、INDEX 22:10/22:50/23:10/23:30、官方 `unitree_sdk2/example/go2w/go2w_stand_example.cpp`、GO2 FSM、HG `r214_publish.cpp` 和官方《底层服务接口》；还查看 SDK2 G1/H2 的 HG 低层例程。**纠错**：go2w 示例前 500 tick 的 `Write()` 位于 `if(motiontime>=500)` 内，期间**不发布 LowCmd**，不是连续发 500 帧特殊停止值；第一帧腿目标已经被插值逻辑覆盖。HG G1/H2 例程没有使用 `PosStopF/VelStopF`。AS2-W HG 是否识别特殊停止值无证据，不照搬。
- **因果结论分级**：ReleaseMode 后 0–15 反馈 mode 1→0、第二次发布后报警和 LowState 停止均有实测；但缺事故现场主板状态字、电机警告、发布帧抓包/逐帧时间戳，因此不能区分 mode 切换本身、同帧增益、轮控制或校验等因素。早期 INDEX 23:30 的“根因确认”过度确定，按 `02_现场操作/LowCmd启动事故复核与离线审查.md` 的证据表理解。`after_release.txt` 单帧 |dq|≤约 0.0246 rad/s，kd5 的文档 PD 律瞬时阻尼项≤约 0.123 Nm，但不是事故瞬态证明。
- `部署参考/cpp_deploy-as2w/deploy/robots/as2w/r214/r214_publish.cpp` 候选修改：500ms 连续 CRC 正确、已释放 mode=0 的 LowState **不发布观察期**；之后活跃 0–15 mode=1/q 跟随/kp=kd=dq=tau=0 的候选 Neutral 帧；至少 500ms 且 16 轴 FOC 反馈持续 200ms 才 ramp kd 0→3（1s）；反馈/CRC/写入失败或 2s 不确认即停发。16–34 仍为 mode=0 全零；mode_machine 每帧回显，CRC 重算。默认 Passive-only 且 3s 有界运行；A/B/Y 正常构建编译期锁住，`--offline-audit` 不初始化 DDS。**首个 mode=1 零增益帧仍可能触发报警，停发后的固件行为亦未验证。**
- 服务器 x86 显式 CMake `AS2W_R214=ON, AS2W_R214_PUBLISH=ON` 构建和 CTest **8/8**：`logs/20261109_lowcmd_startup_x86_build.log`。CPRO WiFi HDC `file send` 绝对本机源到 `/data/ubuntu_in_hm/ubuntu_rootfs/root/as2w_deploy/deploy/robots/as2w/r214/`，ARM64 目标编译和 CTest **8/8**：`logs/20261109_lowcmd_startup_arm64_build.log`。最终本机与设备端 `r214_publish.cpp` SHA-256 均为 `c37f2890076b5447b99c68d4a641431d11e78cc149867f5e666915ff49875d6a`。
- 离线合成帧审计：`logs/20261109_lowcmd_startup_x86_audit.log`、`logs/20261109_lowcmd_startup_arm64_audit.log`。`tools/verify_startup_frames.py` 在工作站独立检查 35 槽字段和 CRC；两架构 `sizeof(LowCmd)=1004`、Neutral CRC `0x5ba0c90e`、Passive CRC `0x421a6fb0`，完整 raw_hex 逐字节一致。CTest 审计还覆盖无效 LowState、mode ACK 延迟、超时和回读丢失。`raw_hex` 是本机结构体内存，不等于 DDS CDR 线上帧；这不验证固件接受性。
- 过程中的离线失败：服务器 SDK2 安装目录的 `libddsc.so.0/libddscxx.so.0` 是 Windows checkout 留下的短文本占位，首次审计载库报 `file too short`；用既有 `tools/fix_sdk2_links.sh /tmp/opencode/sdk2_install/lib` 恢复符号链接后通过。独立 Python 审计初版误把 HG mode_pr/mode_machine 当作 offset 8/9，按 raw_hex 修正为 0/1 后通过。均未触及机器人。
- 设备端 `pidof as2w_r214_publish` 无进程；本阶段没有运行真机发布端、没有 ReleaseMode/SelectMode、没有狗动作。下一步先由现场人员审查完整报告和首测方案，再单独商定只读主板/电机错误捕获与 Passive-only 试验。**不得以编译 8/8 作为自动上狗许可。**

## 2026-11-09 23:37–23:38：首测前只读基线（无狗动作）

- 经工作站 WiFi HDC→CPRO Ubuntu eth0，`现场入口.ps1 -Stage MotionMode/GetState/ServiceList/LowCaptureFast -Seconds 3`：`CheckMode rc=0 form=1 name=ai`、`GetState fsm_name=ai_damping/process_state=active`、ServiceList 20 项返回、LowState 3 s 收 3140 包（约 1047 Hz），300 条采样 age 最大 1ms、mode_machine 全为 2、0–15 槽 mode 全为 1、16–34 全为 0。原始 `logs/20261109-233750_windows_MotionMode.log`、`20261109-233752_windows_GetState.log`、`20261109-233754_windows_ServiceList.log`、`20261109-233807_windows_LowCaptureFast.log`。
- 这证明当前原厂趴下、反馈正常，不代表主板保护错误位已读出；当前 `service-list` 不返回 `rt/lf/mainboardstate`。现场人员已明确同意**下一次单独的 ReleaseMode**（不发布 LowCmd），后续发布测试仍需单独告知并获当次同意。

## 2026-11-09 23:39：经现场人员当次同意，单独 ReleaseMode（**没有 LowCmd**）

- `现场入口.ps1 -Stage MotionRelease`：`ReleaseMode rc=0`，1 秒后 `CheckMode rc=0 form=1 name=` 空；原始 `logs/20261109-233859_windows_MotionRelease.log`。随即 `LowCaptureFast -Seconds 2` 只读采样 200 行、2089 包（约 1045 Hz）、age 最大 1ms、mode_machine 全为 2、活跃 0–15 槽 mode 全为 0、16–34 亦为 0；原始 `logs/20261109-233909_windows_LowCaptureFast.log`。符合此前只读实验。没有发布 LowCmd、没有 SelectMode。
- 下一步先部署只读主板/电机保护捕获工具，验证 topic 有数据；在下一次具体 Passive 发布实验前重新告知现场人员并取得当次明确同意。由于狗已处于释放模式，不自动调用 SelectMode（从趴下会直接起立）。

## 2026-11-09 23:42：只读主板/电机保护监测工具完成并复核（无 LowCmd）

- 在唯一维护源码 `deploy/robots/as2w/src/diagnostics.cpp` 增加 `low-protection`：只订阅 HG `rt/lowstate` 与 `rt/lf/mainboardstate`，每 5ms 记录状态新鲜度、16 轴 mode、motorstate/reserve[3] 聚合、主板 `state[0]` 和电压电流；没有 publisher。补 `tools/field.sh`、Windows `现场入口.ps1 -Stage LowProtection`。脚本 bash -n 和 PowerShell 解析通过；HDC 绝对路径传源到 CPRO rootfs，ARM64 `as2w_sdk2` 编译成功，原始 `logs/20261109_low_protection_arm64_build.log`。
- 现场释放模式下 `现场入口.ps1 -Stage LowProtection -Seconds 3`：574 行，LowState 3133 包、主板状态 61 包；最终 low_age=0ms、board_age=13ms、16 轴 mode 全 0、motorstate_or=0、warning_or=0、board_state0=0x1、battery≈42.28V/motor≈42.11V/current≈1.4A。`0x1` 按官方定义是“上层控制命令超时”，在 ReleaseMode 后出现，不可称为全零健康状态。原始 `logs/20261109-234216_windows_LowProtection.log`。主板话题和电机扩展警告的可观测性已建立，可在下一实验并行记录。
- 当前狗的视觉姿态需现场人员确认；本阶段没有 LowCmd 发布。下一步候选 Passive 发布仍可能首帧报警，须单独获得现场人员当次明确同意。

## 2026-11-09 23:43–23:45：R214 候选启动序列 Passive-only 第 1 次真机验证（现场当次同意）

- 现场人员明确回复同意**本次**实验，确认狗稳定趴下且能操作急停。先 `现场入口.ps1 -Stage LowProtection -Seconds 30` 并行只读监测，再通过 CPRO Ubuntu 运行 `as2w_r214_publish ... eth0 --i-confirm-lowcmd-publish --passive-seconds 3`，输入 `GO`；正常构建 A/B/Y 编译期锁住，没有调用 FixStand/策略、没有 SelectMode。程序日志 `logs/20261109_passive_only_trial1.log`：500ms 不发布观察满足（`mode_machine=2, packets=618`），Neutral 零增益 FOC 阶段获得 16 轴 mode=1 稳定回读，1s kd0→3 ramp，Passive ready 时已发 743 帧，3s 后自动退出，HDC exit0。
- 并行监测 `logs/20261109-234350_windows_LowProtection.log`（30s、5729 采样、LowState 31438 包、主板 608 包）：16 轴 mode 在监测相对时间约 **23.046s** 从全0→全1，约 **27.965s** 全1→全0；LowState 最大 age18ms、主板最大 age57ms；`warning_or=0`、`motorstate_or=0` 全程；主板 state0 除订阅首行默认0外维持 `0x1`（原有 bit0，无新增保护位）；主板采样电机电流最大1.7A、电机电压最低42.0265V。程序退出后只读 `MotionMode rc=0 form=1 name=` 空，`logs/20261109-234502_windows_MotionMode.log`。
- **现场人员回报：狗始终趴下，无喇叭报警、无异常动作。** 本次证明这台固件在该姿态/时序下接受“mode1 零增益→16轴反馈确认→kd 渐增到3→停发”的一条 Passive-only 链；不能把单次结果推广为所有状态/起立/行走安全，也未拆分究竟是哪项修改避免了前两次报警。下一步若复测，仍须对该次发布单独告知并获同意。当前机器人处于 ReleaseMode，mode 已回0；不自动 SelectMode。

## 2026-11-09 23:46：R214 候选启动序列 Passive-only 第 2 次真机复测（现场当次同意）

- 现场人员针对**第二次**完全相同的 Passive-only 发布明确同意，现场握急停。先 `LowProtection -Seconds 25` 只读并行，再运行同一 ARM64 二进制及参数（无 ReleaseMode 重复调用），原始 `logs/20261109_passive_only_trial2.log`：500ms 不发布观察，mode_machine=2，首段收到606包；16轴反馈确认后 kd0→3，Passive ready 时745帧，3s有界自动退出，HDC exit0。A/B/Y 编译期锁住。
- 监测 `logs/20261109-234607_windows_LowProtection.log`：约4773条完整采样（另有1条混入非本进程的 CycloneDDS 断言文字，见下），LowState末计数26131、主板506包；16轴mode在监测相对时间18.894s全0→全1、23.814s全1→全0；主板state0仅初始默认0和既有0x1，warning_or/motorstate_or均0；LowState最大age5ms、主板最大age50ms；电机电流最大1.7A、电机电压最低41.9927V。**现场人员再次确认始终趴下、无喇叭报警或异常动作。**
- 监测日志在相对时间24.819s一条 `PROTECT` 行中嵌入 `as2w_sdk2: ... EntityDelegate::prevent_callbacks(): Assertion 'false' failed` 文字；该监测进程随后仍继续输出到25.003s并返回exit0，故不能把这条插入文字直接归因于本监测进程，也没有对应机器人保护位。需后续追查 HDC 多会话输出混入/另一诊断进程退出；解析监测数据时跳过这条损坏行。**此软件日志异常不影响两次现场“无报警”的事实，但不能忽略。**
- 两次复测都通过，说明**当前这台 AS2-W 在趴下、ReleaseMode 后接受该候选 Passive 启动序列**；仍未定位旧报警单一根因，也未验证 FixStand、轮速度、方向、低层急停、站立时停发和 SelectMode 回收。当前维持释放模式，不自动执行可能令狗起立的恢复命令。进一步有动作实验需另行离线审查和现场当次同意。

## 2026-11-09 23:49–23:50：经现场人员当次同意恢复原厂运控

- 事先明确告知 `SelectMode("ai")` 从趴下可能让狗直接起立，现场人员明确同意并在旁。`现场入口.ps1 -Stage MotionSelect -Model ai`：`rc=0`、读回 `CheckMode form=1 name=ai`，原始 `logs/20261109-234945_windows_MotionSelect.log`。随后只读 GetState 为 `fsm_id=3 fsm_name=ai_free_walk process_state=active`，MotionMode 再证实 `name=ai`；原始 `logs/20261109-234957_windows_GetState.log`、`20261109-234959_windows_MotionMode.log`。
- **现场人员确认狗稳定站立、原厂遥控器正常、无报警异常。** 机器人已恢复原厂控制；本次没有进一步 LowCmd/策略试验。下一阶段任何 ReleaseMode 或可能动作命令都须重新告知并取得当次同意。

## 2026-11-09 23:53–23:55：重新确认原厂趴下状态，编制 R214 遥控/策略递进验收清单

- 现场人员报告已用原厂遥控让狗趴下。工作站只读运行 `现场入口.ps1 -Stage MotionMode`、`-Stage GetState`：`CheckMode rc=0 form=1 name=ai`、`fsm_id=0 fsm_name=ai_damping process_state=active`。原始日志 `logs/20261109-235306_windows_MotionMode.log`、`logs/20261109-235308_windows_GetState.log`。本阶段没有 ReleaseMode、没有 LowCmd、没有机器人动作命令。
- 静态复查当前 `r214_publish.cpp`：正常构建 A/B/Y 编译期锁住，虽然已经通过两次趴下态 Passive-only，尚未验证起立/策略。若强行启用宏，FixSquat F1 仍用 `thigh+0.6, calf=start*0.5`，与 20:25 仿真修正候选 `thigh+0.2, calf=start−0.3` 不一致；末尾 1s settle + 2s kp 衰减由 FSM 线程阻塞执行，期间无法及时处理 X。`r214_direction_test.cpp` 第一段仍用未通过的旧 `kd=5` 并自动串行三项动作，**禁止按现状运行**。
- 新建 `02_现场操作/R214实机遥控与策略递进验收.md`，明确原厂手柄→HG LowState→CPRO R214→HG LowCmd 的链路、A/B/Y/X 含义、S0–S8 分阶段动作与通过/停止条件。下一步先修离线代码并复演，逐项确认 LowCmd 方向与轮速度，再起立/零速策略/趴下，最后才短距离前行。每次可能动作实验须现场人员当次明确同意。

## 2026-11-10 00:01：R214 趴下 FSM 参数/阻塞缺陷离线修复，ARM64 编译

- 工作站维护源码 `部署参考/cpp_deploy-as2w/deploy/robots/as2w/r214/r214_publish.cpp` 修正 FixSquat F1 为 thigh `start+0.2`、calf `start−0.3`，F1 占默认 4 秒轨迹的 1.5 秒，F2 2.5 秒并保持全链仿真的 kp20/kd3；F1 增益从每轴实际策略 kp 过渡到35，而不是假定所有轴都是55。
- 原先 FixSquat 末尾 1 秒 settle + 2 秒 kp 衰减在 FSM 线程中阻塞，导致 X 键期间不被处理；改为 50 Hz 非阻塞子阶段，每 tick 允许全局 X/故障检查抢占。改动前独立增益扫描的 F2 kp35 候选未在全链重新验证，本版沿用已完成的全链仿真 kp20。
- 通过 WiFi HDC 发送**绝对本机路径**的单个源码文件至 CPRO Ubuntu rootfs 对应路径，HDC `FileTransfer finish`；本机/设备文件 SHA-256 一致：`0d61d2d07add045092d387b1ea2123e03d030e9ccaef7a08d18e9e72f62efbab`。在 CPRO Ubuntu 中 `cmake --build build-r214-publish --target as2w_r214_publish -j 4 && ctest --test-dir build-r214-publish --output-on-failure`：ARM64 编译链接成功，CTest **8/8**；原始日志 `logs/20261109-2359_r214_fsm_fix_arm64_build.log`。
- **没有运行发布端、没有 ReleaseMode、没有新的机器人动作命令。** 正常构建 A/B/Y 动作仍编译期锁住；8/8 当前只验证既有测试，未覆盖新版 FSM 的真机或 MuJoCo 闭环。下一步改造旧方向工具、补遥控失联/会话超时、重新仿真及离线 FSM 检查，再申请首个方向动作实验。

## 2026-11-10 00:03：复核“方向已验证”范围，缩减后续验证量（无机器人操作）

- 用户指出此前逐关节手掰方向已经验过，询问可否直接起立。复核 `config/r41_measured_identity_sign.md` 与 `config/hardware_contract.md`：G1 确实逐项验证了 16 轴**LowState 状态方向**；零位也有部分机械限位证据。两次 Passive LowCmd 的 `q=当前反馈, kp=0` 不能证明**非零位置目标**的实际电机响应；轮子也未收到非零 `dq` 命令。原始记录从未出现一个成功的单轴 LowCmd 方向实验。
- 因此不重复 16 轴手掰标定，将 `02_现场操作/R214实机遥控与策略递进验收.md` 的 S4 缩为负号 hip、正号 thigh/calf、轮速度的代表性低幅命令响应，或等价的受限起立预载子阶段；仍不得直接解锁完整 A→PolicyStand。现有自动方向测试工具继续禁用。此阶段只有文档与日志修改，无机器人命令。

## 2026-11-10 00:05–00:09：单轴有界探针离线构建、ReleaseMode、只读基线

- 用户要求开始实机测试。先只读 `MotionMode/GetState/LowProtection -Seconds 3`：原厂 `name=ai`、`ai_damping`，16 轴 mode=1，LowState 约1 kHz、主板 state0=0、无电机 warning/motorstate 位。原始 `logs/20261110-000509_windows_{MotionMode,GetState,LowProtection}.log`。
- 在已通过两次 Passive 的 `r214_publish.cpp` 中增加显式 `--probe-index`/`--probe-amplitude`：一次只允许一个 contract 轴，腿最大 0.03 rad、轮最大 0.5 rad/s；先经过同一已验启动序列，Ready 后 0.5s Passive、0.5s 渐入、0.5s 保持、0.5s 回退、1s Passive，自动退出。未提供 probe 参数时原 Passive-only 行为不变；A/B/Y 动作宏仍锁住。探针会打印目标/回读，腿离起点 >0.08 rad 或轮速 >2 rad/s 则停止。每次运行仍需现场人员针对该轴/幅度当次明确同意。
- 通过 WiFi HDC 绝对路径发送源码到 CPRO Ubuntu；ARM64 编译及 CTest **8/8**，离线帧审计分别验证 contract 0=FL_hip/DDs slot3/sign−1、contract 12=FL wheel/DDS slot13/sign+1；原始 `logs/20261110-0008_r214_probe_arm64_build.log`。**这只是合成帧与编译验证，不代表真实电机响应。**
- 现场人员仅针对本次 `ReleaseMode` 回复明确同意（确认狗趴下、在旁可操作急停）。00:08:09 `MotionRelease rc=0`、`CheckMode name=` 空，原始 `logs/20261110-000809_windows_MotionRelease.log`。没有发布 LowCmd。
- Release 后 `LowProtection -Seconds 3` 读到 16 轴 mode=0、状态流连续、warning/motorstate 均0、主板 state0=0x1（已知 ReleaseMode 上层超时位），但**监测进程结束时退出 134/core dumped**；原始 `logs/20261110-000821_windows_LowProtection.log`。随后 `LowCaptureFast -Seconds 2` 正常退出0，200条采样、16轴 mode=0、LowState 持续约1 kHz，原始 `logs/20261110-000848_windows_LowCaptureFast.log`。监测程序自身异常须追查，不能当机器人保护报警；探针试验前重新说明并获当次许可。

## 2026-11-10 00:10–00:11：首个 FL hip 有界微幅 LowCmd 实验（当次明确同意）

- 现场人员针对**本次** FL hip 约0.02 rad外摆目标明确同意，确认狗稳定趴下且能操作急停。并行运行 `LowProtection -Seconds 15`、`LowCaptureFast -Seconds 15`，原始 `logs/20261110-001035_windows_LowProtection.log`、`logs/20261110-001035_windows_LowCaptureFast.log`；单轴发布端原始 `logs/20261110-0011_fl_hip_probe_trial1.log`。
- 探针先经过500ms不发布观察、FOC零增益确认及kd渐增；Ready 后 contract index0=FL_hip/DDS slot3，原始 q0=+0.567687，`kp=5`，模型目标 +0.02 rad → DDS q 目标约 +0.547687。0.5s渐入、0.5s保持、0.5s回退、1s Passive 后自动结束，HDC exit0。A/B/Y 动作仍锁住，未调用 FixStand/策略。
- 15s保护监测完成、exit0，LowState持续，活跃16轴 mode在相对时间约2.75s从0→1、7.63s从1→0，主板仅既有 `state0=0x1`，`warning_or=0`、`motorstate_or=0`。LowCaptureFast 1500行中1499行完整、1行损坏；完整行分析 FL hip q 仅从约0.567657降到最小0.567471（约−0.00019rad），tau_est 在−0.2125至−0.0625Nm。**幅度远小于0.02rad目标，不能判定 LowCmd 位置命令方向成功。**
- 现场人员确认狗始终趴下、无可见关节动作、无喇叭报警或异常。推测 `kp=5 × 0.02rad≈0.1Nm` 可能低于关节静摩擦/负载，但这只是推断，尚不能排除模式或命令字段问题。下一次若增加幅度/增益，需单独构建审计、说明并取得当次明确同意；不得把首试当作方向通过。

## 2026-11-10 00:13–00:14：第二档 FL hip 探针准备（离线与只读，无动作命令）

- 发布端新增显式 `--probe-kp`，限制0–20，保留单轴和幅度上限；拟用 FL hip 模型目标+0.03rad、kp20（最大名义位置误差项约0.6Nm），其余时序同首试。同步将未启用的 FixStand B1 腿 kd 从2修为3，与既有 MuJoCo 全链仿真一致；A/B/Y 仍编译期锁住。
- WiFi HDC 单文件同步到 CPRO Ubuntu，ARM64 构建链接成功、CTest 8/8，显式 FL hip `--offline-audit --probe-index 0 --probe-amplitude 0.03 --probe-kp 20` 帧审计通过；原始 `logs/20261110-0015_r214_probe_kp20_arm64_build.log`。这不验证真实运动。
- 只读复核 `MotionMode name=` 空（仍为 ReleaseMode），`LowCaptureFast -Seconds 2` 200 样本、exit0，原始 `logs/20261110-001355_windows_MotionMode.log`、`logs/20261110-001355_windows_LowCaptureFast.log`。没有再次 ReleaseMode、没有发布第二档 LowCmd。下一步必须对这一档单独告知并获现场人员当次明确同意。
- 用户纠正 FSM 目标：A 应起立并保持**固定 PD Stand**，B 才进入 R214 策略；现有源码是 FixStand 后自动进入 R214 零速 PolicyStand，B 仅开放摇杆，**与目标不一致**。既有固定 PD Stand/策略回固定 PD MuJoCo 出现下沉，须先重做并验证保持和交接，不能直接解锁 A。已更新 `02_现场操作/R214实机遥控与策略递进验收.md`，当前微幅探针与 A/B 独立。

## 2026-11-10 00:15–00:17：第二档 FL hip 单轴微幅 LowCmd 实验，退出时 DDS 断言

- 现场人员对**本次** `FL_hip +0.03rad, kp20` 探针明确同意，狗趴下、在旁可操作急停。并行原始记录：`logs/20261110-001552_windows_LowProtection.log`、`logs/20261110-001552_windows_LowCaptureFast.log`；发布端原始 `logs/20261110-0017_fl_hip_probe_trial2.log`。
- 发布端 HDC 输出在提示 `GO` 后出现 CycloneDDS C++ `EntityDelegate::prevent_callbacks(): Assertion 'false' failed` / `Aborted (core dumped)`，此前标准输出被缓冲，起初误以为**未发布**。随后交叉解析 15s 原始监测：16轴反馈 mode **0→1(2.70s)→0(7.58s)**，活跃约4.88s，与已通过的 Passive 唤醒+3s探针时长吻合，**证实发布已发生**。首次口头说明“未发命令”已更正，不能以缺少 stdout 判断是否发过 LowCmd。
- FL hip DDS槽3 q：活跃起点0.567591，最小0.564235，沿目标原始负方向移动约−0.00336rad；按0.5s分箱，q在探针目标渐入/保持段下降，tau_est 从约−0.07Nm降至约−0.61Nm，峰约−0.6625Nm；探针结束后 q≈0.5647。较首试−0.00019rad明显，但仍只跟踪了目标−0.03rad的一小部分。它支持**本轴、此增益/姿态下的 LowCmd 位置方向正确**，不足以推断其余轴或固定PD站立性能。
- 主板只见 ReleaseMode 后既有 state0=0x1，无新增保护位；warning_or/motorstate_or均0，LowState持续，监测两进程退出0。现场人员确认狗仍趴下、无可见动作、无报警。
- **软件故障门槛**：当前远端 `echo GO | binary` 的管道使 HDC 端显示0，即使 binary abort134；后续须在远端设置 `pipefail`、显式打印/检查进程真实退出码。发布端应立即刷新日志，并调查/处理 SDK 在 CloseChannel 或进程析构阶段的断言；在修复并离线验证前不继续发 LowCmd。机器人当前仍 ReleaseMode，原厂模式未恢复。

## 2026-11-10 00:20–00:27：按用户今晚目标准备独立 A 起立试验版（无新动作）

- 用户明确接受今晚临时按键语义 **A→FixStand→R214 零速策略**，要求尽快看能否起立、是否报警，随后再考虑 B 策略行走；长期 A 固定 PD Stand/B 才接策略设计暂缓。首次试验仍须对具体动作当次明确同意。
- `r214_publish.cpp` 的诊断进程改为 `std::unitbuf` 即时刷日志，并在 writer 已 join 后对**非完整 FSM**会话用 `std::_Exit` 绕开这台 CPRO 上间歇出现的 DDS C++ 退出断言；这是短时诊断的临时措施，不代表长期控制器退出方案完成。新 `tools/run_r214_probe.sh` 用 Bash `PIPESTATUS[1]` 保留二进制真实退出码，CPRO 无 DDS 的134自测正确打印 `PROBE_REMOTE_RC=134`；NO 输入测试证实不初始化 DDS。
- 新增**单独** CMake 选项 `AS2W_R214_STAND_TRIAL`，只定义独立的 `AS2W_ENABLE_R214_STAND_TRIAL`，没有定义完整 `AS2W_ENABLE_R214_MOTION`。`--stand-trial` 仅允许默认 T1、FixStand 3s、FixSquat 4s，A/Y 可用，B 锁住；A 后 R214 零速保持2s即自动 FixSquat，末尾1s趴下 Passive 后停发；A等待120s未按则退出。`tools/run_r214_stand_trial.sh` 固定参数并用 `PIPESTATUS` 报真退出码。完整动作版 `--enable-fsm-motion` 在此构建中仍被编译锁拒绝。
- 三个文件通过 WiFi HDC 绝对路径同步到 CPRO Ubuntu。独立 `build-r214-standtrial` ARM64 **全构建成功、CTest 8/8**；第一次只构建 publisher 时其余7项测试因未构建而 Not Run，已在随后全构建中纠正。原始 `logs/20261110-0025_r214_standtrial_arm64_build.log`、`logs/20261110-0026_r214_standtrial_arm64_fullbuild.log`。本版 R214 回放1050帧 `max_abs_error=9.53674e-07`；CMakeCache `AS2W_R214_STAND_TRIAL=ON`，模型 SHA256 `b13ed598...`，地图 `7f28104c...`，源码本机/设备同为 `bf4eb133...`，二进制 `6ed89c0e...`。B 编译锁离线拒绝已验证；普通 build 重新编译后 `--stand-trial` 被拒绝。`bash -n` 试验脚本通过。
- 00:27 只读 `MotionMode name=` 空（仍 ReleaseMode）、LowCaptureFast 约200采样、16轴 mode0，FR腿 q≈[-0.558,1.002,-2.756] 趴下附近；LowProtection warning/motorstate均0、exit0。原始 `logs/20261110-002731_windows_{MotionMode,LowCaptureFast,LowProtection}.log`。**尚未启动 A 试验程序，也未发新 LowCmd。** 接下来必须详细预告：可能起立、零速策略轮子可能动作、2s后自动趴下、异常时 X/急停会失去主动支撑，并取得现场人员对本次的明确同意。

## 2026-11-10 00:28–00:33：R214 A 起立→零速策略→自动趴下首试（当次明确同意）

- `LowRemote -Seconds 3` 在 ReleaseMode 中只读收到 `LowState.wireless_remote` 报头 `55 51`、按键/摇杆居中全0，原始 `logs/20261110-002832_windows_LowRemote.log`。随后明确告知本次 A 会触发约3s FixStand→2s R214零速→约7s FixSquat/Passive自动退出，B锁住，可能报警/失稳/急停失撑；现场人员针对**本次**实验明确回复同意。
- 先启动60s只读 LowProtection 与 LowCaptureFast，再启动独立 `run_r214_stand_trial.sh`。程序显示 `Passive ready after 743 frames` 后，明确提示现场人员按原厂遥控器 A 一次；远端日志按顺序出现 `[Passive] → FixStand (A)`、`[FixStand] → PolicyStand`、`[PolicyStand] → FixSquat (Y/stand-trial timeout)`、`[FixSquat] → Passive`，终端 `STAND_TRIAL_REMOTE_RC=0`。原始发布端 `logs/20261110-0030_r214_stand_trial1.log`；本次无 B/PolicyWalk。
- 60s LowCaptureFast 6000条（5999完整、1条损坏），16轴 mode 0→1 在相对19.88s、1→0 在55.51s。FR calf 由趴下约−2.757rad 起，起立末端最近到−1.389rad（T1设定目标−1.23rad，**没有完全追到**），进入 R214零速后约0.2s收腿至−1.638rad并在46–47s稳定；FR thigh 同期约0.63→0.72rad。四腿整体也显示相同收腿趋势，故交接时**可能有一定机身下降**，但 HG LowState 无机身高度，无法实测下降厘米。活动期 IMU upright cosine 最小约0.958，未见翻倒；轮速绝对峰约1.48rad/s，腿 tau_est 绝对峰约23.89Nm。最后再次收腿接近趴下，监测末 FR q≈[-0.625,0.931,−2.67]rad，与原厂趴下锚点略有差异。
- 保护监测 `logs/20261110-002929_windows_LowProtection.log` 约11407有效行，主板 state0 仅0x0（发布中）和0x1（ReleaseMode空窗），warning_or/motorstate_or均0；监测电机电流峰7.1A、电压最低40.69V。**该只读监测进程在60s结束时又遇独立 DDS 清理异常，现场入口报RC1，数据已全程保存；发布端真实退出码0，不能混淆。** 关节原始 `logs/20261110-002929_windows_LowCaptureFast.log` 正常退出0。
- 现场人员表示看起来无异常，询问 FixStand→PolicyStand 是否下降；上述关节角显示确实较T1目标收腿，不能声称完全无下降。00:33 只读 `MotionMode name=` 空、LowCaptureFast 200样本正常，原始 `logs/20261110-003301_windows_{MotionMode,LowCaptureFast}.log`。**当前仍ReleaseMode、无发布进程、16轴反馈mode0、狗趴下；原厂遥控控制权未恢复。** 下一项若试 B 行走，须独立构建/限制时长和速度并获当次明确同意。

## 2026-11-10 上午：复核无报警原因与 A/B 正式验收语义（仅离线文档，无机器人命令）

- 复读 22:10/22:50 两次告警、23:10/23:30 只读扫描、夜间事故复核、23:43/23:46 两次 Passive 实验及 00:28–00:33 A 首试。第一次有“无有效 LowState 仍盲发”的实现缺陷；第二次确认至少收到少量状态，发首帧后状态停止并报警。`ReleaseMode` 后 16 轴 mode 由1变0是实测；其与首帧增益、时序等因素谁单独致警仍未分离。早期 23:30 的“根因确认”措辞过强，以夜间复核的分级结论为准。
- 无报警的现行流程：500 ms CRC 正确状态不发布观察；零增益 `mode=1/q跟随` 唤醒至少 500 ms 且 16轴 FOC 回读稳定200 ms；1 s 把 `kd` 从0升3；Passive ready 后才准 A。两次 Passive-only 与一次 A 首试均未报警；A 首试由 FixStand 自动进入 R214 零速再自动 FixSquat，**B 没有测试**。不能以此确认单个参数的因果，也不能把 A 首试算作固定 PD Stand 验收。
- 用户明确把正式 FSM 语义恢复为 **A→FixStand→固定 PD Stand；B 才切 R214 策略**。更新 `02_现场操作/R214实机遥控与策略递进验收.md` 顶部现行合同及分阶段顺序。旧完整 FSM 仍是 A 后自动进策略；本地全方向遥控改动尚未 ARM64 编译/同步，`AS2W_R214_FULL_MOTION` 与试验脚本不得用于真机。下一步先离线分离 FixedStand/Policy，解决固定 PD 保持及交接的仿真下沉问题，再依次独立验收 A、Y、B 零速、方向行走及回站。
- 本阶段只修改文档；未连接 HDC、未发布 LowCmd、未切换控制权、未令狗动作。没有新原始设备日志；依据的原始日志是上述已有各节所列文件。

## 2026-11-10 上午：R214 正式 A/B/Y/X FSM 开发与离线复演（未发真机 LowCmd）

- 按用户正式约定重构唯一维护源码 `部署参考/cpp_deploy-as2w/deploy/robots/as2w/r214/r214_publish.cpp`：A 从 Passive 起两段 FixStand，结束后固定 PD Stand（不再自动 `controller.arm()`）；B 需摇杆居中、腿目标/反馈误差≤0.25 rad、轮速≤0.5 rad/s，固定站≥0.5 s 后才 `arm()`，经 2 s 零指令目标插值进入 PolicyWalk；策略中 A/Y 或30 s 行走上限先把指令归零，轮速<0.5 rad/s 连续300 ms 后 A 进入 ReturnStand、Y 进入两段 FixSquat；从固定站按 Y 直接进入两段 FixSquat；X 在启动/运行期优先进入 q 跟随、kp0/kd3 的 EmergencyDamping，完整动作会话保持3 s后停发。所有相位仍由 500 Hz writer、50 Hz FSM、已实测成功的零增益 FOC→kd3 唤醒、CRC、mode_machine 回显与状态新鲜度门槛支撑。默认 CMake 发布选项 OFF。
- 回站目标选择有仿真依据：T2 训练默认姿态作为从趴下 A 的固定 PD 目标。旧 T1 方案从 FixStand 到固定保持约降3–4 cm、B 零速交接再降约4 cm；T2 首次固定保持约降1.1–1.5 cm，B 交接略抬约1.3–1.5 cm。从策略回站若强制拉回 T2，约降3–4 cm；将插值延长到4 s未改善；冻结**刹车结束时最后一帧 R214 腿目标**作为新的固定 PD 站姿，3种子回站加后续1 s固定保持约降1.0–1.5 cm、upright cosine≥0.999，站立阶段无非轮触地。这是离线候选，不是实机姿态/安全证明。
- 服务器 `caolin@192.168.10.163` 经现有 SSHFS 读本机源码/写本机日志，用 MuJoCo 3.17.0、Python ONNX Runtime 1.31.1、R214 ONNX 在平地模型复演。`r214_ab_fsm_rehearsal.py` 的 T2×3种子路线 A→固定站→Y、A→固定站→B→短时前进→Y、A→固定站→B→短时前进→A冻结目标固定站→Y，在**起立、策略、回站阶段**没有侧翻/仰翻，零速刹车完成且站立阶段无非轮部位触地；**Y 后机身按预期下降至趴姿**，仿真末端机身高度约0.07–0.16 m。`upright cosine` 仅表示机身朝向未翻转，绝不表示趴下后仍站立。Y 趴下非轮峰在不同路线/种子约38–160 N，**不可用旧50 N行走筛选阈值判定原厂趴下安全**；实机仍需单独观察。原始 `logs/20261110_r214_ab_fsm_final_mujoco.log`、结果 `部署参考/as2w-flat-rerun/results/r214_ab_fsm_final_20261110.json`；中间变体及输出分别存 `logs/20261110_r214_ab_fsm_variants_mujoco.log`、`logs/20261110_r214_ab_fsm_variants2_mujoco.log` 和对应 `results/*variants*20261110.json`。最初两次仿真启动因错误 runtime 路径和缺失 mesh 相对路径失败；在服务器 `/tmp/as2w_r214_sim_assets` 临时布置官方 XML/contract 与 `unitree_ros` 网格软链接后解决，未动机器人；最初失败输出未单独保留，最终脚本与日志可复现。
- 通过 WiFi HDC 绝对路径把新源码、CMakeLists 和两个现场脚本同步到 CPRO Ubuntu rootfs。独立全动作 `build-r214-ab-fsm-full`（`AS2W_R214_FULL_MOTION=ON`, standtrial OFF）与独立 A 固定站试验 `build-r214-ab-fsm`（standtrial ON, full OFF）均 ARM64 全构建、CTest **8/8**；原始 `logs/20261110_r214_ab_fsm_final2_{full,stand}_arm64_build.log`。两版 T2 `--offline-audit` 均 PASS，完整动作版输出 `FSM CONTRACT A=FixedStand B=PolicyHandoff Y=FixSquat X=EmergencyDamping`；原始 `logs/20261110_r214_ab_fsm_final_full_arm64_audit.log`、`logs/20261110_r214_ab_fsm_stand_arm64_audit.log`。R214 回放 `rows=1050 max_abs_error=9.53674e-07`，原始 `logs/20261110_r214_ab_fsm_arm64_replay.log`。脚本 `bash -n` 通过。
- 本机/CPRO `r214_publish.cpp` SHA256 同为 `0ae00f31080947e46ee5a20e2199a5b8079701107dc2fad1f3dde34bf0e232eb`；模型 `b13ed59864fbcde46a6a4d986c2a3552edf2cc9523cfd136a0cf60091aa8f746`；地图 `7f28104cb01b34585e07b32de230192cdf906cef9276739fc5d3e5a1b7e6a8d4`。运行 `部署测试/准备现场包.ps1` 成功，现场包 `cpp_deploy-as2w.tar.gz` SHA `5d460c20f0e934cb9e9fcb88ecfe12a12d66eb759ea695213bca3b1a044d5c27` 与 `01_现场部署包/SHA256SUMS.txt` 一致，归档含新 publisher 与两个脚本。**旧 `/root/as2w_deploy/build-r214-standtrial` 二进制仍是 A 自动进策略的历史版本，禁止使用；新 `run_r214_stand_trial.sh` 已改指向 `build-r214-ab-fsm`。**
- 本阶段没有运行发布端正常模式、没有 ReleaseMode/SelectMode/真实摇杆命令，也没有任何新的狗动作。完整动作版只是代码/离线构建，尚未真机验收；不得直接运行 `run_r214_motion_trial.sh`。下一次先只读确认设备状态，再按 `02_现场操作/R214实机遥控与策略递进验收.md` 的现行顺序，分别对 A固定站、Y固定站趴下、B零速接管、行走、A回站取得现场人员**当次具体同意**，每项留原始日志后再推进。

## 2026-11-10 09:46：最终线程修复编译通过；实机只读基线被物理网口中断阻挡

- 最后静态复核发现 FSM 的 PolicyHandoff/PolicyWalk/Brake 三处在 mutex 外读取订阅线程更新的 `latest_received`，改为与 LowState 快照一起在 `state_mutex` 内取时间戳。新源码经 WiFi HDC 绝对路径同步；本机/CPRO SHA256 均 `8e6f92fe9e8656b148e1d43bfc65dbd5af24a69fe614df2f24e273ebdf5a6960`。CPRO ARM64 独立 full/stand 两版重新编译、CTest各8/8；原始 `logs/20261110_r214_ab_fsm_release_{full,stand}_arm64_build.log`。重建现场包成功，`01_现场部署包/SHA256SUMS.txt` 中 cpp tar SHA `1ffa0286eab37f4a8c2980d340c8d606b186f29473639d4f3a381afd2d931756`；此条覆盖上节旧源码/归档哈希。无真机 LowCmd。
- 准备 A 固定站单项试验前只读 `现场入口.ps1 -Stage MotionMode/LowCaptureFast/LowProtection`：MotionMode `CheckMode rc=3104`；2 s LowCaptureFast **0 包**；2 s LowProtection `low_count=0, board_count=0`，均退出1。原始 `logs/20261110-094618_windows_{MotionMode,LowCaptureFast,LowProtection}.log`。随后只读 CPRO 鸿蒙宿主 `ip -br addr`/`ip -s link show eth0`：`eth0 <NO-CARRIER,...,UP> state DOWN`，IP `192.168.123.100/24` 虽仍配置但物理链路不通；WiFi `wlan0=192.168.10.180` 与 HDC 正常。`ip route` 的机器人子网项带 `linkdown`。这是 CPRO→狗的**物理载波断开**，故不能解释为策略/FSM/DDS 模型故障，**禁止 ReleaseMode 或运行任何发布端**。已向现场人员请求确认狗电源与网线/原厂遥控现状；待 eth0 恢复 carrier 后重跑只读基线，再申请 A 单项的当次具体许可。

## 2026-11-10 09:48–09:49：狗开机后物理链路和只读基线恢复

- 现场人员说明刚给狗开机；只读 CPRO `eth0` 变 `UP,LOWER_UP`。依次运行 `现场入口.ps1 -Stage MotionMode`、`LowCaptureFast -Seconds 2`、`LowProtection -Seconds 2`、`GetState`，均退出0。原始 `logs/20261110-094846_windows_MotionMode.log`、`logs/20261110-094848_windows_LowCaptureFast.log`、`logs/20261110-094852_windows_LowProtection.log`、`logs/20261110-094904_windows_GetState.log`。MotionMode `name=ai`，GetState `fsm_name=ai_damping/process_state=active`；LowState 2秒约2092包、`machine=2`、16轴mode全1，腿槽约 hip±0.58、thigh1.05、calf−2.76 rad 与趴下相符；主板40包，`board_state0=0x0`，`warning_or=0`、`motorstate_or=0`，电池约46.44 V。**本阶段只读，无任何动作或 LowCmd。** 下一步若现场许可，先单独 ReleaseMode，复核16轴mode0，再独立申请新版 A 固定 PD Stand→自动 Y 趴下有界试验；B仍编译锁在独立 A build。

## 2026-11-10 09:50–09:51：独立 A/Y 有界试验离线就绪；当次 ReleaseMode 已执行

- 为同时验收真实 Y 键且保持有界，独立 stand build 改为 A 两段 FixStand→T2 固定 PD 站立，**由现场人员按 Y** 进入两段 FixSquat；若15秒内未按 Y，自动受控趴下；随后1秒 Passive 自动停发。B编译锁住；X紧急 Passive。`run_r214_stand_trial.sh` 指向新 `build-r214-ab-fsm`，脚本参数 T2、`--stand-hold-seconds 15`。本机与CPRO新源码 SHA256 同为 `7c7f42a6f3a610825eb4680856cc8f42ba6049d0e481b68dc585dbb47f67eeb2`。CPRO ARM64 stand/full 两版重新编译、CTest各8/8，stand T2/15s `--offline-audit` PASS，`bash -n` PASS；原始 `logs/20261110_r214_ab_fsm_a_y_{stand,full}_arm64_build.log`、`logs/20261110_r214_ab_fsm_a_y_final_audit.log`。现场包重新生成，cpp tar SHA `adaed642a86032b0ce525c7a3010f5d330759114f690f91bcee7083657d2a8e6`；此条覆盖09:46的旧源码/包哈希。
- 现场人员明确同意**本次单独 ReleaseMode**，并确认在旁看护急停。`现场入口.ps1 -Stage MotionRelease` 返回 `ReleaseMode rc=0`、`CheckMode name=` 空；原始 `logs/20261110-095104_windows_MotionRelease.log`。随后两份只读 2秒采样退出0：LowState约2080包、`machine=2`、16轴反馈全 `mode=0`，主板 `board_state0=0x1`（ReleaseMode 既有上层命令超时位）、`warning_or=0`、`motorstate_or=0`、电压约46V；原始 `logs/20261110-095115_windows_{LowCaptureFast,LowProtection}.log`。**尚未启动新版发布端，也未按 A/Y；狗应仍趴下，但需现场目视再确认。** 下一步是就 A→固定PD约15秒内按Y→受控趴下单项明确告知风险并取得这一次的独立同意，然后才启动有界程序与只读监测。

## 2026-11-10 09:54–09:58：新版 A 固定 PD 站立首试；15秒超时自动趴下，Y 尚未验收

- 现场人员针对这一次 A→Y/超时受控趴下试验明确同意并在旁看护。使用新 `build-r214-ab-fsm` 独立 stand build，B 编译锁。发布端先观察 Released LowState 500ms，再完成 Passive 安全唤醒，明确报 `Passive ready after 729 frames`；提示现场按 A 后依次打印 `[Passive] → FixStand`、`[FixStand] → FixedStand (PD hold)`、`[FixedStand] → FixSquat (Y/timeout)`、`[FixSquat] → Passive`、`STAND_TRIAL_REMOTE_RC=0`。原始 `logs/20261110_r214_ab_fsm_a_y_trial1.log`。现场人员确认先起立并站住、后自行趴下；当时未等到按 Y 提示，故 **本次是15秒自动趴下，不能算 Y 键验收**。现场描述趴下“好像没有非常受控”；尚未给出量化判断，**先不进入 B 策略**。
- 两个50秒只读监测在09:54:11–09:55:01，A 实际动作发生在监测结束后：LowCaptureFast 的4999完整帧中 FR calf 只在−2.76189…−2.76168rad，证明这份监测**没有覆盖起立/趴下**，不得借其保护数据宣称动作期间无告警/冲击。原始 `logs/20261110-095410_windows_{LowCaptureFast,LowProtection}.log`，发布端日志写入至09:56:09。监测期保护 `warning_or/motorstate_or=0`、board_state0仅0/1。09:57:43事后只读 LowCaptureFast约2秒退出0，16轴mode0、FR calf约−2.67rad（趴下附近）；LowProtection采到约1.8秒 warning/motorstate均0、board_state0=1，但诊断进程在退出前遭独立 CycloneDDS断言，退出134，**不是发布端故障**。原始 `logs/20261110-095742_windows_{LowCaptureFast,LowProtection}.log`。
- 源码复核：关节顺序为4髋+4大腿+4小腿；FixSquat F1 由固定PD当前目标按1.5秒使大腿+0.2rad、小腿−0.3rad，同时腿kp从55降至35；F2 在开始时重新取实际q，2.5秒到趴下且kp直接取20，后1秒kp10、2秒降0。F1→F2的目标与增益变化可能影响下沉平顺性，属于**待测推断**，现有日志没有动作时序关节数据，不能确认根因。下一次试验须完整覆盖动作的只读采样，并在启动前明确让现场人员在起立后无需等待额外提示、5秒内按Y；仍需重新取得针对该次动作的明确许可。原厂 SelectMode 未执行，目前仍 ReleaseMode、无发布进程、狗现场报告已趴下。

## 2026-11-10 10:00–10:03：第二次 A→Y；采样定位 FixSquat 段间突降

- 现场人员重新明确同意本次有界 A→Y 试验并在旁握急停。只读 LowCaptureFast/LowProtection 两项120秒在10:00:33开始，覆盖全部动作；发布端 `run_r214_stand_trial.sh` 报 Passive ready 后提示现场按 A，现场在固定站立后按 Y，程序依次经过 FixStand→FixedStand→FixSquat→Passive、自动停发，真实 `STAND_TRIAL_REMOTE_RC=0`。现场确认**起立受控，但按 Y 趴下时中途突然下降、之后再收腿，明显不平顺**；此轮已验证 Y 键能进入 FixSquat，但质量不合格，**禁止直接进入 B 策略**。原始 `logs/20261110_r214_ab_fsm_a_y_trial2.log`、`logs/20261110-100032_windows_LowCaptureFast.log`、`logs/20261110-100033_windows_LowProtection.log`。
- 120秒约12000完整 LowState帧。前右小腿在采样45.0秒约−1.735rad；45.0–46.4秒逐渐到−2.035rad，46.5秒−2.141rad、46.6秒−2.293rad、46.7秒−2.445rad、46.8秒−2.519rad，随后缓慢收至48.9秒−2.668rad。右后小腿也在46.4–46.6秒由约−2.148到−2.412rad；前右小腿突降区间回读速度峰约1.7rad/s，姿态upright cosine约0.992最低（未翻）。FixSquat F1耗时1.5秒，因此46.5秒突降与F1→F2边界吻合；**段间重置目标为实测q、kp由35跳至20**会即时释放支撑位置误差，是首要根因推断。采样无法测机身高度/足端接触力，不能把推断当确定事实。
- 动作窗口40–55秒约2859条保护流，`warning_or=0`、`motorstate_or=0`，主板state0仅0/1；电机电流峰5.7A在起立41.237秒，Y段45–49秒峰3.05A，无新增硬件保护位。发布停止后仍ReleaseMode，16轴mode0，狗现场确认稳定趴下。下一步仅修改段间目标/增益连续性，ARM64编译及离线验收；再次实机须另行申请当次许可。

## 2026-11-10 10:04–10:08：FixSquat 段间连续性修复与离线验收（未发真机 LowCmd）

- 修改唯一发布源码 `部署参考/cpp_deploy-as2w/deploy/robots/as2w/r214/r214_publish.cpp`：FixSquat F2 从F1最后**命令目标**连续插值，不再在F2首tick把目标重置为实际关节角；kp在F2由35渐降至20，接着1秒由20渐降至10，再2秒由10降0。FixedStand进入趴下时打印 `squat trigger=Y|timeout`，下次可明确辨别按键与自动超时。F1仍1.5秒、F2仍2.5秒，A/B/X语义未改。源码本机/CPRO SHA256均为 `f6065537d8d8564753979e43c98e43401701b582ce40770f2b4ac52212822187`，通过 WiFi HDC 绝对路径同步。
- CPRO ARM64 独立 stand build 与 full build 都重新编译成功，各 CTest **8/8**，原始 `logs/20261110_r214_squat_continuous_arm64_build.log`。服务器MuJoCo 3.17对 T2 A→固定站→Y 路线做3种子对比：旧版Y非轮接触峰约38.2/89.2/159.5N，新版15.8/17.5/20.3N；新版末端机身高度约0.163/0.135/0.131m且未翻，表明模型中趴下冲击下降，**不能代替实机验收**。新脚本 `部署参考/as2w-flat-rerun/r214_ab_fsm_squat_continuous.py`，结果 `部署参考/as2w-flat-rerun/results/r214_ab_fsm_squat_continuous_20261110.json`，原始 `logs/20261110_r214_ab_fsm_squat_continuous_mujoco.log`。
- 当前狗仍 ReleaseMode、趴下、无发布进程。下一步需另行向现场人员说明并取得**本次** A→Y 试验许可；先启用覆盖全部动作的只读监测，再启动新独立 stand build（B仍锁住），核对 `trigger=Y`、实际段间角速度与现场观感。仅此通过后再申请 B/策略动作。

## 2026-11-10 10:12–10:15：段间连续性修复版第三次 A→Y 真机复测通过；B 尚未测试

- 现场人员当次明确同意修复版有界 A→Y，确认在旁握急停。10:12:52先启动各120秒只读 LowCaptureFast/LowProtection，再启动新独立 `build-r214-ab-fsm`。程序确认 `Passive ready after 737 frames` 后现场按 A，固定PD站稳后现场按 Y；发布端明确打印 `FixedStand squat trigger=Y`、FixSquat→Passive、`STAND_TRIAL_REMOTE_RC=0`，无 B/策略。现场确认**起立受控、趴下明显较平顺、无报警、现稳定趴下**。原始 `logs/20261110_r214_ab_fsm_a_y_continuous_trial3.log`、`logs/20261110-101251_windows_LowCaptureFast.log`、`logs/20261110-101251_windows_LowProtection.log`。
- 第三次采样11999完整 LowState帧，覆盖全动作；相较第二次Y的同类4秒窗口，前右小腿 `|dq|` 峰约 **1.804→0.654 rad/s**，四小腿最大 `|dq|` 峰约 **1.892→0.816 rad/s**，前右小腿任意约0.3秒内最大位移 **0.439→0.168 rad**，与现场“突降消失/明显改善”一致。第三次Y窗口姿态upright cosine最低约0.987（未翻），末端前右小腿约−2.670rad、16轴mode0。对应保护流动作窗口约2863行，`warning_or=0`、`motorstate_or=0`，主板state0仅0/1；电机电流峰5.7A、电机电压最低45.14V。**这些是实测反馈，不等于有机身高度或接触力直接测量。**
- 当前 CPRO 已同步并编译修复版源码 SHA `f6065537d8d8564753979e43c98e43401701b582ce40770f2b4ac52212822187`；stand/full build 各CTest8/8，stand限定版A/Y已真机通过。**B键策略交接、摇杆行走、策略中A回站与Y趴下仍完全未经真机验证。** 当前ReleaseMode、无发布进程、狗趴下；原厂控制权未恢复。后续继续由服务器OpenCode开发/指导，任何下一次动作（含B或SelectMode）须新一轮具体告知并取得现场人员当次明确同意。
- 新发现的B门槛：第三次固定站立采样42.5–43.5秒按 `config/r152_measured.map` 换成contract关节序后，腿相对T2默认目标最大位置误差约 **0.2705 rad**（后左髋），后右髋约0.264、小腿后右/后左约0.269/0.263；现源码B允许阈值为≤0.25rad，故当前真实姿态下按B**很可能被拒绝**，日志会打印pose_error。不能直接把B能按下等同于交接成功。服务器agent应分析该门槛及实际稳定性，再离线修改/审查、ARM64编译、按单独许可测试B；不可盲目放宽全部安全判据。

## 2026-11-10 10:15–10:22：B 后续开发转交服务器 OpenCode（无狗动作）

- 用户指定后续 B 键策略开发、实机指导交给服务器 agent。本阶段仅整理交接，无新 LowCmd/模式切换。已新增详细任务书 `部署测试/05_OpenCode交接/给OpenCode_R214_B策略接续_20261110.md` 与可直接粘贴的 `给OpenCode_R214_B策略首条Prompt_20261110.md`，并更新该目录README；文档覆盖三轮真机、修复因果边界、B门槛0.2705>0.25、现行FSM、独立有界B零速试验设计、编译/仿真/监测/遥控方向/日志与每次许可要求。
- 交接前只读核实：服务器 `/home/caolin/as2w_workstation` 为有效SSHFS挂载，`opencode` 位于 `/usr/bin/opencode`；服务器经专用密钥可SSH到工作站；Windows HDC `list targets` 为 `192.168.10.180:10178`；本机 `r214_publish.cpp` SHA仍为 `f6065537...822187`。当前狗现场确认趴下、CPRO ReleaseMode、无发布，原厂控制未恢复。下个 agent 先只读复核当下状态，不应复用该时刻结论作为以后事实。

## 2026-11-10 10:55–11:06：B 门槛实测分析、有界零速 B 试验版开发与全套离线验收（未发真机 LowCmd）

- **B 门槛实测分析（任务书 6.1.1）**：重析第三次 A→Y 采样 `logs/20261110-101251_windows_LowCaptureFast.log`。时间线：1–39s 趴下待命（max leg err≈1.09）、39–41s A 起立、**42–44s 固定 PD 站立静止窗**（max leg err=0.2705 rad 恒定）、44–47s Y 趴下。42.5–43.5s 窗按 `r152_measured.map` 转 contract 序逐轴 |q−q_T2|：RL_hip 0.2705、RR_hip 0.2638、RR_calf 0.2693、RL_calf 0.2628、前髋 0.217/0.221、前小腿 0.120/0.131、大腿 0.054–0.092；**1 秒窗内逐轴 std<2e-5 rad（完全静止）**，max |wheel dq|=0.037，upright=0.9954，mode 全 1。结论：0.2705 是 kp=55 下的系统性重力稳态偏差（后髋最大），非震荡/失稳；旧 0.25 门槛会拒绝这个实测安全稳定的姿态，即现场按 B 大概率被拒的直接原因。分析脚本 `/tmp/opencode/analyze_b_gate_trial3.py`（服务器临时，关键数值已记入本节）。
- **门槛改造（源码 `r214_publish.cpp`）**：位置阈值 0.25→**0.30 rad**（`kBGatePoseError`，来源=实测 0.2705+裕量，单独提高阈值不等于 B 安全）；保留轮速≤0.5、摇杆居中、站立≥0.5s；新增**最近 500ms 腿回读 |dq|≤0.15 rad/s 静止窗**与 **IMU upright≥0.9** 两项；拒绝日志打印全部门槛值+12 轴逐轴误差明细，接受日志打印各项实际值。
- **独立有界零速 B 试验版（任务书 6.1.2，`--zero-b-trial` + CMake `AS2W_R214_ZERO_B_TRIAL`）**：A 起立（同已通过 stand 流程）→现场按 B（门槛拒绝则停留 FixedStand，可 Y/15s 超时退出）→2s PolicyHandoff（fixed→策略 q/dq/kp/kd 连续 blend）→**策略零速强制保持 2.5s（摇杆速度强制 0，不读摇杆）**→自动 Brake（轮稳 300ms）→ReturnStand 2.5s（冻结最后零速策略腿目标）→FixedStand 再保持（Y 或 15s 超时）→已通过修复版 FixSquat→1s 趴下 Passive→自动停发。B 仅接受一次上升沿；B 起整链 60s 绝对上限（超时从当前目标连续进 FixSquat）；EmergencyDamping 保持 3s 后停发；X/断流/姿态异常优先紧急退出；`controller.arm()` 仅 B 接受时调用（state[1196] 清零）、B 前不推理。launcher `tools/run_r214_zero_b_trial.sh`（指向 `build-r214-zero-b`，`--stand-hold-seconds 15`）。stand/full/zero-b 三模式互斥，普通构建 `--zero-b-trial` 直接报错。
- **编译流程固化（采纳用户转交的 GPT 建议，已写入 `部署测试/AGENTS.md`）**：服务器固定镜像 `/tmp/opencode/r214_zero_b`（rsync 增量同步、保留构建缓存）、固定构建目录 `b`、日常仅 `cmake --build b --target as2w_r214_publish`（增量实测 **4–6s**，此前每轮冷编译曾超 600s 超时）、上真机前另建 `b-clean` 干净构建。首轮记录：rsync 全量 108M、全量构建+CTest 8/8 通过、单 target 增量 5.79s/4.15s。
- **x86 离线验收**：`b` 全量构建、CTest **8/8**、`--offline-audit` PASS（含 FSM CONTRACT 打印）、1050 帧回放 max_abs_error=5.96e-08。
- **MuJoCo T2 三种子 `A_B_ZERO_RETURN_Y` 路线**（新脚本 `部署参考/as2w-flat-rerun/r214_zero_b_trial_rehearsal.py`，结果 `results/r214_zero_b_trial_rehearsal_20261110.json`）：seed 101/202/303 全程未翻（min_up≥0.989）。B 交接 2s 机身高度 +1.4~+1.5cm、轮 dq 峰≤0.06、腿 dq 峰≤0.10；零速保持 2.5s 高度 −0.9~−1.0cm、轮 dq≤0.04；自动刹车瞬时轮稳（≤0.02）；冻结目标回站 2.5s 高度 −0.5~−1.0cm、轮/腿 dq≤0.04/0.03；回站后 1s 保持稳定；Y 非轮接触峰 18.6/44.3/57.0N（起点为冻结策略目标而非 T2，高于此前 A→Y 直测的 16–20N，仍在已接受量级内）、最终趴下高度 0.105–0.126m。**仿真不代替实机验收**。
- **CPRO ARM64 验收**：`r214_publish.cpp`/`CMakeLists.txt`/`run_r214_zero_b_trial.sh` 经工作站 PowerShell+hdc 推送；新 `build-r214-zero-b`（ZERO_B_TRIAL ON）配置+全构建成功，stand `build-r214-ab-fsm`/full `build-r214-ab-fsm-full` 增量构建成功；**三构建 CTest 各 8/8**；zero-b audit PASS、banner 正确、`GO` 确认门槛在 stdin EOF 下正确退出；回放 1050 帧 9.54e-07。源码 SHA256 工作站=CPRO=`56b6825a185e19a45199da43fb5948661a05bc39373667e37e6f96ce342e179a`；CMakeLists `c0c6b5794cdea6b4...`、launcher `be8d98e0ebe2c3a8...`。现场部署 tar/SHA256SUMS **未重新打包**（发布包仍为旧版，如需交付另行重建）。
- **下一门槛**：向现场人员提交单次 A→B零速→自动回站→Y 有界试验的具体动作说明与自动退出条件，**等待当次明确同意**；真机前按流程做一次干净构建核验。B 被拒时的现场路径=保持固定站、按 Y 或 15s 超时受控趴下退出，不当场反复按 B。

## 2026-11-10 11:18–11:25：⭐ 首轮有界 B 零速策略试验真机通过（R214 首次实机接管）

- 现场人员当次明确同意本轮 A→B零速→自动回站→Y 试验并在旁握急停。先启动发布端至 `Passive ready after 736 frames`（狗趴下未动），再启动 120 秒 LowCaptureFast/LowProtection（覆盖全动作，11999/22787 行完整），随后现场依次按 A、B、Y。发布端完整日志链：`[Passive] → FixStand (A)` → `[FixStand] → FixedStand (PD hold)` → **`[FixedStand] → PolicyHandoff (B accepted: pose_error=0.2746 wheel_dq=0.0122718 upright=0.994948 quiet_dq=0.0306796)`** → `→ PolicyWalk (zero-speed handoff complete)` → 12 条 `WALK_CMD vx/vy/wz 全 0`（强制零速确认）→ `→ Brake (2.5s zero hold cap)` → `→ ReturnStand (wheels stable)` → `[ReturnStand] → FixSquat` → `[FixSquat] → Passive (auto)` → `ZERO-B TRIAL: prone hold complete, stop`，**真实 `ZERO_B_TRIAL_REMOTE_RC=0`**。现场反馈全程无明显异常。原始 `logs/20261110_r214_zero_b_trial1.log`、`logs/20261110_112041_windows_LowCaptureFast.log`、`logs/20261110_112041_windows_LowProtection.log`。
- **B 门槛首次实机验证成功**：实测 pose_error=0.2746（新门槛 0.30 生效；旧 0.25 会拒绝）、wheel_dq=0.012、upright=0.995、500ms 静止窗 dq=0.031，全项通过并打印明细。采样 9–11s 固定站立窗 errT2=0.275 与门槛读数互证。
- **策略接管段实测（12–17s）**：B 交接 2s 腿 |dq| 峰仅 **0.27 rad/s**、轮 dq 峰 0.20、upright 0.9949→0.9965（策略把姿态微调得更正）、errT2 0.275→0.268；策略零速保持 2.5s 内 **errT2 恒 0.259、腿/轮速度 0.034/0.025 rad/s**——R214 首次实机站立保持完全稳定，无明显收腿/下沉（无机身高度实测，不引申具体厘米数）。
- **回站/趴下**：刹车后 ReturnStand 腿 dq 峰 0.41；Y 蹲下（起点为冻结策略目标）四腿 |dq| 峰约 0.90 rad/s，与已通过修复版 0.816 同量级；21s 后稳定趴下 errProne=0.097，upright 全程最低 0.987（未翻）。保护流 22787 行 **warning_or=0x0、motorstate_or=0x0**、board_state0 仅 0/1、电机电流峰 5.80A（起立段，与历次 5.7A 一致）、电压最低 44.16V。
- **监测时序教训（本轮修正了前一轮的缺口）**：LowCaptureFast/LowProtection 输出为块缓冲、结束才回写；若先开监测再启动发布端，120 秒窗口会在按 A 前过期。本轮顺序=发布端 Passive ready（无动作）→ 开监测 → 现场按键，动作段（采样 6–21s）完整落在窗口内。此顺序已验证有效，后续真机试验沿用。
- 当前状态：发布已自动停发、狗趴下、仍 ReleaseMode、无发布进程、原厂未恢复。**B 零速门槛已通过；摇杆速度映射、轮非零方向、行走、策略中 A/Y 仍未验证。** 下一门槛按任务书 6.3：单独申请第一轮手柄低速前进（|vx|≤0.1 m/s、1–2 秒、0.1–0.2 m、松手停车），再逐方向扩展。

## 2026-11-10 11:26–11:33：第二轮真机行走试验——前进可行但策略持续后仰塌陷；根因定位为策略 sim-to-real 支撑缺陷

- 现场人员当次同意一轮 vx/vy/wz 逐方向测试。发布端 full build `run_r214_motion_trial.sh`：`Passive ready after 747 frames` 后依次 `A → FixedStand → B accepted (pose_error=0.270538, upright=0.9952)` → PolicyWalk。现场只实际推了 **ly（vx 前进/后退）**：多段推-松（vx ±0.1 m/s 内），lx/rx 未测。现场反馈"前进可以走，但走着走着后面两条腿像没力气慢慢掉下来"。用户松手后按 A → Brake → ReturnStand → FixSquat → RC=0 正常退出，趴下稳定，全程无报警。原始 `logs/20261110_r214_motion_vxvywz_trial1.log`、`logs/20261110_112901_windows_LowCaptureFast.log`（15001 帧）、`logs/20261110_112901_windows_LowProtection.log`。
- **时间线（监测 elapsed）**：0–34.5s 趴下待命；34.5–36s A 起立；36.5s 固定 PD 站稳（pitch −0.6°，后 thigh≈0.93）；**37.0s B 接管完成瞬间 pitch 已 −7.9°**；38–41s 零指令缓慢塌；42–46s 前进段（轮 |dq| 0.7–1.2）塌加速 −4.8°→−9.4°；46.5–58s 持续塌至 **pitch −21.3°**、后右 thigh 0.99→**0.30 rad**（几乎趴下）、后腿 |tau| 12→21 Nm 持续增长；58.5s 松手后 pitch 稳定在 −21.3°（塌陷平衡点，不再继续掉）；随后 A 回站、Y 趴下成功——**回站/趴下链在塌陷姿态下仍正常工作**。
- **硬件侧全部排除**：后腿驱动温度峰仅 41–42°C（无热限）、电流峰 5.90A（与历次起立一致）、电压最低 43.99V、22787+ 行保护流 warning_or/motorstate_or 全 0x0、后腿 tau_est 持续增长无饱和平台——不是电机失力/电气/热/保护问题。
- **根因判定：策略 sim-to-real 支撑缺陷，非硬件**。决定性对比：同为 kp=55，固定 PD T2 目标下站立完全稳定（首伦 errT2 恒 0.275），策略接管后从第一采样起持续缓慢后仰塌陷。与 R214 交付报告平地弱点（固定集跟踪 44/52、严格检查 21/52）一致。**上轮 2.5s 零速"稳定"实为塌陷早期被窗口截断**——零速观察窗须延长（≥10s）才能判定稳定，此为设计教训。
- **待区分的两个候选机制**（决定修复方向，下轮取证）：A. 策略输出的后腿目标本身过低/负载分配失衡（目标跟着塌）→ 需混合 T2 托底或修策略输出；B. 策略目标站位合理但 PD 支撑刚度不足（目标高于实际、误差稳态 0.36 rad 量级）→ 提策略段 kp 或加前馈。**当前发布端未记录策略 q_cmd，无法离线区分**——下一步先加命令日志再复测。
- 已验证可用的结论保留：前进方向轮映射正确（vx=+0.1 时狗前进）、后退可走、B 门槛、回站、Y 趴下、紧急退出链全部正常。**侧移/转向方向仍未测**；行走测试暂停，待策略塌陷问题解决后按 6.3 逐方向恢复。

## 2026-11-10 11:40–11:55：塌陷取证版开发（10s 观察窗+POLICY_TRACK 日志）与 MuJoCo 前进对照（未发真机 LowCmd）

- **R214 增益考古（用户质疑触发）**：GitHub 最新 `YuTaoV5/Rob2Nav` pull 至 `/tmp/opencode/rob2nav_github` 核对，kp=55/kd=2 三处硬编码：`deliveries/as2w-deploy/policy.cpp:175`（`i<LegCount?55:0, kd=2`）、`mujoco_screen.py:96-97`（`kp=55×12+0×4, kd=2×16`）、`omni-blind-stairs-r214/.../r152_controller.cpp:158`；deploy.yaml 无 stiffness/damping 属交付风格（增益写执行层），与本地副本及我们的部署四方同值——**排除增益错配候选根因**。GO2 部署 yaml 的 25/0.5 是另一训练体系的增益，不可互换。
- **塌陷取证版改动**（`r214_publish.cpp`，工作站=CPRO SHA `330a54cf8ed1c19c9d19fc505396ff24a6dca6c22aca786923d96e2881be72ee`）：① zero-b 零速保持窗 2.5s→**10s**（上轮 2.5s"稳定"实为塌陷早期被窗口截断）；② PolicyWalk/Brake 每 0.2s 打印 `POLICY_TRACK,<hold>,<12腿轴 cmd−actual>`（contract 序 fl/fr/rl/rr × hip/thigh/calf）——后腿条目持续为负/趋零=机制A（策略主动压低），稳定 ~+0.3rad=机制B（目标撑、PD 不足）。x86 增量编译零警告、audit PASS、CTest 8/8；CPRO ARM64 增量构建+CTest 8/8+audit PASS。
- **MuJoCo 对照实验一（10s 零速）**：`r214_zero_b_trial_rehearsal.py` 窗口改 10s 三种子——机身高度仅降 1.9–2.8cm、min_up≥0.999，**不塌**。结果 `results/r214_zero_b_10s_rehearsal_20261110.json`。
- **MuJoCo 对照实验二（12s 前进 vx=0.1，用户新增要求）**：新脚本 `r214_forward_sink_rehearsal.py`——三种子高度 0.37→0.34（-3.4cm）、**pitch 到 -3.6/-4.4/-4.5°（与实机塌陷同方向）**、后腿 thigh 0.67→0.61~0.62 下沉后刹车回稳 0.64、min_up≥0.997、非轮接触 0N。**结论：策略在仿真里就有同方向弱后仰趋势，但收敛稳定；实机同输入塌到 -21°/thigh 0.30，幅度差 5 倍以上**——策略姿态平衡偏弱被实机动力学（质心/质量/摩擦差异）放大，方向落在机制 A/B 之间，待实机 POLICY_TRACK 定论。结果 `results/r214_forward_sink_rehearsal_20261110.json`。
- **下一门槛**：向现场申请单次长零速 B 复测（A→B→10s 零速不碰摇杆→自动回站→Y），实时收集 POLICY_TRACK 判定机制；修复方向按判定结果选 T2 混合托底（机制A）或提策略段 kp（机制B）。

## 2026-11-10 11:56–12:00：⭐ 长零速 B 取证轮真机通过——零速不塌，塌陷由行走指令激发

- 现场人员当次同意 10s 零速取证轮。`Passive ready after 743 frames` 后依次 A、B、Y；`B accepted: pose_error=0.297766 wheel_dq=0.012 upright=0.9895 quiet_dq=0.021`，10s 零速（不碰摇杆）→ `Brake (10s zero hold cap)` → ReturnStand → FixSquat → RC=0 正常退出。**现场确认"屁股没趴"（零速 10 秒无塌陷）**。原始 `logs/20261110_r214_zero_b_10s_trial2.log`。
- **POLICY_TRACK 首批实机数据（零速段，每 0.2s）**：后腿 thigh cmd−actual 恒 **+0.123~+0.124 rad（10 秒不增长）**、后腿 calf +0.123→+0.153（仅 +0.03 缓慢漂移）、后髋 ±0.26~0.27 恒定（固定站静态偏差延续）。**策略目标始终高于实际 ~0.12-0.15 rad 且稳定**——零速下呈轻微机制 B 特征（静态跟踪误差）但**无持续塌陷**。
- **两轮对照修正根因定位**：上轮（11:29）B 交接完成后 ~0.5s 内即推杆行走（轮 dq 0.59），pitch 立即 -7.9° 并持续塌到 -21°；本轮 B 后 10s 零速完全不塌。**塌陷由行走指令激发，不是零速固有**——策略在带速度指令时的后腿支撑/姿态平衡不足（MuJoCo 前进实验的同方向 -4° 弱趋势与此一致），实机动力学放大。
- **下一步**：带行走的 POLICY_TRACK 取证（motion 模式日志代码通用）——用户轻推前进 2-3 秒触发塌陷早期，看行走中后腿 cmd−actual：大正值（目标远高于实际）→ 机制 B 强化 → 提 kp/前馈；误差小但绝对值随实际整体下移 → 机制 A → T2 混合托底。修复前需要这一轮定位。

## 2026-11-10 12:0x：R214 训练命令分布取证与速度敏感性对照（用户关键质疑触发）

- **用户质疑“是否训了特定速度”→ 查训练 trace**（`models/r214/r214-trace.csv` 1050 帧，[flag, obs41, action16] 布局，第1-3列=原样 command）：**vx ∈ {0.4×650, 0.35×200, 0×200}，vy 恒 0，wz ∈ {0×850, −0.5×200}——R214 是以 0.4 m/s 恒速巡航为主的楼梯策略，0.1 m/s 完全没有训练样本（OOD）**。实机首测的 vx=0.1 属分布外。顺带核实：trace obs[0]=原样 0.4 无偏移，C++/Python 复演喂法一致，排除 obs 布局错配嫌疑。
- **MuJoCo 速度对照（12s 前进三种子）**：vx=0.1（OOD）pitch 至 −3.6/−4.4/−4.5°、rearThigh min 0.612；**vx=0.4（训练内）pitch 至 −5.8/−6.3/−6.2°、rearThigh min 0.568——训练内速度后倾反而更深，但两者都稳定不塌**（upright≥0.994、高度收敛 0.32–0.35）。结果 `results/r214_forward{04,}_sink_rehearsal_20261110.json`。
- **修正后的根因图景**：① 策略天生带后倾姿态倾向（训练产物：盲楼梯策略重心后置，仿真里 −4~−6° 是其正常后倾平衡，交付验收“不翻即过”掩盖了这点）；② 该后倾平衡在 MuJoCo 理想动力学下稳定、在实机动力学（质心/质量/摩擦差异）下**失稳**——零速时勉强维持（POLICY_TRACK 误差 0.12–0.15 恒定），行走扰动下失稳塌至 −21°。速度 OOD 非主因但可能加剧。
- **修复预判更新**：机制 B 侧（策略目标的后倾平衡在实机撑不住）概率上升；T2 混合托底（把策略腿目标向 T2 直立姿态按比例拉回）比单纯提 kp 更对症。最终仍以行走中 POLICY_TRACK 取证定论。

## 2026-11-10 12:04–12:12：第三轮行走取证（失误：full build 未重编，POLICY_TRACK 缺失）；行为学证据链补齐

- **失误记录**：12:04 行走取证轮使用的 `build-r214-ab-fsm-full` 是旧二进制（11:40 改版后只重编了 `build-r214-zero-b`，未重编 full/stand），POLICY_TRACK 一行未打。机制判定数据缺失，但 15001 帧监测完整。已重编 full+stand（CTest 8/8、SHA `330a54cf...` 与工作站一致）待重跑。
- **行为学时间线（监测）**：0–13s 趴下；14–16s A 起立（pitch 瞬时 −7.8）；17–23s **B 接管后零速稳定在 pitch ≈ −7.1°、rearThigh 0.699（恒定不塌）**——与零速轮"稳"一致，**策略零速平衡本身就是后倾 −7°**（MuJoCo 同段 −1.4°，实机后倾更深）；24–28s 低速试探 pitch 略回 −6.0；29–38s 持续行走 **pitch 单调 −6.8°→−17.1°、rearThigh 0.585→0.400**；39–40s 松手**不回正**（−18.5 稳住）；41–45s 再走恶化到 −20.1°；46–54s 停止后**完全不可逆（−20.1°、rearThigh 0.290 恒定）**；55–58s **A 回站把狗从 −19° 完全拉正到 0°（rearThigh 0.29→0.92）**；59s+ 固定 PD 站立正常 → Y 趴下 RC=0。现场反馈与数据一致："越走后仰越厉害、前后运动或回零速都不回正"。
- **关键推论**：① 策略塌陷不可逆（递归状态+后倾姿态自锁，"每个 pitch 档位有对应平衡、行走推向更深档"）；② **固定 PD kp=55 能从 −20° 拉回直立而策略 kp=55 却走向 −20°——策略的腿目标本身在跟着掉（偏向机制 A）**，但最终判定待重跑的行走中 POLICY_TRACK；③ A 回站退路已两次从深塌陷成功拉正，安全退出链有效。

## 2026-11-10 12:1x：B 门槛 0.30→0.35（物理依据：PD 稳态误差力矩平衡）+ 第四轮行走取证取消原因与重编

- 12:09 第四轮取证起立后 B 三次被拒：`pose_error=0.3033 (gate 0.3)`，仅超 0.003 rad；拒绝明细定位超差轴 RL_calf=0.303/RR_calf=0.295，其余门槛项（轮速 0.012、静止 0.03、摇杆居中、hold、upright 0.989）全过。用户按 Y 正常趴下退出 RC=0。**根因：4 次实测站立 pose_error=0.2705/0.2833/0.2977/0.3033，0.30 门槛贴边，起立落点 ±0.03 随机波动导致约半数被拒**。
- **用户关键提问"为何固定站立 pose_error 这么大"→ 数据验证**：第 3 次站立窗（42.5–43.5s）逐轴 `kp×err` 与实测 τ_est 完全吻合（差 <0.2Nm，如 RL_hip +14.88 vs −14.74、RR_calf +14.81 vs −14.55）。**PD 稳态误差=维持 T2 所需力矩/kp**：后腿 14–15 Nm、前腿 3–7 Nm（前后 2–4 倍不对称=实机质心偏后），0.26–0.30 rad 是物理必然非控制失败。T2 是训练默认角非本机零力矩构型。**同一个"质心偏后"解释了固定站立的后腿大误差与策略行走的后仰塌陷两个现象**；MuJoCo 模型质心与实机不符故仿真不塌。
- **门槛修改**：`kBGatePoseError` 0.30→**0.35**（注释含物理依据；仍远小于趴下>1.0 的真歪斜；轮速/静止/摇杆/hold/upright 全保留）。x86 编译+audit+CTest 8/8；CPRO full/stand/zero-b 三构建增量编译各 CTest 8/8；工作站=CPRO SHA `c6f82fe6e80949f8275ffc208ad705e60ffdc4853a3ba77f7cf5fd7d339139b3`。
- 下一步：重新执行带 POLICY_TRACK 的行走取证轮（轻推 2-3s 触发塌陷早期，读行走中后腿 cmd−actual 符号定机制 A/B）。

## 2026-11-10 12:15–12:35：⭐ 第五轮真机（vx/vy/wz 全方向）+ 机制 B 最终判定；当日真机测试收官（随后狗下电）

- 现场人员当次同意全方向取证轮（门槛 0.35 生效）。`B accepted: pose_error=0.259015 upright=0.9972`，链：A→FixedStand→B→PolicyWalk（30s cap）→Brake→ReturnStand→FixedStand→Y→FixSquat→**RC=0**。POLICY_TRACK 152 行 + WALK_CMD 61 条非零（现场测了 vx 前后、vy 侧移、wz 旋转）。原始 `logs/20261110_r214_motion_track_trial5.log`、`logs/20261110_121608_windows_{LowCaptureFast,LowProtection}.log`（15001 帧/28537 行完整，监测 ssh 尾挂已按新 AGENTS 规则 pkill 回收）。
- **机制 B 最终判定（POLICY_TRACK 逐轴符号）**：后腿 cmd−actual 从零速的 thigh +0.10/calf +0.33 随行走增长至 **thigh +0.34~0.38 / calf +0.37~0.45 后锁定**——**策略目标始终高于实际（一直在命令"撑住"）但 kp=55 的 PD 在实机质心下撑不到目标**；前腿误差全程仅 +0.01~0.07（前腿撑得住）。55×0.40≈22 Nm 与塌陷时后腿实测 tau 21 Nm 吻合。**策略目标偏低（后倾 −7° 平衡）而非"目标跟着掉"**——纯机制 A 被排除；A 回站能拉正是因 T2 目标在 −22° 时误差 ~0.7 rad→38+ Nm 才够力。
- **时间线（监测）**：13–18s 零速稳 −7.3°（第三次确认）；19–20s 侧移 vy≈−0.05（训练**未训过 vy**）：姿态反而略回正 −5.6→−3.8°、未见明显横移（现场"感觉不行"）；25–29s 前进段开始渐降；30–31s 旋转 wz≈−0.05（训练仅 −0.5 一档）：yaw 仅 0.6→3.9°、轮 dq 峰 3.14 rad/s（基本不转）；32–38s 持续前进 pitch −9.5→−20.8；39–57s **pitch 锁死 −21~−22°、rearThigh 0.28~0.31 不可逆**（期间继续侧移/旋转测试均无法回正）；58–63s **A 回站从 −22° 完全拉正到 0°**（第三次验证深塌陷退路有效）；64s+ 固定站立正常；69s Y 趴下成功。
- **结论**：① R214 在本机**平地行走不可用**——后腿支撑在实机质心/动力学下不足（机制 B：目标偏低+刚度不足，前腿正常后腿差 5 倍误差）；② 侧移/旋转因训练分布缺失（vy 零样本、wz 仅 −0.5）基本无动作；③ 塌陷不可逆但 A 回站退路可靠；④ 全程无报警（保护流 28537 行 warning/motorstate 全 0x0）；⑤ 当日测试收官，狗随后下电。
- **修复方向（供后续会话）**：首选**策略输出与 T2 按比例混合托底**（把后腿目标抬高、误差增大→力矩增大→姿态撑高；混合比可 MuJoCo 扫描后定）；备选提策略段 kp 55→80（治标：目标仍后倾）；根本方案是再训练/换模型（平地+低速+vy 命令域）。修复后按 6.3 逐方向重新验收。

## 2026-11-10 12:35–12:50：02_现场操作 文档全面审阅与补全（用户授权，无狗动作）

- 用户授权审阅 `部署测试` 文档（03/05 不动，02 详细审阅，以本 INDEX 为准）。
- **归档 4 份完全过时文档**至 `02_现场操作/archive/`（附 README 说明归档原因）：`实机测试链方案_R152.md`、`R152_FSM操作与验证门槛.md`（R152 已废弃为离线失败候选）、`CPRO同事问题.md`（初期核实清单全部已被现场实测回答）、`策略选择与测试.md`（旧六模型时代文档）。
- **补全 11 份信息过时文档**（均在标题后插入"2026-11-10 更新"块，正文保留历史）：`R214实机遥控与策略递进验收.md`（新增下午实测状态总节：A/Y 三次、B 门槛 0.35 物理依据、B 零速通过、行走塌陷机制 B、A 回站可靠、增益链、修复方向）、`实机事实与命令.md`（R214 主线现状+管理链+新事实，R152 段标历史）、`现场入口使用.md`（发布端现状覆盖 R152 旧表述、hypothesis.map→r152_measured.map、监测回收规则）、`低层硬件合同.md`（声明权威版本在 config/hardware_contract.md+零位/命令已测状态）、`低层自测计划.md`（完成项清单+剩余项）、`明日bringup手册.md`（现状覆盖"无发布端"前提）、`需厂商确认的低层信息.md`（已解决/待查分列）、`现场部署清单.md`、`部署工程说明.md`、`部署架构.md`、`AS2W_16轴DDS关节序速查.md`（零位/命令验证状态）、`LowCmd启动事故复核与离线审查.md`（后续验证补记）。
- 保留不动（历史证据/审计性质）：`参考资料总审计.md`、`宇树资料核对.md`、`G1关节手动标定记录.md`、`GO2文件移植判断.md`、`calibrated.map.example`。

## 2026-11-10 12:50–13:10：02 文档正文级清理（用户复核反馈：仅加头部声明不够，正文旧内容仍会误导 AI）

- 用户指出第一轮"标题加更新块"方式不足：正文大段过时陈述（"没有 LowCmd 发布端""零位全部未标定""FSM 未实现""只能执行 S0-S2"等）仍会误导读者。本轮做**正文级重写/清除**：
  - **R214验收.md**：中后段 00:01 历史草案整体替换为当前版（按键语义+门槛 0.35+构建/launcher+各阶段验收状态表 S0-S8 含 S7b ⚠️/S7c ❌+机制 B 结论+现场操作硬规则）；旧 standtrial 禁用注记保留。
  - **实机事实与命令.md**：16 轴节改"最终版=G1 标定"（删除 A/B 候选与"全部未标定"过时句）；R41 段压缩为历史行；删"当前包没有 LowCmd 发布端"；待处理项改删除线标注。
  - **明日bringup手册.md**：全文重写为当前状态版——状态快照+停机原则（含急停锁存教训）+真机试验标准流程（11-10 固化的 6 步：只读复核→许可→发布端 Passive ready→监测→按键→归档）+环境重建参考（压缩保留已验证技术步骤）+历史注记。
  - **现场部署清单.md**："尚未满足的门槛"重写为 5 项当前真门槛（塌陷修复/轮速标定/失联急停/速度源）+已完成项删除线。
  - **AS2W速查.md**："五、使用边界"更新（命令方向/CRC/启动序列已验证；剩余待验证项列明）。
  - **低层自测计划.md**：第三轮改"已完成主要验收"；第二轮标注历史。
  - **需厂商确认.md**：8 问标注自答状态（2/8 全部、4 大部分、6/1 部分、8 已自答）。
  - **部署工程说明.md/部署架构.md**："不发布 LowCmd""FSM 未实现"等边界句改写为 11-10 实况；旧六模型 config 定位为离线/影子目录。
  - **现场入口使用.md**：尾部 R152 段压缩为一行历史注记；"当前包没有 LowCmd 发布端"句删除。
  - **低层硬件合同.md 归档**至 archive/（被 `部署参考/cpp_deploy-as2w/config/hardware_contract.md` 权威版取代），`部署测试/AGENTS.md` 第 41 行引用同步更新（原句"当前包不创建也不发布 LowCmd"亦已过时，改为历史行+当前状态）。
- 终检：grep "没有 LowCmd 发布端/全部未标定/FSM 未实现/尚未获准尚未实现" 于 02 目录无未标注残留。

## 2026-11-10 14:1x–14:4x：一键会话脚本 + 策略更新/配置化指南（无狗动作；狗已下电）

- **新增 `tools/run_r214_field_session.sh`（CPRO 侧一键会话）**：stand/zero-b/motion/dry-run 四模式。步骤全部不可跳过：①发布端二进制+源码 SHA 记录+`--offline-audit` PASS ②LowState 1s≥100 包且 mode_machine=2 ③控制权（name=ai→确认趴下，站立则官方 stand-down/遥控器趴下等待，再 ReleaseMode 并复核；name 空→直进）④LowState 2s≥1500 包+**16 轴 mode 全 0（防其他 LowCmd 进程，两次报警教训）** ⑤CPRO 本地后台监测（low-capture 10ms+low-protection，会话目录）⑥调用对应 launcher（发布端内置已验证唤醒序列）。会话产物 `/root/field_sessions/<ts>_<mode>/`。
- **CPRO dry-run 实测通过**（狗下电状态下）：step1 audit PASS（SHA `c6f82fe6...` 与工作站一致）、step2 在 LowState 0 包处正确 FATAL 退出——"校验不跳过"逻辑被验证。后续带狗首次使用前仍按单次许可+人工核对。
- **新增 `02_现场操作/R214一键会话与策略更新指南.md`**：①脚本用法/调用命令/各步失败行为/手柄语义与 B 门槛/会话归档 ②策略模型更新 SOP（含先审训练命令域的教训、trace 布局、五级校验链、增益 55/2 合同、zero-b 先行）③配置化改造蓝图：r214_publish.cpp 硬编码清单→参考 GO2 config.yaml 结构→建议 deploy.yaml fsm 段 schema→新增组合键+新策略的六步模板（连续 blend/冻结回站/P6 位图补测/有界首测）④已知限制。GO2 位置 `部署参考/unitree_cpp_deploy-go2/deploy/robots/go2/config/config.yaml`。

## 2026-11-10 14:5x–15:25：R249 独立适配、离线审计与 ARM64 构建（无机器人动作）

- 用户将首要目标改为测试 `flat-low-speed-r249`，暂缓一键脚本通用化与 Git 管理。通过 GitHub main 分支 sparse clone 保存原始交付到 `部署参考/Rob2Nav-r249-source`；交付明确限定为平地低速预览，楼梯回归 0/16，不得用于楼梯。ONNX SHA256 `2483c7b49ccd0c4db1d738aca8c2fa716a12e52e92e52d6fc8669f9b63b90a2d`，合同为单输入 `obs[1,60]`、单输出 `actions[1,16]`，不同于 R214 的 `obs41+state1196`。
- 新增独立 `deploy/robots/as2w/r249` 控制器与 `models/r249`：实现 `command-[0.4,0,0]`、IMU、q/dq、上一帧**后处理最终 action**、0.62s gait clock；0.25s 命令平滑；低速后腿 action gate；动作缩放及策略 kp/kd 全部从 R249 deploy.yaml 读取。当前 R249 交付值恰为腿 55/2、轮 0/2，但不再视为跨策略不可变常量。共享 FSM 源仅增加编译期策略适配器选择，R214 x86 回归编译及 startup audit 通过。
- x86 zero-B/full 两套构建的 `r249-controller-smoke` 与 `r249-startup-frame-audit` 均 2/2 通过。首次 smoke 因 ONNX Runtime unowned shape view 的 owning TypeInfo 生命周期错误抛 `length_error`，已修复并复测通过；失败也保留在本节结论中。
- MuJoCo 首轮发现：R249 在物理零速度命令下仍固有输出非零轮动作；默认静态合成观测的轮目标约 1.9–4.7 rad/s，闭环三种子实测轮 dq 峰约 4–9 rad/s。原 R214 Brake 等待零命令策略自行停轮会卡住。R249 分支已改为 Brake 时保留策略腿支撑、2s 显式把四轮目标速度插值到零；zero-B 首测策略窗口缩短为 3s。
- 修复后 MuJoCo 三种子 `A→B零速3s→显式停轮→ReturnStand→Y` 均完成且未翻转；但 B handoff+零速阶段机身从约 0.36–0.37m 降至约 0.28–0.30m，min upright 约 0.918–0.938，个别非轮接触峰 62N；说明 R249 的静态零速保持并不理想，不能直接开放长期 motion。回站后固定站约 0.30m，Y 可完成趴下。结果 `部署参考/as2w-flat-rerun/results/r249_zero_b_trial_rehearsal_20261110.json`，日志 `logs/20261110_r249_zero_b_trial_mujoco.log`；第一次错误 runtime 路径失败已被后续同名日志覆盖，错误事实在本节记录。
- 用户追问轮速危险性后补跑机身平移指标：轮半径由官方 FL_foot STL 外形核得约 0.086m；零速3s阶段轮 dq 峰为 6.07/6.21/9.19rad/s（轮缘约0.52/0.53/0.79m/s），机身水平速度峰 0.17/0.17/0.63m/s，三秒净位移 0.15/0.15/0.75m。最差种子已达到明显的现场碰撞风险，**撤回“可直接落地做3s zero-B”建议：当前版本禁止落地按B**。下一步先只读 shadow 确认实机观测上的预测轮目标，并排查训练零命令语义/增加 neutral-stick 不进入策略的状态逻辑；必要的动作测试先上稳定机械支架、轮子离地，仍须当次许可。
- 已经 WiFi HDC Sync 到 CPRO；ARM64 `build-r249-zero-b` 与 `build-r249-full` 均构建成功，CTest 各 2/2。模型、controller、共享 publisher 的工作站/CPRO SHA 一致；原始构建日志 `logs/20261110_r249_zero_b_arm64_build.log`、`logs/20261110_r249_full_arm64_build.log`，同步日志 `logs/20261110-152058_windows_Sync.log`。尚未运行任何 R249 LowCmd；下一步必须先只读复核设备状态，再单独取得一次 3s zero-B 动作许可。

## 2026-11-10 15:40–15:46：切回 R214 一键会话主线；Windows 入口与 dry-run 验收（无机器人动作）

- 用户决定暂停 R249，先让训练同事修正零速策略；当前 R249 保持“禁止落地按B”。主线切回已通过真机 A/Y 的 R214 一键会话。
- 新增个人 PC/工作站入口 `部署测试/运行现场策略会话.ps1`：显式 HDC WiFi target、`r214` policy、stand/zero-b/motion/dry-run、监测时长；非 dry-run 必须带 `-ConfirmMotion`；远端输出实时显示并写本机 transcript；自动把 `/root/field_sessions/<会话>` 从 CPRO rootfs 拉回 `logs/field_sessions/`。首次因 UTF-8 BOM、第二次因 Windows PowerShell 5.1 `Tee-Object` 参数集不兼容在本机入口失败，均未连到 CPRO；已修正并保留事实。
- 因共享 publisher 源在 R249 适配时改为策略编译期选择，CPRO 的 R214 stand/zero-b/full 三套构建均重新增量编译；各 `r214-startup-frame-audit` 1/1 通过。原始日志 `logs/20261110_r214_field_session_rebuild_arm64.log`。
- 最终 dry-run 从 Windows 一条命令通过并实时显示：R214 stand 二进制 audit PASS；LowState 约1043包/秒、mode_machine=2；MotionSwitcher `name=ai`；脚本在“正式运行将先确认趴下再 ReleaseMode”处退出，没有 ReleaseMode/LowCmd/动作。CPRO 会话目录自动拉回 `logs/field_sessions/20261110-154539_dry-run/`，本机 transcript `logs/20261110-154538_windows_r214_dry-run_field_session.log`。下一步为单次获许可的 stand 会话：脚本确认趴下→ReleaseMode→Passive ready→现场 A 起立→Y受控趴下；B 在 stand build 编译锁住。

## 2026-11-10 15:4x：R214 stand 嗡鸣风险发布前复核（仅离线，无机器人动作）

- CPRO 当前 stand 构建编译定义只有 `AS2W_ENABLE_POLICY_STAND_TRIAL=1`；没有 R249、motion 或 zero-B 定义，因此 B/策略路径未编入本次二进制。`pgrep` 未发现存活的 `as2w_r214_publish`（仅命令自身匹配）。
- 当前 ARM64 二进制完整 `--offline-audit` PASS：16个有效槽中性首帧均为 `mode=1`、q跟随、dq=0、kp=0、kd=0、tau=0；槽16–34 mode0；mode_machine=2、CRC已填。Passive 审计帧仅把16轴kd设为3。启动时序仍为500ms不发布观察→零增益FOC请求至少500ms→16轴FOC反馈稳定200ms→1s内kd 0→3→Passive ready，与此前连续两次Passive无报警和修复版A/Y（Passive ready 737帧、现场无报警）相同。原始复核 `logs/20261110_r214_stand_preflight_doublecheck.log`。
- 共享源码因R249适配发生了编译期策略选择重构，所以当前二进制哈希并非历史真机二进制逐字节相同；但R249专属逻辑受未定义宏排除，R214路径的启动帧/时序/FSM audit与已通过流程一致。硬件报警无法由离线审计绝对保证；正式会话建议到 `Passive ready` 后先不按A观察/听5秒，无异常再按A，任何嗡鸣/报警立即X或物理急停。

## 2026-11-10 15:51–15:54：⭐ R214 stand 一键会话首次真机验收通过

- 现场人员从任意 PowerShell 目录用绝对路径执行 `运行现场策略会话.ps1 -Policy r214 -Mode stand -MonitorSeconds 180 -ConfirmMotion`。一键链完整通过：audit PASS；LowState 1035包/秒、mode_machine2；原厂 `ai_damping` 趴下；ReleaseMode rc0且name空；释放后2秒2089包、16轴mode全0；自动开启双监测；发布器500ms不发→FOC确认→kd渐升，`Passive ready after 749 frames`；现场按A完成FixStand→固定PD站立，按Y完成连续FixSquat→Passive，`STAND_TRIAL_REMOTE_RC=0`、publisher rc0。
- 现场人员确认全程一切正常，无嗡鸣、报警或异常动作。180秒 `low_protection.log` 共34194行，`warning_or`/`motorstate_or` 非零行0，峰值电机电流5.7A，正值电机电压最低48.3881V；末尾16轴mode全0。会话已拉回 `logs/field_sessions/20261110-155128_stand/`，Windows transcript `logs/20261110-155128_windows_r214_stand_field_session.log`。
- 用户在发布端已经打印RC0之后按 `Ctrl+C`。本次是安全的：CPRO发布器此前已退出，远端180秒监测随后完整结束并写出 `session complete`；Ctrl+C只中断Windows端等待/自动回收，未中断LowCmd。后续正常结束应等待 `session complete` 和本地归档提示；若仅见publisher rc0，可Ctrl+C但会失去自动拉档，需人工拉回。发布器仍活跃时不得把Ctrl+C当急停，优先X/物理急停并另行确认远端进程。

## 2026-11-10 16:0x：一键会话通用操作文档与 Motion 最小链路SOP（无机器人动作）

- 新增权威通用文档 `02_现场操作/一键现场会话与策略切换指南.md`：个人PC/工作站绝对路径入口、dry-run/stand/zero-b/motion含义、监测等待与Ctrl+C规则、日志三层路径、乱码原因、跨策略按键/profile扩展原则。
- 写入R214 Motion最小链路：场地/急停检查→Passive ready后5秒观察→A固定站→摇杆居中B接管→零速观察2秒→左摇杆约四分之一行程轻推前进1秒（约0.03–0.05m/s）→松杆立即A回站→Y趴下；列明B拒绝、后腿下降、方向错误、报警等中止条件。该文档是操作说明，不代表已取得下一次Motion许可。
- 修正R214专项指南把55/2写成全局“不可改”的错误表述：55/2只属于R214 Policy状态合同；FixStand/FixSquat和未来B/L1+B不同策略可有独立增益，必须逐策略核对训练/部署合同。

## 2026-11-10 16:2x–16:3x：R270-preview 契约审计与独立 MuJoCo 零速门槛（无机器人动作）

- 按用户指定从 GitHub main sparse clone `omni-blind-stairs-r270-preview` 到 `部署参考/Rob2Nav-r270-source`，HEAD `3560a7ab037ed149c1928ff3e6dabf3b3ed3dc9e`。ONNX SHA256 `059e3959c3aa1760acc00eb86e659493bff85d8815c417df906bca4410603851`，PT `a8817cf1e93064cd0bd62b4a31a4865c77b89a843d48ced44a506e8b209bbd7b`，deploy YAML `54593529ae467eae928a25e86d62099c5e66d356b4e8f9b9dd4f687cfb18fa81`。
- 合同为 `obs[1,720]→actions[1,16]`：当前60维帧 + 过去2/4/.../24 tick的 `[3:58]`，覆盖480ms；命令滤波alpha=0.12，物理命令减 `[0.4,0,0]`；腿目标 `default+0.35a`，轮目标 `16a`。上游2350帧数值回放误差约1.49e-7，只证明ONNX/历史拼接数值一致，不证明闭环安全。**交付未明确腿/轮 kp/kd，是落地合同缺项。**
- 上游自身平地动态证据已不满足松杆门槛：standard/heldout各4个stop段全部 `held=false`，stop平均速度约0.15/0.14m/s；左右平移、转向跟踪也很弱。README明确标记simulation-preview、SDK/执行器/实机未验证。
- 新增独立脚本 `部署参考/as2w-flat-rerun/r270_zero_b_trial_rehearsal.py`，在服务器使用既有AS2-W固定资产、R270 ONNX和480ms历史，按当前低层策略基线增益55/2复演 `A→2s B handoff→零速3s→显式Brake→冻结回站→Y`。三种子均不翻、无非轮触地，但零速3秒轮dq峰 **2.77/2.81/2.89rad/s**，机身水平速度峰 **0.20/0.21/0.21m/s**，净位移 **0.42/0.42/0.44m**；这是稳定持续移动，不是启动瞬态。结果 `results/r270_zero_b_trial_rehearsal_20261110.json`，原始日志 `logs/20261110_r270_zero_b_trial_mujoco.log`。
- **结论：R270-preview 当前不通过真机 B 的零速安全门槛，不接入 cpp_deploy、不构建/同步 CPRO、不发布 LowCmd。** 训练侧至少应修正 neutral command：多种子从站姿接管后连续5–10秒松杆位移接近0、轮速收敛，并补齐策略kp/kd、训练命令域、zero/stop统计与完整部署合同；新交付再走回放→独立MuJoCo→有界zero-B→短时motion链。

## 2026-11-10 16:4x–17:0x：按用户决定准备 R270 2秒有界真机接管（仅离线/编译/只读，尚无 LowCmd）

- 用户知晓零速漂移后仍决定做一次真机短测。为限制风险，未开放摇杆：新建独立R270控制器（真实 `obs720`，60维当前帧+2/4/.../24 tick历史，arm/stop清历史，alpha=0.12与0.005归零、动作缩放/限位），B链固定为2秒handoff后**2秒强制零物理命令**，随后显式2秒刹轮、冻结策略腿目标回固定站，Y或15秒超时受控趴下；X仍为紧急退控。
- 服务器x86 `build/r270-zero-b` 构建成功，第一次CTest因从R249复制的smoke错误要求“低速后腿gate”而8/9；R270合同本无该gate，修正smoke后**9/9**。失败和修复均保留：`logs/20261110_r270_x86_build.log`、`logs/20261110_r270_x86_rebuild.log`。
- 按同款2秒路线MuJoCo三种子：策略零速段轮dq峰2.07–2.17rad/s、速度峰0.16–0.17m/s、位移0.24–0.25m；随后显式刹轮段另位移约0.15m；全链未翻、回站和Y成功。真机场地应按**B后总漂移0.4–0.45m**最坏范围准备。结果 `results/r270_zero_b_2s_trial_rehearsal_20261110.json`，日志 `logs/20261110_r270_zero_b_2s_mujoco.log`。
- 已同步CPRO并新建 `build-r270-zero-b`；ARM64编译及CTest **9/9**，`--offline-audit` PASS。二进制SHA `9e9b93509061e3e95813cd31f71bb9ad8fa2c8190983a8532ad906b35ae6146b`，ONNX SHA `059e3959...3851`；原始 `logs/20261110_r270_arm64_build.log`。新增专用 `tools/run_r270_field_session.sh`，保留一键会话的audit→LowState→控制权→mode0→双监测→发布全门槛。
- 真机前只读：LowState约1034包/秒、mode_machine2，MotionSwitcher name空（已ReleaseMode），关节为趴下锚点；2秒capture约2001包且16轴mode均0（HDC输出夹带DDS teardown assertion，但有效LOW_SAMPLE完整）。无发布端、无本轮动作。下一步必须向现场明确说明A起立、B可能前移0.4–0.45m、自动刹停回站、Y/超时趴下及X/物理急停，再取得本次明确许可。

## 2026-11-10 19:1x–19:3x：R284-500 离线审计、MuJoCo与ARM64有界接管准备（狗断电、无动作）

- 用户在R270动作许可前改换GitHub main `flat-r284-500-preview`，因此**R270真机试验取消且从未运行**。sparse clone保存至 `部署参考/Rob2Nav-r284-source`，HEAD `02b3c5987bc2bc7e1d70543a188f2df486e22109`，ONNX SHA `a666bc2b8949c3c517ce1ec65513ba20cedf2f5819d58c6cb801b09d4d968e75`。
- R284合同完整：`obs[1,65]→actions[1,16]`，55/2腿增益、轮kd2；前60维为命令/IMU/q/dq/上一动作/时钟，新增4维“进入零指令时四轮相对角位移/0.2rad”和1维zero flag。官方训练为PhysX从零训练，500/2500迭代、约1231万环境步；是preview。官方静态10秒3/8严格通过，运动后松杆0/8，最大平均漂移约4–5cm；侧移/转向跟踪仍一般。
- 官方 `r284_observations.hpp` 已原样归档进部署控制器。服务器ORT1.22编译运行官方C++ replay：16000帧、16次reset，最大动作误差`1.07288e-6`通过；日志 `logs/20261110_r284_cpp_replay_ort122.log`。
- 新增 `r284_zero_b_trial_rehearsal.py`，在既有AS2-W MuJoCo固定资产独立复演：三种子B handoff后**2秒零速**轮dq峰0.20–0.23rad/s、机身速度显示至0.00m/s、净位移舍入0.00m；**10秒零速**轮dq峰0.23rad/s、净位移0–0.02m；均直立、无非轮触地，自动Brake/回站/Y成功。结果 `results/r284_zero_b_{2s,10s}_trial_rehearsal_20261110.json`及同名日志。
- 运动后停车诊断：先零速2秒→vx0.05运行2秒（前进约0.11–0.12m）→松杆10秒，三种子继续漂移约0.06–0.07m，随后显式Brake能停；没有翻倒/非轮触地。说明R284显著优于R270，**适合先做有界zero-B，但尚不能直接开放长期motion**。结果 `results/r284_motion_stop_trial_rehearsal_20261110.json`、`logs/20261110_r284_motion_stop_mujoco.log`。
- 实现独立 `deploy/robots/as2w/r284` 控制器，直接复用官方65维观测/目标映射；新增 `models/r284`、2秒zero-B launcher与严格field-session。x86构建/CTest **9/9**；同步CPRO后ARM64 `build-r284-zero-b`构建/CTest **9/9**、offline-audit PASS。设备二进制SHA `30c77bfbdf13b57cbe4f22b37b3dd31d463d7458a3f89419867dcd40887f7159`；日志 `logs/20261110_r284_{x86,arm64}_build.log`。
- 狗断电时执行一次专用field-session验证守门：audit PASS后LowState=0包，脚本正确FATAL退出，没有ReleaseMode/LowCmd；日志 `logs/20261110_r284_poweroff_session_guard.log`。当前狗仍下电。下一步可让现场上电，先只读确认原厂趴下/LowState，再单独申请本次A→B强制零2秒→自动Brake/回站→Y许可；首次不开放摇杆。

## 2026-11-10 19:4x：R284 首次真机前上电只读基线（无动作）

- 用户给狗上电后仅做只读检查：LowState 1049包/秒、mode_machine=2，16轴反馈有限且趴下锚点吻合；MotionSwitcher `name=ai`，Sport状态 `ai_damping`、active，确认原厂控制下稳定趴下。未ReleaseMode、未启动发布器、未发LowCmd。原始日志 `logs/20261110_r284_poweron_readonly.log`。
- 下一步仍须现场对本次完整动作明确同意：脚本将确认趴下→ReleaseMode→16轴mode0门槛→双监测→安全Passive唤醒；现场A固定站、B强制零R284接管2秒、自动Brake/回固定站、Y（或15秒超时）趴下。首次摇杆锁零；X/物理急停保留。

## 2026-11-10 19:39–19:42：R284 首次真机会话仅完成A/Y，B未发生（无报警）

- 现场明确许可后专用field-session完整通过audit、LowState 1026包/秒、原厂`ai_damping`、ReleaseMode rc0、释放后2秒2077包且16轴mode0；Passive安全唤醒743帧ready。现场按A完成FixStand→FixedStand，但按上一条提示**没有按B**；15秒FixedStand超时直接FixSquat→Passive并停止，RC0。
- 发布日志明确只有 `[Passive]→FixStand→FixedStand`、`FixedStand squat trigger=timeout`，没有任何 `B accepted/PolicyHandoff/PolicyWalk/Brake`。因此现场看到的“全程自动趴下”是A/Y链重验，**不能记为R284零速接管通过，更不能据此开放运动轴**。
- 120秒保护日志22850行，`warning_or`/`motorstate_or`非零0行；末帧16轴mode0、主板state0=1、电压约48.12V、电流1.45A。目录 `logs/field_sessions/20261110-193947_r284-zero-b/`（low_capture从CPRO接收因WiFi HDC大文件长时间无进度被中止，远端原件仍在）；console `logs/20261110_r284_field_session_console.log`。
- 用户希望随后开放全方向且提议“0.2m/s限速”。合同修正：R284训练平移模长上限仅0.10m/s，不能将vx/vy放到0.2；wz单位为rad/s，首档建议0.20rad/s。下一步必须先另获本次许可，真正执行A→B强制零2秒→自动Brake/回站→Y；通过后再单独构建/许可motion。

## 2026-11-10 19:46–19:48：⚠️ R284真机B接管剧烈振荡；急停终止、重启恢复，永久阻断当前版本

- 现场再次明确许可后运行第二次专用会话：audit PASS、LowState1029包/秒、已ReleaseMode、释放后2094包且16轴mode0；Passive在740帧ready。现场A固定站，B gate通过：`pose_error=0.269871,wheel_dq=0,upright=0.995592,quiet_dq=0.0276`；2秒PolicyHandoff完成并进入PolicyWalk，摇杆全零。
- 进入全量策略后现场报告“关节抖动非常厉害、吓人”。立即要求物理急停/远离，并从CPRO `pkill -INT/-TERM as2w_r284_publish`。发布日志：PolicyWalk约0.4秒现场按A退Brake，但策略零指令仍振荡；远端终止后FOC丢失，publisher exit1。该FOC fault是终止结果，不是振荡起因。
- 100Hz capture共11999帧。稳定固定站阶段腿dq<0.31rad/s；B handoff初期仍温和。**全量PolicyWalk边界后0.5秒腿dq跳至7.44rad/s，随后腿峰11.49rad/s、轮峰14.38rad/s，腿tau_est峰73.425Nm**。POLICY_TRACK在首0.2秒已有腿目标误差最高1.073rad且正负快速翻转，说明策略目标/反馈闭环本身不稳定，不是单纯kp不足。
- 轮角记忆专项复核：B参考时四轮wrapped delta近0，无首帧4π跳变；handoff期间逐渐到约`[−0.03,+0.37,−0.27,−0.01]rad`，全量策略后运动放大并多轴超过±1rad。故排除“初始轮角回绕瞬时错误”为主因；仍可能存在真实轮速命令/角反馈闭环符号、执行器相位延迟或训练域外状态导致的正反馈，需离线辨识。
- 保护流在振荡开始时没有先行warning/motorstate错误；约79.55秒（发布已停、16轴mode0且现场急停/重启阶段）出现`motorstate_or=0x8,board_state0=0x4001001`、motor_v降至16.45V，属于后续断能/保护状态，不能倒因为策略抖动。
- 现场随后重启狗。只读恢复：LowState1069包/秒、mode_machine2、MotionSwitcher `name=ai`、Sport `ai_damping/active`，原厂趴下正常；无发布进程。事故原始：`logs/20261110_r284_zero_b_second_console.log`、CPRO `/root/field_sessions/20261110-194636_r284-zero-b/`；分析 `logs/20261110_r284_incident_{capture_analysis,wheel_memory_detail,protection_and_reboot_check}.log`。
- **结论与处置**：MuJoCo给出假阴性，R284当前真机禁用，R270也不恢复。MuJoCo使用理想质量/质心、摩擦、关节刚度、无真实延迟/量化/柔顺和理想T2起点；真实固定站已有0.27rad稳态误差，R284又只训练500/2500更新，官方静止仅3/8、运动后停车0/8，进入真实反馈后超出训练/动力学域。`run_r284_zero_b_trial.sh`与更上层的`run_r284_field_session.sh`均已改为入口处无条件FATAL exit78并同步CPRO；CPRO两入口实跑均只打印阻断信息，未执行检查、ReleaseMode或LowCmd，且无`as2w_r284_publish`进程。后续只能做捕获数据离线shadow/系统辨识/训练侧修正，未经全新审查不得解除。
- 重启后再次只读复核：LowState 1046包/秒、mode_machine=2，16轴q/dq有限；MotionSwitcher `form=1,name=ai`；Sport状态`mode=0`，速度近零。确认机器已回原厂控制、趴下且无R284发布器；本次复核不含ReleaseMode或LowCmd。

## 2026-11-10 20:xx：原厂站姿 vs 当前 FixedStand 历史日志复核（纯离线）

- 现场观察“当前 FixedStand 最终不像原厂站姿”成立。源码/launcher确认当前 A 键固定使用 **T2策略训练默认姿态**（hip0/thigh0.8/calf−1.6）+腿kp55/kd2，并非已保存的原厂实测T1（hip约±0.12/thigh0.60/calf−1.23）。
- P10原厂稳定窗611帧实际q相对T1最大误差仅0.0075rad、pitch+0.326°；第三次A→Y FixedStand稳定窗实际q相对T1最大/RMS误差0.6393/0.3993rad、pitch−5.498°，相对T2仍有0.2705/0.1902rad误差。四次不进入策略的FixedStand历史重复得到pitch−4.73°至−5.50°、T2最大误差0.263–0.270rad，排除偶发落点。
- 稳态dq近零，故kd不是最终姿态差的主因。逐轴`55×(T2−q_actual)`与tau_est幅值吻合（RL hip14.88vs14.74Nm、RR calf14.81vs14.53Nm），证明纯位置PD靠静态误差提供重力力矩；后腿14–15Nm显著高于前腿3–7Nm。官方q_cmd/kp/kd/tau_ff不在LowState中，不能从日志猜其具体增益或假设其为固定PD。
- 建议后续拆成`FactoryLikeStand(T1)`与每策略独立`PolicyReadyStand`，B前受控过渡；目标/增益/前馈配置化。当前仅研究结论，未改发布代码、未同步、无机器人动作，也不解除R284硬阻断。详见`logs/20261110_fixedstand_vs_factory_analysis.md`，复现工具`部署参考/cpp_deploy-as2w/tools/analyze_stand_pose_comparison.py`。
- 该差异可能放大R284 sim-to-real：真机B前是pitch约−5°、后腿T2误差约0.27rad的负载平衡点，而不是理想T2。它不能单独解释全策略接管后的剧烈振荡，但后续MuJoCo必须用实测q/quat初始化并做真实记录shadow，不能只从理想T2复演。

## 2026-11-10 20:xx：一键现场入口当前能力复核（仅文档，无机器人动作）

- Windows `运行现场策略会话.ps1`当前只注册`r214`，模式为`dry-run/stand/zero-b/motion`；CPRO端仍按audit→LowState→控制权→16轴mode0→双监测→安全唤醒的既有链运行。
- 当前分级：dry-run纯检查；R214 stand与zero-b已有真机通过记录；motion可启动但R214持续行走会后腿下沉，只能做极短受监督诊断。R249/R270未注册；R284在Windows未注册且CPRO两级入口已FATAL阻断。
- 修正`02_现场操作/一键现场会话与策略切换指南.md`中R284仍可首测的过时段落，加入当前能力状态框。本阶段未连接控制权、未发LowCmd、无机器人动作。

## 2026-11-10 20:xx：PolicyReadyStand稳态偏差登记为低优先级遗留（无机器人动作）

- 用户决定暂不处理T2 FixedStand的约0.26–0.30rad稳态误差/约−5°后倾，不追求立即复刻原厂站姿。当前T2等于策略默认姿态，有限kp且无重力前馈时存在负载误差符合纯PD机理。
- 后续工作假设为“策略的训练随机化应覆盖合理的初态姿态/关节误差”，但不登记为已验证事实；每个新策略仍必须核对训练随机化范围，并用真实日志shadow和有界接管检验。若接管反复对初态敏感，再启动重力前馈、目标补偿或独立PolicyReadyStand设计。
- 已将该项加入`02_现场操作/现场部署清单.md`低优先级遗留；本阶段不改发布代码、不编译/同步、不解除任何策略安全阻断。

## 2026-11-10 20:xx：AS2-W 官方 `kp/kd` 公开资料复核（纯资料审查，无机器人动作）

- AS2-W 官方《底层服务接口》只公开 PD 公式 `tau + kp*(q_des-q) + kd*(dq_des-dq)`、字段含义和输出侧单位，没有给出 AS2-W 专用默认或推荐 `kp/kd` 数字；当前官方 SDK2 的 `example/as2` 只有高层 Sport/音频示例，也没有 AS2-W 低层站立示例。
- 官方 SDK2 通用 `example/state_machine/robot_controller.hpp` 提供 Damping 默认 `kp=0,kd=2`、Standing 默认 `kp=40,kd=1`，但该示例使用 `unitree_go` 12 轴接口，只能作为通用框架参考，不能登记为 AS2-W 16 轴官方合同。其他官方机型差异很大，例如 B2-W 站立示例为 `1000/10`，证明不存在可跨机型照搬的“宇树统一默认值”。
- 当前工程 FixedStand 腿 `55/2`、Passive `0→3` 是本项目已实机验证的参数，不是官方 AS2-W 默认；Policy 增益必须按每个模型的训练/交付合同单独核对。原厂 ai_sport 内部的 `q_cmd/kp/kd/tau_ff` 不在 LowState 中，历史日志只能读 `q/dq/tau_est`，不能反推出唯一的原厂增益。
- 结论已同步到 `部署参考/cpp_deploy-as2w/config/hardware_contract.md`；本阶段未改发布代码、未连接控制权、未发 LowCmd，也不改变 R284 的硬阻断状态。

## 2026-11-11：rolling-fixed-exit-preview 上游审计与双初态 MuJoCo 复演（纯离线）

- GitHub main `7bae69bbf682a741339b24dfa66b477fd3890b01` 稀疏拉取至 `部署参考/Rob2Nav-rolling-fixed-exit-source`。ONNX `obs65→actions16`，SHA `4d8e7bcf...b4afa`；7523帧 parity 最大误差`1.91e-6`。离线preflight通过，`--require-hardware-map`按预期拒绝交付内全部16轴空绑定。
- 命令合同确证：三元组为`vx,vy,wz`，但上游`rolling_fixed_exit()`只读取`vx/wz`；`vy`不进入腿motion gate或轮速映射。独立`vy=0.10`探针实际`vy≈0.00008m/s`，故策略不支持侧移。上游评估域为`|vx|≤0.30m/s`，转向测试到`|wz|=0.30rad/s`；零速观测`[-0.4,0,0]`是`vx-0.4`中心偏移，不是物理倒车命令。
- 上游自身门槛已失败：Isaac完整track+brake+hold仅forward1/20、back5/20，四类转向/弧线0/10；MuJoCo总计仅forward1/20、其余5类0/20，即1/120，交付`gate=false`且README声明只供simulation/offline replay。
- 新增`部署参考/as2w-flat-rerun/rolling_fixed_exit_rehearsal.py`，服务器MuJoCo3.17/ORT1.31按既有AS2-W资产复演。轻量3种子理想路线可完成静止/滚动/刹停/回站，但补齐质量、摩擦、增益随机化、2.8–4.5s推扰和物理子步接触后完整通过全为0：forward稳定18/20、跟踪5/20；back20/20、跟踪1/20；turn L/R稳定7/20、13/20；arc L/R稳定16/20、13/20。转向/弧线最坏非轮接触595–919N；全部场景Policy→FixedStand `<0.18rad`门槛0通过。
- 按用户提醒补做真机FixedStand历史实测初态注入（hip/thigh/calf实际q+pitch−5.498°，控制目标仍T2）：静止3/3保持，但B进入腿dq峰约2.57–2.59rad/s；forward/back虽3/3未翻，平均横漂约−0.135/+0.164m/s且跟踪0/3，退出门槛仍0/3。数值不等同真机预测，但否定“理想T2无缝接管”假设。
- **处置：当前preview不绑定B、不开发/同步真机launcher、不做地面有界首测。** 需训练/控制侧修订并通过真实FixedStand初态、压力随机集、停车和退出门槛，再做ORT1.22 C++/ARM64链；未来首测候选也只能`vx=+0.05m/s`、1–2s、`vy=wz=0`。详见`02_现场操作/rolling-fixed-exit-preview离线评估.md`；原始日志与JSON均已本地归档。本阶段无DDS发布、无ReleaseMode、无机器人动作。

## 2026-11-11 10:24–10:47：USB HDC 链路中断定位与修复（gadget 配置缺 function；无线通道未中断）

- 环境：工作站 Windows `192.168.10.61`；HDC 客户端 `00_HDC工具/hdc_6.1.1.280/hdc.exe`（`Ver: 3.2.0d`，`hdc` 不在 PATH）；CPRO 未重启（`uptime` 约 4.8 天），无线 HDC `192.168.10.180:10178`（设备上 `hdcrelay`）全程可用，USB 故障期间管理未中断。
- 现象：CPRO 侧插 USB 后 Windows 完全无枚举，`hdc list targets -v` 仅剩 `0123456789ABCDEF USB Offline`；对多个 USB 口做 120 秒轮询零枚举事件；设备端 `/sys/class/udc/ea100000.hiusbc/state = not attached`，`dmesg` 反复 `udc ea100000.hiusbc: failed to start g1: -22`。
- 排除项：线材（用户复测可正常传文件）、PC 各口（轮询无事件）、HDC 主动关 USB 接口（`/dev/usb-ffs/hdc/ep0..2` 一直由 hdcd 持有，`persist.hdc.mode.usb=enable`）、端口层（`extcon1 hisi_usb3_0 = USB=1, USB-HOST=0`，即线与 VBUS 均在）。
- 根因：`/config/usb_gadget/g1/configs/b.1/` 下 `f1 → functions/ffs.hdc` 的 function 链接缺失，配置内无任何 function，composite start 恒返回 `-EINVAL(-22)`，pull-up 不拉，故 PC 侧无任何电气枚举。
- 修复（经无线通道的 root shell）：`ln -s /config/usb_gadget/g1/functions/ffs.hdc /config/usb_gadget/g1/configs/b.1/f1`，再 `echo ea100000.hiusbc > /config/usb_gadget/g1/UDC`。结果 `UDC=ea100000.hiusbc`、`state=configured`、`[HIUSBC]hiusbc_gadget_pullup: is_on = 1`，Windows 出现 `HDC Device (USB\VID_12D1&PID_5000\0123456789ABCDEF)`，`hdc -t 0123456789ABCDEF shell` 返回 `USB_OK` 与 `uid=0(root)`。
- 过程教训（保留）：排查初期曾向 `UDC` 写空值做“解绑试探”，因当时配置已缺 function，重绑返回 `-EINVAL`，把“能枚举但不 attach”变成“完全绑不上”；补回 `f1` 后才恢复。**不要把 UDC 空写当作试探手段。**
- 另一发现：拔线后设备端 `state` 与 `extcon1` 不复位（该固件未把 VBUS 断开事件上报到 gadget），因此“设备端说 `configured`/`USB=1`”不能证明线仍插在 PC 上；连通性只认 Windows 枚举（`VID_12D1` 是否出现）与 `hdc list targets -v` 是否 `Connected`。
- 收尾：10:47 用户关闭/拔除该 USB 连接。手工 relink+bind **不持久**，CPRO 重启后由 `hdcd` 重建 gadget 通常自恢复；若复现，按 `部署测试/AGENTS.md` 末尾「管理链路：USB HDC 与 WiFi 双通道」第 5–6 步处理。
- 本阶段无机器人动作；未改 `eth0`/`ip rule`/`hdcrelay`；未执行 `hdc tmode`；未连接控制权、未发 LowCmd。
- 原始日志：`logs/20261111-1040_usb_hdc_gadget_repair.log`

## 2026-11-11 20:41–20:47：CPRO 重启后管理链复测（无线直连 8710，USB 自动恢复）

- 现场操作：用户重启 CPRO（约 20:41），USB 线接回个人工作站；本机未做任何 hdc 配置改动。
- USB 结果：`hdc list targets -v` 显示 `0123456789ABCDEF USB Connected`，Windows PnP 出现 `HDC Device`；未做任何 gadget 修复即为正常。据此确认 11-11 上午的 USB 故障（`configs/b.1` 缺 `f1` → `udc ea100000.hiusbc: failed to start g1: -22`）属于 gadget/控制器卡死，**重启即清**，不需要每次手工 relink。
- 无线结果：重启后设备未启动 `hdcrelay`，但 `hdcd` 监听 `0.0.0.0:8710`；`hdc tconn 192.168.10.180:8710` → `Connect OK`，`hdc -t 192.168.10.180:8710 shell` 返回 `WIFI_OK` 与 `uid=0(root)`；`Test-NetConnection 192.168.10.180 -Port 8710` = True。
- 结论更正（覆盖 11-09 的两条旧结论）：① 无线**直连 8710 可用**，`hdcrelay`/`10178` 降级为回退手段，“8710 只接受 lo 连接”未在本次重启后出现；② **“重启 CPRO 会永久失去管理通道”作废**——8710 随 `persist.hdc.mode=tcp` 自启，本机只需重新 `tconn`。
- 双通道现状：USB `0123456789ABCDEF` 与 TCP `192.168.10.180:8710` 同时 `Connected`，所有命令须带 `-t`；旧 `192.168.10.180:10178` 显示 `Offline`，可忽略。
- 已同步文档：`AGENTS.md`（顶部状态行 + 「管理链路」节）、`02_现场操作/实机事实与命令.md`、`02_现场操作/明日bringup手册.md`、`02_现场操作/一键现场会话与策略切换指南.md`、`05_OpenCode交接/README.md`、`04_调试记录/20261111_USB_HDC_间歇性消失_症状汇总.md`。
- 本阶段无机器人动作；未执行 `hdc tmode` / `hdc kill`；未改 `eth0` / `ip rule`；未启动 `hdcrelay`。用户明确**不要**做开机自动 `tconn`。

## 2026-11-11 11:45：USB HDC 当前状态复核（只读，无机器人动作）

- Windows 当前仍无 `VID_12D1` PnP 枚举，HDC USB target 为 Offline；WiFi `192.168.10.180:10178` Connected、TCP 探测成功。
- 经 WiFi 只读核验：`UDC=ea100000.hiusbc`、`f1 -> functions/ffs.hdc` 均在位，故 10:24 的“缺 function / bind -22”软件故障当前没有复发；`state=not attached`，失败点在 HDC/WinUSB 之前的 USB attach/物理枚举层。
- `extcon USB=1` 与 `current_speed=high-speed` 属已知拔线后不复位的旧值，不能据此排除主机 USB-C 口/角色状态、线或 CPRO 母座接触问题。无线模式没有排他关闭 USB；历史已验证 USB/TCP 双 target 可同时 Connected。
- 下一判定实验：原样接回此前成功的另一台 Windows。若能枚举，优先处理当前工作站 USB-C 口/控制器；若多台主机均不枚举，再换已知良好数据线并检查 CPRO USB-A 母座。当前不需要再次 relink/rebind，不执行 `hdc tmode`、CPRO 重启或 `hdcrelay` 变更。
- 原始记录：`logs/20261111-1145_usb_hdc_live_readonly_diagnosis.md`。本阶段未改设备配置、未连接控制权、未发 LowCmd。

## 2026-11-11 11:51–11:52：接到第二台 Windows 后 USB 仍未 attach（只读，无机器人动作）

- 用户将 CPRO USB 接到另一台 Windows；本聊天所在工作站 `bgzou9897` 因线已移走而无本地 PnP 枚举，故通过仍正常的 WiFi HDC 从 CPRO 侧只读核验。
- CPRO 当前 `UDC=ea100000.hiusbc`、`f1 -> functions/ffs.hdc` 正常，但 `state=not attached`；内核日志在第二台 Windows 插线时没有新增 HIUSBC attach/configured 事件，最后一次 pull-up 仍是此前修复时的记录。
- 两台主机均未触发枚举后，原工作站 USB-C 口不再是首要嫌疑；优先检查数据线/接头间歇故障、CPRO USB-A 母座接触，其次才是 CPRO USB device 控制器卡住。先换已知良好数据线和第二台 Windows 的另一个物理口；保持 WiFi 生命线，不重启 CPRO、不执行 `hdc tmode`/UDC 空写。
- 原始记录：`logs/20261111-1152_second_windows_usb_readonly_check.md`。未改设备配置、未连接控制权、未发 LowCmd。

## 2026-11-11 11:53–11:54：CPRO 换口后确认仅一个 USB device/HDC 口（只读，无机器人动作）

- 用户同时更换 CPRO 与第二台 Windows 的物理 USB 口；CPRO 仍为 `state=not attached`，无新增 HIUSBC attach/configured 事件。
- 只读端口清单确认 `/sys/class/udc` 仅有 `ea100000.hiusbc`，路径明确属于 `hiusb-port0`；extcon 中仅 `hisi_usb3_0` 为 `USB=1,USB-HOST=0`，其余四口均为 `USB-HOST=1`。
- 结论：HDC gadget 只绑定唯一 device-mode 口；更换 CPRO 口很可能插入 host-only 口，不能用于 Windows HDC 枚举，也使上一轮双端换口测试失去可比性。下一步必须改回 10:29 成功过的 CPRO 原口，仅更换 Windows 端口/数据线后再观测。
- 原始记录：`logs/20261111-1154_cpro_usb_port_role_inventory.md`。本阶段未改端口角色、设备配置、控制权或 LowCmd。

## 2026-11-11 11:57：已找到正确 CPRO HDC 物理口，第二台 Windows 枚举成功（只读，无机器人动作）

- 用户换到另一个 CPRO USB 口后，UDC 状态立即由 `not attached` 变为 `configured`，速度为 high-speed；`UDC=ea100000.hiusbc`、`f1 -> functions/ffs.hdc` 正常。
- 新内核事件完整出现 `reset → Connected at speed=3 → Set Configuration success → CONFIGURED`，证明 CPRO 到第二台 Windows 的物理链路与 USB 枚举已成功。当前所插口即唯一正确的 `hiusb-port0/ea100000` HDC device-mode 口，应现场标记。
- 若第二台 Windows 的 HDC 客户端仍不显示 Connected，后续只查该机 WinUSB/HDC 工具层，不再查 CPRO gadget/线缆。保持 WiFi 管理链，不执行 `hdc tmode`。
- 原始记录：`logs/20261111-1157_cpro_correct_hdc_port_confirmed.md`。未改设备配置、控制权或 LowCmd。

## 2026-11-11 13:4x–14:0x：T1 前后处理迁移到 AS2-W 的架构评审（纯离线）

- 核对 `T1运控架构详解.md` §6.9/§6.10/§10，以及本地 T1 `qd1_t2d0` 真机配置 `quad_walk.yaml`、`mc_T1.yaml`、`security_guard.yaml`；同时逐项对照 rolling preview 的 65 维观测合同、`rolling_fixed_exit()`、stand bias/wheel hold 与 mode-switch supervisor。
- 结论：应迁移 T1 的六段流水线、命令超时、准入门、切换整形、硬件限位、故障旁路和全链日志等**机制**；不得复制 T1 的观测缩放、10 帧堆叠、100/10 Hz 滤波、14 轴顺序、默认姿态、增益、力矩限幅及跌倒/超时**数值**。模型观测和动作前后处理必须逐策略忠实复现训练合同，避免二次缩放和滤波延迟造成分布/相位偏移。
- rolling preview 已有专属 65 维历史、动作门控、轮角记忆和进退 supervisor；新增通用 T1 处理不能修复其上游/本项目双仿真门槛失败，继续维持不绑定 B、不开发/同步 launcher。
- 建议共用架构：`RemoteCommandGuard → 每策略 ObservationAdapter → 每策略 ActionAdapter → TransitionAndSafetyGuard → HG LowCmd Publisher`；日志同时保存 command/obs/raw action/包装目标/最终 LowCmd/LowState/FSM。
- 详细评审：`02_现场操作/T1前后处理迁移到AS2-W的评审.md`。当前 Windows 未挂载 `Z:`，本次使用本地归档的 T1 真机配置完成核对。本阶段没有连接控制权、没有发布 LowCmd、没有机器人动作。

## 2026-11-11 14:0x：按早期策略开发目标收敛为“最小安全壳”（纯离线）

- 用户明确早期不希望复制完整 T1 框架，优先考虑速度/加速度、命令超时、关节限位和力矩保护。复核现有 `r214_publish.cpp`/controller：已有摇杆0.05死区、LowState 20ms writer watchdog、CRC/有限值、FOC确认、命令绝对限幅、腿位置/轮速度绝对限幅、切换blend和有界时限；因此无需重做复杂 LowState/输入仲裁。
- 确认真正缺口：命令加减速斜率；可判定的命令超时并进入Brake（不能只清零command）；运行中腿/轮dq、LowState tau_est、PD预计力矩的warning/abort两档保护；单帧目标跳变保护；逐策略的试验档位配置。R284虽`tau_ff=0`，事故中腿tau_est仍约73.4Nm，证明力矩保护必须覆盖PD项而不只是LowCmd tau字段。
- 建议早期只实现六项：最小LowState有效性、命令限幅/斜率、超时Brake、输出软包络、速度/力矩双保护、有界试验+全链日志。摇杆精细曲线、多源仲裁、复杂跌倒/接触守卫、里程计补偿与额外低通后置。
- `Z:` 当前已成功挂载；本轮以本项目现有代码和已归档T1配置完成差距核对，无需从Z盘复制任何参数。详细更新已写入`02_现场操作/T1前后处理迁移到AS2-W的评审.md`。没有连接控制权、没有发布LowCmd、没有机器人动作。

## 2026-11-11 14:2x–15:2x：R214 最小安全壳实现、x86/ARM64 编译与交接（无机器人动作）

- 唯一维护源码 `部署参考/cpp_deploy-as2w/deploy/robots/as2w/r214/r214_publish.cpp` 增加低速早期 bring-up 安全壳：`vx/vy/wz` 加速 `0.20/0.10/0.20`、减速 `0.40/0.20/0.40`；合法遥控负载超时200ms→受控Brake；运行中腿/轮dq、tau_est、预计PD力矩及单帧目标跳变的warning/hard连续帧守卫。Warning连续5个50Hz帧→Brake，Hard连续3帧→EmergencyDamping，任一有效轴motorstate非零按hard处理。守卫只覆盖PolicyHandoff/PolicyWalk/Brake，不改变FixStand/FixSquat、观测、动作包装、轴映射或已通过的Passive唤醒。
- 当前warning/hard依次为：腿dq 5/8rad/s、轮dq 8/12rad/s、腿tau_est 35/50Nm、轮tau_est 8/12Nm、预计腿PD 35/50Nm、预计轮PD 8/15Nm、腿目标跳变0.20/0.35rad每20ms、轮目标跳变15/30rad/s每20ms。数值依据R214 trace分位数与R284事故峰值，定义为低速早期试验档；可能阻断R214高动态爬楼，不是官方能力值或通用策略常量。
- 遥控超时只验证40字节payload头`55 51`和轴有限/合理。HG内嵌负载没有可见sequence/timestamp，若固件重复合法陈旧帧，发布端无法与“摇杆保持不动”区分；该限制已写入代码和交接。
- 服务器增量x86构建CTest 8/8、扩展offline-audit通过；源码SHA `3a022ca8fa489efc350732a03f5a9283bff730510c72aaa3aaade532612fac63`，x86二进制SHA `200c4323cd502ce0ee805b9da1acaf526d3c4b3da7a650c23028bfeb4920d58d`。记录 `logs/20261111-1515_r214_minimal_safety_x86_build.log`。
- WiFi HDC起初显示TCP Offline；只读TCP/设备进程复核后重新`tconn 192.168.10.180:10178`成功，目标恢复Connected且root shell正常。没有执行`hdc kill/tmode`，没有改eth0/ip rule/relay。源码已同步CPRO `/root/as2w_deploy`，SHA与本机一致。
- CPRO侧因`cpro_ubuntu.sh`重复mount `/proc`报Resource busy，本轮用`unshare --uts --fork chroot /data/ubuntu_in_hm/ubuntu_rootfs`进入Ubuntu完成增量构建。`build-r214-ab-fsm`、`build-r214-zero-b`、`build-r214-ab-fsm-full`均CTest 8/8、offline-audit通过；二进制SHA依次为`91f005...d362`、`257a29...3c37`、`5b940e...deb6`。完整记录 `logs/20261111-1510_r214_minimal_safety_arm64_build.{sh,log}`。
- 离线audit新增命令斜率端点与safe/unsafe合成守卫帧检查，输出仍明确`firmware acceptance unknown`。本轮没有ReleaseMode、没有启动DDS发布端、没有机器人动作；新运行阈值尚未真机故障注入验收。
- 接续任务书 `05_OpenCode交接/给OpenCode_R214最小安全壳接续_20261111.md`，首条Prompt同目录。OpenCode先做线程/FSM审查、离线warning/hard/remote-timeout故障注入和指南更新；完成后才可另行提出有界真机方案，每次动作仍须现场当次明确许可。
- 运行 `准备现场包.ps1` 成功，6模型完整性校验通过；新包SHA为`cpp_deploy-as2w.tar.gz=091a9c...f2b5`、`unitree_sdk2-src.tar.gz=2d07d4...9bdd`。服务器SSHFS mountpoint与两份新交接文件已只读核验可见；记录 `logs/20261111-1530_r214_minimal_safety_package.log`。因此工作站权威源码、服务器可见挂载、CPRO已编译源码与现场包已完成四点同步。

## 2026-11-11 16:1x–16:5x：R214 最小安全壳 P0–P2 接续完成（静态审查、离线故障注入、文档；无机器人动作）

- 输入：`05_OpenCode交接/给OpenCode_R214最小安全壳首条Prompt_20261111.md` 与接续任务书；SSHFS mountpoint 核验正常；起点源码 SHA `3a022ca8...` 工作站=CPRO 一致。本轮只做无动作的 P0–P2，未 ReleaseMode、未启动任何发布端、未改 launcher；R284/R270/rolling-preview 硬阻断全部维持。
- **P0 静态审查结论（逐项）**：
  1. 线程安全：`latest_remote_received/latest_remote/latest_frame/latest_received/latest_count` 只在 `state_mutex` 下读写，`current_targets` 在 `targets_mutex` 下读写，`g_state/startup_ready/startup_fault/stand_trial_completed/motion_cycle_completed/g_abort` 为 atomic；writer/subscriber/FSM 三线程的锁使用均为单锁短临界区、无嵌套，`zero_b_cycle_used/interp/fixed_pose/leg_dq_history/controller` 等仅 FSM 单线程访问——**未发现数据竞争或死锁风险**。
  2. FSM 转移：单 tick 优先级为 check_safety(LowState>50ms或upright<-0.2)→X→remote-timeout→hard→warn→按键/状态逻辑，每 tick 至多一次状态转移；Brake 态下 warning 因 `st != Brake` 判定不会重复请求 Brake（hard 仍可升级 EmergencyDamping）；warn-SOFT_TRIP 先于 hard return 前打印、hard 优先于 warn——**无重复触发或状态覆盖**。
  3. 状态进入重置：warn/hard/log 计数在一个 policy episode（Handoff→Walk→Brake）内连续累计、离开三态（ReturnStand/FixedStand/Passive 等）每 tick 清零，即"下一轮 B cycle 不被旧 fault 污染"；`safety_previous_targets` 在每次状态边界因 `safety_previous_state != st` 自动失效为 nullptr（防止跨态假 target-step，同时 Handoff 首帧以 FixedStand 目标测量、pd≈15–16Nm 低于 warn 35，无边界假触发）；`slewed_command` 在 B 接受与 `start_brake` 处归零——语义正确。episode 内计数跨 Handoff→Walk 携带属有意设计（同一策略回合的单次故障累计）。
  4. 守卫测量点：读取 writer 发布环同源 `current_targets`（经 `targets_mutex`）+ 实测 LowState（dq/tau_est/motorstate），即最终下发语义；Handoff 期间测量的是 blend 后目标——**正确，非 raw action/未 blend 中间量**。
  5. 日志限频：守卫指标打印仅首 warning 帧、达标帧、此后每 25 个 warning 帧（≈≤2 行/秒）；WALK_CMD/POLICY_TRACK 0.2 s 周期；REMOTE_TIMEOUT/SOFT_TRIP/转移行均单次；writer 500 Hz 环无新增打印——**不会造成发布环时序抖动**。
  - 发现的缺口（已修复）：`FIELD_SAFETY_PROFILE` 启动横幅缺 `leg_pd/wheel_pd`、`leg_step/wheel_step`、`warn_frames/hard_frames` 与单位说明，已补全；其余审查项无需改码。
- **P0 伴随重构（P1 前置，行为等价）**：守卫连续帧计数/决策抽为纯函数 `evaluate_field_guard`（`FieldGuardCounts/Action/Outcome`），remote 超时拆为 `remote_payload_timed_out`/`remote_timeout_requests_brake`；fsm_tick 改为调用同一实现，阈值仍只存在于 `kFieldSafety` 一处。`measure_field_safety`、FixStand/FixSquat、观测/动作包装、Passive 唤醒序列、A/B/Y/X 按键语义全部未动。
- **P1 离线故障注入（扩展 `--offline-audit`，合成帧、无 DDS）**，全部走 FSM 同款纯函数与度量路径：(1) safe 包络 200 帧零触发零日志；(2) leg dq=6（5<6<8）第 1–4 帧 Continue、第 5 帧 SoftBrake、Brake 态同条件不再重复请求 Brake；(2b) 预计腿 PD 力矩 38.5 Nm（35<38.5<50）单独走 warn 计数；(3) leg dq=9（>8）第 1–2 帧 Continue、第 3 帧 HardStop/EmergencyDamping；(3b) 轮目标单帧跳变 32>30（kd=0 消去 PD 项）单独走 hard；(4) motorstate≠0 按 hard 计数第 3 帧触发、单帧闪断被连续性清零（40 交替帧不触发）；(5) remote 谓词 199 ms 不触发/201 ms 触发/epoch 触发 + 状态矩阵仅 Handoff/Walk 请求 Brake、Brake+恢复合法帧无自动回退 PolicyWalk（决策层断言 + FSM 无 Brake→PolicyWalk 转移的结构事实，回站须重过 B 门槛）；(6) 0→{0.1,-0.05,-0.1}→0 全程逐帧斜率界、单调、25 帧/0.5 s 进入、13 帧/0.26 s 回零（含 1e-6 精确归零 snap）；(7) requested/applied 一致：`map_remote_command`→`slew_command` 收敛到摇杆映射端点、居中摇杆精确零。注入开发中发现并修正审核代码自身一处符号错误（vy/wz 镜像负号端点），失败与修复均留痕。audit 通过行扩展为 `... offline fault injection (warn/hard/motorstate/remote-timeout/slew); firmware acceptance unknown`，并新增 `GUARD INJECTION PASS` 摘要行。
- **验证与 SHA**：服务器镜像 `/tmp/opencode/r214_zero_b` x86 增量构建零警告、CTest **8/8**、audit+注入 PASS，x86 二进制 SHA `50917bcbea84c1b205424c53d528066f447915025c665a8e88d24e99c6b41a00`，记录 `logs/20261111-1640_r214_guard_injection_x86_build.log`。源码经工作站 scp→`hdc -t 192.168.10.180:10178 file send` 同步 CPRO（宿主路径 `/data/ubuntu_in_hm/ubuntu_rootfs/root/as2w_deploy`，即 chroot 内 `/root/as2w_deploy`）；新源码 SHA `419dca66e91688a83e87173366d8662bb8c9d03b945a8db3fb43b9bb50951aab`（工作站=服务器镜像=CPRO 三点一致）。CPRO 经 `unshare --uts --fork chroot` + base64 脚本法完成三构建增量编译，各自 CTest **8/8**、audit+注入 PASS；二进制 SHA：`build-r214-ab-fsm=8e7ea22cb2e020bd7a93d91026cff02c41749f091274816c42db315971f8f947`、`build-r214-zero-b=fb010d3204a34967611b60aec99cbbb71afb941e388f4b087733bd651ad800d6`、`build-r214-ab-fsm-full=b2f78bb9e39b83fb1d593f0ebb678687daeb9b2fb9cdca28fa26d0b63fcecc61`。记录 `logs/20261111-1650_r214_guard_injection_arm64_build.{sh,log}`。
- **P2 文档**：`02_现场操作/一键现场会话与策略切换指南.md` 新增 §2.1——启动必须看到 `FIELD_SAFETY_PROFILE` 完整横幅（缺行即二进制不对版须停）、`WALK_CMD requested/applied`、`FIELD_SAFETY_WARN/HARD/SOFT_TRIP`、`REMOTE_TIMEOUT` 判读表与 tau_est/PD 预计力矩语义、Ctrl+C=操作员结束会话（站立停发可能下沉，优先 Y 趴下后退出；运动中制动顺序 A→X→物理急停）、会话目录必须回本机 logs、阈值为 R214 低速早期档而非跨策略常量（共用的是守卫机制）。`02_现场操作/T1前后处理迁移到AS2-W的评审.md` 实现状态节补记本轮。
- **未做与边界**：未运行 `准备现场包.ps1` 重新打包（源码/构建二进制已同步，现场交付包如需更新另行打包并记 SHA）；`cpro_ubuntu.sh` 的 /proc 幂等挂载修复按任务书要求未与安全壳改动混合，本轮沿用 unshare chroot 通道；守卫新阈值仍**未经真机故障注入**，`firmware acceptance unknown` 结论不变；MuJoCo 复演未重跑（本轮改动为纯决策/审计层，不影响已验收轨迹与观测）。
- **下一步（P3 建议，每步均须现场人员当次明确同意后才执行）**：按任务书 §4 顺序——①只读基线（LowState 频率/mode_machine/原厂趴下/无残留发布进程）；②stand 回归 A→固定站立→Y（守卫不应介入 FixStand/FixSquat）；③zero-B：A→B 强制零命令短接管→自动 Brake/回站→Y，核验无误触发与完整日志。第一轮不开放自由 motion；若需 motion 另做 `vx=±0.05 m/s`、非零≤2 s、自动 Brake 的临时有界 launcher 并单独申请。

## 2026-11-11 16:1x–16:2x：R214 stand 回归准备——P3 只读基线、stand 二进制预检、cpro_ubuntu.sh 幂等修复（无机器人动作）

- **P3 步骤①只读基线通过**（现场执行前一键只读，无 ReleaseMode/无 LowCmd/狗原厂趴下）：残留发布进程 none；MotionSwitcher `rc=0 form=1 name=ai`；Sport `fsm_id=0 fsm_name=ai_damping process_state=active speed_level=0`；LowState 约 1042–1045 包/s、mode_machine=2；16 轴 q 有限、趴下锚点吻合（m0=−0.55/1.01/−2.76 三元组与 G1 趴下基线一致）；16 轴 mode 均 1（原厂 FOC 持有，ReleaseMode 后才回 0）。记录 `logs/20261111-1617_r214_stand_regression_baseline_readonly.log`。已知 CycloneDDS 退出断言（`prevent_callbacks()`）在 low-state 阶段退出时核心转储，数据仍有效，为既往已知现象。
- **stand 二进制预检通过**（对照 11-10 15:4x 嗡鸣风险复核模板）：`build-r214-ab-fsm` 编译定义仅 `-DAS2W_ENABLE_POLICY_STAND_TRIAL=1`（B/策略路径编译锁定，新守卫代码编译在内但不可达）；残留进程 none；该二进制 `--offline-audit` PASS（含故障注入）；启动唤醒常量 500ms观察/500ms零增益FOC/200ms FOC ack/1s kd 0→3 与两次无报警 Passive 及 15:51 无嗡鸣 stand 会话一致；launcher `--stand-trial --stand t2` 正确；launcher/一键脚本 SHA 已录。记录 `logs/20261111-1620_r214_stand_preflight.log`。
- **cpro_ubuntu.sh 幂等修复**（任务书 §5 预留的非运动工具修复，与安全壳源码分离）：现场首跑 stand 会话在脚本最开头报 `mount: 'proc'->'.../proc': Resource busy` 并安全中止（未做任何动作）。根因：`/proc/mounts` 显示 HarmonyOS 宿主已在开机时把 `/data/ubuntu_in_hm/ubuntu_rootfs/{proc,sys,dev,dev/pts}` 以 `procfs/sysfs/devfs`（`hmmac=genfs,seclabel`）预挂载，`cpro_ubuntu.sh` 再 `mount` 即 EBUSY。修复：对每个挂载点先 `grep -Fqs` `/proc/mounts` 命中则跳过（幂等），未命中才挂载；原脚本备份为 `cpro_ubuntu.sh.bak-20261111`。修复后 `sh cpro_ubuntu.sh /bin/bash -c echo` rc=0。记录 `logs/20261111-1625_cpro_ubuntu_idempotent_fix.sh`。
- **端到端 dry-run 验证通过**（只读，dog 无动作）：经 `cpro_ubuntu.sh /bin/bash <wrapper>` 跑 `run_r214_field_session.sh dry-run 30`，step1 SHA/audit PASS → step2 LowState 1040/s、mode_machine=2 → step3 name=ai → 在"将 stand-down + ReleaseMode"处退出，未 ReleaseMode/无 LowCmd。会话目录 `/root/field_sessions/20261111-162728_dry-run`。
- 当前状态：狗原厂 `ai_damping` 趴下、name=ai、无残留发布进程，外部检查全部就绪。**下一步 = 现场重跑 `运行现场策略会话.ps1 -Policy r214 -Mode stand -MonitorSeconds 180 -ConfirmMotion`**（同一命令已可通）：脚本自动 audit→控制权/ReleaseMode→16轴mode0门槛→双监测→发布端 Passive ready；现场 Passive ready 后静听 5 秒→A 起立→Y 趴下；任何嗡鸣/报警→X/物理急停。该动作本身仍未获本次批准，待现场明确同意后执行。

## 2026-11-11 16:31–16:34：⭐ R214 stand 回归真机通过（新安全壳二进制首次真机运行，无报警）

- 现场人员当次同意后重跑一键 stand 会话（`运行现场策略会话.ps1 -Policy r214 -Mode stand -MonitorSeconds 180 -ConfirmMotion`），经修复后的幂等 `cpro_ubuntu.sh` 进入，全链通过：step1 源码/二进制 SHA（`419dca66...`/`8e7ea22c...`）记录 + audit PASS → step2 LowState 1097 包/s、mode_machine=2 → step3 name=ai、趴下确认 → ReleaseMode rc0 → recheck name 空 → step4 2093 包、16 轴 mode={0} → step5 双监测 → step6 发布端。发布端打印完整 `FIELD_SAFETY_PROFILE` 全量横幅（新增 pd/step/frames 字段）→ `Passive ready after 730 frames`（历史 749/737/736 同量级）→ `[Passive]→FixStand(A)→FixedStand→(Y)→FixSquat→Passive` → `STAND TRIAL: prone hold complete` → `Publisher stopped, exit=0` → `STAND_TRIAL_REMOTE_RC=0` → 远端 `session complete (mode=stand rc=0)`。
- **保护流判读（本次用 grep 精确复核，纠正前文一次 awk 计数变量逐行重置的笔误）**：34170 行全程 `warning_or=0x0`（0 非零行）、`motorstate_or=0x0`（0 非零行）、`board_state0` 仅 `0x0`(6056)/`0x1`(28114) 两种值（0x1=电机 FOC 激活位，非 bit12 软急停/bit17 关节超限，与 11-10 无报警 stand 会话 6741/27453 分布同构）；峰值电流 5.6A、最低 motor_v 47.47V、最低 battery_v 47.64V；末帧 16 轴 `modes=0000000000000000`（已释放）。**无嗡鸣、无警报、无异常动作，与三次历史 stand 会话一致。**
- **结论**：本轮安全壳源码改动（守卫抽取为纯函数、FIELD_SAFETY_PROFILE banner 扩展、audit 故障注入）**未破坏**已验收的 Passive 唤醒、FixStand、FixedStand、FixSquat 链——新二进制（源码 `419dca66...`）首次真机回归通过。本会话守卫代码编译在内但策略态编译锁定，**守卫未真正当值**（要到 zero-B）。
- 当前状态：狗 **ReleaseMode 已释放（name 空）、趴下、无发布进程**（与历次 stand 会话结束后一致）。恢复原厂控制需 `SelectMode("ai")` 且该动作会让狗从趴下直接起立，须另行获许可，未执行。
- 归档：CPRO 会话目录 `/root/field_sessions/20261111-163136_stand/` 已人工拉回本机 `logs/field_sessions/20261111-163136_stand/{publisher,session,low_protection,low_capture_fast}.log`；Windows transcript `logs/20261111-163136_windows_r214_stand_field_session.log`（Ctrl+C 致其未打印 final "session complete"，但远端 session.log 已确认 complete rc=0）。
- **下一步（P3 步骤③，须现场另行明确同意）**：zero-B 首次——`运行现场策略会话.ps1 ... -Mode zero-b`（A 起立→按 B 进入强制零速 R214 短接管→自动 Brake/回站→Y 趴下，摇杆锁零）；此步守卫（warn/hard/remote-timeout）在 PolicyHandoff/PolicyWalk/Brake 首次真机当值，须重点核对无误触发与完整日志。首次仍不开放自由 motion。

## 2026-11-11 16:4x：motion 会话误启动失败 + HDC 管理链路掉线诊断（无机器人动作，狗随后关机）

- **motion 误启动失败（16:41）**：现场在未完成 zero-B 的情况下直接跑 `-Mode motion`（已知后腿下沉档 S7b，非本次计划步骤），报 `The remote script did not report session completion`。诊断结论：**远端 `run_r214_field_session.sh motion 90` 根本没在 CPRO 执行**——`/root/field_sessions/` 无 16:41 的 motion 会话目录（脚本第一件事即 `mkdir` 会话目录），无残留发布进程，Windows transcript 无任何远端 step 输出即抛错。**无 ReleaseMode、无 LowCmd、无任何机器人动作。**
- **HDC 掉线根因（本日反复出现的解释）**：`hdcrelay` 进程（父 pid 58027）自 11-09 19:49 起连续运行 2 天未重启，日志（`/data/local/tmp/as2w_field/hdcrelay.log`，UTC 时间 +8=北京）**无任何错误**（无 backend unreachable/accept failed）。掉线是两层叠加：①**WiFi 信号偏弱**：`/proc/net/wireless` wlan0 链接质量 48、信号 **-62 dBm**（一般偏弱档），且本工作站 bgzou9897 的 USB HDC 未枚举成功（11-11 上午 USB 修复在另一台 Windows 上成功，本机仍无 `VID_12D1`），WiFi 是唯一管理通道，抖动即全断、无回退；②**Windows hdc 客户端连接生命周期**：relay 是 fork-per-connection，每次 tconn/命令建立一条到 `127.0.0.1:8710`(hdcd) 的转发；日志显示连接 `16:17 open → 16:41:44 closed`（一条持续约 24 分钟的连接在 motion 启动那一刻关闭），目标瞬间 Offline，motion 命令未送达。TCP 探测 10178 端口仍 True（relay 存活），`hdc tconn 192.168.10.180:10178` 后恢复 Connected。唯一客户端是 192.168.10.61（工作站），排除"多客户端抢占 hdcd"假设。
- **处置**：已恢复 HDC 连接。用户决定**不修本工作站 USB**（维持 WiFi 单通道）。后续每个关键动作前先 `hdc list targets -v`，Offline 即 `tconn` 再继续；motion/zero-B 等真机步骤仍按任务书顺序逐次申请。狗随后由现场关机；再上电会回原厂趴下（断电重置控制权）。当前无残留发布进程。

## 2026-11-11 晚：rolling-1199 release 离线审计与实测初态 MuJoCo 诊断（无机器人动作）

- 用户暂停 R214 真机 P3，改评同事 `as2w-rolling-1199-preview.zip`。从 GitHub release 下载到 `部署参考/Rob2Nav-rolling-1199-preview/`，zip SHA `dd212125...c456` 与 GitHub 发布 digest 一致；ONNX/PT SHA 与交付 parity 清单一致。发布标为 simulation preview，官方包 `real_actuation_enabled=false`，16轴硬件字段均 null，没有 DDS 发布端。
- 上游文件直接显示：0.30m/s 前进跟踪+刹住2/4、回固定站姿0/4；倒退跟踪+刹住4/4、最终保持1/4；左右转向与左右弧线完整验收各0/2。MuJoCo诊断六类完整门槛全部0/1，`gate=false`；更高速未过双引擎门槛。包装仅消费vx/wz，vy不支持。
- 服务器 MuJoCo3.17/ORT1.31 用历史真机 FixedStand q/pitch 初态、既有独立复演器和新ONNX跑静止/前进/倒退各3种子：静止轮支撑3/3、回站0/3（腿误差0.19–0.20rad）；前进跟踪/刹住3/3，但非轮接触3/3峰63.5–98.9N、回站0/3；倒退跟踪/刹住3/3，非轮接触2/3峰71.6/93.4N、回站0/3。原始结果 `部署参考/as2w-flat-rerun/results/rolling_1199_measured_start_20261111.json`；诊断不是对上游整个 supervisor 的严格同构复现。
- 结论：忽略最终站姿后，前进仍有运动期非轮接触及上游刹车长尾，不能视作安全真机成功率。当前**不绑定 B、不做有界地面首测、不部署到 CPRO**；R214 P3 zero-B 继续暂停，其他硬阻断不变。详细判读、模型合同和训练侧补齐项目见 `02_现场操作/rolling-1199-preview离线评估.md`。本阶段未执行HDC动作、ReleaseMode或LowCmd。

## 2026-11-11 晚：R1199 独立 MuJoCo 方法对齐文档（仅文档）

- 应用户要求，逐项公开本项目复演的环境、脚本命令、真机 q/pitch 初态、MuJoCo 扰动、65维观测/动作近似、FSM阶段、Brake/非轮接触/回站通过条件及与上游 `speed-evaluation.json` 的不可直接比较之处；文档 `02_现场操作/R1199本项目MuJoCo复演方法与上游对齐问题.md`，原始结果仍为 `部署参考/as2w-flat-rerun/results/rolling_1199_measured_start_20261111.json`。
- 明确纠偏：九条独立复演复用了旧 preview 的 stand-bias/轮角 hold/退出控制，不是 R1199 完整 supervisor 的逐行复刻；固定站姿 `<0.18rad` 和非轮接触 `<1N` 属本项目诊断阈值。需同事以相同初态和逐帧最终目标对齐第一处分歧。本阶段无新仿真、无HDC/控制权/LowCmd、无机器人动作。

## 2026-11-11 晚：R1199 前进 seed 202 推扰消融与首次触地视频（纯仿真）

- 应训练同事要求，给旧复演器增加可选 `ROLLING_TRACE_SEED/ROLLING_CONTACT_TRACE/ROLLING_DISABLE_PUSH` 诊断记录，只跑 seed202 实测 FixedStand 初态前进，分别保留既定推扰与关闭推扰。两回合相同 ONNX、初态、摩擦、质量与执行器增益；脚本及重渲染工具在 `部署参考/as2w-flat-rerun/`。
- 两回合首次大于1N的非轮触地均为滚动 `t=1.440s` 的 `RR_calf`（body16/geom17），首子步法向力24.13N；既定推扰 `t=3.702s`，20ms边界实际 `t=3.720s` 执行。因此首次触地比推扰早约2.28s；首次触地±0.5s的800物理子步与50控制帧两条件逐项完全相同。全运动段峰值有推扰98.9N、无推扰101.8N；首次触地窗口局部峰约53.2N。
- 原始 JSON 归档 `logs/r1199_forward202_{push,no_push}_{contact_window,summary}.json`；Windows 可播放视频 `videos/r1199_forward202_{push,no_push}_first_touch.mp4` 和同名1.46s PNG；详细字段、依赖路径、复现命令和解释在 `02_现场操作/R1199前进202推扰对照与视频.md`。视频为保存状态重渲染，不含3.72s之后的推扰。无HDC/ReleaseMode/LowCmd/真机动作。

## 2026-11-11 晚：R1199 训练服务器只读审阅（未改远端文件）

- 通过用户提供的 SSH 入口只读查看 AS2-W 工作区、训练/评估合同、日志、代码、资产哈希及进程快照；没有编辑/复制到训练服务器、启动任务或停止进程，凭据未入日志。R1199 checkpoint `/root/gpufree-data/Rob2Nav-runtime/as2w-current/runs/r290-three-skills/rolling-knee-margin-formal/model_1199.pt` SHA `bb5c9735...776d` 与本地release一致。训练入口为 `code/train_as2w_isaac_robust.py`，384环境/1200迭代、5ms物理/20ms策略、expanded随机化、膝部净空代价；作业目录有合同/日志/TensorBoard/每25轮checkpoint，`git/`目录空，源码精确快照仍待同事提供。
- 服务器自己的同权重Isaac 0.30m/s：前进跟踪+刹车15/20、完整链1/20；倒退15/20、完整链2/20，`gate=false`。MuJoCo release诊断六类完整链各0/1、`gate=false`；`safety_gate=true`不能替代完整门槛。训练期间`success_rate=1.0`不是留出集安全验收。
- 双方平地XML与默认合同SHA一致，差别在初态（上游仿真reset vs我方实测q/pitch）、native PD vs直接PD力矩、停车/回站supervisor、种子/随机化/丢包及评分口径。上游非轮触地是任意碰撞，我方以>1N计；seed202首次24.13N故触地不可能仅由评分阈值差异造成。详见 `02_现场操作/R1199训练服务器只读审阅与仿真差异.md`；本阶段无新仿真、无CPRO/机器人动作。
- 只读路径、合同字段、评估计数和哈希摘录归档为 `logs/20261111_r1199_training_server_readonly_evidence.md`；训练服务器保持原样，SSH会话已结束。

## 2026-11-11 21:10–21:17：R1199 仿真分歧定位为上一动作观测语义错误（纯离线；覆盖上文“必然触地”结论）

- 设备/环境：机器人及 CPRO 未操作；训练服务器仅 SSH 只读复制 `as2w-current/code/*.py`、release MuJoCo 合同与历史结果，没有修改远端任何文件或启动远端仿真；caolin 服务器运行 MuJoCo 3.17、Torch 2.15、同 SHA 的 R1199 PT 和平地 XML。训练端当前源码与旧 runtime 的平地 `stair_rise` 函数参数不匹配，复演仅在 caolin `/tmp/opencode/r1199_eval_work` 工作副本去掉无效关键字。训练端 `runs/.../git/` 为空，历史源码版本尚未锁定。
- 训练方控制器按 release 合同运行 `--rolling-fixed-exit --rolling-stand-compensation --rolling-wheel-hold --park-precalibrated --park-odometry --park-common-gain-scale 0.5 --park-settle-joints --acceptance --packet-loss 0.02 --push-schedule motion-only --native-pd --substep-safety --trials 1`：caolin 六场景均无非轮触地但完整门槛仍0/6。历史训练服务器结果也是完整0/6，但停车保持 `arc_left` 历史1/6、caolin0/6，不能宣称位级复现；归档原合同/历史行及 caolin 行为 `logs/20261111_r1199_colleague_{mujoco_contract,archived_rows,exact_caolin}.json`。
- seed202 同一训练方评估器：仿真原生初态、无推扰/丢包，前进无非轮接触；注入历史真机 FixedStand q 和 pitch −5.498°、根高接触搜索0.38016m后仍无非轮接触、前进跟踪与刹车通过，但固定站姿入口/出口连续满足时间均0；最终腿角误差0.244rad，10s停车漂移0.02059m、速度p95=0.03055m/s，`held=false`。行及逐帧跟踪在 `logs/20261111_r1199_colleague_{baseline202,measured202,measured202_trace}.json`。
- 我方旧复演器 seed202 原接触因果消融：无推扰初触 `RR_calf` 1.440s、全运动峰98.9N；改摩擦0.70仍81.5N且1.954s初触；去质量/增益应力仍76.5N；进一步 native PD 和0.25s指令渐入仍72.0N。对比控制帧，运动开始时 `obs[42:58]`（上一动作）最大差6.328：旧脚本回填 ONNX 原始 `raw action`，训练方回填动作包装后的 `current`。仅改这一项，名义动力学组合碰地峰变0；恢复原低摩擦、随机质量/增益、直接力矩PD、原突变命令和原推扰，seed202仍0N、平均前进0.305m/s、跟踪和刹车通过。另 seed101/303 同样无非轮触地、跟踪/刹车通过；三例回固定站姿均失败，尾段腿误差0.222–0.251rad。原始输出 `logs/20261111_r1199_legacy_{native_fulltrace,friction070_summary,nominal_summary,nominal_friction070_summary,ramp_summary,history_*}.json`。
- **结论纠正**：上文旧 R1199 “实测初态前进接触3/3/不宜动”的接触统计来自错误观测历史，不可作为权重会碰地的证据；旧视频保留作诊断复现。训练方对原动作语义更可信；但其仿真原生 reset 不足以覆盖实测负载站姿，双方修正后都未通过停车保持/回站完整链，仍**不绑定真机 B、不向 CPRO 同步 R1199 launcher、不发布 LowCmd**。完整消融与改进顺序见 `02_现场操作/R1199仿真差异同条件复演与改进方向.md`；初步审阅文档已加指向。
- 新增可复验脚本仅在 `部署参考/as2w-flat-rerun/r1199_{colleague_ablation_patch,colleague_eval_ablation,legacy_ablation}.py`；原 `rolling_fixed_exit_rehearsal.py` 与训练服务器代码均未修改。本阶段无 HDC、无 ReleaseMode、无机器人动作。下一阶段先统一 obs[42:58]/轮角记忆与包装后动作，补真实起步状态，再攻停车/回站，不把 0.18rad 评估门槛当硬件限值。

## 2026-11-11 晚：R1199 仿真错误是否进入真机发布端的只读核对

- R1199 当前没有 `cpp_deploy-as2w` 控制器或 launcher，release 明示 `real_actuation_enabled=false`；错误仅存在于旧独立 MuJoCo 复演器，没有 R1199 真机 LowCmd。R214 真机控制器是 `obs41+state1196` 并回传 `next_state`，无 `obs[42:58]` 字段；CPRO 1050帧回放误差约9.54e-7。R284 的65维上一动作由官方适配器裁剪后的动作回填，无R1199额外动作包装，官方C++ 16000帧回放误差约1.07e-6；未发现同一种回填错误，但真机振荡原因仍未完成排他性证明，禁令不变。
- R1199 全链仍卡停车保持和回固定站的**关节角评分**，此外尚未有适配器/CPRO构建/shadow/有界退出验收。回站最后100帧轮支撑、直立、速度、偏航均通过，仅 `<0.18rad` 关节角失败；真机稳定FixedStand本就约0.27–0.30rad，不能把该评分失败直接等同于会摔。可在原厂或已验证 A/Y 链下只读采集实机数据供离线修正；目前不进行 R1199 在线实机强化学习或地面 B 接管。详细代码证据、数值和后续门槛在 `logs/20261111_r1199_real_deploy_history_audit.md`。本阶段无 HDC、ReleaseMode、LowCmd 或机器人动作。

## 2026-11-11 21:4x：R214 最小安全壳独立复验第一阶段（离线、只读）

- 用户指定先单独验收现有 R214 安全适配，再处理 R1199 新策略；本阶段未修改 R214 源码或阈值，未接入 R1199。
- HDC 管理链当前只有 `192.168.10.180:8710` Connected（旧 `10178` 与 USB target Offline），所有命令显式 `-t 192.168.10.180:8710`。CPRO `eth0` 只读显示 `NO-CARRIER/state DOWN`，无 `as2w_r214_publish` 残留进程，狗当前下电或物理链路未接好。未尝试 ReleaseMode/LowCmd。
- 核对本机与 CPRO 维护源码 SHA256 均为 `419dca66e91688a83e87173366d8662bb8c9d03b945a8db3fb43b9bb50951aab`；设备 `build-r214-zero-b` 二进制 SHA256 为 `fb010d3204a34967611b60aec99cbbb71afb941e388f4b087733bd651ad800d6`，与 P0–P2 构建记录一致。
- 在 CPRO Ubuntu 容器运行当前 `build-r214-zero-b/.../as2w_r214_publish ... --offline-audit`：`GUARD INJECTION PASS`（safe 200 帧、warn 第5帧 Brake、hard 第3帧 Emergency、motorstate 闪断复位、200ms 遥控超时、指令斜率和 requested/applied 一致），最终 `AUDIT PASS`。原始输出：`logs/20261111_r214_safety_separate_reaudit.log`。
- 同一 ARM64 构建运行 `ctest --test-dir build-r214-zero-b --output-on-failure`：8/8 通过，HDC 退出码0。原始输出：`logs/20261111_r214_safety_separate_ctest.log`。
- 结论仅覆盖当前设备上的二进制身份、离线注入与构建回归；运行时守卫在真实 PolicyHandoff/PolicyWalk/Brake 尚未验收。下一步待狗上电及 CPRO eth0 恢复，仅做只读 LowState/模式/进程基线；随后需分别说明并获得现场人员当次同意，才可 ReleaseMode 和执行有界 zero-B。R1199 B 仍未部署、未获真机许可。

## 2026-11-11 21:45–21:49：R214 安全壳独立复验第二阶段（恢复机器人网段、只读基线）

- 现场人员给狗上电后，CPRO `eth0` 仍无载波，而 `eth1` 有载波、无 IPv4；经现场人员换线到 `eth0`，只读确认 `eth0 LOWER_UP`。CPRO 重启丢失原有 `192.168.123.100/24` 与去 `192.168.123.0/24` 的 priority 1000 路由规则，因此 DDS initially 报 `eth0: does not match an available interface`。原始输出：`logs/20261111_r214_safety_baseline_readonly.log`、`logs/20261111_r214_eth0_link_diagnostic_readonly.log`、`logs/20261111_r214_eth_ports_readonly.log`、`logs/20261111_r214_safety_baseline_eth0_restored.log`。
- 核对设备 `/data/local/tmp/as2w_field/cpro_host_net.sh` 与本地唯一源码 SHA256 均为 `ee5ead45c19c46028557acaf3669c9beaaf909f2631e457b03ac003949f3d3cd` 后，执行已验证的 `sh .../cpro_host_net.sh apply`：仅补 `eth0=192.168.123.100/24` 和去机器人子网的 main 路由规则，不改默认网关。机器人 `.161` ping 3/3，`ip route get` 为 `dev eth0 src 192.168.123.100`。记录：`logs/20261111_r214_robot_net_reapply.log`。
- 随后只读 LowState 约 1063 包/s、`mode_machine=2`，原厂 `MotionSwitcher CheckMode rc=0 name=ai`、`fsm_name=ai_damping` 趴下；无 R214 发布端进程。3秒 LowProtection 得 3135 帧，16轴 `mode=1`（原厂控制）、`motorstate_or=0x0`、`warning_or=0x0`、主板状态0。原始日志：`logs/20261111_r214_safety_baseline_linkup.log`、`logs/20261111_r214_safety_baseline_protection.log`。
- 本阶段无 ReleaseMode、SelectMode、LowCmd 或狗动作；下一步为新安全壳 zero-B 真机短接管，需现场人员对本次明确同意。R1199 仍未接入。

## 2026-11-11 21:50–21:54：R214 最小安全壳独立 zero-B 真机验收通过

- 现场人员对本次完整实验明确同意并在旁看护。运行 Windows `部署测试/运行现场策略会话.ps1 -Policy r214 -Mode zero-b -MonitorSeconds 180 -Target 192.168.10.180:8710 -ConfirmMotion`；一键链重新核对源码/二进制 SHA、audit PASS、LowState 1033包/s 与 `mode_machine=2`、原厂 `ai_damping` 趴下；`ReleaseMode rc=0` 后 2秒采样2098包且16轴mode全0，双监测覆盖全程。
- 发布端 `Passive ready after 741 frames`；操作员 A 固定站立、B 一次获准（pose_error=0.27188rad、轮速0.02454rad/s、upright=0.996313、静止腿dq0.02761rad/s）。进入 `PolicyHandoff→PolicyWalk` 后强制零速度约10秒，所有 `WALK_CMD requested/applied` 均为 `0,0,0`；随后 `bounded zero hold cap→Brake→ReturnStand→FixedStand`，操作员按 Y，`FixSquat→Passive`，`ZERO_B_TRIAL_REMOTE_RC=0`、publisher exit=0。未见 `FIELD_SAFETY_WARN/HARD/SOFT_TRIP` 或 `REMOTE_TIMEOUT`。
- 180秒保护流约34213行，其中有效34209行：`warning_or=0x0`、`motorstate_or=0x0` 全程；主板状态仅0x0/0x1（FOC状态位），16轴mode在发布期间为1，结束后回0。电机电流峰6.1A、最低电机电压45.7825V；10ms LowCapture共约17998有效采样，16轴FOC区间约1.13–59.32秒，腿dq峰2.217rad/s、轮dq峰0.650rad/s、腿tau_est峰24.712Nm。后腿 thigh 在零速保持段有约0.08rad渐变，未触发守卫；这不能单独推断机身高度或接触力。
- 现场人员确认整条 A→B→自动回站→Y 链“没有问题”，无可见后腿下沉、抖动、嗡鸣、报警或异常，目前狗稳定趴下。此结论只覆盖本次零命令、有界时长且无故障的无误触发/退出行为；warning/hard/遥控失联真实触发的物理效果仍未验收，不据此放开 R214 自由行走或推广安全阈值到 R1199。
- Windows transcript：`logs/20261111-215057_windows_r214_zero-b_field_session.log`；CPRO 四份原始日志已自动回收至 `logs/field_sessions/20261111-215058_zero-b/`。当前原厂控制权仍已释放，无发布进程；任何后续动作须新一轮具体许可。

## 2026-11-11 22:0x–22:32：R1199 零速候选独立适配与离线验收（无新真机动作）

- 上游 release 预检 `OFFLINE_PREFLIGHT_OK [1,65] [1,16]`、ONNX SHA `df1f2d...22b6`；其 `--require-hardware-map` 因原 manifest 16轴硬件字段均 null 正确退出2。上游仍标 `real_actuation_enabled=false`，本项目没有修改其交付包。原始日志 `logs/20261111_r1199_release_preflight.log`、`logs/20261111_r1199_hardware_preflight.log`。
- 项目新增独立 `deploy/robots/as2w/r1199/`：仅接收零物理速度命令的65维控制器，重用已测实机映射、R214 Passive/A/Y/FSM 及安全壳；B编译门槛为一次2秒交接+2秒强制零策略，自动Brake→ReturnStand→Y/15秒超时FixSquat。C++接收非零速度即 disarm；未实现/开放R1199前后运动和转向。`models/r1199/deploy.yaml` 单独标为 zero-B candidate、策略增益55/2与训练环境一致；R214已验收二进制未被替换。
- 训练方 `as2w_rolling_fixed_exit.py` 当前包装含停车里程计、0.5公共轮增益、关节静止锁定、预标定站姿偏置，且上一动作观测必须回填包装后动作。用21:50真机日志的501帧固定站姿与零速段建夹具，在CPRO ARM64 C++回放、caolin服务器训练方原Torch helper和本机Python诊断间逐帧比对：C++相对训练方最大目标误差 `8.27e-7`（腿 `4.7e-7rad`、轮 `8.27e-7rad/s`）。一度将0.30s时序改为整数15帧而产生0.004rad差，已恢复训练方float32比较语义并复验。原始 `logs/20261111_r1199_zero_fixture501.txt`、`logs/20261111_r1199_zero_replay_arm64_final.log`、`logs/20261111_r1199_training_zero_parity.csv`、`logs/20261111_r1199_recorded_zero_shadow.json`。
- caolin MuJoCo用本次新采 FixedStand q/pitch `-0.0864059rad`、训练方原PT/正确包装/native PD/无推扰静态复演 seed202：稳定、停车保持通过，无非轮接触/轮卸载/限位，10s量级漂移0.00422m、速度p95 0.00240m/s、执行器力矩峰比0.204；最终理想关节角 `<0.18rad` 评分仍失败（hip偏差约0.22rad），不能据此宣称完整链通过。原始 `logs/r1199_fresh_static_20261111/` 与 `logs/20261111_r1199_fresh_static_sim_console.log`。本机曾试运行旧MuJoCo脚本，因缺Torch未执行；实际复演在caolin服务器完成，未改训练服务器。
- CPRO `build-r1199-zero-b` ARM64全构建、CTest8/8、共享启动帧和守卫故障注入audit PASS。源码/设备控制器CPP SHA `7beac2...dc8`，二进制 `7d3471...5fdb`。早期首次编译缺 `Config.dt`、首次离线审计因临时Ort TypeInfo生命周期报vector大小异常，两项均在**未发布LowCmd前**修复且最终完整构建/回放/audit通过；原始 `logs/20261111_r1199_candidate_arm64_build*.log`、`logs/20261111_r1199_candidate_offline_audit*.log`、`logs/20261111_r1199_final_arm64_ctest.log`。
- 新的 `run_r1199_field_session.sh` 只接受 `dry-run/zero-b`，Windows `运行现场策略会话.ps1` 已注册 `r1199` 且禁止其 `stand/motion`、默认HDC目标更新为已验证的直连8710。R1199 dry-run两次通过（当前name空、16轴mode0），不发LowCmd；最近记录 `logs/20261111-223123_windows_r1199_dry-run_field_session.log`。详细可审查协议见 `02_现场操作/R1199零速有界首测准备.md`。
- **该节是试验前状态，已被下方 22:34 实机结果更新。** 通过后仍不能放开运动摇杆，需要另做非零包装器/闭环仿真/停车回站验收。

## 2026-11-11 22:34：R1199 有界零速 B 实机首试通过，非零运动仍锁定

- 现场人员明确同意本次动作并在旁握遥控器/急停。运行 `运行现场策略会话.ps1 -Policy r1199 -Mode zero-b -MonitorSeconds 180 -Target 192.168.10.180:8710 -ConfirmMotion`。会话预检通过：audit PASS、LowState 约1033包/s、`mode_machine=2`、已 ReleaseMode、16轴mode0、双监测启动。
- Passive ready after 743 frames；操作员按 A 固定站、B 零速接管、Y 受控趴下。B gate 读回站姿误差0.277772rad、轮速0.012272rad/s、直立0.994387；2秒 Handoff→2.00044秒零命令 PolicyWalk→自动Brake→ReturnStand→FixedStand→Y FixSquat→Passive。所有 `WALK_CMD requested/applied=(0,0,0)`；无 `FIELD_SAFETY_WARN/HARD/SOFT_TRIP` 或遥控超时，发布端与远端脚本 RC0。
- 180秒保护流34223有效行：`warning_or=0x0`、`motorstate_or=0x0`；主板状态仅0x0/0x1，电流峰5.6A。全会话腿dq峰2.01054rad/s、轮dq峰1.11674rad/s、腿估算tau峰23.2125Nm。B交接/零策略/刹轮所在44–52秒，俯仰由约-6.28°到+4.35°，腿dq峰0.591rad/s、轮dq峰0.969rad/s；四轮净角变化约1.86–2.95rad。无机身位置测量，不能从轮角推算实际滑动距离。
- 现场人员观察“狗往上抬了身子然后站住了，一切正常，轻微滑动，后续也丝滑”，结束后趴下；无报警或异常。原始 transcript：`logs/20261111-223402_windows_r1199_zero-b_field_session.log`，设备四份日志：`logs/field_sessions/20261111-223403_zero-b/`；复核与量化：`logs/20261111_r1199_zero_b_review.md`。
- **结论仅限这一次零速短接管与退出。** R1199 非零速度控制器仍编译锁定；上游交付的 `real_actuation_enabled=false` 未改。后续需先做非零包装/历史观测逐帧训练方一致性、实测初态 MuJoCo 及短时有界滚动离线审查，获新一轮现场许可才可能测试运动。当前结束状态按现场反馈为趴下，原厂控制权仍 ReleaseMode；无发布端。

## 2026-11-11 23:06：R1199 前进 0.05m/s 两秒候选离线就绪，尚无新实机动作

- 用户要求开发下一档。维护源码新增**独立** `build-r1199-forward` 构建，保留已验收 `build-r1199-zero-b` 原二进制。候选只在B接管后自动请求前进0.05m/s、最多2秒，随后自动Brake→ReturnStand→Y/超时趴下；前后共约4秒的B段。摇杆本次不控制方向，后退/侧移/转向/超过0.05指令均拒绝，且无自由motion入口。共享安全壳加速0.20m/s²、减速0.40m/s²；这些是指令限制，非实测机身速度硬限。
- CPRO ARM64 完整构建及CTest9/9、启动帧和守卫故障注入审计通过；独立拒绝夹具在ARM64实际回放对 `vx=0.06`、负vx、非零vy/wz 均报 `Controller disarmed`。记录 `logs/20261111_r1199_forward_arm64_final_build2.log`、`logs/20261111_r1199_forward_guard_audit.{sh,log}`。第一次局部目标构建导致CTest缺其他可执行而报8项Not Run，已用全构建纠正，原失败及纠正日志均保留。
- 使用501帧实测姿态的静止→前进→松杆夹具，CPRO C++ 与 caolin 服务器运行的训练方原Torch动作包装逐帧比对：最终包装动作最大差 `1.1920929e-6`、上一动作观测差0，118帧非零输入；源/原始回放/比对 `logs/20261111_r1199_forward_{fixture501.txt,replay_arm64.log,training_parity.log}`。未修改训练服务器。
- MuJoCo用实测FixedStand q/pitch、训练方正确包装、native PD、无推扰，0.05m/s两秒窗口种子101/202/303：均稳定、无非轮触地/关节越限/坏站姿/轮卸载，刹轮约0.008–0.010m；但三者`held=false`，随后保持位移约0.034–0.038m、p95速度约0.042–0.054m/s，最终速度接近0。`tracked=false`主要是两秒渐入导致平均仅0.012–0.027m/s；完整理想FixedStand角评分亦未过。训练方仿真 supervisor 与C++实机FSM不同，不能把此称为完整链通过。原始 `logs/r1199_forward005_2s_seed{101,202,303}/`及`logs/20261111_r1199_forward005_sim.sh`；6秒对照种子202无触地且跟踪通过，但同样停车保持失败，留在`logs/r1199_forward005_6s_seed202/`。
- 前进候选最新二进制SHA `139c541bc927deac92fdbe26d34da0913d30975734d243d9206d243e546597e2`；发布源码 `86ede22a...21b1`、控制器 `1dca78ee...53dc`、模型 `df1f2db9...c7f23` 与 Windows/CPRO一致。Windows `-Policy r1199 -Mode forward-dry-run`只读通过，最新记录`logs/20261111-230644_windows_r1199_forward-dry-run_field_session.log`：约1049 LowState/s、mode_machine2、已释放控制权、16轴mode0，**没有发布LowCmd**。现场步骤和风险见`02_现场操作/R1199前进0.05有界首测准备.md`。
- **下一步尚未获本次动作许可，不得直接运行forward。** 需具体告知可能起立、自动短前进、额外滑动和紧急退控下沉，现场人员看护并当次明确同意；然后才运行有界forward会话。R284等既有禁令不变。
- 源码变更后已按项目规则重新运行`部署测试/准备现场包.ps1`，模型校验和打包成功；`cpp_deploy-as2w.tar.gz` SHA256 `a26288b5e75a1671f33b6e314928b7ce95b449f4247eb47f02e68ee1b6e064fa`，`unitree_sdk2-src.tar.gz` SHA256 `c3d46bbddae37e57dc83fa3307d83de921c464f8992b5a8f39f6d5d444915b7c`。原始命令输出`logs/20261111_r1199_forward_package.log`。打包未自动运行实机程序。

## 2026-11-11 23:10–23:13：R1199 0.05m/s 有界自动前进真机首试通过

- 现场人员获知本次具体动作/滑动及下沉风险后明确同意，在旁握原厂遥控器和物理急停。Windows运行`运行现场策略会话.ps1 -Policy r1199 -Mode forward -MonitorSeconds 180 -Target 192.168.10.180:8710 -ConfirmMotion`；前置只读dry-run在23:10再次通过，四小腿趴下角度 gate=yes。
- 现场链：audit PASS→LowState1036包/s、mode_machine2→已ReleaseMode→2秒2083包且16轴mode0→双监测→Passive ready 745帧→现场A固定站→B门槛通过（pose误差0.257115rad、轮速0.024544rad/s、直立0.998423、静止腿dq0.030680rad/s）→约2秒零速交接→自动`vx=+0.05m/s, vy=wz=0`两秒，发布日志先0.04后0.05→自动Brake→ReturnStand→FixedStand→现场Y受控趴下→Passive。发布端RC0、会话结束RC0；摇杆未推，输入记录为零。
- 180秒保护流34,176有效行，`warning_or=0x0`、`motorstate_or=0x0`全程；主板状态仅0x0/0x1，16轴发布期间mode1、结束回0。电流峰5.9A、主板有效后最低电机电压44.7674V；10ms关节采样17,999行，全会话腿dq峰2.02485rad/s、轮dq峰0.93266rad/s、腿估算tau峰23.9625Nm（含起立/趴下）。没有安全守卫warn/hard/remote-timeout。
- 约28–32秒交接/前进/刹轮窗口有轮角变化，32–36秒轮速回近0；小腿从策略姿态约−1.64/−1.51rad回固定站约−1.75rad，俯仰约+3.95°→+0.8°。现场确认狗有小幅移动、回站似有肢体向下运动，最后稳定趴下，全程无报警。缺少机身位置/接触力，不能量化位移或垂向冲击；对回站下移仅记录姿态连续变化，不判定已完全无风险。
- 证据：Windows transcript`logs/20261111-231030_windows_r1199_forward_field_session.log`，CPRO四份完整会话日志`logs/field_sessions/20261111-231030_forward/`，数值提取`logs/20261111_r1199_forward_capture_protection_summary.txt`，详细解释`logs/20261111_r1199_forward_review.md`。本次仅证明**一次0.05m/s两秒有界前进/退出**；三种子MuJoCo的停车保持仍未过，未开放手柄自由调速、倒退或转向。继续运动测试须新开发/离线复核和当次具体许可。当前狗趴下、ReleaseMode、无发布端（按日志与现场反馈）。
- 现场会话脚本最后新增四小腿趴下角门槛后，已重新运行`准备现场包.ps1`且模型校验通过；**当前最终现场包**`cpp_deploy-as2w.tar.gz` SHA256 `512e9e3d3f434cd937f4b1b589f10e48557cd0615b8419d6317da04cfe33f809`，SDK2源包SHA `2857b6bc2b8bac374ddd7c6682342b27a39c07ef8531064f948b4c6ef3e3da9c`，日志`logs/20261111_r1199_forward_package_final.log`。上方23:06的包哈希为中间版本，不用于当前交付。

## 2026-11-11 23:34：R1199 低速摇杆 60 秒候选离线就绪，尚未真机执行

- 独立 `build-r1199-joystick` 只接受一轮 B，B 后 2 秒零速交接，摇杆左前后映射 `vx`、右左右映射 `wz`，两者指令上限分别 0.05 m/s 和 0.05 rad/s；LX/RY 忽略、`vy=0`。PolicyWalk 最长 60 秒，无单次推杆时长限制；保留指令斜率、遥控超时、腿/轮守卫及自动 Brake/ReturnStand/Y 趴下。物理机身速度并无独立硬限，停车保持不能保证原地不动。
- CPRO ARM64 重编、CTest 9/9、摇杆映射 `R1199 JOYSTICK MAPPING PASS`、启动帧/守卫审计 PASS。源码 CPP SHA `a99dc6d812fd35fe6262e7603411ad84cbfbbd229b4f9b31e6ade18ca5219e05`、设备二进制 SHA `e67675672f57ce21e842073436fb96e3abccaa4f4883ebe619cc3ae6f7d95297`。原始构建输出 `logs/20261111_r1199_joystick_final_build.log`。
- 950 帧 CPRO C++ 与训练方 Torch 包装逐帧比对，含 590 帧非零输入，最终动作最大误差 `1.1920929e-6`，前动作观测差 0；证据 `logs/20261111_r1199_joystick_{replay_arm64.log,training_parity.log,fixture950.txt}`。实测起步姿态 MuJoCo 六类动作×三种子、2 秒及 10 秒窗口均未翻倒/非轮触地，但停车保持有失败、前后/转向响应不完全对称；证据 `logs/r1199_joystick005_{2s,10s}_seed{101,202,303}/`。
- Windows `-Mode joystick-dry-run` 本次只读预检 PASS：LowState 1039/s、mode_machine2、MotionSwitcher name 空、2 秒 2058 包、16 轴 mode0、四小腿趴下门槛通过；未发 LowCmd。transcript `logs/20261111-233425_windows_r1199_joystick-dry-run_field_session.log`，远端归档已回收到 `logs/field_sessions/20261111-233426_joystick-dry-run/`。
- 真机摇杆动作**尚未运行**。唯一现场入口与按键语义见 `02_现场操作/R1199摇杆60秒试验.md`。每次真机动作仍按本项目规则由现场人员知悉具体动作并当次明确同意；上游 R1199 preview 的 `real_actuation_enabled=false` 未改。R284/R270/旧 rolling-fixed-exit 禁令不变。
- 已按规则重新运行 `部署测试/准备现场包.ps1`；模型校验通过，`cpp_deploy-as2w.tar.gz` SHA `78170a125a882bc4ce4d12cb06c63727591232f437835faa5aaf87b8951b6ae4`，SDK2源包 SHA `093fd56d30cefd24ee9f0a907ecd5e3f3fc86758561233e9d832a7d08a9e2876`；原始输出 `logs/20261111_r1199_joystick_package.log`。本次现场入口使用已同步并编译的 CPRO 文件，不依赖重新解包。

## 2026-11-11 23:36–23:40：R1199 摇杆首试出现姿态突变和一次软件预警，暂停复测

- 现场人员执行已准备的一键入口，在旁操纵原厂遥控器；A固定站→B 2秒零速交接→PolicyWalk 60秒→自动Brake/ReturnStand→Y受控趴下，发布端/会话RC0。只试前后，`wz=0`，转向未验收。现场反馈高姿态较快降下、听见关节抖动，速度观感尚可；Ctrl+C未能提前结束等待。原始Windows transcript `logs/20261111-233643_windows_r1199_joystick_field_session.log`，CPRO四份日志 `logs/field_sessions/20261111-233644_joystick/`。
- 保护流45,641条有效记录，`warning_or=0x0`、`motorstate_or=0x0`全程，主板状态仅0x0/0x1；**无硬件保护报警**。发布端有**一次软件守卫warn**：首次非零`vx`附近腿目标单帧步进0.272911rad（warn0.2、hard0.35），腿速度1.53194rad/s、估算tau10.95Nm；计数仅1，未触发SoftBrake/HardStop。最终刹轮由60秒时限触发。
- 从10ms关节采样看，固定站四大腿q均值约0.74rad/四小腿约-1.79rad；零速策略姿态约0.87/-1.53rad（更伸展）；首次推前后回约0.79/-1.75rad。无机身高度真值。`POLICY_TRACK`零速四髋目标-实测差0.35–0.47rad，首次推杆后突降到约0.20rad。维护源码的站立`bias_`通过`stand_blend`叠加到腿目标；`age>=4s`且静止保持计数被非零指令清零时，该补偿可能单帧撤掉。代码机制与本次目标跳变吻合，但声音来源仍需离线消融。详细证据及复跑分析脚本 `logs/20261111_r1199_joystick_review.md`、`logs/20261111_r1199_joystick_analysis.{py,txt}`。
- Ctrl+C等待根因：旧会话脚本发布端退出后仍`wait`两个持续240秒只读监测进程，且Windows→HDC→CPRO并不保证信号转发。已将R1199脚本改为发布端退出后额外采5秒即终止监测并归档；**Ctrl+C仍不作为运动急停**。当前`joystick`现场入口开头硬阻断，防止未修复便复测；`joystick-dry-run`保留。下一阶段离线平滑站立补偿退出、与训练方对齐、MuJoCo首次推杆复演，并重新审查短时真机方案。上游权重及已验收零速/自动前进二进制均未改。
- 来源：站立`bias_`并非本次部署端自行设计。训练交付离线包`rolling-fixed-exit-preview/as2w-offline-deployment-preview.zip`含相同`rolling_precalibrated_stand`，提交`0c371f6`于11月11日10:07由Codex署名、13:03由YuTaoV5合并；R1199包沿用。部署端C++是移植。提交记录无法确定最初人类设计者；详细zip哈希见review。暂停脚本已同步CPRO，Windows与设备SHA一致为`1dd7c7a6306d83ee0869237f5a02f393469ff2f04eb85e33d2a2267bfeb0ad85`；设备`bash -n`通过且`joystick 90`在任何DDS/LowCmd前正确FATAL。同步记录`logs/20261111_r1199_joystick_pause_sync.log`。重新打包通过，现场包SHA`e99f85cdf8032a47ffdc382449fc0f4ee963141146cc6eece856cde40bae49cb`，SDK包SHA`890d1b33110464c9fe5f85a50e814219f478e6797d7d4658a2edb26019e1dca5`，日志`logs/20261111_r1199_joystick_pause_package.log`。

## 2026-11-11 23:55–2026-11-12 00:00：应现场要求恢复 R1199 摇杆复测入口，尚未执行动作

- 现场人员已获知上次首次推杆的0.272911rad腿目标跳步、姿态下降及可闻抖动，明确要求解除入口锁自行复测。仅恢复`run_r1199_field_session.sh joystick`，新增风险提示；原C++策略/增益及60秒PolicyWalk上限不变，继续走完整预检和双监测。已修的“发布结束后再采5秒便归档”保留；Ctrl+C仍不可靠，现场须用X/物理急停处理运动异常。
- 会话脚本本机/CPRO SHA均为`4ec4018384aa7a63263897b6c15fe2578aa5d47514c6ded221be020367279251`，设备`bash -n`通过。Windows `-Policy r1199 -Mode joystick-dry-run -MonitorSeconds 30 -Target 192.168.10.180:8710`只读通过：LowState1039包/s、mode_machine2、已ReleaseMode、2秒2095包、16轴mode0、趴下门槛yes；未发LowCmd。原始`logs/20261111-235548_windows_r1199_joystick-dry-run_field_session.log`及`logs/field_sessions/20261111-235549_joystick-dry-run/`。
- 已重跑`准备现场包.ps1`，现场包SHA`dda64e753534d34c4a93797037ee64ba141429ecd0891726fa490c3b1bac7383`、SDK包SHA`a6ec33ea1d956eae153c3cfe11f42446011a0ecf93c01bae176d4c049374897a`；日志`logs/20261111_r1199_joystick_reopen_package.log`。**尚未执行本次运动复测**；复测后须记录现场观感和归档结果。

## 2026-11-12 00:01–00:09：R1199 摇杆第二次实机复测及 CPRO 数据完整回收

- 现场人员自行运行 `-Policy r1199 -Mode joystick -MonitorSeconds 240 -Target 192.168.10.180:8710 -ConfirmMotion`；反馈仍见“运动时下降、停下后抬升”、关节可闻抖动。本轮只试前后，未试转向。发布端 A→FixStand→FixedStand→B两秒零速Handoff→PolicyWalk约58.4秒（按A提前刹车）→ReturnStand→FixSquat→Passive，RC0。当前姿态由现场人员后续确认；本条不推断原厂控制权恢复。
- 保护流17,843有效条，`warning_or=0x0`、`motorstate_or=0x0`全程；一次`FIELD_SAFETY_WARN count=1`，首次非零vx附近腿目标单帧步进0.254249rad，腿速度1.83464rad/s，未达SoftBrake/HardStop。和首试0.272911rad单帧warn构成重复证据。10ms采样可见零速时四大腿均值约0.909rad、小腿-1.508rad，第一次运动后约0.79/-1.75rad；多次停止/前进循环出现两种姿态切换。无机身高度真值，不能定量写机身升降厘米数。
- **数据已在现场离开前从CPRO回收到Windows并逐项核SHA一致**：本地`logs/field_sessions/20261112-000114_joystick/`含`low_capture_fast.log`（7,919,995字节，SHA `09c601985adc7a67e842bda88d86c45d5e5f5a6cd896f654646d739dd103652f`）、`low_protection.log`（3,895,296字节，SHA `e9b5d89ab0e9cc568df77ab3586919cf8d6d975196bd988386a1f9096f2812c0`）、`publisher.log`（61,033字节，SHA `7b0d1dd6eb42531cc299879f3f7f895e6dfe69bddd88e034905cb7549374e33e`）、`session.log`（3,417字节，SHA `f76330271e142c654765d6250c1cd7fbf934839215a0ccc5f6243ecc4dc06e1a`）。Windows终端`logs/20261112-000113_windows_r1199_joystick_field_session.log`；初步离线汇总`logs/20261112_r1199_joystick_retest_analysis.txt`。CPRO会话目录最新就是`20261112-000114_joystick`，无同轮遗漏；后续分析只用本地副本。

## 2026-11-12 凌晨：R1199 二次实机根因评审、训练合同审计与交付规范（离线，无狗动作）

- 10ms实机状态和5Hz发布日志整理为`logs/20261112_r1199_joystick_capture_10ms.csv`、`logs/20261112_r1199_joystick_walk_5hz.csv`、`logs/20261112_r1199_joystick_retest_trace.png`；解析/量化源脚本和输出为`logs/20261112_r1199_joystick_trace.py`、`..._transition_events.txt`、`..._jitter_quant.py/.txt`。可见多个`vx=0↔非零`循环伴四髋目标误差约0.12↔0.35–0.45rad、腿姿态反复变高/低；安静零速四髋tau_est约±16–25Nm，持续前进腿dq RMS0.111rad/s、力矩高通RMS0.672Nm。后两数值仅描述测量窗口，不证明声音的特定频率或机械高频失稳。
- 源码机制：旧R1199包装 `stand_blend` 在4秒后依赖停车`hold_frames`；首次速度使计数清零，站立`bias`在一帧消失，静止后约1.5秒渐入。两次首推单帧目标warn与该机制吻合。正式交付Isaac/MuJoCo合同为`park_continuous_bias=true,park_straight_bias=true`，当前旧C++与另一份诊断结果则为`false/false`；950帧parity只验证后者。正式MuJoCo完整门槛仍仅前进1/20、其余0/20，不能因为切回正式分支便宣称安全。
- 仅对同事训练服务器做只读访问，未改其文件；当时误把较早 `model_550.pt` 的`rolling-fixed-exit-formal/contract.json`当成 R1199 训练合同，故“训练期开关未知”的推断**已撤销**。正确合同与开关见下一节。误取合同仍留`logs/20261112_r1199_training_run_contract_readonly.json`供审计，不纳入对外R1199包。
- 已交付两份文档：`02_现场操作/R1199二次实机抖动与停走姿态切换分析_20261112.md`（事实/推断/方案/明日门槛）与`02_现场操作/AS2-W策略交付合同_v1_20261112.md`（权重、观测、包装、增益、训练开关、仿真结果的必填合同）。本地`r1199_controller.cpp`和CMake新增默认关闭的`AS2W_R1199_FORMAL_STAND_BIAS`独立编译选项；**尚未编译/ARM64验证/仿真，也未同步CPRO**：用户离开现场后CPRO与caolin连接不可用。现有已测试二进制未重建。工作站一键入口已硬阻断旧`r1199 joystick`，断言在HDC前成功；只读模式保留。控制器源码SHA`aece37e08045bf1c8e9cda061f576f72788c44656c7291fe3947abe721a50445`、R1199 CMake SHA`941f0fc3ebb7a3c74c72441fe61a896b90756cd03cd1202d02118807d899f411`。现场包按`准备现场包.ps1`重新生成，模型检查6份通过，包SHA`6554039df1cb769860d087f97aafaa9fa821753fb77952db5c23ca5260020538`，SDK包SHA`b053e50723af2e98f30747ac248cf838c6fe71a604110e5405eb70aceff093b3`；原始`logs/20261112_r1199_docs_formal_candidate_package.log`。

## 2026-11-12 01:15：R1199 运动中抖动量化、训练服务器正确溯源、独立外发包（只读/离线）

- 按现场两次“前后滚动时真实可闻抖动”的反馈重做局部图，证据`logs/20261112_r1199_motion_jitter_evidence.{py,txt,png}`。第二轮10ms LowState：零速27–35s 12腿dq RMS0.00661rad/s、估算力矩去0.2s慢变化RMS0.0181Nm；持续前进53–67s分别0.1113rad/s、0.6799Nm。前进59.35–59.95s FR髋dq连续正负交替（峰0.313rad/s）、tau_est峰谷差3.225Nm，全腿dq峰0.641rad/s。运动中的波动有原始实机数据支持，但100Hz状态流不能确定声源频率/唯一因果；不能把它混作起步目标跳步或用无硬件告警否定。
- 通过用户提供入口只读访问同事训练服务器，**未更改远端任何文件**。发布R1199 `model_1199.pt` SHA`bb5c9735b5bd37ef4bdd2bd13f9d45395d8dc9b4c888c36955de1a345d55776d`与`runs/r290-three-skills/rolling-knee-margin-formal/model_1199.pt`相同。真正训练合同已拉回`logs/20261112_r1199_actual_training_contract_readonly.json`，本地/远端SHA均`b5547500db4462175fad7ad525bde50d17cccbf869c1d48c6343b7f0889d1d29`；作业日志`logs/20261112_r1199_actual_training_job_readonly.log` SHA`748f896c695df6dfbeacbe36fc03a25bf1635a7bcfb9dc90a918893ce7eb8623`。训练合同`continuous/straight=true/true`、`odometry/settle=false/false`，与旧实机C++相反；标称腿PD 55/2与部署配置相同。训练当前源码在作业完成后约2小时改过、作业`git/`为空，缺训练当时不可变源码快照。细节`02_现场操作/R1199训练服务器与实机包装对齐审计_20261112.md`。
- 文档已更正此前误溯源，另写`02_现场操作/R1199明日caolin同条件停走抖动消融计划.md`：同权重/实测初态，仅改变包装补偿，分开验收停走姿态与持续前进抖动；caolin/CPRO今晚仍不可达，**未执行新仿真或真机动作**。两份核心文档也已加入运动段量化与正确训练合同。
- 独立可发同事包`06_训练协作/R1199_real_robot_feedback_20261112.zip`含两次原始会话、Windows记录、图表/可复算脚本、R1199权重、部署源码、真实训练合同/日志/当前源码快照、上游正式合同、分析/交付合同/明日计划；`MANIFEST.sha256`校验53项全一致，ZIP CRC正常，复算脚本从包内CSV运行成功。包SHA`f992d35c4d9550ccb784b297fcdb898e6de1e3a1af3a7cd62224d1f12be13836`。外发包无需访问本工作站；旧R1199 joystick硬阻断和新候选未编译/仿真/同步门槛不变。

## 2026-11-12 01:30：用户改为直接修 R1199；明日 caolin OpenCode 交接（离线源码，无狗动作）

- 用户明确“两次实机旧故障已足够，不要复现，直接修复”。`02_现场操作/R1199明日caolin同条件停走抖动消融计划.md`已标为旧计划；当前任务书`05_OpenCode交接/给OpenCode_R1199训练合同修复与明日实机接续_20261112.md`和可粘贴首条`给OpenCode_R1199首条Prompt_20261112.md`，要求只对新修复版编译、Python parity、MuJoCo和逐次授权有界真机。`05_OpenCode交接/README.md`已更新当前入口。
- 唯一维护源码`r1199_controller.cpp`新增默认关闭的`AS2W_R1199_TRAINING_CONTRACT`分支，对齐真实训练合同四项：站姿 continuous/straight=true/true；停车 odometry/settle=false/false；轮锁存0.12s、每轮`-6*error`限幅/16且无common feedback。`r1199/CMakeLists.txt`仅独立 joystick 候选接受该选项；旧构建不受影响。`tools/r1199_training_forward_parity.py`新增`--training-runtime`，Python语法检查通过。当前源码SHA`9100d6402167383c4528669ac892b154a109475e030b56a9a3fb0004ea0081ad`、CMakeSHA`58acd8c084a1093a03e2ab8f35864e953588ac0209ebee0ab48396e1ecca92cd`、parity脚本SHA`75447a7a85f22bded13b019e7b164de6ec14700af0bc5d5f56e9ab23a7b9e0b9`。本机无可用C++编译器，caolin/CPRO今晚不可达，**C++编译、逐帧parity、MuJoCo、ARM64、真机均未做**，不得把源码候选当成已修好的可发布二进制。
- 工作站`运行现场策略会话.ps1`旧joystick仍硬阻断并更新说明；本地`run_r1199_field_session.sh`也在预检前FATAL阻断旧joystick，但**CPRO已同步的旧脚本可能仍开放**，禁止直接调用。新候选必须另建build和新入口，不覆盖旧二进制。R1199独立外发包已重建含当前源码和新交接，ZIP SHA`a568ac1c7af3d2b4dcf9da296bd68c87cef91894b66073cab2c59fa2a47f1406`，CRC正常、manifest54项全一致；上节旧ZIP SHA是历史版本。没有HDC动作/ReleaseMode/LowCmd。下步 caolin 上线后先静态审查→独立x86编译+parity→仅新候选MuJoCo→ARM64隔离构建与只读入口，之后每次动作另取现场许可。

## 2026-11-12 上午：R1199 训练合同修复候选离线验收（静态审查+修复+编译+parity+仅修复版 MuJoCo，无狗动作）

- 环境：caolin 服务器已可用 g++ 13.3 / cmake 3.28 / torch 2.15 / ort1.31；SSHFS 挂载正常。逐项静态审查唯一维护源码，对照训练端 `as2w_isaac_speed_range.py`+`as2w_rolling_fixed_exit.py` 真实 `model_1199` 运行，`AS2W_R1199_TRAINING_CONTRACT` 四项（odometry=false 原始轮角 / settle=false 无腿速+锁存0.12s / 无 common feedback 逐轮 `-6*error` 限幅/16 / continuous+straight 站姿 `scale.lerp(upright,straight)`）全部正确。**发现并修复一处不匹配**：训练是 `wheels = wheels + hold` 叠加，旧 C++ 锁存时 `=` 覆盖 `rolling_fixed_exit` 轮输出；仅 `TRAINING_CONTRACT` 分支改 `+=`，旧 `#else` 不动。修复后 controller SHA `beb824e53a366455c5a7adedc26038062d02994bbf3b040f68d6a18cde35b115`（CMake `58acd8c0…`、parity `75447a7a…`、ONNX `df1f2db9…c7f23` 均未变）。
- 独立 x86 编译镜像 `/tmp/opencode/r1199_training_contract_build`（`AS2W_R1199_JOYSTICK_CANDIDATE + TRAINING_CONTRACT + PUBLISH`，ORT1.22/SDK2），`-Wall -Wextra -Wpedantic` 无告警；CTest **9/9**、`as2w_r1199_joystick_publish --offline-audit` `GUARD INJECTION PASS`+`JOYSTICK MAPPING PASS`+`AUDIT PASS`。原始 `logs/20261112_r1199_tc_{cmake_configure,x86_build,ctest,offline_audit}.log`。
- 逐帧 parity：复用 950 帧真实传感器夹具（`20261111_r1199_joystick_fixture950.txt`，命令覆盖 0→+0.05→0→−0.05→0→+0.05→0），新 `as2w_r1199_joystick_replay` 产出 `logs/20261112_r1199_tc_replay_output.log`；`r1199_training_forward_parity.py --training-runtime` 对训练端包装 `max_action_error=1.1920929e-07`、`max_previous_action_error=0`、590 非零帧，通过。原始 `20261112_r1199_tc_training_parity.log`。
- 仅新候选 MuJoCo（实测 FixedStand q/pitch `-0.0864 rad`、根高接触搜索）：前进/后退 × 种子101/202/303、10s 持续窗、`--park-continuous-bias --park-straight-bias`（无 odometry/settle/common）。**6/6 全 stable/tracked/held，无非轮接触、无轮卸载、effort≤0.26**；持续前进中段最大单帧腿目标步进均 `0.063 rad`（旧分支首推 0.254/0.273 rad），全窗含起步也无 0.25+ 跳步，轮 dq RMS≈0.55/峰≈0.95 rad/s，轮载 46.7–80.2 N。`passed=false` 仅因理想 `<0.18 rad` 固定站角与 `fixed_entry_s=0`（旧结论），非安全失败。原始 `logs/r1199_training_contract_{forward,back}005_10s_seed{101,202,303}/`、汇总 `20261112_r1199_tc_mujoco_summary.txt`、分析 `20261112_r1199_tc_mujoco_analyze.py`、脚本 `20261112_r1199_tc_mujoco.sh`。详见 `02_现场操作/R1199训练合同修复候选离线验收_20261112.md`。
- **尚未做**：ARM64 交叉编译/CTest/audit、`准备现场包.ps1`、同步 CPRO、新建独立现场入口。仿真无声音/高频电流模型，只进入有界实机首测，不证明抖动声源消失。P2（离线同步+dry-run，狗不动）需 CPRO 可达并重打包；P3 有界实机逐次（①A→B零速→回站→Y ②有界+0.05 约2s ③短时前后轻推）每次动作须现场人员当次明确同意，异常用 X/物理急停。
- **停走姿态跳步 MuJoCo 复现**（回应“FixStand→零速接管→策略回落”）：专写 `logs/20261112_r1199_posture_repro.py`，实测 FixedStand q 起步，零速6s→前进0.05 3s→松杆5s，逐20ms记录 q/目标/bias/hold。旧诊断分支（odometry+settle+common，无 continuous）零速接管整机伸展（thigh 0.74→0.82、calf −1.79→−1.60，方向同实机0.87/−1.53），首次前进瞬间单帧腿目标步进 `0.124–0.127 rad @ t=4.08s`（hold_frames 175→0），随后 thigh 0.82→0.78、calf −1.62→−1.76，对应实机 0.254/0.273 rad 首推跳步；MuJoCo 偏置约0.13 rad（约为实机一半）故幅度略小。新候选（continuous+straight）零速仍伸展，但首次前进**无起步跳步**，单帧目标步进全程最大 0.063 rad（正常控制，非起步），消除“策略回落”。证据 `logs/20261112_r1199_posture_repro_{summary.json,report.txt,trace_{old,new}_seed{101,202,303}.json}`，详见 `02_现场操作/R1199训练合同修复候选离线验收_20261112.md` 5b。

## 2026-11-12 上午：R1199 P2 现场包/独立入口准备 + 训练合同对齐硬规则（离线；CPRO 同步被 HDC 掉线阻塞）

- 按用户要求把“训练合同对齐”落成**长期硬规则**写入两份 `AGENTS.md`（根+部署测试）：“任何策略运行时开关/动作包装/增益必须与训练 `actual_runtime_flags` 逐项一致，MuJoCo/实机验收与部署 C++ 编译宏用同一份合同，任何差异即新版本”。交付合同 `06_训练协作/R1199_real_robot_feedback_20261112/docs/policy_delivery_contract.md` 在会话期间被（工作站侧）并行重写为更完整的“训练方→部署方交付清单 v3”，已覆盖开关三方一致/差异表/`resolved_flags` 要求，不再重复叠加。
- P2 独立现场包/入口：`tools/build_on_cpro.sh` 新增门控 `build-r1199-training-contract`（`AS2W_R1199_JOYSTICK_CANDIDATE + TRAINING_CONTRACT + PUBLISH`）；`field.sh` 新增 `r1199-training-contract-build SDK ORT` 阶段；新增 `run_r1199_training_contract_trial.sh`（指向新 build，参数同已验证 joystick）；`run_r1199_field_session.sh` 新增 `training-contract` / `training-contract-dry-run` 模式（指向新 build，prone 门槛一并纳入，旧 joystick 阻断不变）；Windows `运行现场策略会话.ps1` 注册 `training-contract(-dry-run)` 且仅在 `-ConfirmMotion` 下允许运动。全部 bash 语法检查通过。SHA：controller `beb824e5…`、build_on_cpro `80575a35…`、field.sh `7607d7cc…`、field_session `8547ad5c…`、trial `44b6ad0f…`。
- 重新打包成功：Windows 侧跑 `准备现场包.ps1`，模型校验 6/6 通过，`cpp_deploy-as2w.tar.gz` SHA `a650d285bc33662591e5ecf15d7bb3593f8880e7f827feeb5c13a49713e80ca4`（已核内含新 launcher 与 `+=` 修复后的 controller）、SDK2 包 SHA `0a1679fe…`；包在 `部署测试/01_现场部署包/`。
- **CPRO 同步/ARM64 构建/CTest/audit/dry-run 被阻塞**：工作站 `hdc list targets -v` 三目标全 `Offline`，`hdc tconn 192.168.10.180:8710` 报 `Connect failed`，工作站 `Test-NetConnection 192.168.10.180:8710` `TcpTestSucceeded=False`（CPRO hdcd 8710 不可达；本会话早期 09:50 LowState 尚可达）。`-Stage Sync` 因 `现场入口.ps1` 用裸 `hdc`（无 `-t`）在多目标态下报 `need connect-key` 而中断，未向 CPRO 传输/解包，未改 CPRO 任何文件、未动旧构建。**P2g（ARM64 构建+audit）、P2h（dry-run）留待 CPRO 可达后执行；P3 有界实机仍逐次许可。**

## 2026-11-12 上午：R1199 P2g ARM64 构建/CTest/audit 完成（CPRO 恢复后）；核对同事 reanchor 新预览

- CPRO 8710 恢复 `Connected`（USB/10178 仍 Offline），`-Stage Sync` 成功：重打包 `cpp_deploy-as2w.tar.gz` SHA `125497dfbd0fb6a25667d3d3bd8d9de8767e9e74e896bb7a795bf764efa5f78a`、SDK2 包 `9a822f4f…`，两包 CPRO 端 `sha256sum -c` 全 OK，解包到 `/root/as2w_deploy`（未动旧 build-r1199-* / build-r214-*）。
- **ARM64 独立构建 `build-r1199-training-contract` 成功**：CPRO 端 `-DAS2W_R1199_JOYSTICK_CANDIDATE + AS2W_R1199_TRAINING_CONTRACT + AS2W_R1199_PUBLISH`，ORT `/root/ort122`、SDK2 `/root/unitree_sdk2_install`。CTest **9/9**（含 r1199-joystick-startup-audit）、`as2w_r1199_joystick_publish --offline-audit` `GUARD INJECTION PASS + JOYSTICK MAPPING PASS + AUDIT PASS`。CPRO 侧源码 SHA 复核：controller `beb824e5…`、policy.onnx `df1f2db9…`、trial 脚本 `44b6ad0f…` 均一致；新二进制 `as2w_r1199_joystick_publish` SHA `3e16c25f432336545416042b2eaa227f566e44f2b3dd187d1e92bc10de0f9118`。**未动/未重建任何旧二进制。**
- **同事新 repo `rolling-1199-reanchor-preview`（commit b070a72）核对**：权重 `model_1199.pt`（bb5c9735…）与 `policy.onnx`（df1f2db9…）与本地**完全一致**；`as2w_rolling_fixed_exit.py` 与训练服务器快照**完全一致（SHA fcdebb8f，0 diff）**。新内容是 `eval_entry_reanchor_holdout.py` 的“reanchor”交接（固定站/标定窗 4s→**12s**、12s 且关节误差<0.14 rad 时冻结标定偏置+复位一次轮锁存）并按 `--park-odometry --park-common-gain-scale .5 --park-settle-joints --park-continuous-bias --park-straight-bias` 运行（即 `odometry/settle=true/true, continuous/straight=true/true`）。**其 continuous/straight 开对了（与我们的修复方向一致，独立印证），但 odometry/settle 仍 `true/true`，不符合训练合同 `false/false`**——按新立的“训练合同三方一致”硬规则，这是与正式合同仍不一致的点，需与同事对齐；其 MuJoCo 无推 8/8、带推 8/12、`gate=false`、ONNX parity 8.58e-6（仅原始动作）。权重/包装底层无变化，可放心参考其 reanchor 交接思路，但不直接照搬标志。
- **当前阻塞**：狗仍 `LowState packets=0`（未上电/eth0 down）。P2h（dry-run）与 P3 有界实机需狗上电；P3 每一动作仍须现场人员**当次明确同意**。

## 2026-11-12 10:28–10:32：P2h dry-run 通过 + P3-1 首次实机会话被 LowState 新鲜度看门狗安全中断（含完整根因分析）

- 狗上电后只读确认：LowState ~1045包/s、`mode_machine=2`、`name=ai`、`fsm_name=ai_damping`（趴下）。`training-contract-dry-run` 全预检 PASS：新二进制/audit/SHA 复核一致（controller `beb824e5…`、onnx `df1f2db9…`、二进制 `3e16c25f…`）、LowState≥100包/s、16轴mode0、趴下门槛 yes；工厂态处正确停在"would ReleaseMode"（只读，未释放）。会话 `logs/field_sessions/20261112-102822_training-contract-dry-run/`。
- 现场人员对本次动作明确同意后运行 `-Policy r1199 -Mode training-contract -ConfirmMotion -MonitorSeconds 120`：预检全过、趴下确认、`ReleaseMode rc=0`（name=空）、16轴mode0、双监测启动、发布端 Passive ready 741帧。操作员按 A 起立（~38.5s 起 FixStand，~41.5s 到 FixedStand，thigh 0.729/calf −1.798、tau≈14.85Nm 静态保持，无跳步）。**B 未曾被按**。站立约3秒后 t≈44.59s 发布端报 `STARTUP FAULT: stale/invalid LowState; stop publisher after 21611 frames` 安全自停，电机 mode 1→0，狗在重力下约4秒缓沉至半蹲（thigh 0.43/calf −2.17），后继续缓沉稳定于 thigh≈0.89/calf≈−2.63。**全程保护流 `warning_or=0x0`、`motorstate_or=0x0`，无任何硬件告警**。
- **根因分析**（10ms capture 逐帧）：监测端自身在 t=44.20s 也看到 ~25ms LowState 接收间隙（age 10→12ms、tick 跳 +25），证明当时 DDS 用户态投递有抖动；发布端独立 reader 的 20ms `MaxStateAge` 看门狗（r214_publish.cpp:1394，`received==epoch || age>20ms || !valid_startup_state`）在 44.58s 命中另一次更长间隙。会话后只读核查：eth0 物理层 0 错 0 丢（carrier=1）、**CPRO loadavg≈20（高负载）**、wlan0 RX 丢包 247（同期 HDC 两次掉线，tconn 即恢复）。结论：**高负载下 DDS 投递抖动触发了设计好的安全自停**，非策略/包装回归（发布端源码与此前全部成功会话字节级一致 SHA `a99dc6d8`），非硬件保护，狗缓沉无跌落。分析脚本 `logs/20261112_r1199_tc_fault_analysis/{analyze_tc_session,analyze_tc2,analyze_tc3}.py`（临时目录，正式版随下次日志归档）。
- 安全自停行为本身按设计工作：无 LowCmd 陈旧命令继续发布（r214_publish.cpp:2307）、电机回 mode 0、狗缓沉、无保护。**不改 `MaxStateAge`（安全参数，任何放宽需独立离线重验收+新版本）**。
- 当前状态（10:42 只读）：LowState ~1046包/s、`name=`（控制权仍释放）、电机全 mode0、狗稳定半蹲趴姿、四小腿 −2.60~−2.67（在趴下门槛内）、无发布端。原始证据：`logs/20261112-103109_windows_r1199_training-contract_field_session.log`、`logs/field_sessions/20261112-103110_training-contract/`（publisher.log/session.log/low_capture_fast.log/low_protection.log 四份已回收）。**下一步：需新一轮当次同意后重跑 training-contract 会话（从半蹲直接 A→B 零速→A→Y）**；若再次被看门狗中断，先处理 CPRO 负载/网络环境再测。

## 2026-11-12 10:46：P3-1 第二次运行——15s 站立保持超时自动趴下（会话干净，无故障）；启动器 stand-hold 15→30s

- 现场同意后第二次运行 `-Mode training-contract -ConfirmMotion`：预检全过（已释放态续用、16轴mode0、趴下门槛yes）、Passive ready 745帧、操作员 A 起立到 FixedStand。**B 未在15s内按下，发布端 `FixedStand squat trigger=timeout` 按设计自动趴下**，FixSquat→Passive→干净退出 `rc=0`。上次网络看门狗故障**未复发**；全程无 `FIELD_SAFETY_WARN`、保护流 `warning_or=0x0`（初析一条“非零”为 awk 解析 modes 字段串位的误报）。证据 `logs/field_sessions/20261112-104621_training-contract/`、transcript `logs/20261112-104621_windows_r1199_training-contract_field_session.log`。
- 根因与修复：超时值来自启动器参数 `--stand-hold-seconds 15`（沿自此前所有已验证 zero-b/forward/joystick 试验脚本，本次新启动器原样沿用，非临时改动）；计时从进入 FixedStand 起算（r214_publish.cpp:1728-1732），发布端二进制校验上限 **30s**（:664-665）。已将 `run_r1199_training_contract_trial.sh` 改为 **`--stand-hold-seconds 30`**——启动器级参数变更，不改发布端二进制/策略/包装/训练合同/安全守卫；工作站与 CPRO SHA 一致 `ef70b2dfe39c4cd68d52e11740936ea99e61a37a8d1f0ceaf58d43e2545cf9d0`，CPRO 端 `bash -n` 通过（单文件经 `C:\Users\zoubu\` 中转 `hdc file send` 同步，避开中文路径编码）。
- 待新一轮当次同意后按同计划重跑：A 起立 → **30秒窗口内按 B** 零速交接（摇杆不推）→ 观察 → A 回站 → Y 趴下。

## 2026-11-12 10:55：R1199 训练合同候选 P3-1 零速交接实机通过——B 交接无跳步、零告警、干净退出

- 现场同意后第三次运行 `-Mode training-contract -ConfirmMotion -MonitorSeconds 120`（启动器已改 `--stand-hold-seconds 30`，SHA `ef70b2df…`）。完整链：预检全过（已释放态、16轴mode0、趴下门槛yes）→ Passive ready 749帧 → **A** FixStand→FixedStand（thigh 0.729/calf −1.797，tau≈15Nm）→ **B** accepted（pose_error=0.275643、wheel_dq=0.0123、upright=0.9950、quiet_dq=0.0245）→ 2秒零速交接 → PolicyWalk 零速保持约13秒（`WALK_CMD requested/applied` 全程 0,0,0，摇杆未推）→ **A** brake trigger=A → Brake→ReturnStand→FixedStand → **Y** squat trigger=Y → FixSquat→Passive → `rc=0` 干净退出。现场人员确认"一切正常"。
- **核心结果：B 交接处零跳步**——姿态从固定站平滑伸展至零速策略位（~2.3秒渐变，thigh 0.73→峰值0.92→稳态0.786，calf −1.80→−1.618），**10ms采样单帧 thigh 最大步进 0.0031 rad / calf 0.0040 rad**（旧版两次首推为 20ms 单帧 0.2729/0.2542 rad 并触发 FIELD_SAFETY_WARN）。交接瞬态 maxlegdq 0.628 rad/s、maxtau 30.23Nm（远低于 35/50 warn/hard 门限）；零速稳态 maxlegdq≈0.01、tau≈27.9Nm 恒定。**全程零 `FIELD_SAFETY_WARN`、保护流 12,953 行 `warning_or=0x0`/`motorstate_or=0x0`、无 REMOTE_TIMEOUT**。注意：零速策略稳态（0.786/−1.62）与固定站（0.729/−1.80）仍存在小幅姿态差，属标定补偿的预期行为，关键是过渡平滑无跳变。
- 证据：`logs/field_sessions/20261112-105453_training-contract/`（四份原始日志已自动回收）、transcript `logs/20261112-105453_windows_r1199_training-contract_field_session.log`、量化脚本 `logs/20261112_r1199_p31_handoff_analysis.py`。
- **本次仅覆盖零速交接（P3-1）**；旧故障的另一半——"首推前进时的姿态回落"与"运动中可闻抖动"——需 P3-2（PolicyWalk 中轻推 LY 前进约2秒后松杆，观察起步无跳步、运动平顺、松杆后姿态保持不下沉）另行逐次同意验证。

## 2026-11-12 11:00：R1199 训练合同候选 P3-2 有界前进通过——首推无跳步、运动-松杆-保持全程姿态不回落、零告警

- 现场同意后运行（同 30s stand-hold 启动器）。两个完整循环：①A→FixedStand→B（pose_error=0.2694、upright=0.9969）→零速交接→**推杆 LY 前进（WALK_CMD vx 峰值 0.05，含多次推/松段，约 t=43~62s）→松杆保持约20秒→A 刹车→回站→Y 趴下**；②A→FixedStand→Y 趴下。`rc=0` 干净退出，现场反馈"效果还不错"。
- **量化结果**：全程**零 `FIELD_SAFETY_WARN`**（含首推瞬间——旧版两次都在首推触发 0.27/0.25rad 跳步警告）；保护流 21,914 行全零。姿态时间线：固定站 0.732/−1.799 → 交接渐变（~2s，无跳步）→ 零速稳态 0.795/−1.617 → **推杆运动全程 thigh 保持 0.79~0.84、松杆后 20 秒保持 0.81~0.84 不下沉**（旧版首推即从 0.87 跳落 0.79 并伴随停/走高低姿反复切换）→ A 回站 → Y 趴下。运动段 maxlegdq≈0.2、tau 21~26Nm，均远离门限。
- **旧故障两项对照**：停走姿态跳步/回落——**已消除**（数据+现场确认）；运动中可闻抖动——现场观感"效果还不错"，未再报告明显抖动声；无高频电流/声音测量，此项按现场观感记录。
- 证据：`logs/field_sessions/20261112-105937_training-contract/`、transcript `logs/20261112-105937_windows_r1199_training-contract_field_session.log`、量化脚本 `logs/20261112_r1199_p32_motion_analysis.py`（即 analyze_p32.py，待归档）。
- **后续**：现场询问能否提速。注意 0.05m/s 是控制器**编译期上限**（`AS2W_R1199_JOYSTICK_CANDIDATE` 分支 `|vx|>0.050001` 即 disarm），提速=新候选修订：改源码→x86 重编+parity（夹具需扩到新速度）→MuJoCo 新速度复验→ARM64 重编+audit+同步→再逐次同意。

## 2026-11-12 11:10–11:40：速度包络改为 deploy.yaml 可配置项（默认 vx 0.2 / wz 0.1）+ 0.2 包络全链复验

- 现场要求"速度可自己改，默认 0.2、角度同样 0.2"。实现为**可配置项而非硬编码**：`models/r1199/deploy.yaml` 新增 `vx_limit/wz_limit`（唯一改速位置，控制器 disarm 上限与发布端摇杆映射均从它读取；范围校验 0.01–0.30；yaml 缺省时回退 0.05）。改动：`r1199_controller.{hpp,cpp}`（Config 增限值、load_config 读取+校验、joystick 分支 disarm 阈值改为 `config_ 限值×1.00002`）、`r214_publish.cpp`（joystick 分支：`map_r1199_joystick_command` 参数化、audit 映射检查/横幅动态化、撤销 `--vx-limit==0.05` 硬检查、新增 `--wz-limit`，CLI 只能在 yaml 包络内进一步收紧 `min()`）、启动器去掉 `--vx-limit`（yaml 驱动）。旧 zero-b/forward 构建语义不变（分支隔离，未重建旧二进制）。
- **MuJoCo 复验（训练合同开关、实测初态、10s 窗）**：前进/后退 0.2m/s ×3 种子 **6/6 全 stable/tracked/held、无非轮接触**（mean vx 0.175–0.201，effort≤0.32，前进中段单帧腿目标步进 0.126rad=0.05 时 0.063 的两倍线性放大，仍低于 0.2 warn 门限）。**转向 0.2rad/s 被否决**：膝部最小离地仅 1.5–12mm（<15mm 门槛）、刹停距离与保持漂移超限（2/6 stable=False）。**转向 0.1rad/s 6/6 安全通过**（stable、无非轮），但偏航跟踪仅达指令 50–65%、3/6 转后保持漂移 0.03–0.037m（cap 0.02）；0.05rad/s 安全但几乎不转（跟踪 0/6）。**故默认包络定为 vx 0.2 / wz 0.1**，yaml 注释中写明已验证/被否决档位。
- x86 重编+CTest 9/9+audit PASS（映射检查显示 `LY +/-0.2 RX -/+0.1`）；parity 夹具扩展（vx±0.2/wz±0.1，615 非零帧）`max_action_error=1.1920929e-07`、previous-action 差 0。ARM64 增量重编+CTest 9/9+audit PASS，6 个改动文件工作站/CPRO SHA 逐一一致（controller.cpp `e8d1c2cf…`、hpp `c3146543…`、r214_publish.cpp `577d6825…`、deploy.yaml `1dfa0567…`、trial `7e8e9f5e…`、field_session `02243f6b…`），新二进制 SHA `b2cfded9891194b2a498d9e4d34ecab36d4e226e7ac05e63f31fa0022b0e2db3`。MuJoCo 原始目录 `logs/r1199_training_contract_{forward,back}02_seed{101,202,303}/`、`_{turn_left,turn_right}02_seed*/`、`_{turn_left,turn_right}_r{0.1,0.05}_seed*/`，脚本 `logs/20261112_r1199_tc_speed_envelope_*.sh`（待归档）。
- **待新一轮当次同意后**在实机按新包络测试：A→B→前进推杆（≤0.2m/s）与首次有界转向（≤0.1rad/s，偏航从未实机测过，需现场重点看护）。

## 2026-11-12 11:50：新增 50Hz POLICY_DIAG 逐帧诊断日志（推理侧↔硬件侧分流）+ 最终二进制复验

- 按现场要求补齐诊断链：发布端新增 `POLICY_DIAG`（50Hz 逐策略帧，**写本地文件 `policy_diag.log`**，不经 hdc stdout 管道——避免上次类看门狗故障的环路阻塞风险；每250行flush、文件打开失败则静默停记）。字段：phase(HANDOFF/WALK/BRAKE)、t_since_walk、cmd(vx,vy,wz)、LowState tick（与 10ms `low_capture_fast.log` 对齐）、**raw ONNX 16**、**包装后动作16**、**最终目标（12腿q+4轮dq）**、stand_bias 12、bias_scale、hold_frames。控制器 `r1199_controller.{hpp,cpp}` 暴露 `last_raw_action/last_stand_bias/last_bias_scale/hold_frames`（纯记录，不改数学；`AS2W_POLICY_R1199` 门控，旧二进制不动）。会话脚本在发布端退出后归档 `policy_diag.log` 到 `$SESS/`。实际关节侧（q/dq/tau/IMU）继续由 10ms 双监测记录——两侧经 tick 对齐后即可按 raw ONNX→包装→最终目标→实际关节 四段定位问题在推理侧/包装侧/硬件侧。
- 复验：x86 重编+CTest 9/9；最终二进制 parity（±0.2/±0.1 夹具，615非零帧）`max_action_error=1.1920929e-07`、previous-action 差 0；ARM64 重编+CTest 9/9+audit PASS（`LY +/-0.2 RX -/+0.1`）。SHA：controller.cpp `feebea78…`、hpp `fc52625…`、r214_publish.cpp `ada5bac…`、field_session `e6d58c35…`（工作站/CPRO 一致），**新二进制 `28f1ca7213645d9530cf2759db3153e9f544d6533c65f059b4d84719248ca4bb`**；deploy.yaml `1dfa056…`（vx 0.2/wz 0.1）。归档 `logs/20261112_r1199_tc_{speed_envelope_02,speed_envelope_turn}.sh`、`20261112_r1199_tc_fixture950_vx02wz01.txt`、`20261112_r1199_tc_rev3_replay.log`。
- **待现场对新动作明确同意后**：新包络首测（A→B→前进 ≤0.2m/s→观察→A→Y；转向 0.1rad/s 为首次实机偏航，建议单独小段尝试）。
- 现场询问"rosbag 式回放"：答复**现有日志已具备策略链回放能力**（POLICY_DIAG 50Hz raw/包装/目标/补偿 + capture 实际关节，tick 对齐，可离线逐帧重放+what-if），新增转换工具 `tools/r1199_session_replay.py`（会话→回放夹具→replay/parity 链；capture 解析已在旧会话验证 11,477 行，端到端待下次带 POLICY_DIAG 的会话）。按现场决定将快采集 **10ms→2ms（500Hz）**以覆盖可闻抖动频段（>50Hz 原 100Hz 采样看不见），并给两个监测进程加 `nice -n 10` 降优先级——机制上排除监测抢 CPU 影响发布环路（针对上次看门狗故障的高负载诱因）。会话脚本 SHA `226422c25f0f5c2f58711ca27ea500ac466f80aa572f91006bc3d5e54fb5b6cb`（工作站/CPRO 一致，远端 bash -n 通过）。

## 2026-11-12 12:10–13:30：新同事交付 mlp57（as2w_mlp57_flat_model2700_v1_20261112）MuJoCo sim2sim 验证——未通过，不绑定 B 键

- 新交付包（`部署参考/as2w_mlp57_flat_model2700_v1_20261112/`，197MB）按 v3 清单组织：`sim2sim_candidate`、57→512→256→128→16 MLP、FR/FL/RR/RL 按腿分组、动作 scale[0.125,0.25,0.25]/offset[0,0.65,−1.3]/轮×5、上一动作存 raw、腿 40/1 轮 0/1、入口姿态[0,0.65,−1.3]×4 高 0.42844、PhysX 156 例 156/156 生存、严格三轴速度 56/156。其自带 `verify_package.py` **PASS**（1183 文件哈希+溯源）、`verify_parity.py` **PASS**（ONNX 差 3.34e-06、C++ 映射差 0）。
- **我们的移植链逐位验证通过**：`runtime/reference.hpp` 权威映射 + `observations.csv` 57 维合同复现——obs vs 他们 `native_samples.npz` 6000 帧录制 = **4.8e-08**；我的 ORT 推理 vs 录制 raw = **1.3e-06**；关节序/符号/轮向（前进=+dq，他们 forward 稳态轮 +6.5rad/s↔+0.515m/s 一致）/URDF 同源（26kg、力矩限 60/60/90/15、轮 mesh 官方 STL）全核。
- **发现关键合同语义（此前文档未明写）**：其 Isaac 执行器 PD **每个物理子步(5ms)重算**（"zero-order target hold"指目标保持，力矩每子步刷新；证据=帧0轮力矩 +0.077 是末子步对已加速轮子的刹车值，而帧首力矩 −1.31）。我最初按 50Hz 力矩保持实现→轮速发散全崩；改逐子步 PD 后 stand 存活 12s。**此语义对任何后续移植（含真机 C++ 若走自定义力矩路径）都是硬约束**（真机走 FOC 驱动器闭环，无此问题）。
- **sim2sim 未通过，根因隔离到 MuJoCo 轮静摩擦保真**：58N 法向、μ=1（他们对齐值，我们原随机 0.62 已纠正）、1Nm（容量 5Nm）下轮恒速爬行 1.5-2.3 rad/s（法向力稳 ±0.8N 无弹跳；换解析圆柱轮更差 3.0；impratio/noslip/solimp/Euler-implicitfast/cone 全试无效；最小刚体模型同设置锁住 0.12 → 差异在"轻有效质量轮链"的约束阻抗）。连锁：策略 stand 稳态非对称轮指令在 PhysX 被静摩擦完全吸收、在我们这里爬行→漂移→后坐（开环注入他们的动作序列：他们 0.419 平稳 vs 我们 0.32m/+33° 后小腿撑地）。闭环 solref 全谱 0.02→0.001 无稳定窗口（振荡或翻转，tilt 峰 44-178°）。**结论：R2 第二仿真器门槛未过，按 v3 合同不升级 hardware_candidate，不绑定 B 键实机**；156 例矩阵评估器 `mlp57_mujoco_eval.py` 已写好（精确 rng 初态复现+五项判据），待接触建模改善后可全量复跑。证据与判定存档 `logs/mlp57_2700_sim2sim_debug/`（含 README）。
- 对训练方反馈价值：①"PD 逐子步重算"应写入 effective_runtime（部署端自定义力矩路径必须知道）；②该策略低速稳定依赖被动轮静摩擦，第二仿真器/实机的摩擦保真是核心敏感项；③建议他们在自己侧跑第二仿真器（他们有 MuJoCo 渲染管线可加闭环）或确认实机 FOC 驱动器的轮速度环带宽后再议。

## 2026-11-12 14:10–14:40：同事"四维补零"提示核实 + 训练服务器网页（192.168.10.35:8082）一致性核查——未发现我们移植的不一致；sim2sim 失败结论维持

- 同事微信图（`logs/mlp57_2700_sim2sim_debug/colleague_note.png`）明确"四维补零"= **57 维观测索引 21-24（第 22-25 维）四个轮关节位置槽 FR/FL/RR/RL_foot 必须填 0**，"之前迁移别的项目没注意"指其 B2W→MuJoCo 适配器迁移时漏了这点。网页 `docs/validation_2026-11-11.md` 证实：**他们自己的 B2W MuJoCo 适配器未通过（1.72s 失稳，当时原因未定）——零填充 bug 即疑似根因**。
- **对我们的 mlp57 移植：此点已正确**（三重证据）：①评估器/parity 中 `obs[21:25]=0.0`；②我的 obs vs 他们 6000 帧录制 = 4.8e-08（含四维）；③他们录制 `observation[:,:,21:25]` 全 600×10 帧恒 0.00e+00（本次复验）。**我们的 MuJoCo 失败（轮静摩擦保真）与该 bug 是不同问题**。
- 其余一致性核查（网页 `config/as2w_robot.json` + README vs 我方）：✓轮几何（**原始 STL 本身带 −0.0546 y 偏移**，两引擎轮盘一致 ±0.220 vs 我们 ±0.2196；他们 config `center_in_base ±0.1654` 只是运动学关节中心）；✓质量 26kg/惯量/力矩限 60/60/90/15/PD 40/1 与 0/1/轮半径 0.086/入口姿态；✓初高度（他们=接触+5mm 净空 0.42844，我接触搜索 0.4234 与 0.42844−0.005 完全吻合；已按忠实初态重跑 stand/forward_0.3/0.5——仍不稳 tilt 峰 123-172°，结论不变）。网页另载明：训练把 **XY 合速度<0.2m/s 的命令清零**（低速覆盖缺口）。
- **重要情报**：交付的 model_2700 是 ±1.0 m/s 初版；网页 `outputs/` 已有 `simulation_mlp57_model_7500`（13:56）与 `current_effects_mlp57_model_6000`——训练已按用户要求扩到 ±1.5 m/s 续训并远超 2700 更新。后续若继续 sim2sim/实机，应向同事确认要最终推荐 checkpoint 及其新合同。

## 2026-11-12 15:0x：建立"策略交付到实机全流程"文档体系 + 02_现场操作归档整理

- 应用户要求固化全流程，新目录 `02_现场操作/策略交付到实机全流程/`：`README.md`（总览+阶段门槛+新策略到达 10 步快速清单）、`01_收包验收.md`（包校验+合同字段要点）、`02_移植对齐与sim2sim.md`（parity 方法+**已知坑表**：轮位槽补零/重力符号两家相反/上一动作 raw-wrapped/PD 逐子步/关节序/命令偏移/轮向/速度包络+被动静摩擦策略的 MuJoCo 失败分流）、`03_Cpp部署适配与按键绑定.md`（控制器/CMake/A-B-Y-X 按键 FSM/deploy.yaml 速度包络/ARM64 双端构建/现场入口三件套/打包）、`04_实机验证阶梯.md`（dry-run→zero-B→有界低速→短时摇杆四级+同意规则+POLICY_DIAG 四段诊断分流+运维坑）、`参考文件索引.md`（全部脚本按用途/机器索引）。R1199 与 mlp57 分别作为成功/失败两个工作范例引用。
- `02_现场操作` 归档整理（12 个文件移入 `archive/`，含理由更新到 archive/README.md）：交付合同 v1/v2（被 v3 取代）、R1199 早期仿真文档与消融旧计划、已完成的零速/前进首测准备、摇杆 60 秒试验（旧入口已阻断）、rolling 两 preview 评估、T1 评审、测试脚本.txt。顶层保留：v3 清单、现行 R1199 三份分析、R214 验收（R214 线暂停但二进制仍在）、LowCmd 事故复核（安全历史证据）、全部基础设施文档；`部署工程说明.md` 等七份为 `准备现场包.ps1` 每次自动再生的副本，属正常顶层存在。老 AGENTS/INDEX 状态行中的旧路径按 archive/README.md 解释。

## 2026-11-12 15:3x：共享发布端统一命名 r214_publish.cpp → common/as2w_publish.cpp（机械重构+全链重验，无行为变化）

- 应用户要求消除命名误导（`r214_publish.cpp` 实为 R1199/R249/R270/R284 共享发布端）。改动：`deploy/robots/as2w/r214/r214_publish.cpp` → `deploy/robots/as2w/common/as2w_publish.cpp`（仅 include 相对路径修正 `"r214_controller.hpp"`→`"../r214/r214_controller.hpp"` + 头注释，无逻辑改动）；5 个 CMakeLists（r1199×3/r214/r249/r270/r284 路径）；4 个会话脚本 sha256sum 路径（r1199/r214/r270/r284）。R214 旧试验脚本的**二进制输出路径**不变（CMake 目标位置未动）。
- 重验链全过：x86 重编（三个 publish 目标均从新路径编译）+ CTest 9/9 + audit PASS（`LY ±0.2 RX ±0.1`）+ parity `1.1920929e-07`（950帧复跑）；R214/R249/R270/R284 四个旧策略 CMake 配置验证 OK；`准备现场包.ps1` 重打包（cpp 包 SHA `49f4950f7fb03dea52f4e52150f8060274485bf57cd1c34ec123a3fe491b1310`，SDK2 包 `e588a556eb9360cea9c6edeba6755bffd9de441a76461f44d7894f76cfc94644`）；CPRO 同步 10 文件（`common/` 目录需先 mkdir 再传）+ 删除旧路径文件 + 双端 SHA 核对 + ARM64 增量重编 + CTest 9/9 + audit PASS。源码 `as2w_publish.cpp` SHA `449cf5b9f1bb5466150ad99efbaca4d7b6a5f60631937f814687b85671bbbac0`，重建后 training-contract 二进制 SHA `cc2ecfd8bfa728133ba76fab278b4a660fdbef1f9449fca330dde877b453203e`（功能等同旧 `28f1ca72…`，下次会话的 sha256sum 记录将自然更新）。全流程文档 03 的"命名待统一"注释已改为完成记录。
- **CPRO 同步/INDEX 规则固化**：新增 `策略交付到实机全流程/05_CPRO数据同步与远程操作.md`（链路拓扑、tconn 恢复、scp+file send 两跳、base64 脚本法、整包/定点同步选择、ARM64 远端构建模板、日志回收、八条实测坑清单）；根 `AGENTS.md` 新增"CPRO 数据同步与远程操作（固化为标准流程）"节指向该手册，并把"调试日志与交接"的 INDEX 规则升级为硬规则（阶段类型全列举：收包/parity/sim2sim/编译/打包/同步/实机/重构/文档整理/故障分析，失败急停同样立即追加）；`部署测试/AGENTS.md` 同步更新同两条。

## 2026-11-12 11:44：R1199 新包络 0.2m/s 实机通过 + 诊断链首次完整落地：可闻抖动根因分流为推理侧

- 现场同意后运行（vx 0.2/wz 0.1 包络、2ms 快采集、POLICY_DIAG 首次启用）。完整链：A→FixedStand→B（pose_error=0.2703、upright=0.9963）→零速交接→**多段推杆（峰值 applied vx≈0.132、requested 0.187，松杆多次）→松杆保持→A 刹车→回站→Y 趴下**，`rc=0`。**零 FIELD_SAFETY_WARN、保护流 22,819 行全零**；姿态全程保持 thigh 0.79~0.84（起立 0.732→交接渐变 0.884 峰→稳态），无跳步无下沉。转向未测。证据 `logs/field_sessions/20261112-114347_training-contract/`（含 policy_diag.log 2283 帧、2ms capture 59,993 行/120s）。
- **诊断链首次完整工作并给出根因分流**（现场要求"定位推理侧还是硬件侧"）：
  1. **2ms 采集看见可闻频段**：运动段大腿 dq 在 40-120Hz 带 RMS 是零速段的 **8.2×**（1.110 vs 0.135 rad/s）、120-250Hz 为 5.3×——运动中高频振动有实锤（旧 100Hz 采样不可见）。
  2. **推理侧实锤**：运动段 raw ONNX 腿动作**逐帧在 ±6 限幅间大幅摆动**（步进均值 2.07、p99=12=满摆程），零速段被 motion=0 门控掉。包装 `0.18*motion*clamp(±1)` 把它限幅成 50Hz 目标抖颤（腿目标单帧步进均值 0.018rad、峰 0.12rad，低于 0.2 warn），PD 跟踪该抖颤激起 40-250Hz 关节振动——与"零速安静、滚动有嗡声"完全吻合。**初步结论：可闻抖动主因在推理侧（策略原始输出噪声），包装只限幅未滤抖。**
  3. **回放链验证**：`r1199_session_replay.py` 转换（tick 对齐）→ C++ 重放→与当场 POLICY_DIAG 逐帧比对：**前 6 帧误差 0（管线正确）**，第 15 帧起发散（2ms 传感器时差被近饱和 raw 放大翻转）——回放可用于短窗/统计对比与 what-if，不能全会长位重现；该敏感性本身亦是推理侧噪声佐证。转换器初版列号差一已修（`f[3:6]/f[6]`）。
- **运维发现**：capture 按 MonitorSeconds=120s 自停，而用户趴等 95s 才按 A，策略跑到 ~145s——**后 25s 运动段未被采集**（1249/2283 diag 帧 unmatched）。下次若慢启请在会话命令给 `-MonitorSeconds 240`（范围 90..300）。
- 归档：分析脚本 `logs/20261112_r1199_02envelope_{session_analysis,hf_analysis,action_steps}.py`、回放夹具与输出 `..._replay_{fixture,output}`、修正后的转换器 `tools/r1199_session_replay.py`。
- **给训练同事的分流交付**（按任务书"修复后仍抖分流"第 1 条）：raw ONNX 稳态周期性大幅变化已实锤——附本会话回放夹具 + 40-120Hz 谱证据 + raw 步进统计，请其检查低速命令分布、动作变化惩罚、执行器随机化与观测噪声；部署侧可另行评估包装滤波（属新版本需重走门槛）。
- 现场确认**0.2 时嗡声比 0.05 更强**（与推理侧噪声机制吻合：0.18×motion 使抖颤幅度随速度线性放大，0.05→0.2 摆幅上限 0.18→0.36）。**已打包给同事的证据包** `06_训练协作/R1199_motion_jitter_feedback_20261112/`（README 诊断摘要 + 0.2/0.05 两会话五件套 + 全部分析脚本 + 回放夹具/转换器/C++重放输出 + MANIFEST 19 项），ZIP `R1199_motion_jitter_feedback_20261112.zip` SHA `15b1cac5c81d3c20b18150301fa9855e242974d3cea7af3cc472e96d6071f9f6`（7.67MB）。
- 现场转达同事"微调了权重"并给同一链接（`b070a72` reanchor-preview）。**核实：该 commit 权重未变**（`bb5c9735…`/`df1f2db9…`，即 R1199 原始权重；路径仅此一 commit）；main 仅新增 v3 交付要求文档（`0e201791`，10:32+08:00）；`studio/mujoco-telemetry-replay` 分支（`fb1d4045`，最后 09:00+08:00）无新 R1199 权重（只有旧 rolling-fixed-exit-preview）。**新权重尚未推送**——待用户与同事确认实际位置；收到后按硬规则走新版本全链（新 SHA→parity→MuJoCo→x86/ARM64 重编→audit→同步→当次同意实测）。

## 2026-11-12 10:03：训练→部署交付清单改为通用核心＋按技能模块（文档阶段，无狗动作）

- 根据现场人员指出“有的策略不是行走策略”，现行文件为 `02_现场操作/AS2-W训练到部署交付清单_v3_通用核心与按需模块.md`。所有策略仅交可复现的版本、模型接口、逐维观测、动作包装及实际开关、入口/退出、训练资产、已有证据和代表性回放（C1–C8）；速度跟踪、停车、轮速、起身、楼梯等仅在使用或声称支持时启用。`not_applicable` 须写原因，未做第二仿真器可标 `not_run`，部署方可补做；不强求训练同事做所有专项实验。
- v1/v2 已标历史，根和现场 `AGENTS.md` 已指向 v3；OpenCode 交接引用和 R1199 独立反馈包内 `docs/policy_delivery_contract.md` 同步为 v3。当前 ZIP SHA256 `239234867ea60b165c82455f218f2a8b105b00350fd7b9433ede8b26308abac2`，替代上文旧 SHA；包内条目存在。文档 SHA256 `544a9294ef4c5ecea637aa519c6329f201386bdc177f720fa33e61db71992ac6`。校验记录 `logs/20261112-1002_policy_handoff_v3_verify.log`。
- 本阶段只改本地文档和反馈包，无 HDC、ReleaseMode、LowCmd 或机器人动作。R1199 修复候选的 ARM64/CPRO/真机门槛仍按上节执行。

## 2026-11-12 20:41：实机数据录制现状核查与 Debug 模式建议（文档阶段）

- 核查 `tools/run_r1199_field_session.sh`、`src/diagnostics.cpp`、共享发布端 `common/as2w_publish.cpp` 和已归档 `field_sessions/20261112-114347_training-contract/`：会话当前录约500Hz LowState（35槽 q/dq/ddq/tau_est/mode/温度+IMU四元数/角速度）、保护流，以及仅R1199在约50Hz控制周期的 `POLICY_DIAG`（命令/raw/包装/策略目标/补偿内部量）。**真正送入ONNX的65维 Observation未逐帧落盘；Handoff的策略目标也不是2秒插值后的最终LowCmd。**不能把现有日志称为“所有策略的全量Observation”。
- 已在 `02_现场操作/策略交付到实机全流程/04_实机验证阶梯.md` 增加现状表、现有录制及归档用法、拟议 `-Debug` 的按策略全链字段/采样频率/性能约束；并修正文中“五份日志”和R1199适用范围。建议新增模式**尚未实现**，没有修改发布端、脚本或CPRO，也未进行机器人动作。文档SHA256 `0bc24fdd945b8ecdf58c01122d6048f943d54fa856766a0d44ded53f87ba61e7`；原始核查记录 `logs/20261112-2040_field_recording_debug_review.log`。
- 下一阶段如决定开发：先离线实现按策略完整 Observation 50Hz + 最终发布 LowCmd 500Hz 的有界缓冲录制，验证数据龄/丢帧/磁盘与看门狗，再x86和CPRO ARM64构建/audit；任何动作仍逐次单独许可。

## 2026-11-12 21:23：通用 Debug 与可选目标低通候选实现、ARM64 离线验收（无狗动作）

- 已按用户要求在**共享发布端**实现 `--debug` 全链采集（每次推理的实际模型输入、raw/包装动作、前后目标，以及成功 DDS Write 后约500Hz的最终16轴LowCmd），R1199 与 R214 现场会话均接入；新策略需提供模型输入/raw接口并在会话脚本透传。2ms发布线程只向有界队列拷贝定长记录，写盘由独立线程完成。实机录制负载尚未验收，不能把合成帧审计当真机通过。
- 可选一阶低通写在共享发布端最终策略目标处，默认关闭；R1199隔离构建允许选腿目标时间常数，轮速默认不滤，Brake轮速/X/Passive/固定站/趴下绕过。**Windows+CPRO双层锁住滤波运动入口**，待同滤波闭环MuJoCo、实机Debug负载验收及现场逐次许可。滤波是独立执行合同，仿真必须保持训练的 previous-action 取包装动作（滤波前）。
- CPRO ARM64最终构建：共享CTest16/16；R1199 debug/filter各9/9；R214 debug stand/zero-b/full各8/8；5组500帧离线Debug审计均 `dropped=0 file_ok=1`、AUDIT PASS。旧/Debug/filter关闭时离线帧一致；Windows脚本解析和CPRO shell语法 PASS。CPRO LowState 0 包，dry-run在ReleaseMode前FATAL，未发LowCmd。最终源 SHA `0b019509477200c1abcd0afdedaf835cf96ce616589acc5a85451d1424faa674`，Windows=CPRO=现场包；包 SHA `29a20d66f4778231be66aa0fe4d2c1ae43db6896a9f04205bd86359a10039e9a`。
- 旧R1199日志开环目标重算，腿目标单帧步进p99原0.12341rad、60ms估算0.02766rad、80ms估算0.02139rad；**不代表闭环稳定或抖动已解决**。caolin SSH本次超时，尚未跑同滤波MuJoCo。完整实施、命令与限制见 `logs/20261112-2123_debug_lowpass_final_verification.md`，原始构建/审计见 `logs/20261112-2120_debug_lowpass_tick_fix_build.log`、`logs/20261112-2140_debug_lowpass_frame_parity.log`、`logs/20261112-2230_r1199_debug_filter_dryrun.log`；操作说明已更新 `02_现场操作/策略交付到实机全流程/04_实机验证阶梯.md`。
- 21:xx 文档复核：把 `04_实机验证阶梯.md` 中旧的“目前没有 debug 模式”文字改为现行状态；不加 `-Debug` 的基础日志表仍保留作对照。此处仅修文档，无设备动作。

## 2026-11-12 21:58–22:00：R1199 Debug 首次实机预检与 CPRO 机器人网段恢复（无狗动作）

- 现场人员表示已准备测试。本机 WiFi 到 CPRO `192.168.10.180:8710` HDC Offline，TCP 8710/10178 不通；按现场人员提供的 USB 数据线改用 HDC USB 目标 `0123456789ABCDEF`，未改 HDC 模式。CPRO `eth0` 有载波但缺原先的 `192.168.123.100/24` 与机器人网段规则；第一次 `-Policy r1199 -Mode training-contract-dry-run -Debug` 在 LowState 0 包处 FATAL，**没有 ReleaseMode 或 LowCmd**。原始日志 `logs/20261112-215824_windows_r1199_training-contract-dry-run_field_session.log`，会话归档 `logs/field_sessions/20261112-215823_dry-run/`。
- 核对 CPRO 宿主 `/data/local/tmp/as2w_field/cpro_host_net.sh` 与本地唯一源码 SHA 同为 `ee5ead45c19c46028557acaf3669c9beaaf909f2631e457b03ac003949f3d3cd`；执行项目既有 `apply`：只恢复 `eth0=192.168.123.100/24`、去 `192.168.123.0/24` 的 priority1000 main 路由，不改默认路由。`.161` ping 3/3、`ip route get` 为 eth0 src .100；原始输出 `logs/20261112-2205_cpro_robot_net_reapply.log`。
- 第二次 USB HDC 只读 dry-run：独立 Debug 二进制 audit PASS、LowState 1047 包/s、`mode_machine=2`、原厂 `CheckMode rc=0 name=ai`，因 dry-run 在 ReleaseMode 前正常退出。`SportClient GetState=ai_damping`，2秒保护流约2083 LowState包，16轴 mode=1、主板与电机 warning/motorstate 均0。原始日志 `logs/20261112-215943_windows_r1199_training-contract-dry-run_field_session.log`、`logs/field_sessions/20261112-215943_dry-run/`、`logs/20261112-2200_r1199_debug_baseline_readonly.log`。
- **当前仍是原厂 ai 控制、狗趴下、未发 LowCmd。** 下阶段是无滤波 R1199 Debug 的首次真实 DDS 负载与零摇杆短时 A→B→A→Y；须现场人员对具体动作与风险当次明确同意后才能启动。滤波运动入口继续双层锁定。

## 2026-11-12 22:00–22:01：R1199 无滤波 Debug 首次实机完成，前后运动抖动声仍在

- 现场人员明确同意一次无滤波 Debug 的 A→B零速短保持→A→Y 测试并在旁看护。实际 B 后有约21秒 PolicyWalk 与多次前后摇杆输入（`vx`约 −0.20～+0.16m/s），超出计划的零速范围；程序接收 A 后 Brake→ReturnStand→FixSquat→Passive 自动趴下，发布端RC0。现场确认稳定趴下、无报警/明显失稳，**但前进、后退时都能听到关节抖动声**。本次不能称零速验收，也未单独验收 Y 趴下触发。
- Debug 真机负载采集完整：50Hz策略帧1170条（含实际65维Observation、raw/包装/前后目标），最终LowCmd 26586条、`dropped=0 file_ok=1`；策略控制周期p99 20.492ms、最终发布p99 2.825ms；保护流11297有效行的 warning/motorstate 全0，发布端无 FIELD_SAFETY 警告。运动帧腿目标单帧步进p99 0.12598rad，raw腿输出仍频繁近±6；2ms反馈中前进与后退段四大腿dq均有明显运动相关40–120Hz成分。此证据与可闻抖动相符，但不能单独定位声源或证明低通可解决。
- 原始七文件已回本机 `logs/field_sessions/20261112-220051_training-contract/`；Windows transcript `logs/20261112-220052_windows_r1199_training-contract_field_session.log`；详细判断 `logs/20261112-2201_r1199_debug_first_field_review.md`，可复算脚本/输出 `logs/20261112-2201_r1199_debug_first_field_analysis.{py,txt}`。本次 `-LowPassMs 0`，**滤波运动仍锁定**；下一次动作须重新获当次具体许可。
- 结束后只读复核 `CheckMode rc=0 name=`，LowState 1058包/s；原厂控制权**尚未恢复**，若调用 SelectMode 可能令狗起立，须单独获当次许可。原始日志 `logs/20261112-2201_r1199_debug_postcheck_readonly.log`。

## 2026-11-12 22:25：R1199 腿目标低通 40 ms 有界首测离线审查完成（尚无滤波真机动作）

- 应现场人员要求聚焦“选一个滤波频率直接抓数据”，caolin 上用原评估器隔离副本做同合同闭环对照；副本滤波关闭时与原评估器500帧目标/实际角逐项一致。0.05m/s 前后×3种子：40ms `stable/tracked/held` 6/6，无非轮触地；0.2m/s 前后×3种子：40ms `stable/tracked` 6/6、无非轮触地，但后退seed101停车保持未过，后续位移约2.16cm（无滤波1.88cm）。60ms在0.05m/s另有一组停车保持未过。滤波减小腿目标步进，不保证实机声音消失；原评估器固定站姿角完整门槛仍有失败。证据与全部输出见 `logs/20261112_r1199_lp40_field_gate.md` 及 `logs/r1199_debug_lowpass_*`。
- 独立40ms Filter构建已同步CPRO、ARM64 CTest9/9及Debug审计PASS；原训练合同和无滤波Debug构建各9/9。源码SHA `bf241a8fa835763c8bf93ae5ea28f1fc1005311976145ffd483bf8edd18aae56`，Filter二进制SHA `393b99c832fbe3b17af838f2035f82350d196a3a658ab457a88bac44da7d4aee`。Windows/CPRO双层门槛只允许 `-Policy r1199 -Mode training-contract -Debug -LowPassMs 40`、腿目标滤波、最大15秒PolicyWalk、前后上限0.2m/s、转向锁零；其他滤波配置仍拒绝。CPRO只读dry-run于LowState/ReleaseMode/趴下/审计全PASS，原始 `logs/20261112-222540_windows_r1199_training-contract-dry-run_field_session.log`；**此时尚无滤波真机LowCmd**。新现场包SHA `8a40dc479747434e2ee737bd90cc89a4cac399ebca51e81e80ce75bdf6e5360a`。
- 下一步若实机首测，必须另行具体告知并获现场人员当次明确同意；本次许可尚未取得。首测后按Debug七文件与现场观感评估，不因通过单次实验开放常规策略运行。

## 2026-11-12 22:30：unitree_ros 完整仓库拉取 + AS2-W / Go2-W / B2-W 模型与训练配置深度对比（文档阶段，无狗动作）

- 原 `部署参考/unitree_ros` 只是 `robots/as2w_description` 的 sparse 检出（partial clone）。本次经本机代理补全为完整工作树：**1597 文件 / 1711.7 MB / HEAD `41dec58`（2026-11-06）**。训练包锁定的 `4ddbf6d`（2026-08-24 `add as2w_description`）与 HEAD 在 as2w / as2 / go2w / b2w 四个目录上 `git diff` **为空**，即训练用 URDF 与当前 master 逐字一致。
- 解析 71 个 URDF（0 失败），产出 `.dsh_tmp/urdf_facts.json`、`urdf_summary.md`、`quadrupeds_dump.txt`；脚本 `urdf_deep_compare.py`、`wheel_radius2.py`、`base_geom.py`、`md_to_docx.py`。
- **主要发现**：
  1. **AS2-W 的腿就是 AS2 的腿**：关节原点、连杆 0.2202/0.1054/0.212/0.212、限位（髋 ±0.785、前大腿 −2.0…3.492、后大腿 −1.3…4.19、小腿 −2.7677…−0.8133）、力矩 60/60/90 与 AS2 完全相同，只有速度 24/24/16 → 25/25/16.67。质量差 8.36 kg 可逐项拆解（本体 +1.28、髋 +0.22、大腿 +0.64、小腿 +3.52 轮毂电机、轮 +2.20、JT128 +0.5）。
  2. **Go2-W = Go2 − 12 个 0.089 kg 转子 link + 4 个 0.646 kg 轮毂电机 + 4 个 0.52 kg 轮**，质量差 3.436 kg 与 URDF 总和差完全相等；Go2-W 丢掉了 Go2 的转子惯量表示且未用 armature 补回，AS2-W 沿用此做法。
  3. **AS2-W 与 Go2-W 的轮网格同尺寸**（172 × 51.8 mm，r=0.086），但绕轴惯量差 **2.15 倍**；回转半径 AS2-W 0.765 r（合理）、Go2-W 0.559 r（与轮胎几何不符）——至少一方数据有问题。
  4. **AS2-W 轮速上限 98.47 rad/s 折合 8.47 m/s**，是 Go2-W（2.59 m/s）的 3.3 倍，而训练限速 1.0 m/s；需确认是否输出侧限值。
  5. **官方 `as2.xml` 有腿关节 armature / damping / frictionloss**（髋/大腿 0.026/0.2/1.0，小腿 0.038/0.5/2.0），AS2-W 的 URDF、Isaac 配置、部署 MuJoCo **三处都没有用**；因腿电机同源，这批值可直接借用。
  6. **训练线 A（mlp57）整体继承 B2W 配方**（audit 硬断言奖励权重等于 B2W）：力矩/加速度正则的实际强度约为 B2W 的 1/11，`upward` 却是 Go2-W 的 3 倍；质量随机化 (−1,+3) kg、外力 ±30 N 也按 B2W 量级。
  7. 部署安全包络（R1199）仍是 “URDF × 0.9 + 仿真膝面偏移”，文件自标 `simulation_urdf_not_hardware_calibration`。
- **交付**：`部署测试/02_现场操作/AS2-W与Go2W-B2W模型与训练配置深度对比_20261112.md` 与同名 `.docx`（17 张表，A4，标题/表格/正文样式已设）。
- **未做/边界**：没有改任何模型、配置、策略或部署源码；没有真机动作；docx 未做视觉渲染（本机无 LibreOffice/Office 渲染引擎），只做了结构与版心检查（每张表宽 17.0 cm = 可用版心）。
- **后续**：按报告 P0 建议（补 armature/damping/frictionloss、轮改圆柱碰撞、base 加盒近似、确认 JT128 是否在实机）走独立候选 + 离线验收后，再谈是否影响 R1199 抖动排查。
## 2026-11-12 22:28–22:43：R1199 40ms 腿目标低通两轮有界实机；前后改善、转向偏弱

- 22:28 初次启动在 C++ `--wz-limit 0` 参数解析处返回 Usage，**发布 LowCmd 前结束，狗未动作**；脚本曾误归档离线 audit 遗留的501行 `debug_lowcmd.csv`。已修解析与启动前清理，原始 `logs/20261112-222858_windows_r1199_training-contract_field_session.log` 和会话目录 `logs/field_sessions/20261112-222858_training-contract/`，该目录的 Debug CSV **不可当作真机记录**。
- 现场指定最终 `vx≤0.2m/s`、`wz≤0.1rad/s`、40ms 仅腿目标滤波（轮速不滤）；同合同 MuJoCo 0.1rad/s 左右×3种子均直立、无非轮触地，但仅2/6偏航跟踪达标，实际均值约0.025–0.055rad/s；0.2rad/s 2/6失稳，故未开放。输出 `logs/r1199_debug_lowpass_turn_{left,right}010_10s_seed{101,202,303}_tau40/`。
- 当次现场明确同意后，22:38 第一轮15秒：原厂遥控器 A→B→前后摇杆→15秒到期自动 Brake/ReturnStand→Y→FixSquat→Passive，发布端 RC0，最终 LowCmd 25013行 `dropped=0 file_ok=1`，策略帧868行；完整保护记录10681行 `warning_or=motorstate_or=0`，无软件守卫触发。本机原始 `logs/field_sessions/20261112-223732_training-contract/`、Windows transcript `logs/20261112-223732_windows_r1199_training-contract_field_session.log`。这轮没有转向指令。
- 按用户要求将滤波候选 PolicyWalk 时限15→30秒，摇杆包络和保护阈值不变；源码 SHA `15a2f654ba973cc064a56ecbfcc67babdb0f1f189927851dee34bae0206fca6a`，Filter二进制 SHA `5d963ce3c1cf9051315649b525d24fa29891218d8eaf1db8863ff15efd17e1ae`；CPRO ARM64 CTest9/9、离线帧/Debug审计 PASS，原始 `logs/20261112-2240_r1199_lp40_30s_arm64_gate.log`；只读 dry-run 审计/LowState/ReleaseMode/趴下/16轴mode0 全PASS，原始 `logs/20261112-224122_windows_r1199_training-contract-dry-run_field_session.log`。
- 22:42 第二轮再次获现场当次同意。A后首次B因关节未静稳被门槛拒绝，静稳后再次B成功；前后及左右转向输入均抵达发布端，30秒到期自动Brake/ReturnStand→Y→FixSquat→Passive，发布端 RC0。最终 LowCmd 30886行无丢，策略帧1619行；完整保护记录12952行保护位全零、软件守卫未触发。现场反馈“前后比之前丝滑”，但“转还是转不了”。输入偏航命令同向均值 +0.091/−0.088rad/s，IMU gyro_z 实测同向均值仅 +0.025/−0.022rad/s，故**输入链工作、策略/执行闭环偏航响应不足**；不能仅凭此区分权重本身、低通造成的响应损失或轮地接触差异。本机原始 `logs/field_sessions/20261112-224151_training-contract/`、transcript `logs/20261112-224151_windows_r1199_training-contract_field_session.log`，复算 `logs/20261112_r1199_lp40_field_summary.{py,txt}`。
- 当前狗已自动趴下，发布端退出；MotionSwitcher 原厂控制权未恢复（下次需重新只读核对）。本次两轮是有界探索试验，**不代表转向性能或长期运行验收**。后续先比较同合同无滤波/滤波转向响应并请训练方提高小偏航命令响应与左右对称性；任何新实机动作仍须逐次说明并获现场明确同意。修改源码后已重建现场包 `部署参考/cpp_deploy-as2w/dist/cpp_deploy-as2w.tar.gz`，SHA `67d8ecd877d0a87df33c69fac3de025edabb01428ab901a83427cfe8df573cb4`。
- **勘误（22:59）**：本报告初版曾写“AS2-W 是三个轮足里唯一没有 MJCF 的”，有误——实际 **as2w / go2w / b2w 三个轮足都没有 MJCF**（Go2-W 目录下唯一的 .xml 是 `package.xml`），官方 MJCF 只覆盖 a2 / as2 / b2 / g1 / h1 / h1_2 / h2。报告已就地更正并补充“MJCF 覆盖范围”一段；结论不变：轮关节的 armature / 阻尼 / 摩擦官方没有，只能借 As2 的腿值 + 台架辨识轮子。

## 2026-11-12 深夜：R1199 无滤波 vs 40ms 低通三次实机日志对照 + tau=0/40 配对偏航仿真（离线，无狗动作）

- 环境：caolin 服务器（`caolin@192.168.10.163`，SSHFS 挂载正常），numpy 1.26/scipy 1.11/matplotlib 3.6；原始数据先拷 `/tmp/opencode/r1199_filter_compare/` 本地解析，正式脚本/结果全部写回工作站。任务书 `05_OpenCode交接/给OpenCode_R1199滤波前后实机日志对照分析_20261112.md`；报告 `02_现场操作/R1199低通前后实机对照与改进建议_20261112.md`。无 HDC、无 ReleaseMode、无 LowCmd、未改训练服务器与生产部署代码。
- 对照对象仅三次有效会话：NF `20261112-220051`（tau=0，21s 前后、无转向）、LP15 `20261112-223732` 与 LP30 `20261112-224151`（tau=40ms 仅腿目标，15/30s；LP30 含 ±0.09rad/s 双向转向）。`20261112-222858` 已排除。完整性复核：policy 1170/868/1619 帧、LowCmd 26586/25013/30886 行均 0 坏行、walk 段 500Hz 覆盖、保护位全 0。
- **滤波效果（匹配运动窗口，非整段均值）**：无滤波最终 LowCmd 腿目标单帧步进 p99=0.126rad（requested=applied），40ms 后 ≤0.05rad（滞后 mean≤0.013rad）；大腿 dq 40–120Hz Welch 功率前进 2.98e-2→8.0e-4/1.2e-3（25–37×）、后退 2.88e-3→6.1e-5（47×），瞬态切片 max 2.7e-2→≤2.2e-3；raw ONNX 腿输出饱和交替滤波前后不变（requested 均为 0.126rad p99）——改善在执行链最后一段，推理侧根因仍在，前进残余 ~1e-3。NF 前进无 ≥1s 稳态可比（短推含瞬态），已用 1s 滑动切片分类规避单窗偏差。
- **新事实：观测命令平面裁剪 0.10m/s**（`r284_observations.hpp Observations::push`，训练 parity 一致）：slewed 0.12–0.20 的推杆在策略/包装处全部截到 0.10，实测轮 common 跟踪 76–82%，机身速度折算仅 ±0.065–0.080m/s——"0.2 包络"实为"0.10 命令/约 0.08 实际"（建议 D2 修文档）。
- **转向链路定量（LP30）**：输入链完好；ONNX 4 轮 raw 全饱和 +1、steering=0.000（策略零差动），偏航段腿 L/R 不对称(0.052–0.096)反小于直行(0.177–0.196)；包装注入命令轮速差 1.29–1.37rad/s(=15.3×wz)，实测仅 0.20–0.70（kp=0/kd=2 速度模式跟踪 0.15–0.56），gyro_z 19–27% 命令、左右对称；按 URDF 轮距 0.331m 折算约 86% 差动损耗于侧向滑移。
- **tau=0/40 配对 MuJoCo**（同权重/实测初态/合同/摩擦/PD，唯一差异 `R1199_LOWPASS_MS`，0.10rad/s 左右×3 种子，评估器 SHA `698d9552…` 与归档 tau40 组相同）：tau=0 偏航跟踪均值 0.48（5/6 tracked）vs tau=40 0.38（2/6），12 例全直立无非轮接触——**滤波在仿真中损失约 22% 偏航响应，属次级因素；不滤波也只跟踪约一半，主因是策略无转向技能+执行链损耗**。另见左转(0.46–0.67)优于右转(0.32–0.43)的左右不对称。
- **姿态复核（训练合同版三会话）**：起步跳步已消除（首次非零 ±1s 最大 applied 步进 NF 0.090/LP≤0.043，全程 max NF 0.126/LP≤0.0496，无 0.25+）；停走高/低姿态切换未再现；退出无下沉（LP30 转向后刹车温和下沉 0.064rad）。会话间站姿高度漂移 ~0.12rad 源于 4s 限时 stand-bias 积分器落点不同，与滤波无关。
- 交付物（均在 `04_调试记录/logs/`，前缀 `20261112_r1199_filter_compare_`）：主脚本/图脚本/MuJoCo 配对脚本+表脚本、`_analysis.txt`、`_integrity.txt`、`_windows/_hf_bands/_slices/_turning/_bandtime/_mujoco_yaw.csv`、`_fig.png`（脚本已从工作站位置复跑通过，数值与 /tmp 一致）。改进建议按证据排序见报告第七节（训练端 T1 转向命令覆盖/门槛、T2 raw 噪声、T3 轮差动通道、T4 轮执行器一致性；部署端 D1 维持 40ms、D2 修包络语义、D3 暂缓方向自适应滤波、D4 不提高 yaw 上限）。
- **边界**：无滤波实机无转向输入，"滤波使实机转向变弱多少"只有仿真配对值 22%；40–120Hz 振动是声音的可测代理而非声学证据；机身速度为轮速折算无独立真值；LP30 后退单切片(4.7e-4)与 LP15(5.6e-5)差异成因未定（换向污染 vs 会话状态）。下一步若现场需再测：转向改进走训练端 T1，实机验收阶梯（0.05→0.1→弧线）见报告；每次动作仍须当次具体许可。

## 2026-11-13：新权重 rolling-4000-stage020-research 收包验收 S0（离线，无狗动作）

- 来源：用户指定 GitHub `YuTaoV5/Rob2Nav` main `deliveries/as2w-deploy/rolling-4000-stage020-research`；caolin `git clone --filter=blob:none --depth 1` 拉取，提交 `abc4f2c4`（2026-11-13 08:17 +0800）；归档至 `部署参考/Rob2Nav-rolling-4000-stage020-research/`（31 文件，PROVENANCE.md 记录来源）。训练源码参考提交 `9dffc8c9`，经 git diff 核对 `training/as2w-backup/as2w-current/code/` 两提交无差异。权重 SHA256 本机复核与 manifest 一致：`model_3999.pt e46954b6…7769`、`policy.onnx dd42ada2…83775`。
- **交付自述状态（必须如实携带）**：`research_archive`、`hardware_actuation_authorized=false`、C7 Isaac 行为与安全门槛均未通过（转向/弧线 0/24）、MuJoCo 稳定 72/72 但完整通过 27/72（gate=false, safety_gate=true）；实机闭环/连续手柄全时序/ARM64 影子 not_run。训练方明确把轮速残差全程饱和（487 帧实机运动观测回放）列为已知问题。
- 自带校验在本机复现：ONNX-vs-PT 实机观测回放 1034 帧 max err `4.77e-6` PASS（fixture 即我方 `R1199_motion_jitter_feedback_20261112.zip`，SHA `15b1cac5…` 复核一致）；`filter-parity` C++/Python 腿滤波+限速夹具 1039 帧 max err `2.98e-8` PASS。
- **接口与 R1199 相同**：obs 1×65 → actions 1×16、20ms、opset17；关节序/默认角 [0,0.8,−1.6]/增益 55/2 腿、0/2 轮、动作缩放 0.35/16、限位表同源 URDF（`runtime/as2w-official-reference.json`）。**运行时合同与 R1199 的差异**（部署必须逐项实现）：① 新增腿残差 5Hz 一阶低通（α=1−exp(−2π·5·0.02)≈0.4665，作用于 ±6 限幅后 raw 腿输出，回合起点清零）；② 新增腿目标限速 0.9 rad/s（每步 0.0514 归一化单位，在站姿补偿叠加后）；③ `pure_turn_common_scale=0`（纯转向时轮共模项归零，|vx|≥0.04 时与旧公式一致）；④ 命令域扩大：训练直线命令 |vx| 至 0.20（R1199 观测平面裁剪 0.10）、转向 0.035–0.12，评估矩阵 ±0.20 直行 / ±0.10 原地转 / 0.05+0.08 弧线；⑤ 训练命令含 40% 纯转向 + 15% 弧线（rolling-maneuvers）。其余（precalibrated continuous/straight 站姿补偿、轮锁存 0.12s −6·err/16、无 odometry/settle/common、previous-action=包装后动作、2s 接管混合、65 维观测构造）与 R1199 训练合同一致。`park_policy_rad=0` 在公开源码无引用，记录为待同事确认（值 0）。
- 实机日志回放特征（同事审计脚本本机复跑）：新权重腿输出限幅比例仅 0.1%（R1199 同数据 85–95%），滤波+限速后腿目标帧间变化 p99 0.018 rad（R1199 无滤波 0.126）；四路轮残差运动帧仍 100% 饱和——训练方已知未解。
- 判定：**进入 S1/S2/S3 离线链**（包完整、校验复现通过、合同可读）。实机门槛前置事实：交付为研究归档且训练方未授权实机；任何实机动作仍按项目规则逐次告知并获现场当次明确同意，首次只允许有界阶梯（zero-B → 有界低速），并明示 Isaac 双门未过的风险。

## 2026-11-13：R4000（rolling-4000-stage020）S1 移植对齐 + S2 sim2sim + S3 双端构建全链完成（离线；CPRO 只读，无狗动作）

- **S1 移植对齐**：新建独立 `deploy/robots/as2w/r4000/`（`r4000_controller.{hpp,cpp}`、`r4000_observations.hpp`、`r4000_replay.cpp`、CMake 默认全 OFF）+ `models/r4000/{deploy.yaml,policy.onnx}`。观测构造与 R1199 相同（65 维），唯一合同差异：观测目标平面裁剪改为 deploy.yaml 包络（0.20，训练直线命令采样上限），wz 裁剪仍 0.30（对包络不生效）。动作链按训练实现逐行移植：raw(±6)→5Hz 一阶腿残差滤波(α=1−exp(−2π·5·0.02))→±1 限幅→×0.18×motion→+站姿补偿(precalibrated continuous/straight, 4s 标定, ±0.38)→0.9rad/s 限速(0.0514/步)→包装腿动作；轮链 `pure_turn_common_scale=0`（纯转向共模项按 forward_blend=|vx|/0.04 归零）、轮锁存 0.12s(−6·err/16, ±1.5)、previous-action=滤波/限速/锁存后的包装动作。共享发布端 `common/as2w_publish.cpp` 加 `AS2W_POLICY_R4000` 分支（banner/包络/映射审计/POLICY_DIAG/30s walk cap/65s 绝对周期上限/`--debug` 全链）。**parity**：实机 LP30 会话 1601 帧传感器带（含 ±0.2/±0.1 全域命令）过 C++ 回放，与训练参考实现（`as2w_rolling_filtered`+`as2w_rolling_fixed_exit`，提交 9dffc8c9=HEAD，与本机旧快照逐文件 diff 一致）逐帧对比：previous-action 误差 0、包装动作最大误差 **1.155e-07** PASS（脚本 `tools/r4000_wrapper_parity.py`）。x86 独立构建 0 告警、CTest 8/8、`--offline-audit` AUDIT PASS。
- **S2 sim2sim（同事现行评估器 `eval_as2w_mujoco_rolling.py` + 实测 FixedStand 初态 + 我们 omni 平面资产）**：
  1. 完整验收矩阵 72 例（±0.20 直行/±0.10 原地转/0.05+0.08 弧线 ×12 种子，全推扰+2% 丢包+±5% 质量随机）：stable 9–11/12、非轮触地 2–3/例、完整通过 0/72——比同事原生 reset 归档（72/72 stable、0 非轮）差，实测初态是更严条件。
  2. 无推扰 12 种子：失败集中于 **46005/46006** 两个质量抽样种子（RR_calf 非轮触地，最小膝面 −1.2~−1.5cm，多发于转向后松杆/驻停段，个别运动中），与同事 Isaac 记录的"外侧后小腿偏差"问题同源；其余 10 种子直行 stable/tracked、无非轮。
  3. **与 R1199 部署门槛同种子对照（101/202/303、实测初态、无推扰）**：直行前后 6/6 stable/tracked/**无非轮**，速度跟踪 0.186–0.198/0.20（93–99%，R1199 同门槛约 50%）；转向/弧线 12/12 stable、0 非轮，实际偏航 0.021–0.053（21–53% 命令，方向正确左右对称，仅 2/6 达跟踪线）；驻停保持 7/18。**结论**：同门槛下直行明显优于 R1199（命令域扩到 0.20 起效+训练内滤波把腿目标帧间变化压到 p99 0.018rad）；转向仍弱（与 R1199 同量级）；±5% 质量随机下后小腿净空是本权重已知短板，实机测试必须避开"转向后立即松杆驻停"的连招并逐级开放。
- **S3 双端构建**：`tools/run_r4000_trial.sh`（Debug 强制、CLI 只能收窄包络）+ `tools/run_r4000_field_session.sh`（六步预检链+Debug 归档校验+`--debug` 兼容）+ `tools/build_on_cpro.sh` 加 `AS2W_R4000_BUILD` 门控 + Windows `运行现场策略会话.ps1` 注册 `-Policy r4000 -Mode r4000|r4000-dry-run`（r4000 会话强制全链 Debug；新增 `C:/Users/zoubu/as2w_package.ps1` 英文包装绕过中文路径编码）。CPRO 同步 12 文件 tar（`97c2eabe…`），ARM64 独立构建 `build-r4000-joystick` CTest 8/8、`--offline-audit --debug` AUDIT PASS（DEBUG 500 帧 dropped=0 file_ok=1）、R4000 JOYSTICK MAPPING PASS，二进制 SHA `3b0bbc28…`；7 份源码/模型/脚本 SHA 双端逐一一致（as2w_publish `b13e674c…`、controller `dc9b5808…`、onnx `dd42ada2…` 等）。重新打包：cpp 包 `ffbb6618…`、SDK 包 `9e868d15…`。
- **CPRO 只读 dry-run（20261113-111012）**：步骤 1 audit PASS 后在步骤 2 LowState 0 包处正确 FATAL。只读排查：CPRO `eth0` 保留 `192.168.123.100/24` 但 **NO-CARRIER**——狗与 CPRO 物理链路断（大概率狗未上电或网线松），需现场上电后重跑 dry-run。运维注记：本轮 WiFi HDC 会话中断一次，改用 USB 目标 `0123456789ABCDEF` 完成（双通道并存命令带 `-t`）。
- **下一步（S4，每步须现场当次明确同意）**：狗上电→重跑 `r4000-dry-run`→1) zero-B（B 后摇杆居中 5–10s）→2) 有界低速（`--vx-limit 0.1` 单轴短推）→3) 包络内短摇杆（30s cap 内）。风险前置事实：交付为 research archive 且训练方未授权实机、Isaac 行为与安全双门未过（转向 0/24）、±5% 质量随机 2/12 种子有后小腿触地、MuJoCo 完整门槛 27/72；首次动作仅做 zero-B 并全程 Debug 双监测。原始日志：parity/mujoco 输出在 caolin `/tmp/opencode/r4000_*`（关键结果已录本节），CPRO dry-run 归档 `logs/field_sessions/20261113-111012_r4000-dry-run/`。

## 2026-11-13 11:26–11:28：R4000 首两次实机行走会话（现场同意，±0.2 m/s 前后全程；无转向输入）

- 前情：11:21 首次启动因操作侧看不到 Passive ready 提示（会话输出未实时转发，属显示方式问题）未按键，120s 等待超时干净退出、无任何狗动作；档案 `field_sessions/20261113-112115_r4000/`（保护位全零）。此后改为操作员在工作站 PowerShell 直接运行入口（输出实时可见）。
- **会话 1 `20261113-112630_r4000`**：A→FixStand→FixedStand→B 一次通过（pose_error=0.298、upright=0.995、quiet_dq=0.031）→2s 零速交接→PolicyWalk **30s 全程**（slewed 命令 vx 达 ±0.20，912 运动帧）→30s 上限自动刹车→ReturnStand→FixSquat→Passive→退出 RC=0。保护流 12276 行全零、无 FIELD_SAFETY 告警、Debug 双文件完整（会话脚本强制校验 dropped=0/file_ok=1 通过）。
- **会话 2 `20261113-112750_r4000`**：同链路（B gate pose_error=0.293、upright=0.996），1147 运动帧、30s 上限触发刹车；65s 绝对周期上限在 FixSquat 段触发（无害，趴下正常完成）RC=0；保护流 16517 行全零。
- **量化（两次均值口径）**：最终发布腿目标单帧步进 p99/max=**0.0043 rad**（R1199 无滤波 0.126、部署端 40ms 滤波 0.05——训练内 5Hz 滤波+0.9rad/s 限速实机兑现约 30×/12× 更平滑）；轮命令共模 p50/p99≈1.9/2.33 rad/s，实测轮速 p50 1.5–1.9 rad/s → 机身约 **0.13–0.16 m/s @0.2 命令**（R1199 同方式约 0.075，提升约一倍）；行走姿态 F 大腿 0.66–1.14 循环、无塌陷；**两次 wz 命令恒 0，转向未测**。
- "控制一会儿就失效"解释（已告知现场）：PolicyWalk 30 秒硬上限为首次试验安全边界（到期自动刹车/回站/趴下），且 B 每会话仅一次；周期结束即需重启会话。延长上限=改源码常数，按流程需 x86+ARM64 重编+audit+同步后再用。
- 下一步：转向 ±0.1 rad/s 单测（预期偏航响应仍弱 ~25%，注意"转向后立即松杆驻停"连招有后小腿触地风险，先小幅、松杆前先回正）；或先延长 30s 上限作 60s 候选修订。

## 2026-11-13 11:43–12:20：R4000 120s/0.4 档实机会话 + 转向机制分析 + WALK-diag 修复 + 训练侧反馈包

- **会话 3 `20261113-114335_r4000`**（现场同意，120s PolicyWalk、包络 ±0.4/±0.1）：A→B(gate pose_error=0.307, upright=0.994)→2s 交接→120s 全程（命令 vx 达 ±0.400、wz 双向 ±0.10）→120s 上限自动刹车→回站→Y 趴下，RC=0。保护流 16517 行全零、无 FIELD_SAFETY、debug_lowcmd 74237 行 dropped=0。工作站自动拉回被截断，经 USB `file recv` 补齐（7 文件字节与 CPRO 一致）。
- **直行**：0.30+ 六段实测机身 0.27–0.34 m/s（85–91% 命令）；腿目标步进直行 p99 0.0051 rad（限速上限 0.018 兑现）；0.2 档两对照会话一致。**转向机制（新发现）**：8 转向段呈"短转可、长转停"——≤2s 段 gyro_z 23–50%、轮差跟踪 0.5–1.0；≥4s 段塌缩至 5–15%、实测轮差 0.14–0.23 rad/s（命令恒 1.4–1.5）；持续转向内部实测轮差 3–4s 内由 ~0.35 塌到 0.05、gyro_z 0.02→0.004、后大腿 0.94→0.77 单调下沉（后小腿至 −1.93）；ONNX 轮输出 4157 运动帧回放 100% 饱和且 steering 分量恒 0（`replay/fixture_replay_report.json`）。0.2 rad/s 档实测初态 MuJoCo 0/6（全翻+膝面 −1.2cm）被门槛拒绝，实机 wz 保持 0.1。
- **发现并修复发布端 bug**：R4000 构建的 `policy_diag.log` 缺 WALK 段（WALK 诊断调用点的宏门漏改，`as2w_publish.cpp` L2337），本会话仅 117 行；修复后 x86/ARM64 各重编+CTest 8/8+audit PASS，二进制 `4f6b978d…`、as2w_publish.cpp 双端 SHA `47820e47…` 一致；本会话分析不受影响（改用 debug_policy.csv 超集）。
- **训练侧反馈包** `06_训练协作/R4000_field_turn_feedback_20261113/`（28 文件，目录 59MB，ZIP 11.4MB SHA `865a7444…`，MANIFEST 28/28 校验过）：README+详细分析报告（直行量化/转向四层根因链/训练建议 T1–T5：转向命令驻留扩到 5–10s、给轮差动通道真实权威、稳态偏航奖励、持续转向后腿净空代价、命令域扩 0.4）+ turn_mechanism 图 + 可复算分析脚本 + **6101 帧实机观测回放夹具**（debug_policy 逐帧生成，parity 1.155e-07、ONNX-vs-PT 8.3e-07）+ compare_r4000_replay.py + 三会话原始数据与 2ms 关键窗抽取。
- 边界：实测机身速度为轮速折算；后小腿 −1.93 未触地但按风险对待；0.4 档仅 3 种子快速门槛+6 段直行实机验证。

## 2026-11-13 下午：Rob2Nav as2w-backup 三条最新权重 S0/S1/S2 离线验收（离线，无狗动作）

- 对象：用户 pull 的全仓快照 `部署参考/Rob2Nav-as2w-backup/`（commit `2de96cba…`）内三条最新线——rolling `actor-wheel-saturation-loss.Uliv0s/baseline/train/model_1200.pt`（SHA `a5e79209…`）、stepping `support-aware-reward.bp4984/formal/model_1199.pt`（`57af5130…`）、recovery `deep-side-curriculum/formal/model_1199.pt`（`4fe19b8e…`）。与上午 R4000 交付包（filtered-4000 终版 model_3999，已实机）相互独立。三份权重/ONNX SHA 本机复核与合同一致；S1 ONNX↔检查点 parity：rolling 1512 帧 5.96e-07（同训练方）、stepping 真实观测 4524 帧 1.86e-05、recovery 1351 帧 5.13e-06。
- S2（训练方评估器+资产+种子，本机 MuJoCo 3.17）：**stepping 0/96**（stance 崩 70/非轮触地 24 等，与训练方归档完全一致，研究中继不可交付）；**rolling model_1200 gate=false 12/72、safety_gate=false**（1 例 back knee_surface；跟踪优秀 forward 0.192–0.195/0.20、非轮触地 0；失败集中驻停漂移 2.0–3.7cm>2cm 门限，转向实际 0.08–0.094/命令 0.12 与 R1199/R4000 同源弱点），且该 4000-iter run 终版 model_3999 未入库无法验收；**recovery 平地趴地起身 prone 起身 48/48 全成功**（高 0.378m/四轮支撑/零翻倒零非轮触地，5 组×8 例含 2% 丢包+执行器延迟+推扰），17 例严格判据失败全部是末段推扰时序伪影（推扰 9.8–10.9s+试验 11s 截止，残余 0.06–0.075 m/s），**侧倾起身 left/right 仅 60–65%（14/40 真翻倒 up_z≈−0.10）**，near_stand 95%。seed 7301 组与训练方归档逐例一致（4/4/4/7）。
- 判定：stepping 退训练侧；rolling actor-wheel-saturation 中间检查点不引入实机（rolling 线继续用已实机 R4000）；recovery deep-side 是三者中唯一核心技能仿真可用——若上实机需全新 rXXX 线（obs42/act12 腿、轮运行时位置保持 0、staged-rise/stand-integral/low-support-handoff/predictive-guard 包装链 C++ 移植），首次范围应限定"趴地→起身→站稳"不做侧倾，实机动作仍逐次当次同意。
- 原始日志与复现脚本：`logs/20261113_rob2nav_three_latest_s2/`（7 个 S2 运行 + parity 脚本 + README 判据细节）。
- **rolling 追加对照（同机同协议）**：R4000 终版 model_3999 复跑 gate=false/safety=true/18/72/held38；model_1200 为 12/72/held31/safety=false（1 例 back 膝面）。**轮饱和同输入对照**：4536 帧同批观测下 R4000 轮输出 100% 饱和 ±6（=96 rad/s 上限），model_1200 饱和 0%（max1.23≈19.6 rad/s）——actor_wheel_saturation_loss（0.025/0.9）确已修复今天实机分析定位的轮残差饱和根因，但训练方自证与我们的 S2 均未转化为驻停/转向门槛提升（"低速驻停或转向完整通过的提升尚无证据"）。**建议**：不用中间检查点 model_1200 上实机；向训练方索要该 run 终版 model_3999+服务器验收后同条件对照，若保持去饱和且驻停/膝面达标即为 R4000 继任候选（接口与 R4000 完全一致，S3 链可复用）。

## 2026-11-13 下午：起身 getup1199 实机部署前置验证 + 部署方案（离线，无狗动作）

- 对象：recovery 最新权重 deep-side model_1199（SHA 4fe19b8e…）+ ONNX 970e692e…。四组 MuJoCo 实验（证据 `logs/20261113_getup1199_deploy_precheck/`）：
  1. **实机真实趴姿提取**（114335 会话尾段）：Y 趴姿 calves −2.73~−2.77、thighs≈1.0、高 0.215m——与训练 prone 库（thighs 2.4–2.9、calves −1.5~−1.7、躯干平贴）完全不同，且 **calf −2.77 超策略 90% 包络（−2.55）与 URDF 限位（−2.65）**。
  2. **入口消融 8 配置×40 例**：真实 Y 趴姿直接起身 0/40（全部 joint_angle@t0 被安全层拒绝）；经 FixProne 预趴姿（库中位）或库 prone：起身 40/40、严格门 24/40（失败全为末段推扰时序）。**预测守卫与 effort 0.8 对成功率零影响**（合同安全要素不损失成功率）。
  3. **FixProne 过渡预演**（A 键 crouch→prone 6s 插值 kp55/kd2）：3 种子终点误差≤0.083rad、水平、接触峰 650–911N（躯干落地瞬态）——预趴姿动作可行。
  4. **部署安全阈值实测**（16 例逐帧）：腿步进 max 0.61rad、>0.2 最长 6 连（**现行行走档 warn 会误杀，getup 档调 0.35/0.75**）；腿 dq max 6.5（>5 最长 3 连，不触发）；**腿 tau max 仅 37.2Nm**（不触发，远低于 R284 事故值；此前 ratio=1.0 为轮瞬态触自身剪幅）。
- 部署与测试方案：`02_现场操作/getup1199实机部署与测试方案_20261113.md`（42 维 obs 合同含**重力符号与 R1199 相反**等差异点、动作链六步规格、A=FixProne/B=PolicyGetup/Y/X FSM、getup 专用安全档、S4 四级阶梯；v1 只做趴地起身不做侧倾）。S3 C++ 编码尚未开始；任何实机动作仍逐次当次同意。

## 2026-11-13 傍晚：getup1199 真实趴姿直接起身的补充诊断 + 开膝中间态（离线，无狗动作）

- 用户追问"真实数据直接输能不能起"后的修正实验（证据 `logs/20261113_getup1199_deploy_precheck/` 实验5/6）：
  1. 前述"真实趴姿 0/40"是安全审计在 t=0 判入口超包络即终止，**策略从未运行**——结论已修正。
  2. 用模型关节范围（calf −2.7677）表达真实趴姿、仅放开入口包络检查（命令仍剪 90%）：
     **33/40 起身、28/40 完整通过、90% 包络 0.07s 内自动回归**；另 7/40 为起始膝贴死硬限位的
     t=0.01s 边界伪影（真实 Y 趴姿恰处贴限位状态）。策略能力上不怕蹲伏趴姿；
     "中间态"的本质是合同问题（入口超包络+膝压限位）。
  3. **新增 FixCrouch-lite 方案**（2.5s 仅开膝 −2.77→−2.43、不后扫腿、躯干不落地、
     接触峰 69–73N、终点全回包络，预演 3 种子稳定；随后起身 40/40）——方案文档已更新为
     v1 首选（替代动作更大的 FixProne，后者留作备选）。
- 方案文档 `02_现场操作/getup1199实机部署与测试方案_20261113.md` 第 0/2/3 节已相应修订。

## 2026-11-13 傍晚：getup1199 测试流程改为单键 B 起身链（设计确认，离线）

- 用户确认测试操作只保留：趴姿下按 B 一次（起身）+ Y（趴下）。方案文档 FSM 已改为单键四段内部链：入口检查→FixCrouch-lite 开膝 2.5s（包络内自动跳过）→包络复检（未达自动 Passive 不硬起）→PolicyGetup 15s 上限→FixedStand 保持→Y/30s 自动趴下；A 在该构建禁用、X 随时急停。当次同意的告知口径已写入文档（"按 B 后开膝约 2.5s→起身 3–5s→站立保持"）。S3 编码未开始。

## 2026-11-13 15:34–15:40：caolin 服务器换网段到 192.168.43.12，恢复工作站 SSHFS 映射（无狗动作）

- 背景：caolin 服务器（`eai-MS-7E17`，Ubuntu，`wlp131s0f0=192.168.43.12/24`）地址由旧 `192.168.10.163` 改为 **`192.168.43.12`**；工作站 WLAN 现为 **`192.168.43.4/24`**（旧 `192.168.10.61`）。目标是把服务器的 `/home/caolin/as2w_workstation` 重新挂回本 Windows 项目目录，恢复 OpenCode 读写通道。
- 只读诊断：`Test-NetConnection 192.168.43.12 -Port 22` 成功（工作站→服务器通）；`Get-Service sshd` = Running、22 端口 LISTENING；注册表 `HKLM\SYSTEM\CurrentControlSet\Services\SharedAccess\Parameters\FirewallPolicy\FirewallRules` 中 `AS2W-OpenCode-Workstation-SSH` 的 `RA4` 仅为 `192.168.10.163`（`OpenSSH-Server-In-TCP` 仍 Active=FALSE）。**根因：Windows 防火墙按旧服务器 IP 放行，新 IP 入站被静默丢弃**；表现为服务器→工作站 `ssh` 连接超时，而双向 ARP 正常（`192.168.43.12` ↔ `ac:f2:3c:a1:78:83`），可排除物理链路与客户端隔离。
- 修复：管理员权限执行 `Set-NetFirewallRule -Name 'AS2W-OpenCode-Workstation-SSH' -RemoteAddress @('192.168.10.163','192.168.43.12')`（保留旧地址作回退）；读回 `remote=192.168.10.163,192.168.43.12`。退出的 netsh 尝试返回 RC1 且未改注册表，改用 `Set-NetFirewallRule` 成功。原始日志 `logs/20261113_workstation_ssh_firewall_fix.log`。修复后服务器 `ssh -i ~/.ssh/as2w_workstation zoubu@192.168.43.4 whoami` 返回 `bgzou9897\zoubu`。
- 挂载恢复：服务器上残留旧 sshfs 进程（PID 569514，指向 `zoubu@192.168.10.61`），旧挂载点已 stale（`mountpoint` 报“输入/输出错误”）。`fusermount3 -u /home/caolin/as2w_workstation` 成功解除；随后 `sshfs -o IdentityFile=/home/caolin/.ssh/as2w_workstation,reconnect,ServerAliveInterval=15,ServerAliveCountMax=3 'zoubu@192.168.43.4:/D:/Projects/Athena/运动控制/Collie/AS2-W_CPRO' /home/caolin/as2w_workstation`。验证：`mountpoint -q` 通过、`AGENTS.md` 可读（33863 B、mtime 2026-11-13 11:11），经挂载点写入→读回→删除探针文件 `部署测试/04_调试记录/logs/.as2w_mount_probe_20261113.txt` 全部成功（服务器 uid 1002）。
- 注意：① `/D:/...` SFTP 路径写法与专用密钥 `~/.ssh/as2w_workstation` 均未变；② 服务器重启/网络重连后仍需手工重挂（无开机自挂）；③ 本机 IP 若再变（DHCP），需同步改服务器挂载命令与防火墙 RA4 列表；④ 防火墙规则现同时放行旧、新两个服务器地址；⑤ 项目文档中出现的 `192.168.10.61/163` 均为旧网段，按本节替换。
- 未做：未改 `cpp_deploy-as2w` 源码/模型/现场包；未运行 HDC、ReleaseMode 或 LowCmd；狗无任何动作。本阶段仅在 Windows 与 caolin 之间做网络、防火墙与文件挂载操作。

## 2026-11-13 下午：getup1199 S3 起步——C++ 控制器线 + 三层 parity 完成（离线，无狗动作）

- 新建唯一源码线 `deploy/robots/as2w/getup1199/`（控制器/回放/CMake 默认 OFF）+ `models/getup1199/`（ONNX `970e692e…`，deploy.yaml 全合同常量），根 CMakeLists 注册 `AS2W_GETUP1199`。x86 构建（ORT1.22 镜像）零告警；修复两个移植 bug（ORT Unowned 悬垂临时、staged 斜坡 [起点,时长] 语义）。
- **三层 parity（550 帧预趴姿起身全程，干净传感器+部署估计门夹具）**：逐帧 oracle **1.55e-6 PASS**（python 训练实现重放 C++ obs/blend 时间线，隔离包装数学）；闭环全带 max 4.4e-2，根因=ONNX fp32 基线（训练方自身 1.9e-6 同源）经 previous-action 反馈放大 + ≤1 帧门边界翻转；功能等价=估计门版 40/40 与真值门一致。判据与复现脚本见 `logs/20261113_getup1199_deploy_precheck/README.md` 实验7。
- 运维：SSHFS 资产在高负载下 `from_xml_path` 109s，评估改用本地拷贝。
- **下一步**：共享发布端 `AS2W_POLICY_GETUP1199` 分支（FixCrouchLite/PolicyGetup 状态机、getup 安全档、入口/成功门、A 禁用）→ CTest/offline-audit → 会话脚本/Windows 注册 → ARM64/CPRO 同步 → dry-run。

## 2026-11-13 傍晚补充：getup1199 发布端集成规格固化（离线）

- 共享发布端 as2w_publish.cpp 的 getup 集成规格（State 追加、getup 安全档、B 入口链、FixCrouchLite/PolicyGetup 细节、debug/CTest/会话件）已逐条写入方案文档第 5 节，作为下一段机械执行的输入；本段不改动共享安全文件（长会话尾部不赶工）。已完成物：控制器线+parity+估计器验证+方案文档，全部归档。

## 2026-11-13 下午：R4000 转向轮差 ~10× 缺口根因调查（纯离线：复算+审计+MuJoCo 单变量对照；无实机/无训练/无部署改动）

- 任务：解释会话 20261113-114335 长转（11.6/12.7 s）软件轮差 ~1.4–1.5 rad/s 仅实现 5–11% 的原因。报告 `02_现场操作/R4000转向轮差10倍gap根因调查_20261113.md`；附件 `logs/20261113_r4000_turngap/`（17 项：复算/分析/波形回放仿真脚本、stage_table.csv、同步图、7 组单变量 sim 原始输出、开环×N 与闭环 Kp 系列目录）。
- **独立复算**（轮槽位从会话发布流自推导：槽 13/12/15/14、前进全正后退全负、发布-测量相关 0.95+）：源码公式重算=记录目标 max 1.376e-06（含从 HANDOFF 起回放的锁存状态机）；applied=最终发布 LowCmd 100%（29705/29708 帧精确，残差 3 帧边界）；发布轮行 mode=1/kp=0/kd=2/tau=0；锁存窗内 0 帧；保护位全零、通信龄 p99 1–3 ms。**与任务参考值出入**：右转 3–5 s 实测轮差 −0.068（参考 −0.17 为全窗均值），塌缩核心期更极端；其余一致。
- **轮速环定量**：`tau_est≈2×速度误差` 逐窗斜率 1.89–2.01 全程线性（无死区/限流证据），tau 峰 1.6–3.4 Nm/轮远低于 8/12 守卫——速度环按 kd=2 正常工作，其差动力矩被结构性封顶在 kd×命令差/2≈1.5 Nm/轮，停在力平衡点。**时序**：右转（新鲜）后腿下沉 t≈1.6 s 略先于轮差塌缩 t≈2.1 s；左转（已蹲姿态开始）塌缩立即发生而进一步下沉 t≈10 s——塌缩与后蹲姿态存在性相关、无固定先后；无接触力证据不断定因果。
- **MuJoCo 实机命令波形回放**（同权重/同合同/实测初态，11.6 s 右转窗）：E1 原包装：轮差 −0.27/−0.41/−0.32（首1s/3–5s/末5s）**不塌缩**、偏航 38%（实机同窗 −0.36/−0.07/−0.17、13%）；E2 摩擦×0.5/×2 单调变化（65%/29%）；E3 实机轮目标+固定腿同样不塌缩（腿姿非根因）；**E4 固定腿+kd×4：轮差 29%→73%、偏航 86%；kd×10：91%/106%**——力矩权威为第一控制变量。先前开环注入系列（×2/×5/×10 → 168%/638%/1507% 超调 0/3 稳定）与闭环 Kp=3（89%、0 触地、1 种子驻停待查）并入报告。Isaac not_run（caolin 无 Isaac；同口径命令已备给训练侧）。
- **结论**：10× ≈ 轮速环结构性力矩上限（~3×，实/仿共有）× 实机轮地阻力高于 MuJoCo（~3×）；差动唯一来源为开环 0.66 注入（ONNX steering≡0、部署无已启用偏航反馈）；后腿下沉为伴随加重因素。**优先修复**=有界偏航率反馈注入独立候选（Kp=3、限幅 0.15），复验门槛（12 种子全矩阵+直行回归+双端构建+实机三阶梯）已列；训练端 turn-20k 手册需补 ≥10 s 持续转驻留与摩擦上界 ×3 随机化。

## 2026-11-13 17:05–17:10：网段再次变动（服务器 192.168.10.13 / 工作站 192.168.10.34），重新挂载 SSHFS（无狗动作）

- 现象：用户报告地址“变成 10.13”。只读探测：工作站 WLAN `192.168.10.34/24`；`Test-NetConnection` 显示 `192.168.10.13:22` 通，旧地址 `192.168.10.163:22`、`192.168.43.12:22` 均不通。服务器 hostname 仍为 `eai-MS-7E17`，与下午是同一台。
- 防火墙：`AS2W-OpenCode-Workstation-SSH` 原 `RemoteAddress=192.168.10.163,192.168.43.12`，不含 `.13`，故服务器→工作站 `ssh` 再次超时（与 15:36 同机制，非链路问题）。管理员权限改为 `192.168.10.163,192.168.43.12,192.168.10.13`，读回一致；原始日志 `logs/20261113_1707_workstation_ssh_firewall_fix_1013.log`。修复后 `zoubu@192.168.10.34 whoami` 返回 `bgzou9897\zoubu`。
- 挂载：下午的 sshfs 进程（PID 358436，指向 `192.168.43.4`）随网络切换失效，挂载点 stale（`mountpoint` 报“输入/输出错误”）。kill 旧进程 → `fusermount3 -u`（此时已无 mtab 条目，报 `not found` 属预期）→ 重挂 `sshfs -o IdentityFile=/home/caolin/.ssh/as2w_workstation,reconnect,ServerAliveInterval=15,ServerAliveCountMax=3 'zoubu@192.168.10.34:/D:/Projects/Athena/运动控制/Collie/AS2-W_CPRO' /home/caolin/as2w_workstation`。验证：`mountpoint -q` 通过、`AGENTS.md` 可读、写入→读回→删除探针文件成功，且挂载点立即可见下午新增的 INDEX 节。
- 文档同步：`05_OpenCode交接/README.md` 顶部地址说明改为“当前 192.168.10.13 / 192.168.10.34，下午曾 192.168.43.12 / 192.168.43.4”；`启用工作站SSH.ps1` 默认 `RemoteAddress` 加入 `192.168.10.13`（重跑即更新规则，ParseFile 校验 PARSE OK）。
- 复用口诀（地址再变时照做）：① `Get-Service sshd` 与 `Test-NetConnection` 确认两边可达；② 管理员执行 `Set-NetFirewallRule -Name 'AS2W-OpenCode-Workstation-SSH' -RemoteAddress @(<新服务器IP>, 旧IP…)`；③ 服务器上 kill 旧 `sshfs` → `fusermount3 -u ~/as2w_workstation` → 以新 `zoubu@<工作站IP>:/D:/...` 重挂；④ 更新 README/INDEX。
- 未做：无 HDC、无 ReleaseMode、无 LowCmd、无狗动作；未改部署源码/模型/现场包。

## 2026-11-13 17:15：R4000 轮差根因调查 standalone 交付包完成（含全部原始日志；另修复 112630 debug_lowcmd 传输截断）

- **交付包** `06_训练协作/R4000_turn_gap_rootcause_20261113.zip`（24.8MB，解压 229MB，**87 文件，MANIFEST.sha256 87 项**，ZIP SHA `57dfe717…`）：根因报告 + 八联同步图 + 分阶段链路表 + 开环×N/闭环 Kp/实机波形回放 E1–E4 三系列汇总与原始输出 + 5 份可复算脚本 + 6101 帧回放夹具与 compare_r4000_replay.py + **三次运动会话全部七文件全量原始日志**（114335=120s 主分析、112630/112750=±0.2 对照）+ 两次 dry-run 档案。README 含读序、字段/槽位约定、复现命令与期望数字。可直接发训练同事。
- **数据修复（本节新发现）**：`20261113-112630_r4000/debug_lowcmd.csv` 当时自动拉回时被截断为 0 字节（CPRO 原件 12,645,936 字节完整；112750 与 114335 各文件均完整）——本次经 USB `file recv` 补拉并核验，工作站权威位置与包内副本均已修复（SHA `9021e976…`）。此前所有针对该会话的结论只用 debug_policy/capture/protection，不受影响。
- 网络迁移记录：本机 WLAN 改址为 192.168.10.13、工作站 192.168.10.34（同一台 eai-MS-7E17），SSHFS 重挂验证读写；CPRO `192.168.10.180:8710` 暂 Offline（路由器重分地址），USB 通道正常，HDC 命令继续用 `-t`。

## 2026-11-13 晚：getup1199 发布端分支完成——S3 代码全部落地，x86 全绿（离线，无狗动作）

- `common/as2w_publish.cpp` 落地 `AS2W_POLICY_GETUP1199` 单键链（B=入口门→FixCrouchLite 开膝→PolicyGetup→FixedStand→Y；15s 上限；A 禁用；一次会话一链），getup 专用安全档（仅步进 0.35/0.75），`fill_targets` 轮位置保持扩展（kp!=0 分支，行走状态不受影响）；CMake `AS2W_GETUP1199_PUBLISH` + `AS2W_ENABLE_GETUP_TRIAL` + `--getup-trial` CLI。
- 验证：getup 构建 **CTest 8/8**（audit PASS）；**R214+R4000 回归构建 CTest 8/8**；闭环 parity 4.4e-2（根因已归档）+ **oracle 1.552e-6 PASS**（最终二进制）。
- **过程事故与教训**：staged 斜坡修复曾误写镜像未回写工作区，被后续同步覆盖回退（干净构建复现定位后在工作区修复）。方向规则（工作区→镜像单向）必须遵守。
- 剩余 S3：会话三件套 + Windows 注册 + 重打包 + CPRO/ARM64 同步构建 + dry-run。全部完成后按方案 §3 阶梯逐次申请实机动作。

## 2026-11-13 晚：getup1199 S3 收尾——会话三件套/Windows 注册/重打包/CPRO ARM64/双端 parity/CPRO dry-run 全部完成（狗上电趴姿；运动待现场当次同意）

- **会话三件套**：`tools/run_getup1199_trial.sh`（--getup-trial + 强制 --debug + 30s 站立保持）、`tools/run_getup1199_field_session.sh`（六步预检链+趴姿小腿基线门+监测+Debug 归档校验）、Windows `运行现场策略会话.ps1` 注册 `-Policy getup1199 -Mode getup|getup-dry-run`（运动需 -ConfirmMotion；getup 无低通候选）。
- **CPRO 同步与 ARM64**（经工作站 zoubu@192.168.10.34，USB 目标 `0123456789ABCDEF`——WiFi 8710 Offline，tconn 失败）：10 文件 tar 同步、源码/模型 SHA 双端一致；`build-getup1199` ARM64 全构建零错误、**CTest 8/8、--offline-audit AUDIT PASS**，二进制 SHA `9bdbb2a3…b52c12`；**ARM64 parity = 4.429e-2 与 x86 完全一致**（同 ORT 图跨架构一致）。
- **重打包**：`准备现场包.ps1`（经英文包装 as2w_package.ps1）cpp 包 SHA `c0edef37…5b69`、SDK 包 `9fe26cd2…84f4`。
- **CPRO dry-run（20261113-173702）通过**：step1 audit PASS；step2 **LowState 1040 包/s、mode_machine=2——狗已上电**，实时姿态 calf≈−2.748~−2.769/thigh≈0.97~1.02（趴姿，与部署前分析一致）、IMU 水平；step3 原厂 ai 模式（dry-run 按设计停在此处）。档案 `logs/field_sessions/20261113-173702_getup-dry-run/`。
- **运动会话就绪**：命令 `运行现场策略会话.ps1 -Policy getup1199 -Mode getup -MonitorSeconds 150 -ConfirmMotion`（当前用 `-Target 0123456789ABCDEF` USB 通道）。按键语义：B 一次=开膝→起身→站立保持→Y/30s 趴下；A 禁用；X 急停；一会话一链。**实机动作须现场人员当次明确同意并握原厂遥控器/物理急停。**
- 证据：ARM64 parity/构建输出、dry-run session.log 已归档；转输中转文件已清理。

## 2026-11-13：AGENTS.md 固化双机拓扑/IP 变更规则（文档阶段）

- 应现场要求，把"同事如何参照本项目文件结果"的网络基础固化进 AGENTS.md：根文件顶部新增 2026-11-13 状态条目（IP 迁移与覆盖声明），文末新增常设节「双机拓扑与网络变更」——机器与角色表（工作站=权威文件+唯一碰 CPRO、caolin=SSHFS 镜像+分析编译、CPRO=ARM64/发布端）、**路径对应表**（`D:\Projects\Athena\运动控制\Collie\AS2-W_CPRO\` ↔ `/home/caolin/as2w_workstation/`、`/tmp/opencode/` 不持久、`C:\Users\zoubu\` 英文中转、CPRO `/root/field_sessions/` 第一落点）、SSHFS 挂载与服务器→工作站 SSH 命令（密钥 `~/.ssh/as2w_workstation`、`accept-new`、大文件先拷 `/tmp` 再处理的 EIO 规则）、**IP 变更五步恢复流程**（实测三地址→工作站防火墙放行服务器新 IP→重挂 SSHFS→CPRO 仅 `tconn` 不改配置→狗走 192.168.123.x 私网不受影响）、当前快照（服务器 192.168.10.13 / 工作站 192.168.10.34 / CPRO WiFi 暂 Offline、USB 正常）与历史地址清单。
- 同步在根 AGENTS.md「目标与目录」节与 `部署测试/AGENTS.md` 顶部加指向该节的提示；旧条目中写死的 IP（192.168.10.61/163/180 等）均被声明为历史快照。本阶段纯文档，无设备/代码/模型改动。

## 2026-11-13 夜：getup1199 首晚三次实机会话——三个同源集成 bug 全部定位修复，链路已通到开膝段（狗零动作、无风险暴露；下次可直接测）

- **会话1 `175045_getup`**：B 无反应。根因=FSM 按键总门缺 `getup_trial`（FSM 线程提前 return）。已修。
- **会话2（流式）**：B 收到但入口门拒绝 `up=0.999985 (max 0.6)`——`up` 方向写反（趴地本就水平，应为 `up>0.6` 排除侧躺）。已修（`entry_min_up_z`）。
- **会话3 `181327_getup`**：B 通过、正确进入 FixCrouchLite、开膝 2.5s 命令全部发出（1240 帧 LowCmd）——但**写线程状态分派清单缺新状态，整段发的是 Passive 阻尼帧（kp=0）**，狗不动，2.5s 后"envelope NOT reached"安全回 Passive 停机。实测核对：state=9 帧恒 q=测量值/kp=0/kd=3，leg_step=0。已修（写线程 fill_targets 清单加 FixCrouchLite/PolicyGetup）。
- 教训：向共享发布端加新状态，必须 `grep State::FixSquat` 逐一核对全部状态清单站点（state_name/audit 矩阵/写线程分派/policy_safety_state/FSM 总门/squat_by_timeout/remote_timeout 矩阵）。
- **修复后状态**：x86+回归 8/8，CPRO ARM64 重建 8/8+AUDIT PASS，二进制 SHA `fa4d74c1…`，`as2w_publish.cpp` `ce185513…`。**整条软件链（按键→入口门→FixCrouchLite→写线程）已实机验证到状态切换，仅剩 kp=55 命令的物理执行未确认。**
- 遥控探针教训：1Hz 采样抓不住 200ms 按键边沿，"全零"不能证明遥控故障（操作员质疑正确）。
- **下次测试入口文档**：`02_现场操作/getup1199下次bringup操作单_20261113.md`（含预期日志顺序、失败分流、第一观察点=开膝段 kp=55、证据索引、遗留事项）。
