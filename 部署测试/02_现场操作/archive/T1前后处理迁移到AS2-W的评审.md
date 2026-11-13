# T1 前后处理迁移到 AS2-W 的评审

日期：2026-11-11。范围：评估 `T1运控架构详解.md` 及本地 T1 真机配置中，哪些处理应进入 AS2-W 策略发布链。本文不授权任何真机 LowCmd，也不改变各策略现有禁用状态。

## 结论

有必要吸收 T1 的**分层结构和安全护栏**，但不能把 T1 的数值处理整套复制到 AS2-W。正确做法是：

1. 模型合同层严格复现该模型训练时的观测、历史、缩放、裁剪和动作映射；
2. 合同外只加入不改变正常策略语义的命令整形、切换整形、限位、超时和故障旁路；
3. 任何会改变网络输入分布或闭环相位的滤波，都必须先由训练配置或 recorded-observation parity 证明一致，再启用。

T1 最值得借鉴的是 `命令→观测→推理→动作→设备` 六段流水线和独立安全旁路，不是其 14 轴顺序、100 Hz 策略、200 Hz 下发、滤波截止频率、增益或阈值。

## 新策略早期开发的最小安全壳

早期 bring-up 不需要一次实现完整 T1 安全体系。建议只保留下列六项，其他功能后置：

1. **最小 LowState 有效性检查**：只检查帧新鲜、CRC/有限值、`mode_machine` 和接管后 16 轴 FOC。现有发布端已经实现，保留即可，不再扩展复杂状态识别。
2. **命令限幅 + 斜率限制**：各轴上限由每个策略自己的训练/交付合同决定；不支持的轴锁零。前进、后退、转向分别设置加速斜率，松杆可用更快但连续的减速斜率。
3. **命令超时**：遥控输入失效或上层命令超龄后，不能只把 command 置零并假设机器人会停；应触发 FSM 的零命令 Brake，轮速稳定后受控回站。短暂失联先 Brake，持续失联再进入阻尼/退控。
4. **输出安全包络**：腿目标限制在经实机确认的软限位内，轮速限制在当前试验档位；再增加“单帧目标跳变”保护。早期可在超阈值时拒绝该帧并退出，不必对正常 action 持续滤波。
5. **速度/力矩双保护**：运行时检查腿/轮 `dq`、LowState `tau_est` 和按 PD 公式估计的命令力矩。设置 warning/abort 两档并要求连续若干帧命中，避免单点噪声；abort 走 Brake 或 EmergencyDamping。`LowCmd.tau=0` 只代表无前馈力矩，不代表 PD 项不会产生大力矩。
6. **有界试验与完整日志**：新策略首轮强制零命令、1–2 s 自动退出；再按单轴小命令逐级开放。同步保存 command、obs、raw action、最终目标、LowCmd、LowState 和 FSM 事件。

### 现有代码覆盖与缺口

- 已有：摇杆 `0.05` 死区、LowState 20 ms writer watchdog、CRC/有限值、FOC 确认、命令绝对限幅、腿位置/轮速度绝对限幅、B 准入、切换 blend、试验时限和日志。
- 现有绝对关节/速度限值主要来自 URDF/模型配置，是“不越声明边界”的最后限制，不等于新策略早期试验的安全档位。
- 主要缺口：命令加速度/减速度限制、可判定的命令超时、运行中 `dq/tau_est/预计PD力矩` 两档保护、单帧目标跳变保护，以及这些阈值的逐策略配置。
- R284 事故中 `LowCmd.tau=0`，腿 `tau_est` 仍达到约 73.4 Nm，说明只限制前馈 `tau` 没有意义；保护必须覆盖 `kp(q_cmd-q)+kd(dq_cmd-dq)` 产生的力矩和实际反馈。

### 可以后置的项目

