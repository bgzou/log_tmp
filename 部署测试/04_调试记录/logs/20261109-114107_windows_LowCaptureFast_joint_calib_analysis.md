# AS2-W 只读关节标定分析

源日志：`D:\Projects\Athena\运动控制\Collie\AS2-W_CPRO\部署测试\04_调试记录\logs\20261109-114107_windows_LowCaptureFast.log`
有效样本 29999，丢弃行 1。候选姿态和轮侧别须结合现场动作记录复核。

## 活动段

段间空隙大于阈值才分段；主导槽按净 Δq 排名，轮滚动可能压过手掰腿轴。往返动作净位移会抵消，另列区间 q 范围最大槽。

| 段 | 时间 s | 时长 s | 净 Δq 主导/次主导槽 | q 范围最大槽 | 平均 gyro_z rad/s |
| --- | --- | ---: | --- | ---: | ---: |
| 1 | 76.27–79.09 | 2.82 | 8/5 | 5 | -0.030 |
| 2 | 149.29–150.48 | 1.19 | 13/7 | 14 | 0.000 |
| 3 | 153.26–154.18 | 0.92 | 14/13 | 5 | 0.002 |
| 4 | 166.88–175.05 | 8.17 | 14/15 | 14 | -0.004 |
| 5 | 181.64–191.55 | 9.91 | 14/13 | 14 | 0.151 |
| 6 | 202.95–206.23 | 3.28 | 15/13 | 15 | -0.742 |
| 7 | 219.22–219.73 | 0.51 | 14/15 | 14 | -0.022 |
| 8 | 221.59–225.01 | 3.42 | 5/8 | 5 | 0.092 |
| 9 | 232.36–235.11 | 2.75 | 5/8 | 5 | -0.019 |
| 10 | 239.59–242.99 | 3.40 | 8/5 | 5 | 0.079 |

### 每段 0–15 槽净位移 Δq / 平均 dq / q 范围

**段 1** (76.27–79.09 s)：0:Δ+0.689 rad/dq+0.237 rad/s/range0.945 rad; 1:Δ-0.396 rad/dq-0.134 rad/s/range0.929 rad; 2:Δ+1.517 rad/dq+0.536 rad/s/range1.529 rad; 3:Δ-0.716 rad/dq-0.254 rad/s/range0.954 rad; 4:Δ-0.349 rad/dq-0.127 rad/s/range0.923 rad; 5:Δ+1.531 rad/dq+0.549 rad/s/range1.550 rad; 6:Δ+0.676 rad/dq+0.238 rad/s/range0.942 rad; 7:Δ-0.393 rad/dq-0.135 rad/s/range0.921 rad; 8:Δ+1.533 rad/dq+0.538 rad/s/range1.539 rad; 9:Δ-0.690 rad/dq-0.241 rad/s/range0.924 rad; 10:Δ-0.345 rad/dq-0.120 rad/s/range0.932 rad; 11:Δ+1.515 rad/dq+0.539 rad/s/range1.542 rad; 12:Δ-0.544 rad/dq-0.188 rad/s/range0.732 rad; 13:Δ-0.416 rad/dq-0.140 rad/s/range0.497 rad; 14:Δ-0.532 rad/dq-0.181 rad/s/range0.642 rad; 15:Δ-0.555 rad/dq-0.194 rad/s/range0.630 rad

**段 2** (149.29–150.48 s)：0:Δ+0.005 rad/dq+0.003 rad/s/range0.006 rad; 1:Δ+0.041 rad/dq+0.049 rad/s/range0.064 rad; 2:Δ-0.020 rad/dq-0.040 rad/s/range0.096 rad; 3:Δ-0.008 rad/dq-0.013 rad/s/range0.008 rad; 4:Δ+0.020 rad/dq+0.024 rad/s/range0.056 rad; 5:Δ+0.002 rad/dq-0.019 rad/s/range0.089 rad; 6:Δ+0.003 rad/dq+0.009 rad/s/range0.004 rad; 7:Δ+0.050 rad/dq+0.053 rad/s/range0.058 rad; 8:Δ-0.040 rad/dq-0.061 rad/s/range0.108 rad; 9:Δ-0.007 rad/dq-0.007 rad/s/range0.008 rad; 10:Δ+0.047 rad/dq+0.049 rad/s/range0.064 rad; 11:Δ-0.024 rad/dq-0.047 rad/s/range0.111 rad; 12:Δ+0.017 rad/dq+0.028 rad/s/range0.029 rad; 13:Δ+0.063 rad/dq+0.087 rad/s/range0.100 rad; 14:Δ+0.022 rad/dq+0.071 rad/s/range0.121 rad; 15:Δ-0.006 rad/dq+0.048 rad/s/range0.112 rad

