# AS2-W 只读关节标定分析

源日志：`D:\Projects\Athena\运动控制\Collie\AS2-W_CPRO\部署测试\04_调试记录\logs\20261109-G1_live_snapshot_10.log`
有效样本 16383，丢弃行 1。候选姿态和轮侧别须结合现场动作记录复核。

## 活动段

段间空隙大于阈值才分段；主导槽按净 Δq 排名，轮滚动可能压过手掰腿轴。往返动作净位移会抵消，另列区间 q 范围最大槽。

| 段 | 时间 s | 时长 s | 净 Δq 主导/次主导槽 | q 范围最大槽 | 平均 gyro_z rad/s |
| --- | --- | ---: | --- | ---: | ---: |
| 1 | 17.79–22.15 | 4.36 | 15/10 | 15 | 0.002 |
| 2 | 23.73–28.98 | 5.25 | 15/10 | 15 | 0.002 |
| 3 | 126.95–130.63 | 3.68 | 14/15 | 6 | 0.001 |

### 每段 0–15 槽净位移 Δq / 平均 dq / q 范围

**段 1** (17.79–22.15 s)：0:Δ+0.000 rad/dq-0.002 rad/s/range0.000 rad; 1:Δ-0.000 rad/dq+0.002 rad/s/range0.000 rad; 2:Δ+0.000 rad/dq-0.002 rad/s/range0.000 rad; 3:Δ+0.000 rad/dq-0.003 rad/s/range0.000 rad; 4:Δ+0.000 rad/dq-0.002 rad/s/range0.000 rad; 5:Δ+0.000 rad/dq+0.000 rad/s/range0.000 rad; 6:Δ+0.000 rad/dq+0.003 rad/s/range0.000 rad; 7:Δ-0.002 rad/dq+0.001 rad/s/range0.002 rad; 8:Δ-0.000 rad/dq-0.002 rad/s/range0.000 rad; 9:Δ+0.002 rad/dq+0.003 rad/s/range0.002 rad; 10:Δ-0.016 rad/dq-0.007 rad/s/range0.016 rad; 11:Δ+0.000 rad/dq+0.002 rad/s/range0.000 rad; 12:Δ-0.000 rad/dq+0.000 rad/s/range0.000 rad; 13:Δ+0.002 rad/dq+0.001 rad/s/range0.002 rad; 14:Δ-0.000 rad/dq+0.000 rad/s/range0.001 rad; 15:Δ+2.618 rad/dq+0.604 rad/s/range2.663 rad

**段 2** (23.73–28.98 s)：0:Δ+0.000 rad/dq-0.002 rad/s/range0.000 rad; 1:Δ+0.000 rad/dq+0.001 rad/s/range0.000 rad; 2:Δ+0.000 rad/dq-0.001 rad/s/range0.000 rad; 3:Δ+0.000 rad/dq-0.003 rad/s/range0.000 rad; 4:Δ-0.000 rad/dq-0.002 rad/s/range0.000 rad; 5:Δ-0.000 rad/dq+0.001 rad/s/range0.000 rad; 6:Δ-0.000 rad/dq+0.003 rad/s/range0.000 rad; 7:Δ+0.000 rad/dq+0.001 rad/s/range0.000 rad; 8:Δ-0.000 rad/dq-0.002 rad/s/range0.000 rad; 9:Δ-0.003 rad/dq+0.002 rad/s/range0.003 rad; 10:Δ+0.008 rad/dq-0.000 rad/s/range0.008 rad; 11:Δ-0.000 rad/dq+0.001 rad/s/range0.001 rad; 12:Δ+0.000 rad/dq-0.000 rad/s/range0.000 rad; 13:Δ-0.000 rad/dq+0.001 rad/s/range0.000 rad; 14:Δ-0.001 rad/dq+0.000 rad/s/range0.001 rad; 15:Δ-2.856 rad/dq-0.540 rad/s/range3.587 rad

