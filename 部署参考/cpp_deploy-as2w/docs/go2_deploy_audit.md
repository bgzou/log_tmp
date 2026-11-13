# GO2 `deploy/` 文件移植判断

核对对象：`部署参考/unitree_cpp_deploy-go2/deploy/`，2026-11-08。这里审的是 upstream `go2` 分支，而 `AS2-W_部署改造指南_from_Go2_v0.6.6.md` 还讨论另一套重度修改的 v0.6.6。两者的文件内容不可混作同一版本。本次 AS2-W 是 16 轴、58→16 的 C++ `.bin` 策略，推理在 CPRO Ubuntu；下表以这批**实际交付权重**为准。

## 先看 GO2 真正运行的链

```text
robots/go2/main.cpp
  → include/param.h 读 robots/go2/config/config.yaml
  → include/FSM/CtrlFSM.h 创建、每 1 ms 调度各状态
  → include/FSM/FSMState.h 每轮更新 LowState/手柄并发布 LowCmd
  → State_Passive / State_Fix / State_RLBase
  → State_RLBase.cpp 加载 deploy.yaml 和 policy.onnx
  → isaaclab/manager_based_rl_env.h + observation/action managers
  → OrtRunner 推理 → GO2 motor_cmd
```

这不是“很多独立脚本”。`deploy/` 只有两个 Python 画图工具；部署主链主要是 C++ 头文件、一个 GO2 专属 `State_RLBase.cpp`、`main.cpp`、CMake 和 YAML。仓库根的 `scripts/udp_test.py` 是一个 12 轴关节位置 UDP 包接收器，不在部署主链。用户过去的 `go2_v066_xbox_wifi_workstation.sh` 是另一个 v0.6.6 项目的启动脚本，也不在这个 upstream `deploy/` 目录。

## 按文件组决定是否移植

