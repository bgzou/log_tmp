# R1199 无滤波 Debug 首次实机记录（2026-11-12 22:01）

## 范围与现场反馈

现场人员本次同意的计划是 A 起立、B 后摇杆居中约 2–3 秒、A 回站、Y 趴下。实际会话在 B 后约 21 秒的 PolicyWalk 中出现多次前进/后退摇杆输入；这是比计划更大的动作范围，不把它记成“零速试验”。程序收到 A 后 Brake→ReturnStand→FixSquat→Passive 自动趴下；日志未显示单独 Y 趴下触发。现场最终确认狗稳定趴下、无报警或明显失稳，并补充：**前进与后退过程中都能听到关节抖动声，问题仍存在。**

## 机器与记录结果

- 入口：USB HDC `-Policy r1199 -Mode training-contract -MonitorSeconds 240 -Debug -LowPassMs 0 -ConfirmMotion`。`POLICY_LOWPASS tau_ms=0 wheels=0`，本次**没有滤波**。原厂 ai_damping→ReleaseMode rc0→16轴mode0→Passive ready after 749 frames→A→B→策略→A→自动趴下，发布端退出0。最终仍是 ReleaseMode、无发布端；未执行 SelectMode。
- 完整归档：`field_sessions/20261112-220051_training-contract/` 七文件；Windows transcript `20261112-220052_windows_r1199_training-contract_field_session.log`。`debug_policy.csv` 有 1170 条有效控制帧（Handoff100、Walk1054、Brake16），每帧完整 65 维 Observation，无坏行；`debug_lowcmd.csv` 有 26586 条有效最终发布帧，无坏行，`dropped=0 file_ok=1`。独立 LowState 快采 29687 有效行；保护流 11297 有效行，`warning_or`、`motorstate_or` 全程为0。未见发布端 `FIELD_SAFETY_WARN/HARD/SOFT_TRIP`。
- 采集节拍：策略控制帧间隔 p50 19.999 ms、p99 20.492 ms、最大22.040 ms；最终 LowCmd p50 2.001 ms、p99 2.825 ms、最大10.969 ms，未有 >40 ms 间断。说明本次 Debug 写盘没有可见的发布周期失守；不代表所有未来负载均如此。
- 实际 `vx` 指令范围约 −0.200～+0.160 m/s；373个Walk帧在 `|vx|≥0.03`，600帧在 `|vx|<0.005`。滤波关闭时请求与应用的腿关节目标差严格为0。运动帧腿目标最大单帧变化 p99 0.12598 rad、峰0.12599 rad，静止帧 p99 0.05504 rad；raw腿输出在运动帧中约88.7%的标量值达±5.9附近。此前“模型 raw 输出近饱和”的现象本次仍存在。
- 2 ms LowState 中，以各自最长的连续前进/后退段与同长度静止段相比，四大腿 `dq` 的40–120Hz频带能量明显更高；详值见 `20261112-2201_r1199_debug_first_field_analysis.txt`。这是**关节反馈的运动相关高频成分**，和现场声响相符，但没有同步麦克风或声源定位，不能单独证明声音来自哪一个关节，也不能仅凭频谱认定控制失稳。前进段较短、比值对静止基线和窗口敏感，后续比较滤波效果须用同条件时窗。
- 会话结束后只读复核：`MotionSwitcher CheckMode rc=0 name=`（仍是 ReleaseMode）、LowState 1058包/s，狗保持趴下；原始输出 `20261112-2201_r1199_debug_postcheck_readonly.log`。**原厂遥控控制权尚未恢复**；任何 `SelectMode("ai")` 均须另行告知现场人员并获当次许可，因为趴下时可能直接起立。

## 判断与后续

本次证实通用 Debug 链能在这台设备上完整录到真实 Observation、最终 LowCmd 与反馈，且无写盘丢行或保护触发；**无滤波 R1199 的前后运动抖动声没有改善**。目标单帧变化、raw 输出饱和与实测高频反馈提供了可分层分析的证据，但没有隔离训练策略、执行器/增益和接触动力学各自贡献。应将本次七文件与训练合同提供给训练同事核查；如考虑腿目标低通，先用完全相同的动作包装/previous-action 语义和滤波时间常数完成闭环仿真，再讨论独立有界实机对照。滤波运动入口目前仍锁定。

只读分析脚本：`20261112-2201_r1199_debug_first_field_analysis.py`。任何下一次机器人动作都要另行具体告知并获得现场人员当次明确同意。
