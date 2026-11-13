# R152 发布端 FSM：2026-11-09 离线实现记录

**状态：已在 CPRO ARM64 编译；新增“固定 PD Stand / ReturnStand”在 MuJoCo 预演未过严格判据，禁止上机。未运行发布端、未向真机发布 LowCmd。**
源码唯一位置：`部署参考/cpp_deploy-as2w/deploy/robots/as2w/r152/r152_publish.cpp`。CMake 选项 `AS2W_R152_PUBLISH` 默认 OFF；现场入口未提供运行该发布端的阶段。

## 遥控器与状态

| 当前状态 | 触发 | 下一状态 | 具体动作 |
| --- | --- | --- | --- |
| Passive | A 按下沿 | FixStand | 从当前趴下关节读数启动两段起立 |
| FixStand | 轨迹完成 | Stand | 固定 PD 保持 T1/T2 站姿，四轮目标速度为零 |
| Stand | B 按下沿 | R152 | R152 控制器 arm，开放摇杆前进 |
| R152 | A 按下沿 | ReturnStand | R152 零速刹停；轮速稳定后快照当前关节并插值回固定 PD 站姿 |
| ReturnStand | 插值完成 | Stand | 固定 PD 保持 |
| Stand | Y 按下沿 | FixSquat | 两段受控趴下，再回 Passive |
| 任意非 Passive | X 按下沿、终端 q/Ctrl-C、LowState/姿态看门狗 | Passive | 立刻切阻尼并锁存，必须重启才能再用 A 起立；站立时机身可能下沉 |

R152 中左摇杆纵向 `ly` 首测只映射 `vx=clamp(0.2*ly,0,0.2)` m/s；死区 0.05。侧移 `vy` 和转向 `wz` 固定为零，虽已完成遥控器轴标定，但这两种运动未过首次实机的仿真严格门槛。Y 在 R152 中无效，必须先 A 返回 Stand 才能受控趴下。B 在其它状态无效。X 是紧急阻尼，不是常规趴下。

ReturnStand 采用：R152 零速度命令保持平衡；四轮实测 `|dq|<0.5 rad/s` 连续 300 ms 后，快照 12 腿实际位置；1.5 s 插值到固定站姿，腿 `kp` 由 35 升至 55、`kd=2`，轮 `dq=0,kd=2`。刹车超过 3 s 尚未达阈值则锁存 Passive。**这些时长、阈值和增益目前是离线实现参数，ReturnStand 尚无 MuJoCo/实机验证。**

## 真机前门槛

1. `hardware_contract.md` 的 LowCmd **命令方向、轮速度响应、断流/失联行为**仍未实测；不得因编译通过就运行发布端。原厂遥控器在低层接管后的物理急停路径也未实测。
2. 服务器 MuJoCo 已对 **固定 PD Stand 保持、B 接管 R152、R152 行走→A 刹停→固定 PD Stand、Stand→Y FixSquat** 做 6 组整链预演，**未过关**，详见下节。需改设计并重新预演；现有 P8 只覆盖旧的 FixStand→R152→FixSquat 顺序链。
3. 每个可能让狗动作的现场步骤，先告知现场人员具体动作并取得当次明确同意。A/B/Y/X 的按键操作者在场并握住原厂遥控器。
4. S0–S9 测试单需按上表拆成独立状态转换；不得沿用旧顺序定时执行的操作脚本。SelectMode 从站立的行为未验证，当前发布程序不自动调用它。
5. 当前 q/Ctrl-C 只锁存阻尼并保持 500 Hz 发布；**没有经过验证的停发→恢复原厂运控退出程序路径**。在这一门槛补齐之前，不能把程序当作可完整回收控制权的现场控制器。

## 构建记录

- Windows 源码经服务器挂载运行基础 CMake/CTest：7/7。
- `部署测试/现场入口.ps1 -Stage Sync`：打包、HDC 传输与远端 SHA-256 校验通过。
- `-Stage SdkBuild`：CPRO Ubuntu 原有诊断工具构建、CTest 7/7。
- CPRO Ubuntu 显式 `AS2W_R152_PUBLISH=ON` 的 ARM64 构建：`as2w_r152_publish` 链接成功，CTest 7/7。此显式构建目录是 `/root/as2w_deploy/build-r152-publish`，不会改变默认 OFF 选项。
- 原始日志在 `部署测试/04_调试记录/logs/20261109-193835_windows_Sync.log`、`20261109-193848_windows_SdkBuild.log`、`20261109-1939_r152_publish_configure.log`、`20261109-1940_r152_publish_build.log`、`20261109-1941_r152_publish_ctest.log`。

