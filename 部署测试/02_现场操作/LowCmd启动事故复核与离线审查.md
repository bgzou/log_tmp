# AS2-W LowCmd 启动事故复核与离线审查

**2026-11-10 后续（补充本页 11-09 的"其余仍待验证"）：** 本页分析的两事故根因（盲发/确认门槛）及候选启动序列已随后续多轮真机验证消化：Passive-only 两次→A/Y 三次→B 零速两次→行走取证，均按 500ms 观察→中性唤醒→FOC 确认→kd 渐升序列通过，无报警；急停锁存导致重启不上电的教训已入 AGENTS。剩余未验证项与全部原始日志见 `../04_调试记录/INDEX.md`。
日期：2026-11-09。**更新：现场人员逐次同意的两次 Passive-only 真机试验已通过；本文其余起立/策略/退出部分仍是待验证方案。**维护源码：`部署参考/cpp_deploy-as2w/deploy/robots/as2w/r214/r214_publish.cpp`。

## 23:43–23:46 现场结果（覆盖下面实验前限制）

- 两次相同参数 Passive-only 试验均按 500ms 不发布观察→zero-gain mode1→16轴反馈确认→kd0→3→3s保持→自动停发完成，日志 `部署测试/04_调试记录/logs/20261109_passive_only_trial{1,2}.log`。
- 并行只读主板/电机监测均见 16 轴 mode 0→1→0，主板仅既有 bit0、没有新增保护位，电机 warning/motorstate 聚合均0；现场人员两次确认狗始终趴下、无报警异常。详 INDEX 最新两节。
- **结论仅限这台固件当前趴下姿态的 Passive 启动链。** 两次成功没有区分旧报警到底由模式切换、kd5、状态等待还是其他字段造成；不验证 FixStand/轮命令/失联/低层遥控器急停/运控回收。监测第二次日志有一条混入 CycloneDDS 断言文字的损坏采样行，已在 INDEX 记录，后续应复核软件日志来源。
- 23:49–23:50 经现场人员单独同意 `SelectMode("ai")` 恢复原厂运控，读回 `ai_free_walk`；现场确认稳定站立、原厂遥控正常，无报警。**当前狗不再处于 ReleaseMode**，下次低层试验需重新履行释放与每次动作告知/同意门槛。

## 证据与结论的边界

| 类别 | 内容 | 依据 |
| --- | --- | --- |
| 已实测 | 第一次启动发生喇叭保护；当时 stdin EOF 跳过确认，writer 在未收到 LowState 时盲发，mode_machine 可能为 0。 | INDEX 22:10；事故程序与日志。 |
| 已实测 | 第二次修复首包守卫和输入 `GO` 后仍报警；至少收到过 LowState，报警后其流停止。 | INDEX 22:50；`r214_passive2.out`。日志没有逐帧 `Write()` 时间戳，不能严格断言**恰为第一帧**。 |
| 已实测 | ReleaseMode 前 0–15 槽反馈 mode=1，之后 mode=0，反馈持续约 1 kHz；16–34 槽反馈 mode=0。 | INDEX 23:10/23:30；`before_release.txt`、`after_release.txt`。 |
| 可由旧代码推断 | 第二次发布意图是 mode=1、q=最新反馈、kp=0、dq=0、kd=5、tau=0、mode_machine 回显；没有事故现场的实际 LowCmd 原始帧抓包。 | 旧 `r214_publish.cpp`。 |
| 尚未证实 | 保护到底由 **mode=0→1**、同帧 kd、轮电机语义、命令 CRC/字段校验、机型/软启动/电机警告，或其组合触发。 | 缺事故时主板状态字、电机 `motorstate/reserve[3]` 和发布原始帧。 |

所以，交接文件中“根因确认=mode 切换加 q/kp/kd 同帧”应读作**当前最强的事故关联假设**，不能据此宣布采用任一唤醒序列必然安全。`after_release.txt` 的一个样本里活跃轴 |dq|≤约 0.0246 rad/s；若按文档的 PD 律，仅 kd=5 所致的该瞬时阻尼力矩上界约 0.123 Nm。这降低了“静止时 kd=5 单独导致过流”的直觉可能性，却不能排除切换瞬态、轮状态或固件校验。

## 官方代码逐项核对

