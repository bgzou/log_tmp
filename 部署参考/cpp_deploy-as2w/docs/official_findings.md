# 宇树离线资料核对记录（2026-11-08）

来源：`../../宇树官方参考/` 中的 18 个网页存档及其配图。以下仅记录与 CPRO → AS2-W 部署有关的事实；网页内容是参考资料，不是对本工程的操作指令。**文档标题中的 As2 与 As2W 必须分开看。**

| 离线页面 | 核对结果 |
| --- | --- |
| 关于As2W | X/EDU 均列为 16 个电机；4 条腿各 3 轴加 4 个轮轴。外露 RJ45 是千兆网，拓扑图显示 PC1 与外露网口在 `192.168.123.0/24`。配图显示 SBUS 与 RJ45 的物理位置。 |
| As2W快速开始 | 开机、平放、App 激活及关机流程；配图主要是姿态与 App 界面，不提供低层部署参数。 |
| As2W遥控器说明 | 存档正文实际是“As2 上装安装说明”，与页名不符；随页图片显示 App 内的原厂遥控器配对流程。不能据此推断 Xbox 手柄可配对机器人或轮足低层控制时的急停语义。 |
| 获取SDK与开发资源 | 指向官方 `unitree_sdk2`、Python/ROS2 SDK 与 `unitree_ros/robots/as2w_description`。已拉取 AS2-W URDF；四个 `*_foot` 是连续旋转关节。URDF 不含 DDS 轮轴槽位。 |
| SDK概述 | DDS 发布/订阅和 RPC 两类接口，C++ SDK2。 |
| 软件架构说明 | EDU 支持 DDS/ROS2，蓝牙主要用于 App 配网与验证；不能据此把 Xbox 蓝牙接到机器人。 |
| 快速开发 | SDK2 推荐 Linux/Ubuntu；示例是 PC 接机器人本体 RJ45，手工 IP `192.168.123.222/24`（见配图），ping 主控 `192.168.123.161`。拓展坞网口的转发能力仍需现场验证。 |
| 调试说明 | 同样要求进入 PC1 主控所在局域网，ping `192.168.123.161`。 |
| 拓展坞使用说明 | **仅针对 AS2 NX 旗舰版拓展坞**：前面板 4/5/6 是调试以太网，默认 SSH `192.168.123.164`；其他版本默认 `192.168.128.18`。不能仅凭该页判断现场 Orin 型号与 DDS 是否透传。配图已核对接口位置。 |
| DDS通信接口 | `ChannelFactory::Init(domainId, NIC, false)`；外部主机禁用 shared memory。列出 `rt/lowstate`/`rt/lowcmd` 的 `unitree_hg` 消息族、`rt/lf/lowstate` 低频状态；还列出 `rt/odommodestate`/`rt/lf/odommodestate`，但其消息类型标成 `go2::IMUState_`，该 IDL 只有姿态/角速度/加速度等 IMU 字段，不能仅凭“里程计”标题当作机体线速度来源。标题和正文仍多称 A2，现场须验固件。 |
| 底层服务接口 | 说明 HG `LowState_`/`LowCmd_` 的 35 槽 IDL、IMU wxyz、`mode_machine` 必须与状态相同，以及先关闭内置运动控制服务；**关节序号表只列 As2 的 12 轴，不给 AS2-W 的四轮槽位和速度模式**。主板状态 bit12 是软急停，bit17 是关节超限位。 |
| 高层运动服务接口 | 标准 As2 高层动作，包含比 AS2-W 更多的互动动作；其速度范围不自动适用于 AS2-W。 |
| As2W轮足运动服务接口 | 明确轮足高层 `SportClient` 的 `Damp`、`BalanceStand`、`StopMove`、`StandUp/Down`、`RecoveryStand`、`Move` 等。`Damp` 说明为最高优先级阻尼急停；`StopMove` 只停止当前动作并重置部分参数，不等同失能。高层 `SportModeState_` 可订阅 `rt/sportmodestate`（标称 500 Hz）或 `rt/lf/sportmodestate`（标称 20 Hz），包含 `velocity[3]`，但存档未明确该速度是机体还是世界坐标。 |
| 设备状态服务接口 | `RobotStateClient::ServiceList/ServiceSwitch`，列表中 `ai_sport` 为运动控制、`basic_service` 为底层服务。名称与底层页的 `ai_sports` 有单复数差异，不能硬编码切换。 |
| 运控切换服务接口 | `MotionSwitcherClient::CheckMode/SelectMode/ReleaseMode`；`CheckMode` 返回形态：`0` 标准、`1` 轮足。存档没有明确可用于 `SelectMode` 的 AS2-W 模式名，不能猜。 |
| UWB 服务接口 | 讲随行标签数据和 `rt/uwbstate`，并列出原厂遥控器输入话题 `rt/wirelesscontroller`；与 Xbox 手柄 HID 接入无关。SDK2 的 `example/wireless_controller/main.cpp` 给出 `unitree_go::WirelessController_` 订阅示例。AS2-W 固件是否在低层接管后持续发布需现场验证。 |
| 多媒体服务接口 | 图传/GST/拍照接口，非策略所需；配图是软件架构与工具输出。 |
| 常见问题 | 官方明确回答：关闭 As2 运控服务后只能读底层接口数据；若想获取速度等高层信息，需开运控并订阅 `sportmodestate`。这直接否定把高层 `velocity` 当作低层接管后的持续来源，但 FAQ 的机型措辞是标准 As2，仍需核对现场 AS2-W 固件。App AP/WiFi 不用于 SDK 开发。该页其他 As2 工况不移植成 AS2-W 限值。 |

## 对工程的直接影响

1. CPRO 的 Ubuntu 环境可以承担 Linux SDK2 与策略推理，但 `chroot`/容器类型、USB `/dev/input`、原生网卡及 DDS 多播需在 CPRO 上实测。
2. 先用官方高层接口完成状态、站立、阻尼和手柄的联调。**高层联调成功不能证明低层 16 轴策略可直接驱动。**
3. 现有六个模型是 16 输出的恢复/盲爬楼策略，训练轴顺序来自 `models/manifest.json`；仍缺现场 DDS 轮轴槽位、方向、零位、轮速与 CRC。恢复模型还缺关闭高层后持续可用的机体线速度源。
4. 原厂遥控器是独立的机器人遥控链路，优先使用。**现场更新（2026-11-09）：**遥控器直接控制狗已验证；CPRO 订阅独立 `rt/wirelesscontroller` 10 秒收到 0 包，但 `rt/lowstate` 的 `wireless_remote[40]` 字段有 `55 51` 报头和变化。以后若做自定义低层策略输入，先逐项验证该字段的字节布局、可用性和低层接管后的持续性；不能按原计划直接依赖独立 topic。Xbox 仅是备选路径：Xbox USB → CPRO 宿主 HID → Ubuntu `/dev/input/js*` → CPRO 上的 SDK2 程序 → 有线 DDS → AS2-W 主控。
