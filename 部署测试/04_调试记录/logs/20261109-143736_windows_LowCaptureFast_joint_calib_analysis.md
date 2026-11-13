# AS2-W 只读关节标定分析

源日志：`D:\Projects\Athena\运动控制\Collie\AS2-W_CPRO\部署测试\04_调试记录\logs\20261109-143736_windows_LowCaptureFast.log`
有效样本 30000，丢弃行 0。候选姿态和轮侧别须结合现场动作记录复核。

## 活动段

段间空隙大于阈值才分段；主导槽按净 Δq 排名，轮滚动可能压过手掰腿轴。往返动作净位移会抵消，另列区间 q 范围最大槽。

| 段 | 时间 s | 时长 s | 净 Δq 主导/次主导槽 | q 范围最大槽 | 平均 gyro_z rad/s |
| --- | --- | ---: | --- | ---: | ---: |
| 1 | 41.50–47.83 | 6.33 | 12/1 | 12 | 0.001 |
| 2 | 131.41–132.46 | 1.05 | 9/10 | 9 | 0.004 |
| 3 | 134.45–135.41 | 0.96 | 9/10 | 9 | 0.001 |
| 4 | 202.30–208.27 | 5.97 | 15/9 | 10 | 0.001 |
| 5 | 283.66–300.00 | 16.34 | 15/10 | 10 | 0.002 |

### 每段 0–15 槽净位移 Δq / 平均 dq / q 范围

**段 1** (41.50–47.83 s)：0:Δ-0.005 rad/dq-0.003 rad/s/range0.066 rad; 1:Δ-0.014 rad/dq+0.000 rad/s/range0.053 rad; 2:Δ+0.001 rad/dq-0.001 rad/s/range0.002 rad; 3:Δ+0.000 rad/dq-0.003 rad/s/range0.000 rad; 4:Δ+0.000 rad/dq-0.003 rad/s/range0.001 rad; 5:Δ+0.000 rad/dq+0.001 rad/s/range0.000 rad; 6:Δ+0.000 rad/dq+0.003 rad/s/range0.001 rad; 7:Δ-0.000 rad/dq+0.002 rad/s/range0.000 rad; 8:Δ-0.000 rad/dq-0.003 rad/s/range0.000 rad; 9:Δ-0.000 rad/dq+0.002 rad/s/range0.001 rad; 10:Δ+0.000 rad/dq-0.003 rad/s/range0.000 rad; 11:Δ-0.000 rad/dq+0.003 rad/s/range0.000 rad; 12:Δ-1.335 rad/dq-0.205 rad/s/range4.566 rad; 13:Δ+0.001 rad/dq+0.001 rad/s/range0.002 rad; 14:Δ-0.004 rad/dq-0.001 rad/s/range0.008 rad; 15:Δ+0.001 rad/dq-0.002 rad/s/range0.002 rad

**段 2** (131.41–132.46 s)：0:Δ-0.003 rad/dq-0.006 rad/s/range0.004 rad; 1:Δ+0.000 rad/dq-0.001 rad/s/range0.000 rad; 2:Δ+0.000 rad/dq-0.003 rad/s/range0.000 rad; 3:Δ-0.000 rad/dq-0.003 rad/s/range0.000 rad; 4:Δ-0.002 rad/dq-0.006 rad/s/range0.003 rad; 5:Δ-0.000 rad/dq+0.000 rad/s/range0.000 rad; 6:Δ+0.000 rad/dq+0.003 rad/s/range0.000 rad; 7:Δ+0.000 rad/dq+0.002 rad/s/range0.000 rad; 8:Δ-0.000 rad/dq-0.002 rad/s/range0.000 rad; 9:Δ+0.181 rad/dq+0.203 rad/s/range0.198 rad; 10:Δ+0.039 rad/dq+0.047 rad/s/range0.044 rad; 11:Δ-0.000 rad/dq+0.002 rad/s/range0.000 rad; 12:Δ+0.005 rad/dq+0.002 rad/s/range0.005 rad; 13:Δ-0.000 rad/dq+0.001 rad/s/range0.001 rad; 14:Δ+0.003 rad/dq+0.001 rad/s/range0.004 rad; 15:Δ-0.002 rad/dq-0.002 rad/s/range0.003 rad

**段 3** (134.45–135.41 s)：0:Δ+0.000 rad/dq-0.002 rad/s/range0.000 rad; 1:Δ-0.000 rad/dq+0.001 rad/s/range0.000 rad; 2:Δ-0.000 rad/dq-0.002 rad/s/range0.000 rad; 3:Δ+0.000 rad/dq-0.004 rad/s/range0.000 rad; 4:Δ-0.000 rad/dq-0.004 rad/s/range0.000 rad; 5:Δ+0.000 rad/dq+0.001 rad/s/range0.000 rad; 6:Δ+0.000 rad/dq+0.003 rad/s/range0.000 rad; 7:Δ+0.000 rad/dq+0.002 rad/s/range0.000 rad; 8:Δ+0.000 rad/dq-0.003 rad/s/range0.000 rad; 9:Δ-0.153 rad/dq-0.186 rad/s/range0.167 rad; 10:Δ-0.020 rad/dq-0.025 rad/s/range0.021 rad; 11:Δ+0.000 rad/dq+0.003 rad/s/range0.000 rad; 12:Δ-0.000 rad/dq-0.000 rad/s/range0.000 rad; 13:Δ+0.001 rad/dq+0.001 rad/s/range0.001 rad; 14:Δ-0.001 rad/dq-0.001 rad/s/range0.001 rad; 15:Δ-0.003 rad/dq-0.003 rad/s/range0.003 rad