**段 3** (153.26–154.18 s)：0:Δ-0.001 rad/dq-0.003 rad/s/range0.001 rad; 1:Δ+0.001 rad/dq+0.002 rad/s/range0.001 rad; 2:Δ-0.000 rad/dq-0.002 rad/s/range0.001 rad; 3:Δ+0.000 rad/dq-0.003 rad/s/range0.000 rad; 4:Δ+0.001 rad/dq+0.005 rad/s/range0.005 rad; 5:Δ-0.001 rad/dq-0.008 rad/s/range0.007 rad; 6:Δ-0.000 rad/dq+0.002 rad/s/range0.000 rad; 7:Δ+0.000 rad/dq+0.003 rad/s/range0.000 rad; 8:Δ-0.001 rad/dq-0.004 rad/s/range0.002 rad; 9:Δ+0.000 rad/dq+0.002 rad/s/range0.000 rad; 10:Δ+0.000 rad/dq+0.001 rad/s/range0.002 rad; 11:Δ-0.003 rad/dq-0.005 rad/s/range0.006 rad; 12:Δ-0.003 rad/dq-0.001 rad/s/range0.004 rad; 13:Δ-0.003 rad/dq-0.003 rad/s/range0.004 rad; 14:Δ+0.004 rad/dq+0.002 rad/s/range0.005 rad; 15:Δ+0.003 rad/dq+0.001 rad/s/range0.005 rad

**段 4** (166.88–175.05 s)：0:Δ+0.021 rad/dq+0.003 rad/s/range0.415 rad; 1:Δ+0.019 rad/dq+0.004 rad/s/range0.283 rad; 2:Δ-0.020 rad/dq-0.006 rad/s/range0.547 rad; 3:Δ-0.009 rad/dq-0.006 rad/s/range0.429 rad; 4:Δ+0.016 rad/dq-0.002 rad/s/range0.271 rad; 5:Δ-0.039 rad/dq-0.001 rad/s/range0.564 rad; 6:Δ+0.058 rad/dq+0.012 rad/s/range0.501 rad; 7:Δ+0.004 rad/dq+0.003 rad/s/range0.261 rad; 8:Δ-0.054 rad/dq-0.012 rad/s/range0.589 rad; 9:Δ-0.078 rad/dq-0.008 rad/s/range0.572 rad; 10:Δ-0.012 rad/dq-0.001 rad/s/range0.322 rad; 11:Δ-0.058 rad/dq-0.006 rad/s/range0.628 rad; 12:Δ-0.839 rad/dq-0.100 rad/s/range2.444 rad; 13:Δ-0.434 rad/dq-0.049 rad/s/range2.635 rad; 14:Δ+11.473 rad/dq+1.408 rad/s/range11.505 rad; 15:Δ+11.063 rad/dq+1.348 rad/s/range11.110 rad

**段 5** (181.64–191.55 s)：0:Δ+0.050 rad/dq+0.001 rad/s/range0.170 rad; 1:Δ+0.054 rad/dq+0.007 rad/s/range0.158 rad; 2:Δ-0.033 rad/dq-0.005 rad/s/range0.207 rad; 3:Δ-0.032 rad/dq-0.008 rad/s/range0.108 rad; 4:Δ+0.022 rad/dq-0.001 rad/s/range0.205 rad; 5:Δ-0.001 rad/dq+0.002 rad/s/range0.280 rad; 6:Δ-0.007 rad/dq+0.003 rad/s/range0.201 rad; 7:Δ+0.007 rad/dq+0.003 rad/s/range0.209 rad; 8:Δ+0.031 rad/dq+0.000 rad/s/range0.273 rad; 9:Δ+0.018 rad/dq+0.008 rad/s/range0.158 rad; 10:Δ+0.014 rad/dq+0.000 rad/s/range0.190 rad; 11:Δ+0.002 rad/dq+0.004 rad/s/range0.357 rad; 12:Δ+2.630 rad/dq+0.263 rad/s/range6.935 rad; 13:Δ-10.792 rad/dq-1.088 rad/s/range11.538 rad; 14:Δ+16.523 rad/dq+1.667 rad/s/range20.894 rad; 15:Δ-4.549 rad/dq-0.455 rad/s/range5.527 rad

