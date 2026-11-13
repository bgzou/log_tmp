# R1199 运动中抖动：诊断证据包（给训练侧）

日期：2026-11-12。本包可独立阅读复算，无需访问部署工作站。所有分析脚本只依赖 numpy（Python3）。

## 一、结论摘要

R1199（`model_1199.pt` SHA `bb5c9735b5bd37ef4bdd2bd13f9d45395d8dc9b4c888c36955de1a345d55776d`，`policy.onnx` `df1f2db98efe32ad4a8b767c34b7ca4235c717f80e5778d59552a522b6fc7f23`）在真实 AS2-W 上：

1. **停走姿态跳步/回落**：已通过把部署端运行时开关对齐训练合同（`park_continuous_bias/park_straight_bias=true/true`、`park_odometry/park_settle_joints=false/false`，即 `rolling-knee-margin-formal/contract.json` 的实际值）解决。实机验证：B 交接单帧步进 0.003-0.004rad（旧包装 0.25-0.27rad）、零告警、姿态保持不下沉。**此项已关闭。**
2. **运动中可闻关节抖动**：现场确认存在且**速度越大越强**（0.2m/s 比 0.05m/s 明显）。诊断链定位**主因在推理侧（策略原始输出噪声）**，见下。

## 二、推理侧实锤（本包核心证据）

实机 0.2m/s 会话（`data/20261112-114347_training-contract_vx0.2/`）的逐帧策略诊断 `policy_diag.log`（50Hz，含 raw ONNX 16 维 / 包装后 16 维 / 最终目标 / 站姿补偿内部态）：

| 量 | 零速段 | 运动段 |
|---|---|---|
| raw ONNX 腿动作单帧步进（±6限幅内） | ~0（motion=0 门控） | **均值 2.07，p99=12=满摆程**（逐帧 -6→+6 摆动） |
| 包装后腿动作（0.18×motion×clamp±1） | 平滑 | 均值步进 0.052，峰 0.34 |
| 最终腿目标 q 单帧步进 | 0.006 rad | 均值 0.018 rad，峰 0.119 rad（50Hz 抖颤） |

配套 2ms（500Hz）关节采集（`low_capture_fast.log`）：**运动段大腿 dq 在 40-120Hz 带 RMS 是零速段的 8.2 倍**（1.110 vs 0.135 rad/s），120-250Hz 为 5.3 倍。50Hz 目标抖颤经 PD(kp55/kd2) 跟踪，谐波正落该频段——即现场听到的嗡声。零速时 motion=0 把抖颤门控掉，与"零速安静、滚动发嗡"现象一致。

**回放敏感性佐证**：`replay/session_replay_fixture.txt` 由会话数据（capture 传感器 + POLICY_DIAG 命令，tick 对齐）重建，喂给部署端 C++ 控制器逐帧重放：与实机记录前 6 帧完全一致（0 误差），第 15 帧起因 ≤2ms 传感器时差被近饱和 raw 放大而发散——策略当前工作点对微小输入差异极度敏感，本身就是输出噪声区的特征。

## 三、请训练侧检查（按《AS2-W v3 交付清单》分流第 1 条）

raw ONNX 在稳态运动中逐帧大幅摆动，符合"保留可重跑夹具交训练侧"的情形，建议检查：
1. 低速命令段（0.05-0.2 m/s）的命令采样分布与该速度区间的训练覆盖；
2. 动作变化率惩罚（rate/action-delta penalty）是否覆盖该频段；
3. 执行器随机化与观测噪声的设置是否使策略在该工作点缺乏平滑先验；
4. 若做输出平滑/滤波，请给出训练侧一致的做法（部署端单方面加滤波会破坏 parity，需按新版本走流程）。

复算方法：`python3 analysis/20261112_r1199_02envelope_action_steps.py`（步进统计）、`analysis/20261112_r1199_02envelope_hf_analysis.py`（频段能量，需 2ms 会话数据）。回放夹具可直接输入你们的环境：传感器（quat/gyro/q16/dq16）+ 命令（vx,vy,wz）逐帧，50Hz。

## 四、运行时合同提醒

- 我们实机部署端已按**真实训练合同**运行：`continuous/straight=true/true, odometry/settle=false/false`（`resolved` 自 `rolling-knee-margin-formal/contract.json`）。
- 你的 reanchor 预览（commit `b070a72`）按 `--park-odometry --park-settle-joints` 运行，**与训练合同相反**；其 12s 标定+冻结+锁存复位的交接设计我们认可并愿意在开关对齐后评测。请确认新权重微调版的实际训练开关，并按 v3 交付清单给 `resolved_flags` 差异表。

## 五、包内清单

- `data/20261112-114347_training-contract_vx0.2/`：0.2m/s 会话五件套（policy_diag.log 2283帧、2ms capture 60k行、protection、publisher、session）
- `data/20261112-105937_training-contract_vx0.05/`：0.05m/s 对照会话（10ms capture，无 policy_diag——早于该功能）
- `analysis/`：全部复算脚本 + 旧版停走跳步复现摘要
- `replay/`：会话→夹具转换器、回放夹具、C++ 重放输出
- `MANIFEST.sha256`：全部文件哈希