| GO2 文件/组 | 在 GO2 做什么 | AS2-W 当前决策 |
| --- | --- | --- |
| `include/FSM/BaseState.h`, `CtrlFSM.h` | 状态接口、工厂注册、事件转移、定时调度 | **移植设计，不原样复制。** AS2-W 需要自己的观察/就绪/翻正/爬楼/停止/故障状态。上游定时 `dt=0.001` 是 GO2 控制调度值；策略交付为 20 ms 推理周期，低层发送频率需实机确认。 |
| `include/FSM/FSMState.h` | 共享 GO2 LowState/LowCmd，执行手柄 DSL；每轮 `post_run()` 发布命令 | **必须重写。** 它绑定 GO2 `Types.h`，会自动发布 LowCmd。AS2-W 要先有只读状态源与输入适配，经模式、映射、看门狗合同通过后才接发送端。 |
| `include/FSM/State_Passive.h` | GO2 电机模式/kd、跟随当前 q | **只借状态概念。** AS2-W 的阻尼、失能和交还原厂运控语义未知；不能把 GO2 的 `mode/kd` 视作安全停止。 |
| `include/FSM/State_Fix.h`, `LinearInterpolator.h` | 固定姿态插值与自动转移 | **后续借插值算法，重写执行状态。** 该 upstream 版本从上次命令角取起点、立即设增益；改造指南提到的“读实测角并渐变增益”属于另一个 v0.6.6 版本。AS2-W 16 轴姿态、轮轴保持与 PD 均待校准。 |
| `include/FSM/State_RLBase.h`, `robots/go2/src/State_RLBase.cpp` | 起 ONNX 策略线程、配置固定/摇杆速度、写 GO2 电机、记 CSV | **用现有 `src/policy.*` 重写对应状态。** 本交付不是 `policy.onnx + deploy.yaml` 路径；是两类 `.bin` 权重，58 维观测/16 维动作，包含轮速目标。不能套它的 `joint_ids_map`、增益或 12 轴 UDP 包。 |
| `robots/go2/include/Types.h`, `unitree_articulation.h` | GO2 SDK 包装类型、将 IMU/电机状态投给 IsaacLab 环境 | **AS2-W 平台层重写。** GO2 是 `unitree::robot::go2`，当前 AS2-W 研究资料指向 HG LowState；16 个实体轴在 35 槽消息中的具体位置仍需核对。现有 `deploy/robots/as2w/src/diagnostics.cpp` 是这层的只读起点。 |
| `include/unitree_joystick_dsl.hpp` | 解析 `LT + A.on_pressed` 等 GO2 手柄表达式 | **暂不复制，待原厂遥控器 DDS 实测后决定。** 需要先记录 AS2-W 原厂遥控器 `keys` 位、按键边沿、超时和运控切换后是否持续发布，再建模式选择输入。 |
| `include/param.h`, GO2 `config/config.yaml` | Boost CLI、yaml-cpp 配置、路径解析、FSM 转移和策略目录 | **保留配置驱动思想，重写 schema。** 现有 AS2-W `deploy/robots/as2w/config/config.yaml` 只列六份模型，Python 真实读取；尚未声称它是运行中的 FSM。C++ 控制器完成时再加明确的状态图、门槛和退出配置。 |
| `include/isaaclab/algorithms/algorithms.h` | ONNX Runtime 的 `OrtRunner` | **当前不需要。** 同事交付 `.bin` 可直接用 C++ 标准库推理；保留 `.onnx` 用于交叉校验。如果未来模型只能以 ONNX 交付，再单独引入 ORT。 |
| `include/isaaclab/envs/manager_based_rl_env.h`, `manager/*`, `mdp/observations/*`, `mdp/actions/*`, `assets/articulation/*` | 解析 `deploy.yaml` 声明的观测组、历史帧和动作缩放 | **当前不需要整套移植。** `src/policy.cpp` 已按这批 58 维/16 维模型的交付定义构造观测、动作与限制。未来新增不同维度、历史帧或多输入策略，再按该策略训练合同选择声明式管理器或专用状态。 |
| `include/isaaclab/envs/mdp/terminations.h` | GO2 策略坏姿态终止判断 | **重写判据。** AS2-W 轮足姿态、故障码、IMU 与退出模式需现场验证；不能直接复用 GO2 阈值。 |
| `include/utils/VelocityCommandDamper.h` | 摇杆速度滤波、加减速限制 | **这两类策略目前不需要。** 模型并非手柄可调速的普通行走策略；未来有速度指令型模型时可借设计并重设范围。 |
| `include/isaaclab/devices/keyboard/keyboard.h`, `UdpSocket.h` | 本地键盘/UDP 外部控制输入或日志转发 | **备用路径。** 优先原厂遥控器 DDS；如 CPRO 无法取得它，再评估本地 USB 手柄/键盘。不要复制工作站→Orin 的 GO2 WiFi UDP 链。 |
| `include/DataLogger.h` | 通用逐帧 CSV 记录 | **可借格式/字段设计，非运行依赖。** 现阶段 `field.sh` 已留原始日志；未来真机控制器应记录状态、推理耗时、输出、切换原因和故障。 |
| `robots/go2/CMakeLists.txt` | Boost/yaml-cpp/ONNX Runtime/GO2 SDK 链接 | **不用移植。** 当前 AS2-W `CMakeLists.txt` 只需 C++ 核心、SDK2 与线程；CPRO Ubuntu 上要实际完成链接验证。 |
| `deploy/tools/visualize_logs.py`, `visualize_position.py` | 按 GO2 CSV/URDF 画足高、里程计 | **当前不需要。** 前者硬编码 GO2 12 轴和足名，后者依赖尚未生成的里程计 CSV；将来日志 schema 固定后再改。 |
| 根目录 `scripts/udp_test.py` | 收 `<IIQ12f>` 的 `JPOS` 12 轴 UDP 包 | **不移植。** 当前链路是 CPRO 经 DDS 控制 AS2-W，不使用该 UDP 关节监视协议。 |

## 结论与下一步代码边界

需要的是 **GO2 的模块职责和状态转换方法**，不是整包复制头文件。现在已经有模型推理核心、只读 DDS/原厂高层诊断、按名字选权重、打包与阶段日志。真正缺少的是：

1. `RobotStateSource`：把这台 AS2-W 的 HG LowState、IMU、16 轴、机体速度整理成受时间戳约束的状态；这一步可先只读。
2. `RemoteInput`：把经实测的原厂遥控器 `keys` 转为带边沿和超时的使能/停止/模式请求。
3. `LowCmdSink`：基于实际轮轴槽位、模式、CRC、发送频率和控制权协议编码命令，并实现看门狗；这一步是上机合同门槛。
4. `CtrlFSM`：只有前三层可验证后，才把两类策略、进入姿态、自动结束、故障和交还原厂运控连成单进程控制器。

上述模块建议放在 `deploy/robots/as2w/` 下，通用的 `src/policy.*` 保持与设备无关。详细系统图和现场阶段顺序见 `docs/architecture.md`。现有 `field.sh` 是调试入口，不能替代最终 FSM。
