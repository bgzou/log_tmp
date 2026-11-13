# R1199 有界前进 0.05 m/s 实机首试复核（2026-11-11 23:10–23:13）

## 实际步骤与结果

- 现场人员当次明确同意，在旁看护并持原厂遥控器/物理急停。Windows 执行 `运行现场策略会话.ps1 -Policy r1199 -Mode forward -MonitorSeconds 180 -Target 192.168.10.180:8710 -ConfirmMotion`。
- SHA/audit PASS；LowState 1036包/s、`mode_machine=2`，已有 ReleaseMode，2秒状态2083包、16轴mode0、四小腿趴下角校验通过。监测在发布前启动。Passive 唤醒后 `Passive ready after 745 frames`。
- 现场按 A：`Passive→FixStand→FixedStand`。按 B 时门槛通过：pose_error 0.257115rad、轮速 0.024544rad/s、直立指标 0.998423、静止腿dq 0.030680rad/s。随后约2秒零速PolicyHandoff，进入PolicyWalk；发布日志显示速度指令从0.04渐入0.05m/s、`vy=wz=0`，摇杆读数均为0。2.00003秒后因 `bounded forward 2s cap` 自动 Brake→ReturnStand→FixedStand；现场按 Y 两段FixSquat→Passive。`R1199_FORWARD_REMOTE_RC=0`、发布端exit=0，未见守卫警告/硬触发/遥控超时。
- 现场人员观察：“有移动，没多远，我不好量化评估，然后它回站的时候感觉应该是肢体有往下运动。现在稳定趴下，全程无报警。”没有明显异常，但单次短测不代表自由行走或停车保持已验收。

## 数据复核

- 180秒保护流34,176有效行：`warning_or=0x0`、`motorstate_or=0x0` 全程；主板状态仅0x0/0x1；16轴在发布期间mode1，结束回mode0。电流峰5.9A，滤掉首次未收到主板帧后最低电机电压44.7674V。
- 10ms LowCapture 17,999有效行。全程腿dq峰2.02485rad/s、轮dq峰0.93266rad/s、腿估算力矩峰23.9625Nm；全程峰值包含起立和趴下，不能归到策略段。
- 约28–32秒为B交接、自动前进及刹轮窗口。28–30秒机身俯仰约−3.58至+3.97°，轮速峰0.933rad/s，四轮角净变为−0.112、−0.230、−0.407、−0.545rad；30–32秒俯仰约+1.48至+3.95°，轮速峰0.712rad/s，四轮角净变为+0.693、+0.733、+0.536、+0.469rad。短暂反向/正向轮转跨越交接、策略和刹轮，不能仅由这些窗口精确断言哪一帧开始移动，也不能用轮角推算机身实际位移。
- 回站后的32–36秒轮角基本稳定、轮速峰≤0.147rad/s；小腿角从30秒约−1.64/−1.51rad，32秒约−1.75/−1.73rad，固定站静稳约−1.75rad；俯仰约+3.95°回到+0.8°。这对应现场看到的下移/收腿姿态过渡；没有高度或接触力测量，不能直接判定机身垂向位移或冲击。Y约36秒后趴下，至40秒小腿约−2.7rad。

## 结论与后续门槛

**这一次 0.05m/s 自动前进2秒的有界链通过**：指令按限定输出，狗有小幅实际移动，自动刹轮回站和Y趴下完成，无硬件保护位/现场报警。此次不能证明实际机身速度硬限、精确位移、长时间停车保持、倒退/转向，亦不代表 R1199 上游release的 `real_actuation_enabled=false` 已变更。任何进一步手柄自由速度测试需要独立开发、离线核对与当次动作许可；先审当前回站下移的关节/姿态连续性与停车滑移。

原始：`20261111-231030_windows_r1199_forward_field_session.log`、`field_sessions/20261111-231030_forward/{session.log,publisher.log,low_capture_fast.log,low_protection.log}`、计算摘录`20261111_r1199_forward_capture_protection_summary.txt`。本记录没有保存密码或序列号。
