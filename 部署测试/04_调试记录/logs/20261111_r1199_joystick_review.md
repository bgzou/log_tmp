# R1199 摇杆首试复核（2026-11-11 23:36–23:40）

现场报告：先出现较高站姿，随后明显下降；只试前后，听见关节抖动声，速度观感尚可；Ctrl+C 未中止等待。原始证据：`20261111-233643_windows_r1199_joystick_field_session.log` 与 `field_sessions/20261111-233644_joystick/`。发布端完成 A→固定站→B约2秒零速交接→PolicyWalk满60秒自动Brake→ReturnStand→Y趴下→Passive，RC0；`wz=0`，转向未验收。

保护流45,641条：`warning_or=0x0`、`motorstate_or=0x0`全程；`board_state0`仅0x0/0x1。电流峰5.9A、电机电压最低44.3952V均在起立附近，不能据此证明全程平顺。发布端**有一次软件守卫预警**：`FIELD_SAFETY_WARN state=PolicyWalk count=1`，腿目标单帧步进0.272911rad，高于warn门槛0.2、低于hard门槛0.35；该帧腿速度1.53194rad/s、估算力矩10.95Nm、PD估计10.9239Nm，电机错误0。未达到连续5帧SoftBrake或3帧HardStop，无`SOFT_TRIP/HARD/REMOTE_TIMEOUT`；实际刹轮原因是60秒时限。

姿态变化与首次推杆同段：固定站时四大腿q均值约0.74rad、四小腿约-1.79rad；零命令策略期间分别约0.87、-1.53rad，更伸展；首次非零`vx`后约0.79、-1.75rad，腿速度峰约1.92rad/s。没有机身高度测量，不能把腿角差换算成下沉距离。`POLICY_TRACK`在零命令时四髋目标与实际差约0.35–0.47rad，首次前进后差缩至约0.20rad；同时发生上述目标跳步。行走段10ms采样腿dq RMS约0.062rad/s、峰1.51rad/s；固定站RMS约0.012rad/s。采样未显示持续多帧高幅速度振荡，但无法排除高频力矩/电流振荡或直接判断声音来源。可复跑的离线汇总脚本与结果为`20261111_r1199_joystick_analysis.py/.txt`。

首要机制见维护源码`r1199_controller.cpp`：`age>=4s`后`stand_blend`依赖`release_blend`；首个非零速度令`centered=false`、`hold_frames_=0`，于是`stand_blend`可从接近1瞬间变0，原先积累的`bias_`腿补偿在单个20ms控制帧撤掉。速度命令有斜率限制，但这项站立补偿没有。代码机制与目标跳变、姿态下降时间吻合；仍需离线消融确认是否也是声音的唯一来源。较大的髋关节跟踪误差另待查。

**来源复核**：这一补偿不是本次实机临时创造。`Rob2Nav-rolling-fixed-exit-source` 的提交`0c371f6`（2026-11-11 10:07 +0800，提交人Codex）附带离线部署zip，其中`as2w_rolling_fixed_exit.py`含`rolling_precalibrated_stand`相同计算；YuTaoV5于13:03通过`7bae69b`合并。解压的Python文件与zip内SHA同为`77a143d05f3d0017e72a70ad7736cb82bcca370d270709c7dd68d13132f277ea`。R1199发布包也包含该函数。CPRO C++版是训练/交付包装的移植，不是ONNX权重本身的输出。Git提交人不等于能确认最初的人类设计决策者。

Ctrl+C方面：旧会话脚本在发布端RC0后仍`wait`两只持续240秒的只读监测进程；Windows→HDC→CPRO的Ctrl+C也不保证传到远端发布端。此次日志显示发布端已正常结束，监测一直采到240秒才归档。**Ctrl+C不能当运动急停**，运动中用X或物理急停。已把R1199会话脚本改为发布端退出后再采5秒便终止监测并归档；它不改变活动运动期间Ctrl+C不可靠的事实。

当前`joystick`入口已在远端会话脚本开头硬阻断，`joystick-dry-run`仍可只读使用。暂停再次动作；下一步离线让站立补偿渐出，核对训练侧包装与MuJoCo首次推杆，再评估新的短时有界真机测试。上游权重、已验收zero-B和自动前进二进制均未重建。