| 来源 | 实际行为 | 可用于 AS2-W 的程度 |
| --- | --- | --- |
| `unitree_sdk2/example/go2w/go2w_stand_example.cpp` | `LowCmdWrite()` 先 `motiontime++`；`if(motiontime>=500)` **才调用 `Write()`**。前 500 tick 是不发布的传感器观察期。第一帧发布时 12 条腿的 q 已被插值逻辑覆盖，kp=70/kd=5；轮槽仍可能保留初始化的 `PosStopF/VelStopF`。 | 它使用 `unitree_go::LowCmd_`，不能推出 HG 有相同的停止值语义。尤其不能声称它“先连续发 500 帧停止命令唤醒”。 |
| `unitree_sdk2/example/g1/low_level/g1_dual_arm_example.cpp`、`h2/low_level/h2_dual_arm_example.cpp` | 使用 `unitree_hg::LowCmd_`，从 LowState 取 `mode_machine`，在有状态/命令后写 mode=1 的实际 q/kp/kd；没有使用 `PosStopF/VelStopF`。 | 证明 HG 例程没有必须使用特殊停止值的通用规则；**不证明 AS2-W 接受同样命令**。 |
| `unitree_cpp_deploy-go2/deploy/include/FSM/State_Passive.h` | Passive 为 q 跟随反馈、kp=0、kd 配置值；它依赖 GO2 的 IDL、启动和固件。 | 可参考“q 跟随”形式，不能直接继承 GO2 的唤醒/安全结论。 |
| 官方《底层服务接口》 | HG `LowCmd_` 有 `mode_pr/mode_machine/motor_cmd[35]/reserve/crc`；电机 mode 0=STOP、1=FOC；PD 律 `tau+kp(q_des-q)+kd(dq_des-dq)`。文档没有 HG `PosStopF/VelStopF` 或 AS2-W 启动时序说明。 | 不把特殊数值写入 HG 命令；所有步骤仍需该固件实测。 |

## 本次 C++ 修改：候选启动序列

`r214_publish.cpp` 的 R214 FSM 状态仍为 `Passive/FixStand/PolicyStand/PolicyWalk/Brake/FixSquat/EmergencyDamping`，但编译期**锁住 A/B/Y 运动**（正常构建未定义 `AS2W_ENABLE_R214_MOTION`），运行默认仅 Passive，最长 10 秒、默认达成 Passive 后 3 秒自动停止。`--offline-audit` 在 ChannelFactory 初始化前返回，不连接 DDS。

| 阶段 | 0–15 活跃槽 | 16–34 空槽 | 进入下一段的条件 |
| --- | --- | --- | --- |
| 观察期，**不发布** | 无 LowCmd | 无 LowCmd | CRC 正确、mode_machine 非 0、16 轴 q/dq 有限、16 轴反馈 mode=0、状态新鲜 ≤20 ms，连续 ≥500 ms 且至少 100 包；5 秒不满足即退出。 |
| Neutral 候选，500 Hz | mode=1；q=各槽最新原始 q；dq=0、kp=0、kd=0、tau=0；mode_pr=0，mode_machine 每帧回显，CRC 每帧重算 | 全零，mode=0 | 至少 500 ms，16 轴反馈 mode=1 连续 ≥200 ms；2 秒未确认即停止发布。**首帧仍会请求 FOC，可能再次报警。** |
| PassiveRamp，500 Hz | 同上，但 kd 在 1 秒内从 0 线性升到 3 | 全零 | 16 轴 mode=1 一直保持，状态持续有效；反馈丢失、CRC 错、Write 失败即停止发布。 |
| PassiveHold，500 Hz | mode=1、q 跟随、kp=0、dq=0、kd=3、tau=0 | 全零 | 首测默认保持 3 秒后停止发布；X 变 EmergencyDamping（同一 Passive 帧），SIGINT/SIGTERM 停止。**停止后固件行为仍未验证。** |

这样分离了 FOC 请求和增益引入，使用有限的实测 q，避免文档未定义的 `2.146E+9/16000` 特殊值；但**零增益的 mode=1 帧是否被 AS2-W 接受仍未知**。观察期不发布不会测试接管，且发送 mode=0 帧并非“必然无害”，因此本版不采用未经验证的 mode=0 预热发布。空槽保持默认 mode=0；其反馈无实体轴不意味着已严格证明固件忽略所有命令，但没有证据支持把 16–34 强设 FOC。