**段 6** (202.95–206.23 s)：0:Δ-0.020 rad/dq-0.005 rad/s/range0.223 rad; 1:Δ+0.010 rad/dq+0.008 rad/s/range0.169 rad; 2:Δ+0.001 rad/dq-0.004 rad/s/range0.317 rad; 3:Δ-0.023 rad/dq-0.010 rad/s/range0.199 rad; 4:Δ+0.016 rad/dq+0.003 rad/s/range0.161 rad; 5:Δ-0.011 rad/dq-0.001 rad/s/range0.364 rad; 6:Δ+0.050 rad/dq+0.011 rad/s/range0.352 rad; 7:Δ+0.028 rad/dq+0.008 rad/s/range0.260 rad; 8:Δ-0.042 rad/dq-0.012 rad/s/range0.525 rad; 9:Δ-0.013 rad/dq-0.002 rad/s/range0.424 rad; 10:Δ-0.015 rad/dq-0.008 rad/s/range0.314 rad; 11:Δ+0.013 rad/dq+0.004 rad/s/range0.402 rad; 12:Δ-6.532 rad/dq-1.977 rad/s/range7.261 rad; 13:Δ+6.701 rad/dq+2.022 rad/s/range6.714 rad; 14:Δ-1.925 rad/dq-0.582 rad/s/range3.061 rad; 15:Δ+17.818 rad/dq+5.406 rad/s/range17.836 rad

**段 7** (219.22–219.73 s)：0:Δ-0.003 rad/dq-0.000 rad/s/range0.007 rad; 1:Δ-0.113 rad/dq-0.218 rad/s/range0.115 rad; 2:Δ+0.119 rad/dq+0.215 rad/s/range0.126 rad; 3:Δ+0.014 rad/dq+0.018 rad/s/range0.015 rad; 4:Δ-0.076 rad/dq-0.145 rad/s/range0.079 rad; 5:Δ+0.080 rad/dq+0.151 rad/s/range0.085 rad; 6:Δ-0.024 rad/dq-0.044 rad/s/range0.026 rad; 7:Δ-0.079 rad/dq-0.152 rad/s/range0.086 rad; 8:Δ+0.141 rad/dq+0.268 rad/s/range0.145 rad; 9:Δ+0.003 rad/dq+0.008 rad/s/range0.004 rad; 10:Δ-0.045 rad/dq-0.095 rad/s/range0.049 rad; 11:Δ+0.092 rad/dq+0.173 rad/s/range0.098 rad; 12:Δ+0.032 rad/dq+0.062 rad/s/range0.042 rad; 13:Δ+0.003 rad/dq-0.004 rad/s/range0.008 rad; 14:Δ-0.173 rad/dq-0.363 rad/s/range0.194 rad; 15:Δ-0.167 rad/dq-0.320 rad/s/range0.172 rad

**段 8** (221.59–225.01 s)：0:Δ-0.763 rad/dq-0.226 rad/s/range0.780 rad; 1:Δ+0.437 rad/dq+0.135 rad/s/range0.927 rad; 2:Δ-1.503 rad/dq-0.450 rad/s/range1.525 rad; 3:Δ+0.780 rad/dq+0.224 rad/s/range0.794 rad; 4:Δ+0.432 rad/dq+0.128 rad/s/range0.923 rad; 5:Δ-1.519 rad/dq-0.453 rad/s/range1.545 rad; 6:Δ-0.800 rad/dq-0.230 rad/s/range0.814 rad; 7:Δ+0.461 rad/dq+0.143 rad/s/range0.943 rad; 8:Δ-1.508 rad/dq-0.445 rad/s/range1.525 rad; 9:Δ+0.786 rad/dq+0.236 rad/s/range0.800 rad; 10:Δ+0.464 rad/dq+0.136 rad/s/range0.947 rad; 11:Δ-1.487 rad/dq-0.439 rad/s/range1.515 rad; 12:Δ+0.558 rad/dq+0.164 rad/s/range0.586 rad; 13:Δ-0.280 rad/dq-0.081 rad/s/range0.383 rad; 14:Δ+0.488 rad/dq+0.145 rad/s/range0.798 rad; 15:Δ-0.623 rad/dq-0.180 rad/s/range1.058 rad

