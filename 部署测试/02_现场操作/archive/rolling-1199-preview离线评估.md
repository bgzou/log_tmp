# rolling-1199-simulation-preview 离线评估（2026-11-11）

> 晚间复核纠错：本页基于旧复演器得出的“实测初态前进会非轮碰地”已被定位为 `previous_action` 回填原始动作的实现错误。修为最终包装动作后种子101/202/303均无非轮触地；停车/回固定站姿仍未过。最新结论见 [R1199仿真差异同条件复演与改进方向.md](./R1199仿真差异同条件复演与改进方向.md)。

结论：**当前不能绑定真机 B，也不做有界地面滚动首测。** 这是一次独立 release；不能把此前 `rolling-fixed-exit-preview` 的结果当作它的结果，但两者均未越过本项目完整动作链门槛。本阶段没有控制权切换、LowCmd 或机器人动作。

## 来源及完整性

- GitHub release：`YuTaoV5/Rob2Nav` tag `as2w-rolling-1199-preview`，资产 `as2w-rolling-1199-preview.zip`，发布于 2026-11-11 08:52 UTC。资产 SHA256 `dd212125b9c6d6e4cc840eab1f0fe46d7c335542c9d39c97e275981bad33c456`，本地复核一致。
- 本地资产：`部署参考/Rob2Nav-rolling-1199-preview/`；`policy.onnx` SHA `df1f2db98efe32ad4a8b767c34b7ca4235c717f80e5778d59552a522b6fc7f23`，`model_1199.pt` SHA `bb5c9735b5bd37ef4bdd2bd13f9d45395d8dc9b4c888c36955de1a345d55776d`，均与交付 parity 清单一致。
- 交付自述：1200 training iterations；ONNX `obs[1,65]→actions[1,16]`，opset17，7560记录帧 parity 最大误差 `8.59e-6`。此 parity 只验证模型导出一致，不验证控制安全。
- release 标为 Simulation Preview；README 明示只供 simulation/offline shadow，转向、刹车和高速未通过双仿真验收。`as2w-shadow-contract.json` 和 reference 均标 `real_actuation_enabled=false`；reference 的 16 个 `dds_slot/hardware_direction/hardware_zero_rad/hardware_effort_limit_nm` 全为 null。项目已有实测轴映射可另行集成，但这份包本身没有可运行真机发布端。

## 上游提供的评估

- `mujoco-rolling-diagnostic-summary.json`：完整路线 `forward/back/turn_left/turn_right/arc_left/arc_right` 均 0/1，`gate=false`，虽 `safety_gate=true`。这里的 safety_gate 不等于完整运动验收。
- `speed-evaluation.json` 低速 0.30 m/s：前进跟踪且刹住 2/4，最终固定站姿保持 0/4；倒退跟踪且刹住 4/4，最终保持 1/4。左右转向各 0/2，左右弧线各 0/2 完整通过；转向有个别样本失稳/膝部接近地面。前进某样本刹车约 1.54 m、9.16 s，显著超过其 0.1625 m、2.5 s 限制。
- 3 m/s 档和更高档均未过双仿真门槛。`vy` 不进入当前滚动动作包装，策略实际仅接受 `vx,wz`，手柄侧移不能开放。

## 本项目独立 MuJoCo 诊断

复用 `部署参考/as2w-flat-rerun/rolling_fixed_exit_rehearsal.py` 的 65 维观测、与本交付相同的 `rolling_fixed_exit()` 轮/腿动作包装及固定站姿进退路线；只替换新 ONNX。MuJoCo 3.17、ORT 1.31，服务器 192.168.10.163。用此前真机 FixedStand 的实测腿角和 pitch −5.498° 作为初态，种子 101/202/303，每种静止、前进 +0.30、倒退 −0.30 共 9 条。原始逐阶段结果：`部署参考/as2w-flat-rerun/results/rolling_1199_measured_start_20261111.json`。

| 场景 | 跟踪 | 刹车 | 轮支撑/非轮接触门槛 | 退出固定站姿 | 主要数值 |
|---|---:|---:|---:|---:|---|
| 静止 | 3/3 | 3/3 | 3/3 | 0/3 | 最终腿误差 0.19–0.20 rad，高于本项目 0.18 rad 门槛 |
| 前进 +0.30 | 3/3 | 3/3 | 0/3 | 0/3 | 平均 vx 约 0.236 m/s；非轮接触峰 63.5–98.9 N；刹车距离 0.095–0.113 m；最终腿误差 0.41–0.46 rad |
| 倒退 −0.30 | 3/3 | 3/3 | 1/3 | 0/3 | 平均 vx 约 −0.291 m/s；两次非轮接触峰 71.6/93.4 N；最终腿误差 0.25–0.34 rad |

这是基于旧项目复演器的**诊断复演**，不是对本交付全部 stand-bias、parking supervisor 和双引擎设置的逐行同构复制。动作包装首函数与本交付一致；仿真动力学和转移实现仍可能有偏差，不能将这些数值解释成真机发生概率。它验证了“去掉最终站稳保持就已经安全”的推论不成立：前进运动阶段的非轮接触仍全部触发。

## 对现场问题的解释和下一门槛

“回固定站姿”是策略刹轮后接回 A 键固定 PD 站立目标，并在退出后持续保持；其关节误差门槛是本项目现有验收标准，不是宇树厂商定义，也不是策略交付自带的成功率。可以重新研究退出设计，但不能直接删除退出环节，因为现有 A→B→A/Y 手柄链必须有受控的后继状态。

“非轮接触”是轮子之外的腿部或机身部件触地。当前独立复演的前进 3/3、倒退 2/3 出现 63–99 N 峰值，属于独立于最后站姿保持的运动期问题。

训练/交付侧需先补齐：低速 0.05–0.10 m/s 的多种子跟踪、刹停、保持、非轮接触和固定站姿退出；用本项目真机 FixedStand 初态和摩擦/质量/时延扰动复演；左右转向及弧线门槛；明确腿/轮 `kp,kd`、动作前后处理和零命令停车合同。修订后先进行 ONNX/包装等价与独立 MuJoCo 复演，再考虑只读 shadow、CPRO ARM64 集成和另行申请有界真机动作。当前不修改 R214 发布端、不同步此策略到 CPRO、不解除其他策略硬阻断。
