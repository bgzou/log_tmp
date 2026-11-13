# R1199 实机抖动反馈与策略交付合同（可独立阅读）

2026-11-12。请先读 `docs/robot_jitter_and_posture_analysis.md`、
`docs/training_server_alignment.md`、`docs/current_opencode_fix_handoff.md`
和 `docs/policy_delivery_contract.md`。
本包含两次真实机器人前后滚动的原始日志、
提取后的 10 ms/5 Hz 表、图、复算脚本、当前部署控制器源码、R1199 权重和上游合同。
**无需访问工作站、CPRO 或 caolin 服务器。** `MANIFEST.sha256` 列出包内全部文件校验值。

## 要解决的两个不同现象

1. **前后滚动过程中真实可闻的关节抖动**：现场人员两次都听到，不只是起步/停车。
   第二轮持续前进窗口（10 ms 状态采样时钟 53–67 s）12 腿轴 `dq` RMS
   0.1113 rad/s，对照安静零速 0.0066；去 0.2 s 慢变化的 `tau_est` RMS
   0.6799 Nm，对照 0.0181。前进中 59.35–59.95 s 的 FR 髋 `dq` 正负交替，
   同段 FR 髋估算力矩峰谷差 3.225 Nm。见 `evidence/derived/motion_jitter.png`。
   这些是运动中实机反馈波动的证据；100 Hz 采样无法确定声音频率或唯一声源。
2. **停走切换时身高/腿姿态变化**：见 `evidence/derived/posture_and_command.png`。
   第一次推杆两轮分别触发 0.272911/0.254249 rad 腿目标单帧软件预警；
   停车后髋目标误差再次增大。当前 C++ 的站立补偿在非零速度时可一帧撤掉，
   是姿态突变的直接候选原因，不能据此解释所有持续滚动抖动。

两轮主板/电机保护位均为 0，软件守卫各一次 warn，均未触发自动制动。
没有硬件报警并不表示抖动不存在。

## 重要配置差异

`upstream/formal/{isaac_contract,mujoco_contract}.json` **及真正的 R1199 训练运行**
`upstream/actual_R1199_training_contract.json` 均记录
`park_continuous_bias=true, park_straight_bias=true`、
`park_odometry=false, park_settle_joints=false`；现有实机 C++ 默认分支
相当于补偿 false/false，并启用后两项，与训练不一致。
训练权重 SHA 与发布 `model_1199.pt` 相同；此前拿较早 `model_550.pt`
合同判断“训练开关未知”已纠正。训练服务器当前 `code/` 源码在该训练完成后
被修改，运行目录 `git/` 为空，仍需补**训练当时的不可变源码快照**。当前 C++ 源码
`runtime/deployed_controller_candidate.cpp` 已含一个**默认关闭、未编译验证**的
`AS2W_R1199_TRAINING_CONTRACT` 候选，修正补偿和停车四项；它不是已上狗版本。实际发布端是共享的
`runtime/shared_r214_publisher.cpp`，R1199 的 CMake 为它加策略编译开关。
原来的 950 帧 parity 仅覆盖 false/false。

## 请训练同事先做的事

1. 补交本次 `model_1199.pt` 的实际启动命令、**训练时不可变源码快照**、
   权重/代码/资产哈希和命令分布统计。四个关键开关的训练实值已由正确合同核实，
   见 `docs/training_server_alignment.md`，不要再用较早权重的合同代替。
2. 用户已确认旧故障两次实机足够，**不再复演旧版故障**。请协助用正确训练合同
   核对新候选的动作包装，并只对修复版跑同初态的零速、持续 +0.05 m/s、
   `0→+0.05→0→−0.05→0`；保留原始 ONNX 动作、包装后16轴目标、
   PD目标力矩、实际 q/dq、轮载/非轮接触。勿同时改权重和执行器参数。
3. 对**运动中**抖动溯源：若原始动作振荡，处理训练奖励和停走/低速命令分布；
   若包装后才振荡，处理包装器；若目标平顺但真实关节/力矩振荡，
   比对执行器、PD、延迟、速度噪声及轮地接触。给出与本包相同窗口的曲线和
   峰值/频谱，不只给视频或通过率。
4. 按 `docs/policy_delivery_contract.md` 提交下一个策略版本。训练服务器绝对
   路径只可作为溯源信息，不能替代可复制的模型、源码、配置和逐例证据。

## 复算

包内可直接运行 `python evidence/derived/motion_jitter_recompute.py`
（需 numpy+matplotlib；读取同目录 `robot_state_10ms.csv`）。
若需要从原始日志重提取，使用 `state_and_command_recompute.py`，其 `session`
路径需设为本包 `evidence/trial2/`。原始日志保持未改。

`evidence/derived/posture_and_command.png` 上两组时间轴起点不同，不能用上下图
相同横坐标做毫秒级因果对齐。没有实测机身高度、接触力和高频电流/录音。
任何后续实机动作仍须重新完成离线验收并由现场人员对当次动作明确同意。
`ORIGIN_MAP.tsv` 对应项目原路径与包内相对路径；包内文件已经全部复制，
无需依赖这些原路径。
