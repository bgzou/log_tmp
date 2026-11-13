# AS2-W × 鸿蒙 PC：RL 运动策略部署项目背景与开发计划

> 日期：2026-11-08  
> 用途：作为 Codex 后续开发的项目背景和技术约束  
> 当前阶段：开发环境准备、通信验证、部署方案设计

## 一、项目目标

将宇树 AS2-W 轮足机器人的强化学习（RL）运动控制策略部署到华为鸿蒙 PC（Charlotte Pro / CPro）上执行。

**目标是让鸿蒙 PC 承担完整的策略推理及控制命令生成，直接通过宇树 DDS SDK 与 AS2-W 机器人通信。**

希望复用之前 Go2 EDU 上的 `unitree_cpp_deploy` C++ 部署方案，尽可能减少对现有运控代码的改动。

## 二、目标系统架构

```text
个人 Windows PC
    │
    │ HDC / SSH
    │ 开发、编译、部署、调试
    ▼
鸿蒙 PC（Charlotte Pro）
    │
    ├── AS2-W C++ Deploy 程序
    │     ├── Unitree SDK2 / CycloneDDS
    │     ├── LowState 接收
    │     ├── Observation 构建
    │     ├── RL Policy 推理
    │     ├── Action 转换
    │     ├── PD / MotorCmd 生成
    │     └── LowCmd 发布
    │
    │ Ethernet / DDS
    ▼
AS2-W 机载 Orin
    │
    │ 现有网络连接
    ▼
AS2-W 运控上位机
    │
    ▼
轮足电机控制系统
```

### 核心架构约束

1. **Windows PC 只负责开发调试鸿蒙 PC**，原则上不参与机器人控制，也不需要直接连接 Orin。
2. RL Policy、Observation、Action 和控制命令生成均在鸿蒙 PC 上完成。
3. 机载 Orin 主要作为现有 DDS 网络的连接节点，不需要运行 RL 推理程序。
4. 优先让鸿蒙 PC 直接通过 `unitree_sdk2` 与 AS2-W 通信，**不预先设计 Orin DDS Bridge**。
5. 只有实际验证发现跨网卡 DDS 不可达，才考虑在 Orin 上调整路由、网络桥接或增加转发服务。
6. 必须确认 AS2-W 的低层控制权限及官方运控接管方式，避免多个控制进程同时发布 LowCmd。

## 三、已有开发经验

### 3.1 CPro 控制 Go2 EDU 的历史经验

此前已经使用过一台 CPro，在其 Ubuntu 容器中直接运行宇树 DDS SDK，并成功控制 Go2 EDU。

这说明：

- 曾经成功从 CPro Linux 环境直接访问机器人 DDS 网络。
- 不需要将推理程序部署到机器人机载 Orin。
- C++ DDS 通信、Observation、Policy、Action 可以组成一个独立部署程序。
- 该经验可以作为新项目的参考，但不能直接保证 Charlotte Pro 当前的鸿蒙版本和 AS2-W 网络完全兼容。

### 3.2 Go2 EDU 部署基础

此前使用过：

- `unitree_cpp_deploy` C++ 部署框架
- Unitree SDK2 / DDS
- ONNX Runtime
- RL Policy 推理
- Observation 构建
- Action Scale、Offset 和 PD 控制
- LowState / LowCmd 通信
- 运动模式切换及安全退出

之前 Go2 Policy 的典型频率为 50 Hz，底层收发可使用更高频率，但 AS2-W 的最终频率必须按照新策略和 SDK 确认。

**开发时应优先复用原有 Deploy 的结构，而不是重新设计一套运动控制程序。**

## 四、AS2-W SDK 已确认的信息

官方仓库：

https://github.com/unitreerobotics/unitree_sdk2

AS2 示例：

https://github.com/unitreerobotics/unitree_sdk2/tree/main/example/as2

目前已检查的官方源码：

```text
example/as2/
├── sport/
│   ├── as2_sport_client.cpp
│   └── as2_sport_state.cpp
├── audio/
└── CMakeLists.txt
```

其中：

