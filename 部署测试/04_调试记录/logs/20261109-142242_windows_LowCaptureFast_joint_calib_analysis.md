# AS2-W 只读关节标定分析

源日志：`D:\Projects\Athena\运动控制\Collie\AS2-W_CPRO\部署测试\04_调试记录\logs\20261109-142242_windows_LowCaptureFast.log`
有效样本 29999，丢弃行 1。候选姿态和轮侧别须结合现场动作记录复核。

## 活动段

段间空隙大于阈值才分段；主导槽按净 Δq 排名，轮滚动可能压过手掰腿轴。往返动作净位移会抵消，另列区间 q 范围最大槽。

| 段 | 时间 s | 时长 s | 净 Δq 主导/次主导槽 | q 范围最大槽 | 平均 gyro_z rad/s |
| --- | --- | ---: | --- | ---: | ---: |
| 1 | 37.25–59.02 | 21.77 | 13/15 | 13 | 0.002 |
| 2 | 258.13–264.54 | 6.41 | 13/3 | 13 | 0.001 |
| 3 | 266.37–272.43 | 6.06 | 13/4 | 13 | 0.002 |

### 每段 0–15 槽净位移 Δq / 平均 dq / q 范围

**段 1** (37.25–59.02 s)：0:Δ-0.000 rad/dq-0.002 rad/s/range0.001 rad; 1:Δ+0.000 rad/dq+0.002 rad/s/range0.000 rad; 2:Δ+0.000 rad/dq-0.001 rad/s/range0.000 rad; 3:Δ-0.024 rad/dq-0.006 rad/s/range0.381 rad; 4:Δ+0.020 rad/dq-0.003 rad/s/range1.830 rad; 5:Δ+0.003 rad/dq+0.002 rad/s/range1.937 rad; 6:Δ-0.000 rad/dq+0.003 rad/s/range0.010 rad; 7:Δ+0.001 rad/dq+0.002 rad/s/range0.004 rad; 8:Δ+0.000 rad/dq-0.002 rad/s/range0.000 rad; 9:Δ-0.004 rad/dq+0.002 rad/s/range0.005 rad; 10:Δ+0.014 rad/dq-0.001 rad/s/range0.027 rad; 11:Δ-0.001 rad/dq+0.002 rad/s/range0.001 rad; 12:Δ-0.001 rad/dq+0.000 rad/s/range0.002 rad; 13:Δ+1.013 rad/dq+0.047 rad/s/range2.207 rad; 14:Δ-0.002 rad/dq-0.000 rad/s/range0.009 rad; 15:Δ-0.032 rad/dq-0.004 rad/s/range0.080 rad

**段 2** (258.13–264.54 s)：0:Δ-0.000 rad/dq-0.002 rad/s/range0.000 rad; 1:Δ+0.000 rad/dq+0.001 rad/s/range0.000 rad; 2:Δ+0.000 rad/dq-0.002 rad/s/range0.000 rad; 3:Δ+0.019 rad/dq+0.000 rad/s/range0.020 rad; 4:Δ-0.018 rad/dq-0.007 rad/s/range0.019 rad; 5:Δ+0.002 rad/dq+0.002 rad/s/range0.003 rad; 6:Δ+0.000 rad/dq+0.003 rad/s/range0.000 rad; 7:Δ-0.000 rad/dq+0.002 rad/s/range0.001 rad; 8:Δ+0.000 rad/dq-0.002 rad/s/range0.000 rad; 9:Δ-0.000 rad/dq+0.001 rad/s/range0.000 rad; 10:Δ+0.000 rad/dq-0.002 rad/s/range0.000 rad; 11:Δ-0.000 rad/dq+0.002 rad/s/range0.000 rad; 12:Δ-0.000 rad/dq+0.000 rad/s/range0.000 rad; 13:Δ+3.937 rad/dq+0.613 rad/s/range3.980 rad; 14:Δ-0.001 rad/dq+0.000 rad/s/range0.001 rad; 15:Δ+0.007 rad/dq-0.001 rad/s/range0.009 rad

**段 3** (266.37–272.43 s)：0:Δ+0.000 rad/dq-0.002 rad/s/range0.000 rad; 1:Δ-0.000 rad/dq+0.001 rad/s/range0.000 rad; 2:Δ+0.000 rad/dq-0.001 rad/s/range0.000 rad; 3:Δ-0.014 rad/dq-0.005 rad/s/range0.016 rad; 4:Δ+0.055 rad/dq+0.008 rad/s/range0.057 rad; 5:Δ-0.007 rad/dq-0.000 rad/s/range0.007 rad; 6:Δ+0.000 rad/dq+0.003 rad/s/range0.000 rad; 7:Δ+0.002 rad/dq+0.002 rad/s/range0.002 rad; 8:Δ-0.000 rad/dq-0.002 rad/s/range0.000 rad; 9:Δ+0.001 rad/dq+0.002 rad/s/range0.001 rad; 10:Δ-0.003 rad/dq-0.004 rad/s/range0.005 rad; 11:Δ+0.000 rad/dq+0.002 rad/s/range0.000 rad; 12:Δ+0.000 rad/dq-0.001 rad/s/range0.000 rad; 13:Δ-5.540 rad/dq-0.913 rad/s/range5.581 rad; 14:Δ+0.002 rad/dq-0.000 rad/s/range0.003 rad; 15:Δ-0.007 rad/dq-0.002 rad/s/range0.009 rad

## 已知转向交叉检查

按 gyro_z 左正右负、前进轮 dq 正的现场事实，检验 12/14 右、13/15 左；此项只校验旧采样，不能代替逐轮标定。

| 段 | 时间 s | 方向 | gyro_z | dq12,13,14,15 | 侧别一致 |
| --- | --- | --- | ---: | --- | --- |

## 趴下/站立静态读数

选取每态最长的全 16 槽低速窗口；轮 q 是累计转角，不是姿态零位。

| DDS 槽 | 趴下候选 q rad | 站立候选 q rad |
| ---: | ---: | ---: |
| 0 | -0.57273 | — |
| 1 | 0.99362 | — |
| 2 | -2.75636 | — |
| 3 | 0.54516 | — |
| 4 | 1.00031 | — |
| 5 | -2.76808 | — |
| 6 | -0.56959 | — |
| 7 | 1.01092 | — |
| 8 | -2.75710 | — |
| 9 | 0.57668 | — |
| 10 | 0.96446 | — |
| 11 | -2.71548 | — |
| 12 | -0.16660 | — |
| 13 | 3.47316 | — |
| 14 | -0.46009 | — |
| 15 | -0.20520 | — |

### 全部静态窗口

| 时间 s | 时长 s | 姿态候选 |
| --- | ---: | --- |
| 0.02–37.24 | 37.22 | prone_candidate |
| 59.03–258.12 | 199.09 | prone_candidate |
| 264.55–266.36 | 1.81 | prone_candidate |
| 272.44–300.00 | 27.56 | prone_candidate |

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
