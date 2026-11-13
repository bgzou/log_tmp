# R1199 与已运行真机发布端的上一动作合同核对

时间：2026-11-11 晚。仅本机只读代码、历史日志；未连接 CPRO、未发布 LowCmd、未操作机器人。

| 策略 | 真机状态 | 观测历史如何更新 | 与旧 R1199 复演错误的关系 |
|---|---|---|---|
| R1199 | 当前 `cpp_deploy-as2w` 无 R1199 controller/launcher；release `as2w-shadow-contract.json` 标注 `real_actuation_enabled=false`。未上狗。 | 交付训练评估器将经过动作包装的 `current` 写入下一帧 `history`；我方旧**仿真**脚本误回填原始 ONNX 输出，已在独立消融副本修正。 | 错误未通过 R1199 LowCmd 真机发布，因为尚无这条发布链。 |
| R214 | 已实机 A/Y、B 零速及有限运动。 | ONNX 为 `obs[1,41] + state[1,1196] → actions + next_state`。C++ `make_observation` 只装 command/gyro/gravity/q/dq；`Controller::replay` 每帧把上一轮 `next_state` 回传 `state`。没有独立的 `obs[42:58]` 上一动作字段。CPRO 1050 帧模型回放最大误差 `9.53674e-07`。 | 不可能犯同一字段的 raw-vs-wrapped 回填错误。R214 行走后腿下沉另有真机证据：后腿目标高于反馈约0.34–0.45rad，kp55提供约21Nm仍支撑不足；A回站可拉正。 |
| R284 | 已实机 B 零速后全量策略出现剧烈振荡，当前硬阻断。 | 65维上一动作字段由交付方 `r284_observations.hpp` 写入 `previous_`；C++ `r284_controller.cpp` 对 ONNX 输出裁剪至±6后调用 `remember(clipped)`，再由 `targets(clipped)`做q/dq缩放，没有 R1199 的额外 `rolling_fixed_exit` 包装。官方C++ 16000帧、16次reset数值回放最大误差约 `1.07e-6`。 | 目前没有发现同一 raw-vs-wrapped 错误；数值回放并不证明真实闭环稳定，也不能据此确定振荡单一根因。R284继续禁用。 |

R1199 完整链目前卡在两个位置：①停车后 10 s 保持（训练方实测姿态复演 seed202 漂移0.02059m、速度p95 0.03055m/s，超过0.02m/0.02m/s门槛）；②回固定站的**关节角评分**（我方修正后三种子尾段腿误差0.222–0.251rad，训练方实测姿态 seed202 0.244rad，均超过项目0.18rad评价门槛）。训练方 seed202 回站最后100帧的轮支撑、直立、水平速度、偏航速度全部通过，仅关节角评分失败；真机已稳定 FixedStand 的误差约0.27–0.30rad。因此0.18rad很可能过严，不能据此断言实际回站会失稳。训练方正式 Isaac 完整链前进1/20、倒退2/20。需区分受重力负载的静态平衡偏差与真正危险的过渡冲击/失稳。R1199 还未完成 C++/ARM64 部署、只读 shadow、B交接及人工安全退出验收。

可做的实机工作：在原厂控制或已验证的 A/Y 链下**只读采集**连续 LowState、IMU、轮角/轮速和实际负载站姿；离线运行 R1199 shadow 检查观测、包装动作和命令。若“实机训练”指在线运行 R1199 反复试错，目前不具备可靠停车/退出/复位，不应开始。未来有界地面测试需先完成正确适配器的逐帧回放、实测初态双仿真、停车与退出改进，再设计当次获许可的短时试验；既有 R284 振荡事故说明离线平稳不等于真机闭环安全。

依据：`cpp_deploy-as2w/deploy/robots/as2w/r214/r214_controller.cpp`、`r284/r284_controller.cpp`、`r284/r284_observations.hpp`、R1199 release 合同；`INDEX.md` 2026-11-10 12:15–12:35、19:46–19:48 和 2026-11-11 R1199 同条件复演节。未在此日志存凭据。