- `as2_sport_client.cpp`：高层运动 API，包括站立、行走、步态控制等。
- `as2_sport_state.cpp`：订阅运动状态，使用 `rt/lf/sportmodestate`。
- DDS 初始化使用 `ChannelFactory::Instance()->Init(0, networkInterface)`。
- SDK2 内有 `unitree_hg::msg::dds_::LowState_` 和 `LowCmd_` 类型定义。
- 这些底层消息定义包含35个电机槽位，但不能据此推断 AS2-W 的实际电机数量和索引。

需要注意：公开仓库中的 AS2 高层控制示例，不等于已经验证 AS2-W 支持所有低层电机控制接口。

**AS2-W 是轮足平台，不能直接照搬 Go2 的12关节控制模型。** 当前按12个腿部关节电机及4个轮毂电机规划适配，具体配置以 AS2-W 对应的官方开发资料为准。

需要从 AS2-W 文档进一步确认：

- LowState / LowCmd 的实际 DDS topic、IDL 和消息频率。
- 电机索引及轮毂电机控制模式。
- 低层控制是否需要 EDU 权限、专用固件或其他条件。
- 官方运控退出、低层接管和恢复方式。
- 接管后如何避免与原厂控制器冲突。

## 五、鸿蒙 PC 的开发路线

当前存在两条候选路线。

### 路线 A：鸿蒙 PC 的 Linux 环境（优先验证）

在鸿蒙 PC 可用的 ARM64 Linux 环境中运行：

```text
Linux 环境
├── unitree_sdk2
├── CycloneDDS
├── ONNX Runtime
├── AS2-W Deploy
└── DDS Ethernet
```

优点：

- 可以最大程度复用现有 C++ 工程。
- 可以使用 Linux CMake、GCC、GDB 等工具。
- 如果 SSH Server 和网络访问正常，可以直接使用 Windows VS Code Remote-SSH / MobaXterm。
- 初期不需要完成原生 HarmonyOS NDK 适配。

主要风险：

- 鸿蒙当前版本是否提供可用 Linux 环境。
- 是否支持 Ubuntu 容器，还是只提供 openEuler 等环境。
- Linux 环境能否访问物理网卡。
- DDS 组播发现和双向通信是否正常。
- 网络隔离、NAT 或虚拟网卡是否影响低层控制。
- 控制周期是否存在明显延迟或抖动。

### 路线 B：HarmonyOS 原生部署

如果项目明确要求策略推理在鸿蒙原生运行环境中执行：

- 使用 HarmonyOS NDK 开发 ARM64 C++ 程序。
- 研究 `unitree_sdk2` 与 CycloneDDS 原生移植。
- 研究 ONNX Runtime 或 MindSpore Lite 推理。
- 通过 HDC 部署、运行和调试。
- 验证原生 Socket、DDS、线程调度和程序生命周期。

特别注意：

**Linux ARM64 与 HarmonyOS ARM64 不能直接视为二进制兼容。**

现有 Linux 可执行文件不应假定能够在 HarmonyOS 原生环境直接运行。

当前尚未确定项目是否强制要求原生 HarmonyOS。Codex 应先调查设备的实际开发权限与运行环境。

## 六、Windows PC 开发方式

Windows 是主要源码开发和调试主机。

推荐工具：

- VS Code：代码编辑与 Git 管理。
- HDC：连接鸿蒙原生系统、执行 Shell、传输文件。
- MobaXterm / SSH：在 Linux 环境支持 SSH Server 且网络可达时进行远程开发。
- HarmonyOS SDK / NDK：用于原生开发。
- CMake：构建 C++ 项目。

HDC 常用指令：

```powershell
hdc version
hdc list targets
hdc shell
hdc shell uname -a
hdc shell uname -m
hdc shell id
```

HDC 可以承担原生调试任务，但不等同于 SSH。

如果 Windows 通过有线网口进行 HDC 调试，同时鸿蒙 PC 还需要有线连接 AS2-W，应检查端口数量以及是否可以通过 Wi-Fi 或交换机实现两条连接。

**不需要为了 Windows 调试而把 Windows PC 加入机器人的 DDS 控制网络。**

## 七、建议的 Codex 开发顺序

### Phase 0：环境与接口审计

先完成信息收集，不修改现有机器人控制程序。