摇杆精细死区/曲线、多输入源优先级、T1 式多通道跌倒识别、接触/足端几何守卫、里程计补偿、额外低通滤波和复杂动作图，都可以等策略基本闭环稳定后再加。它们不是当前新策略 bring-up 的第一优先级。

## 对 rolling-fixed-exit-preview 的直接判断

该交付已经包含专用处理，不能再随意套一层 T1 变换：

- 65 维观测包括 command、gyro、projected gravity、16 轴位置偏差/速度、上一拍动作、phase、零命令轮角记忆和 zero flag；
- 50 Hz 推理，raw action 裁剪为 ±6；腿动作和轮速由 `rolling_fixed_exit()` 专门映射；
- `vy` 被动作包装忽略，只支持 `vx/wz`；
- 已有零命令腿残差门控、轮速归零、stand bias、wheel hold、precalibrated stand 以及 0.75 s 进退权重；
- supervisor 已有反馈年龄 60 ms、静止/姿态/接触/超时门槛。

因此 T1 的 `obs_scales`、10 帧堆叠、默认姿态、action scale、wheel reduction、滤波和 kp/kd **不得叠加**。当前交付自身双仿真门槛失败，增加通用前后处理不能把它变成可真机测试的策略，仍维持“不绑定 B、不开发/同步 launcher”。

## 应迁移的处理

| 位置 | AS2-W 应实现的内容 | 说明 |
|---|---|---|
| 命令入口 | 单一来源/占用权、摇杆死区、策略域限幅、斜率限制、命令超时自动归零 | 数值按每个策略合同配置；首测可额外用更窄的试验限幅 |
| 策略准入 | LowState 连续、mode_machine、16 轴 FOC、姿态、轮速、摇杆居中、站姿保持时间 | 复用已经验证的 A/B gate 思路，不照搬 T1 动作编号 |
| 观测装配 | 有限值、时间戳/帧连续性、轴序/符号/单位、默认角、上一拍 action、phase/历史重置 | 必须逐模型精确匹配；错误时锁存 fault，禁止推理输出进入 LowCmd |
| 推理输出 | raw action 有限值和模型合同内裁剪 | 同时记录 raw action；不能只记录最终 LowCmd，否则难以区分模型振荡和包装错误 |
| 动作映射 | 使用交付专属 action scale/残差/轮速包装，再做硬件关节软限位和硬件能力降额 | 模型内裁剪与硬件安全限位是两层，不能互相替代 |
| 状态切换 | FixedStand→Policy 的连续 blend；退出先命令归零/刹轮，再冻结可达目标或受控回站 | blend 应覆盖 q/dq/kp/kd/tau_ff 的实际语义，不只混 q |
| 发布层 | 50 Hz 策略结果在约 500 Hz LowCmd 环中确定性保持/插值；发布线程 watchdog | 不复制 T1 的 200 Hz，只按 AS2-W 已验证链路设计 |
| 安全旁路 | 反馈陈旧、NaN/Inf、控制周期跳变、姿态异常、关节/轮速/力矩异常、固件告警时锁存退出 | 退出优先受控归零/阻尼；物理急停仍是最终手段 |
| 取证 | 同步记录 command、完整 obs、raw action、包装后目标、最终 LowCmd、LowState 和 FSM 事件 | R284 事故说明只看仿真或最终姿态不足以定位正反馈 |

## 不能直接迁移的 T1 数值

- `dof_vel×0.05`、`ang_vel×0.25`、`lin_vel×2.0`、obs/action clip 50 等缩放裁剪；
- `frame_stack=10`；rolling 模型已经把需要的历史显式编码进 65 维合同；
- IMU/腿 100 Hz、轮 10 Hz 的低通；AS2-W 50 Hz 策略下相同截止频率的离散效果不同，额外延迟还可能降低相位裕度；
- T1 `transition_duration=0.2 s`、轮刚度 3 s 渐增、30/0.5 等增益以及 15/30 Nm 力矩限幅；
- T1 的 60°/6 rad/s 跌倒阈值、10 ms 数据超时和 200 ms 命令超时的具体数值。机制可复用，阈值应由 AS2-W 实测频率、噪声和故障注入确定；
- T1 的 14 轴关节顺序、四足/双足动作图、里程计补偿和偏置补偿。