**段 3** (126.95–130.63 s)：0:Δ+0.001 rad/dq-0.002 rad/s/range0.001 rad; 1:Δ-0.007 rad/dq-0.001 rad/s/range0.007 rad; 2:Δ+0.000 rad/dq-0.001 rad/s/range0.000 rad; 3:Δ+0.001 rad/dq-0.002 rad/s/range0.002 rad; 4:Δ+0.000 rad/dq-0.002 rad/s/range0.001 rad; 5:Δ+0.000 rad/dq+0.001 rad/s/range0.000 rad; 6:Δ+0.003 rad/dq+0.003 rad/s/range0.223 rad; 7:Δ+0.005 rad/dq+0.003 rad/s/range0.088 rad; 8:Δ+0.000 rad/dq-0.002 rad/s/range0.000 rad; 9:Δ+0.000 rad/dq+0.002 rad/s/range0.001 rad; 10:Δ+0.000 rad/dq-0.002 rad/s/range0.000 rad; 11:Δ-0.000 rad/dq+0.001 rad/s/range0.000 rad; 12:Δ+0.001 rad/dq+0.000 rad/s/range0.001 rad; 13:Δ+0.003 rad/dq+0.001 rad/s/range0.004 rad; 14:Δ+0.065 rad/dq+0.020 rad/s/range0.077 rad; 15:Δ+0.015 rad/dq+0.001 rad/s/range0.016 rad

## 已知转向交叉检查

按 gyro_z 左正右负、前进轮 dq 正的现场事实，检验 12/14 右、13/15 左；此项只校验旧采样，不能代替逐轮标定。

| 段 | 时间 s | 方向 | gyro_z | dq12,13,14,15 | 侧别一致 |
| --- | --- | --- | ---: | --- | --- |

## 趴下/站立静态读数

选取每态最长的全 16 槽低速窗口；轮 q 是累计转角，不是姿态零位。

| DDS 槽 | 趴下候选 q rad | 站立候选 q rad |
| ---: | ---: | ---: |
| 0 | -0.57254 | — |
| 1 | 1.00981 | — |
| 2 | -2.75626 | — |
| 3 | 0.55254 | — |
| 4 | 0.99810 | — |
| 5 | -2.76812 | — |
| 6 | -0.56426 | — |
| 7 | 1.01789 | — |
| 8 | -2.75711 | — |
| 9 | 0.55162 | — |
| 10 | 0.98389 | — |
| 11 | -2.75843 | — |
| 12 | -0.40570 | — |
| 13 | 1.97104 | — |
| 14 | -0.45122 | — |
| 15 | 2.03757 | — |

### 全部静态窗口

| 时间 s | 时长 s | 姿态候选 |
| --- | ---: | --- |
| 0.02–17.78 | 17.76 | prone_candidate |
| 22.16–23.72 | 1.56 | prone_candidate |
| 28.99–126.94 | 97.95 | prone_candidate |
| 130.64–163.84 | 33.20 | prone_candidate |

## Contract 关节序 → DDS 槽位/符号（人工填写模板）

只有现场记录的物理关节、手掰方向与对应活动段能填槽位和 sign；本表不自动赋值。offset 需另行站姿标定。

| contract 序号 | joint_names | 动作段号 | DDS 槽位 | 物理正方向 | sign | 趴下 q | 站立 q | 证据 |
| ---: | --- | ---: | ---: | --- | ---: | ---: | ---: | --- |
| 0 | FL_hip |  |  |  |  |  |  |  |
| 1 | FR_hip |  |  |  |  |  |  |  |
| 2 | RL_hip |  |  |  |  |  |  |  |
| 3 | RR_hip |  |  |  |  |  |  |  |
| 4 | FL_thigh |  |  |  |  |  |  |  |
| 5 | FR_thigh |  |  |  |  |  |  |  |
| 6 | RL_thigh |  |  |  |  |  |  |  |
| 7 | RR_thigh |  |  |  |  |  |  |  |
| 8 | FL_calf |  |  |  |  |  |  |  |
| 9 | FR_calf |  |  |  |  |  |  |  |
| 10 | RL_calf |  |  |  |  |  |  |  |
| 11 | RR_calf |  |  |  |  |  |  |  |
| 12 | FL_foot |  |  |  |  |  |  |  |
| 13 | FR_foot |  |  |  |  |  |  |  |
| 14 | RL_foot |  |  |  |  |  |  |  |
| 15 | RR_foot |  |  |  |  |  |  |  |

**禁止把未核实模板当 calibrated.map 使用；本工具不发送任何控制命令。**