**段 9** (232.36–235.11 s)：0:Δ+0.701 rad/dq+0.250 rad/s/range0.938 rad; 1:Δ-0.459 rad/dq-0.163 rad/s/range0.930 rad; 2:Δ+1.514 rad/dq+0.549 rad/s/range1.527 rad; 3:Δ-0.704 rad/dq-0.255 rad/s/range0.942 rad; 4:Δ-0.452 rad/dq-0.168 rad/s/range0.930 rad; 5:Δ+1.537 rad/dq+0.565 rad/s/range1.550 rad; 6:Δ+0.703 rad/dq+0.255 rad/s/range0.940 rad; 7:Δ-0.460 rad/dq-0.162 rad/s/range0.931 rad; 8:Δ+1.533 rad/dq+0.551 rad/s/range1.543 rad; 9:Δ-0.701 rad/dq-0.249 rad/s/range0.925 rad; 10:Δ-0.458 rad/dq-0.168 rad/s/range0.934 rad; 11:Δ+1.524 rad/dq+0.557 rad/s/range1.538 rad; 12:Δ-0.312 rad/dq-0.112 rad/s/range0.380 rad; 13:Δ-0.493 rad/dq-0.179 rad/s/range0.531 rad; 14:Δ-0.449 rad/dq-0.163 rad/s/range0.491 rad; 15:Δ-0.456 rad/dq-0.165 rad/s/range0.494 rad

**段 10** (239.59–242.99 s)：0:Δ-0.704 rad/dq-0.217 rad/s/range0.720 rad; 1:Δ+0.449 rad/dq+0.135 rad/s/range0.941 rad; 2:Δ-1.494 rad/dq-0.451 rad/s/range1.518 rad; 3:Δ+0.712 rad/dq+0.209 rad/s/range0.727 rad; 4:Δ+0.444 rad/dq+0.132 rad/s/range0.933 rad; 5:Δ-1.515 rad/dq-0.455 rad/s/range1.544 rad; 6:Δ-0.717 rad/dq-0.208 rad/s/range0.730 rad; 7:Δ+0.453 rad/dq+0.142 rad/s/range0.936 rad; 8:Δ-1.517 rad/dq-0.452 rad/s/range1.535 rad; 9:Δ+0.707 rad/dq+0.220 rad/s/range0.721 rad; 10:Δ+0.448 rad/dq+0.133 rad/s/range0.932 rad; 11:Δ-1.507 rad/dq-0.447 rad/s/range1.534 rad; 12:Δ+0.556 rad/dq+0.162 rad/s/range0.585 rad; 13:Δ-0.356 rad/dq-0.101 rad/s/range0.472 rad; 14:Δ+0.514 rad/dq+0.148 rad/s/range0.863 rad; 15:Δ-0.522 rad/dq-0.150 rad/s/range0.805 rad

## 已知转向交叉检查

按 gyro_z 左正右负、前进轮 dq 正的现场事实，检验 12/14 右、13/15 左；此项只校验旧采样，不能代替逐轮标定。

| 段 | 时间 s | 方向 | gyro_z | dq12,13,14,15 | 侧别一致 |
| --- | --- | --- | ---: | --- | --- |
| 5 | 187.56–190.74 | left | +0.454 | +1.72, -2.30, +6.11, -0.40 | True |
| 6 | 203.11–205.35 | right | -1.079 | -3.14, +2.60, -1.12, +7.53 | True |

## 趴下/站立静态读数

选取每态最长的全 16 槽低速窗口；轮 q 是累计转角，不是姿态零位。

| DDS 槽 | 趴下候选 q rad | 站立候选 q rad |
| ---: | ---: | ---: |
| 0 | -0.56880 | 0.12134 |
| 1 | 0.99302 | 0.58843 |
| 2 | -2.75651 | -1.23964 |
| 3 | 0.58595 | -0.12983 |
| 4 | 0.96564 | 0.60716 |
| 5 | -2.75504 | -1.22428 |
| 6 | -0.54458 | 0.13080 |
| 7 | 0.99701 | 0.59904 |
| 8 | -2.75821 | -1.22686 |
| 9 | 0.56841 | -0.12154 |
| 10 | 0.94526 | 0.60091 |
| 11 | -2.74080 | -1.22663 |
| 12 | -28.36515 | -28.90307 |
| 13 | -7.55724 | -7.95134 |
| 14 | 82.36163 | 81.84693 |
| 15 | 128.22300 | 127.66303 |

### 全部静态窗口

| 时间 s | 时长 s | 姿态候选 |
| --- | ---: | --- |
| 0.02–76.26 | 76.24 | prone_candidate |
| 79.10–149.28 | 70.18 | standing_candidate |
| 150.40–168.47 | 18.07 | standing_candidate |
| 175.06–181.65 | 6.59 | standing_candidate |
| 185.01–186.16 | 1.15 | standing_candidate |
| 186.20–187.31 | 1.11 | standing_candidate |
| 191.54–202.96 | 11.42 | standing_candidate |
| 206.16–219.21 | 13.05 | standing_candidate |
| 219.74–221.58 | 1.84 | standing_candidate |
| 225.02–232.35 | 7.33 | prone_candidate |
| 234.90–239.58 | 4.68 | standing_candidate |
| 243.00–300.00 | 57.00 | prone_candidate |

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