Writer 每个周期只使用 CRC 正确且 ≤20 ms 的状态，重建 LowCmd（防旧字段残留）；一旦超时或写失败就停发并锁故障。**停发不是已验证的安全退出**，尤其不适用于站立/运动阶段。因此运动编译锁必须保持，直到专门验证反馈失联、急停和运控回收。

## 离线验收与证据

1. 在服务器 x86 显式构建 `AS2W_R214=ON,AS2W_R214_PUBLISH=ON`，CTest **8/8**；原始 `部署测试/04_调试记录/logs/20261109_lowcmd_startup_x86_build.log`。
2. `as2w_r214_publish models/r214/deploy.yaml config/r152_measured.map --offline-audit` 生成 35 槽 Neutral/Passive 合成帧和完整内存十六进制；不初始化 DDS。原始 `logs/20261109_lowcmd_startup_x86_audit.log`。
3. `python tools/verify_startup_frames.py logs/20261109_lowcmd_startup_x86_audit.log` 独立逐字计算 CRC、核对字段；同一程序也检查合成 LowState 拒绝条件、500/200/1000ms 时序、无回读超时、回读丢失。注意完整内存 hex 包括内存布局，不等于 DDS CDR 线上序列化字节；固件接收校验仍未验证。
4. CPRO Ubuntu ARM64 显式构建/CTest **8/8**；原始 `logs/20261109_lowcmd_startup_arm64_build.log`、`logs/20261109_lowcmd_startup_arm64_audit.log`。两个架构生成的合成帧 raw_hex **逐字节一致**，CRC 分别为 Neutral `0x5ba0c90e`、Passive `0x421a6fb0`。此证明离线字段构造一致，**不证明固件接受**。

## 现场审查后才允许的分步取证方案

下面是**计划，不授权执行**；每一步可能导致狗动作、报警或失稳时，先明确告诉现场人员具体行为/风险，等其当次同意。现场人员握原厂遥控器并能操作物理急停，狗保持趴下、场地开阔，旁人远离；急停能否在低层接管生效**仍未知**，不能作为唯一自动保护。

1. **只读基线**：并行记录 `rt/lowstate`（完整 35 槽的 mode/q/dq/tau_est/motorstate/reserve[3]）、官方 `rt/lf/mainboardstate` 状态字/电压、电池、运控模式，核对无当前错误、`mode_machine=2` 和约 1 kHz 连续性。主板错误字重点看 bit7 软启动、bit8 电机、bit9/10 过流、bit12 软急停、bit14/15 机型、bit17 关节限位；来源为官方《底层服务接口》。若读不到这些信号，应先补只读诊断工具。
2. **ReleaseMode 独立复核**：仅在现场人员当次同意下做 ReleaseMode，不发布 LowCmd；期望 0–15 反馈 mode 1→0、狗保持趴下、状态流稳定。任何异常立即停止，不进入下一步。
3. **首个发布实验只测 Passive**：再次逐项告知现场人员，获得当次明确同意后才启动当前被动模式构建；现场不得使用 `--enable-fsm-motion`，默认 A/B/Y 无效。期望先有 500ms 不发布，再零增益候选帧；若固件接受，mode 0→1，随后 kd 渐增到 3，保持 3 秒，无预期位移/警报。连续采集每个阶段的状态字和电机警告、发布计数、时间戳；任何报警、反馈中断、非预期动作或电压异常立即终止实验并由现场人员处理。**零增益首帧可能仍触发第三次报警；离线测试无法排除。**
4. **失败分析**：不要重复尝试或扫参数。记录首个错误位、首次异常时间、受影响槽位、是否在 mode 切换前/后发生，和 `Write` 计数。急停锁存时先解除，再按既有现场流程冷启动；不得自动 `SelectMode("ai")`（已知从趴下会突然起立）。根据证据修复并重新走离线审查。
5. **若 Passive 一次通过**：仍不进入 FixStand/策略行走；至少复核停止发布和控制权恢复后的状态，再单独审查 LowCmd 方向、轮速、失联/急停。最终能否测试 A/B/Y 属另一阶段。

## 未完成的硬件合同

HG 零增益 mode=1 帧的固件接受性、具体保护报警位、LowCmd 命令方向和轮速、站立时断流、原厂遥控器在低层模式下急停、退出及 `SelectMode` 站立行为、CPRO/机器人当前固件版本，均需现场设备证据。两次事故足以说明**目前不能将源码编译通过视为准许发布**。