1. 识别 Charlotte Pro 的实际 SoC、HarmonyOS 版本、CPU 架构。
2. 确认 HDC 权限、Linux 环境、SSH 支持。
3. 确认机载 Orin 与 AS2-W 运控上位机的网络拓扑。
4. 阅读 AS2-W 对应 SDK、低层控制及运控接管文档。
5. 审阅现有 Go2 Deploy 工程，整理可复用组件。

交付：环境审计报告、技术风险和推荐部署路线。

### Phase 1：鸿蒙开发环境验证

1. Windows 与鸿蒙 PC 建立可靠连接。
2. 完成 C++ Hello World 编译及运行。
3. 验证文件传输、日志和远程调试。
4. 如果采用 Linux 环境，测试 SSH / VS Code Remote-SSH。
5. 建立可重复执行的构建和部署脚本。

交付：可重复使用的 Windows → 鸿蒙开发链路。

### Phase 2：AS2-W DDS 只读通信

1. 编译 Unitree SDK2。
2. 识别正确的 DDS 网络接口。
3. 验证 AS2-W 高层状态订阅。
4. 在接口开放的情况下进一步验证 LowState。
5. 记录状态数据、接收频率、丢包和延迟。
6. 确认是否需要修改 Orin 的网络配置。

这一阶段**禁止主动下发 LowCmd**。

交付：DDS 只读测试程序及通信验证报告。

### Phase 3：RL 推理迁移

1. 从原有 Deploy 工程提取推理模块。
2. 在鸿蒙 PC 上加载 AS2-W 策略模型。
3. 用固定 Observation 对比原始推理输出。
4. 测量推理延迟、控制周期抖动和 CPU 负载。
5. 实现完整的 Observation → Policy → Action 软件链路。
6. 使用录制的状态数据进行离线回放，禁止驱动实机电机。

交付：推理与离线回放测试程序。

### Phase 4：低层控制适配

1. 适配 AS2-W LowState / LowCmd。
2. 适配关节及轮毂电机索引。
3. 适配 PD 参数与控制模式。
4. 适配运动状态机及安全接管。
5. 增加命令超时、状态超时、关节限幅和异常退出保护。
6. 按官方要求完成控制器切换。

交付：AS2-W 低层部署程序及安全测试记录。

### Phase 5：实机闭环

在低层接口权限、控制模式和安全保护全部确认后：

1. 验证状态接收及命令格式。
2. 进行受限、可安全停止的控制测试。
3. 验证站立与基础轮足运动。
4. 测试通信丢失、策略超时和恢复。
5. 测量完整闭环延迟、频率与运行稳定性。

交付：可重复运行的 AS2-W 鸿蒙部署方案。

## 八、关键技术原则

1. 不默认需要 Orin DDS Bridge。
2. 不默认可以将 Go2 的 `unitree_go` 消息直接用于 AS2-W。
3. 不默认 AS2 的高层运动 API 等于 AS2-W 的低层控制接口。
4. 不默认 Linux 容器可以直接使用 DDS 组播网络。
5. 不默认鸿蒙原生可以直接运行 Linux ARM64 程序。
6. 不在尚未完成底层接管和安全验证前向实机发布 LowCmd。
7. 优先使用 CPU 推理跑通链路，NPU 加速作为后续性能优化。
8. 对未确认的产品规格和接口能力，明确标记为待验证，不以推测替代实测。

## 九、给 Codex 的工作指令

请以本文作为项目背景。

首先进行 **Phase 0：开发环境、SDK 接口和现有 Deploy 架构审计**，不要直接开始修改机器人控制代码。

重点确认：

- Charlotte Pro 上最适合运行 C++ RL Policy 的环境。
- 是否能够复用之前 CPro Ubuntu 容器的 DDS 方案。
- AS2-W 是否能够由外部 PC 直接通过 SDK2 进行低层控制。
- 现有 `unitree_cpp_deploy` 迁移至 AS2-W 的必要代码改动。
- Windows PC 如何高效完成鸿蒙端的构建、部署和日志调试。

在得到实际设备信息与源码后，优先选择改动最少、可验证、安全性明确的技术路线。

不要在未经验证的情况下引入 Orin DDS Bridge、ROS2 或额外的控制通信协议。
