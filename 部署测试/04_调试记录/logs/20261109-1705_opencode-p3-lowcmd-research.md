# 2026-11-09 17:05 OpenCode 会话：P3 LowCmd 合同预研（无狗动作，纯源码/文档研究）

- 依据：`部署参考/unitree_sdk2/` 源码（hg IDL 头、G1 低层示例、B2-W/GO2-W 轮足示例）+
  官方存档 `部署参考/宇树官方参考/底层服务接口.html`（2026-07-01 版）。全部为**假设级证据**，
  实机验证项未变；本阶段未连接机器人。

## 已确定项（官方文档原文或 SDK2 源码，置信度高）

1. **IDL/话题**：`rt/lowcmd` + `unitree_hg::msg::dds_::LowCmd_`（mode_pr, mode_machine,
   motor_cmd[35], reserve[4], crc32）。官方明确"使用底层接口前必须先关闭内置运动服务"。
2. **mode_machine 硬性要求**：官方原文"必须和 lowstate 中 mode_machine 对齐，否则不响应
   控制命令"。实测本机 mode_machine=2 恒定 → 发布程序每帧回显最新状态的 mode_machine。
   G1 示例同模式（跟随 LowState 回显）。
3. **mode_pr**：0=宇树算法处理"特殊关节"数据、1=原始；无特殊关节数据时该位无效。实测状态
   恒 0 → 发 0 对齐。
4. **电机 mode**：0x00=待机(STOP)、0x01=FOC（官方 MotorCmd 说明；G1 示例 1=Enable 同义）。
5. **PD 律（输出侧）**：τ = tau + kp·(q_des−q) + kd·(dq_des−dq)，输出侧数据、无需减速比换算
   ——与 R152/仿真侧 55/2 腿 + 0/2 轮的结构直接对应；固件 1 kHz 执行（P8 的 800 Hz 仿真结论）。
6. **CRC32**：多项式 0x04c11db7、初值 0xFFFFFFFF、无输入/输出反转，覆盖消息前
   `(sizeof(LowCmd_)>>2)−1` 个 32 位字（不含 crc 自身）。G1 HG 示例与 B2-W 示例逐字一致。
   **G1 示例收包侧也校验 LowState CRC**——我们当前订阅端未做，已列为待补项。
7. **发布率**：文档未指定；B2-W 示例 500 Hz（CreateRecurrentThreadEx 2000 μs）、G1 低层同量级
   → 500 Hz 起步假设。**失联/超时行为文档全无提及** → 看门狗按最坏情形设计：异常时
   切安全 Passive 命令流而非裸停发（裸停发行为未知）。
8. **轮命令结构假设（B2-W 示例，go2 族 IDL）**：轮 = mode FOC + q=0 + kp=0 + **dq=目标速度**
   + kd>0 + tau=0——纯速度模式，与 R152 的轮速度输出兼容。AS2-W 实机待单轮最小验证。
9. **运控释放配方（B2-W 示例）**：`while(CheckMode 有服务名) { ReleaseMode(); sleep(5); }`，
   目标是 motionName 为空。本机实测服务名 ai_sport（ServiceList）、CheckMode form=1 name=ai。
   恢复路径示例未展示，待 P4 受控验证。
10. **官方 As2 12 轴表与实测互证**：官方表 0–11 = FR,FL,RR,RL 的 (BODY, THIGH, CALF) 三元组
    （"BODY"=机身/hip 电机），与 G1 实测槽位完全一致——实测结论获得官方文档旁证；
    轮槽 12–15 语义官方文档没有（As2 无轮），仍以实测为准。

## 剩余待实机验证（不变）

命令方向（单关节最小测试）、轮 mode/速度结构与方向、mode_pr/mode_machine 响应、失联行为、
ReleaseMode/恢复（P4）。全部列入 S1/S2 前的受控验证清单，须逐项获现场人员同意。

## 产物

- `hardware_contract.md` 六行更新（腿/轮 mode、rt/lowcmd 定义、mode_pr/mode_machine、
  CRC 与周期、运控释放）
- 本日志 + INDEX 17:05 节