## MuJoCo 回退预演失败（暂停实机）

服务器使用 R152 ONNX 与交付同源模型，在 T1/T2 站姿各 3 种子上模拟 A 起立→固定 PD Stand→B R152 慢走→A 零速刹停→插值固定 PD Stand→Y 受控趴下。所用脚本 `部署参考/as2w-flat-rerun/r152_fsm_rehearsal.py`，结果 `results/fsm_rehearsal_20261109.json`，原始终端 `logs/20261109-1945_r152_fsm_mujoco.log`。轮速 0.5 rad/s 连续 300 ms 的刹停门槛 6/6 达成；**固定 PD 回退时机身降至 0.25–0.33 m，6 例中 5 例非轮触地峰值 >50 N（最高 152 N）**，未满足严格判据。T1 固定 Stand 首段本身有一例高度降至 0.293 m。

两组诊断变体也未解决：①轮阻尼从 2 提至 10、回退插值 1.5 s 延至 3 s，6/6 非轮触地峰值 128–203 N（`results/fsm_rehearsal_wheelkd10_3sec_20261109.json`，`logs/20261109-1947_r152_fsm_mujoco_tuning.log`）；②刹停后只固定 PD 保持实测关节姿态，不插值到 T1/T2，仍有 5/6 超过 50 N，T1 最终高度约 0.21 m（`r152_fsm_rehearsal_snapshot_hold.py`、`results/fsm_rehearsal_snapshot_hold_20261109.json`、`logs/20261109-1950_r152_fsm_snapshot_hold.log`）。

**判断：当前固定 PD Stand 是明确失败的离线候选，不能通过“编译成功”升级成实机流程。** 已向用户建议：保留 A/B/Y/X 按键意义，但 Stand 改成 R152 零速度保持；这个零速度策略站姿在旧 P8 预演较稳定，仍需针对新 FSM 重新全链测试。等待用户设计选择。

## 零速策略 Stand 与 FixSquat 的进一步复演

应用户追问，重新按 `FixStand→零速 R152 Stand→行走→零速 R152 Stand→FixSquat` 做 T1/T2 × 3 种子预演。旧 `r152_fixstand_rehearsal_2seg.py` 复跑结果依然 6/6 最终趴下、未翻倒，**但旧“全绿”只计算行走阶段的非轮触地，没有检查趴下过程**；复跑 `results/fsm_zero_policy_stand_20261109.json`、原始 `logs/20261109-1952_fsm_zero_policy_stand.log`。

`r152_fsm_zero_policy_rehearsal.py` 新增 Y 按下后前 0.5 s 量测：从当前关节读数起插值，第一帧关节位置目标变化只有 0.013–0.016 rad；但 6 例中 4 例在这半秒非轮触地峰值已 >50 N，最高约 127 N（`results/fsm_zero_policy_transient_20261109.json`、`logs/20261109-1955_fsm_zero_policy_transient.log`）。**角度连续不等于支撑力连续**。

`r152_fsm_squat_handoff_rehearsal.py` 用策略最后一帧的腿位置目标/轮速目标及 kp55 作 FixSquat 起点，再渐变到轨迹/增益。前 0.5 s 的触地峰值在 6/6 变成 0 N，初始交接改善；但覆盖完整 F1/F2/落位后，**6 例整体非轮触地峰值仍为 253–1006 N、最大下落速度 1.35–1.82 m/s**（`results/fsm_squat_handoff_full_20261109.json`、`logs/20261109-2000_fsm_squat_handoff_full.log`）。这是中后段落地冲击，不能称作受控安全趴下。需重新设计 F1/F2 支撑和落地轨迹，或找到经严格判据验证的退出方式；**Y 不能在真机启用**。

当前 C++ 仍是离线 FSM 骨架，与上述实验性平滑交接尚未同步；不应因最初 ARM64 构建成功而运行。任何重构后须再做编译、7/7、Sync、ARM64 编译、仿真和阶段日志。