**段 4** (202.30–208.27 s)：0:Δ+0.001 rad/dq-0.002 rad/s/range0.001 rad; 1:Δ-0.001 rad/dq+0.002 rad/s/range0.001 rad; 2:Δ+0.000 rad/dq-0.001 rad/s/range0.000 rad; 3:Δ+0.000 rad/dq-0.002 rad/s/range0.001 rad; 4:Δ-0.001 rad/dq-0.003 rad/s/range0.001 rad; 5:Δ+0.000 rad/dq+0.000 rad/s/range0.000 rad; 6:Δ-0.001 rad/dq+0.003 rad/s/range0.005 rad; 7:Δ+0.000 rad/dq+0.001 rad/s/range0.001 rad; 8:Δ-0.000 rad/dq-0.002 rad/s/range0.000 rad; 9:Δ-0.038 rad/dq-0.006 rad/s/range0.081 rad; 10:Δ+0.015 rad/dq-0.002 rad/s/range0.694 rad; 11:Δ-0.032 rad/dq-0.004 rad/s/range0.034 rad; 12:Δ+0.000 rad/dq-0.000 rad/s/range0.001 rad; 13:Δ+0.011 rad/dq+0.002 rad/s/range0.013 rad; 14:Δ-0.005 rad/dq-0.001 rad/s/range0.007 rad; 15:Δ+0.374 rad/dq+0.062 rad/s/range0.421 rad

**段 5** (283.66–300.00 s)：0:Δ-0.000 rad/dq-0.002 rad/s/range0.009 rad; 1:Δ+0.000 rad/dq+0.002 rad/s/range0.001 rad; 2:Δ-0.000 rad/dq-0.001 rad/s/range0.000 rad; 3:Δ-0.001 rad/dq-0.003 rad/s/range0.004 rad; 4:Δ-0.009 rad/dq-0.003 rad/s/range0.009 rad; 5:Δ+0.000 rad/dq+0.001 rad/s/range0.000 rad; 6:Δ-0.000 rad/dq+0.003 rad/s/range0.011 rad; 7:Δ+0.003 rad/dq+0.002 rad/s/range0.013 rad; 8:Δ+0.000 rad/dq-0.002 rad/s/range0.000 rad; 9:Δ-0.015 rad/dq+0.002 rad/s/range0.298 rad; 10:Δ+0.571 rad/dq+0.033 rad/s/range1.365 rad; 11:Δ-0.012 rad/dq+0.002 rad/s/range1.028 rad; 12:Δ+0.006 rad/dq+0.000 rad/s/range0.007 rad; 13:Δ+0.005 rad/dq+0.001 rad/s/range0.009 rad; 14:Δ+0.003 rad/dq+0.000 rad/s/range0.030 rad; 15:Δ+0.934 rad/dq+0.060 rad/s/range0.973 rad

## 已知转向交叉检查

按 gyro_z 左正右负、前进轮 dq 正的现场事实，检验 12/14 右、13/15 左；此项只校验旧采样，不能代替逐轮标定。

| 段 | 时间 s | 方向 | gyro_z | dq12,13,14,15 | 侧别一致 |
| --- | --- | --- | ---: | --- | --- |

## 趴下/站立静态读数

选取每态最长的全 16 槽低速窗口；轮 q 是累计转角，不是姿态零位。

| DDS 槽 | 趴下候选 q rad | 站立候选 q rad |
| ---: | ---: | ---: |
| 0 | -0.56562 | — |
| 1 | 1.01087 | — |
| 2 | -2.75619 | — |
| 3 | 0.55319 | — |
| 4 | 1.01475 | — |
| 5 | -2.76808 | — |
| 6 | -0.56414 | — |
| 7 | 1.01770 | — |
| 8 | -2.75711 | — |
| 9 | 0.58274 | — |
| 10 | 0.95151 | — |
| 11 | -2.71546 | — |
| 12 | -0.41945 | — |
| 13 | 1.94359 | — |
| 14 | -0.45902 | — |
| 15 | -0.19832 | — |

### 全部静态窗口

| 时间 s | 时长 s | 姿态候选 |
| --- | ---: | --- |
| 0.01–41.49 | 41.48 | prone_candidate |
| 43.97–45.43 | 1.46 | prone_candidate |
| 47.81–131.40 | 83.59 | prone_candidate |
| 132.47–134.44 | 1.97 | prone_candidate |
| 135.42–202.29 | 66.87 | prone_candidate |
| 204.57–205.94 | 1.37 | prone_candidate |
| 208.28–283.65 | 75.37 | prone_candidate |
| 293.31–294.34 | 1.03 | prone_candidate |

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