## 滤波的专项结论

T1 的关节速度/IMU 低通可能对真实高频噪声有价值，但**不能作为修复 R284 剧烈振荡或 rolling preview 失败的经验补丁**。滤波会同时引入延迟；若策略训练时没有同样滤波，可能把输入推离训练分布并加重闭环相位问题。

启用任何新滤波前应依次完成：

1. 用真机静止和动作 LowState 估计噪声频谱、采样抖动和延迟；
2. 从训练代码/交付合同确认训练观测是否滤波及滤波参数；
3. 对同一 recorded-observation 运行“无滤波/候选滤波”回放，量化 obs 和 action 偏差；
4. 在 MuJoCo 加入同等滤波和真实延迟，重新跑闭环随机集；
5. 最后才允许进入离地支架或有界 zero-B 门槛。

## 建议的实现边界

后续发布端可抽成四层，避免每换一个策略复制一套安全逻辑：

```text
RemoteCommandGuard
  -> PolicyObservationAdapter（每策略独有）
  -> PolicyActionAdapter（每策略独有）
  -> TransitionAndSafetyGuard（硬件共用、阈值可配置）
  -> HG LowCmd Publisher（硬件共用）
```

其中前后两个 Adapter 只忠实复现训练/交付合同；命令超时、状态准入、切换 blend、硬件限位、watchdog 和日志属于共用层。

## 资料边界

本次核对了本地 `T1运控架构详解.md`、T1 `qd1_t2d0` 的 `quad_walk.yaml`、`mc_T1.yaml`、`security_guard.yaml`，以及 rolling preview 的 65 维合同、动作包装与 supervisor。当前 Windows 会话没有挂载 `Z:`，因此未读取 Z 盘；本地已归档的真机配置足以支持上述机制/数值边界判断。

## 2026-11-11 实现状态

R214 已按上文“最小安全壳”边界实现第一版：命令加减速斜率、200 ms 合法遥控负载超时→Brake、运行中腿/轮 dq、tau_est、预计 PD 力矩和目标跳变 warning/hard 两档守卫，以及 requested/applied/触发原因日志。守卫只在 PolicyHandoff/PolicyWalk/Brake 生效，没有修改 FixStand/FixSquat、模型观测或动作映射。

服务器 x86 与 CPRO `build-r214-ab-fsm`、`build-r214-zero-b`、`build-r214-ab-fsm-full` 均通过既有 8 项 CTest 和扩展 offline-audit。当前仍只是离线/编译验收；阈值是低速早期试验档，不是官方硬件能力、不是所有策略共享常量，也未经过真机故障注入。详细数值、SHA、限制和后续工作见 `部署测试/05_OpenCode交接/给OpenCode_R214最小安全壳接续_20261111.md`。

2026-11-11 接续轮补充：P0 静态审查完成（共享状态均在 `state_mutex`/`targets_mutex`/原子量保护下，无数据竞争；守卫读取的就是发布线程实际下发的 `current_targets` 与实测 LowState）；守卫计数/决策已拆成纯函数 `evaluate_field_guard` 与 remote 超时谓词，FSM 与离线审计共用同一套阈值；`--offline-audit` 新增离线故障注入（safe 包络 200 帧、warn 第 5 帧 SoftBrake、hard 第 3 帧 EmergencyDamping、motorstate 走 hard 计数且单帧闪断复位、200 ms remote 超时→Brake 且无 Brake→PolicyWalk 自动回退、0→满量程→0 全程斜率/耗时、requested/applied 一致性）。x86 与 CPRO 三构建均 8/8 + 注入 PASS。
