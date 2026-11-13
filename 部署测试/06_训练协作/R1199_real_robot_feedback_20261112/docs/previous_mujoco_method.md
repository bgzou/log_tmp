# R1199：本项目 MuJoCo 复演方法与上游对齐问题

> 晚间复核纠错：下文记录的是旧复演方法，不是正确的 R1199 观测合同。其 `obs[42:58]` 错把原始 ONNX 输出回填为上一动作；应回填最终包装动作。完整消融和修正后结果见 [R1199仿真差异同条件复演与改进方向.md](./R1199仿真差异同条件复演与改进方向.md)。

日期：2026-11-11。供策略训练同事核对。本文只说明**本项目额外跑的九条独立诊断复演**；交付 zip 内的 `speed-evaluation.json` 和 `mujoco-rolling-diagnostic-summary.json` 是上游自己的评估，二者的通过率不能混在一起算。

## 1. 我实际运行了什么

- 交付资产：GitHub release `as2w-rolling-1199-preview` 的 `as2w-rolling-1199-preview.zip`。zip SHA256 `dd212125b9c6d6e4cc840eab1f0fe46d7c335542c9d39c97e275981bad33c456`；本次加载 `policy.onnx` SHA256 `df1f2db98efe32ad4a8b767c34b7ca4235c717f80e5778d59552a522b6fc7f23`。
- 仿真脚本：本项目此前为 `rolling-fixed-exit-preview` 写的 [`rolling_fixed_exit_rehearsal.py`](../../部署参考/as2w-flat-rerun/rolling_fixed_exit_rehearsal.py)，**没有修改脚本，只把 ONNX 换成 R1199**。脚本执行时检查模型签名 `obs[1,65]→actions[1,16]`；模型实际加载成功。
- 服务器环境：Ubuntu x86_64，MuJoCo `3.17.0`，ONNX Runtime `1.31.1`，CPU；脚本 `DT=0.02 s`（50 Hz），每步按 MuJoCo `model.opt.timestep` 做物理子步。
- 命令（服务器工作站 SSHFS 挂载正常时）：

```bash
cd /home/caolin/as2w_workstation
ROLLING_MEASURED_ONLY=1 python3 \
  '部署参考/as2w-flat-rerun/rolling_fixed_exit_rehearsal.py' \
  '/tmp/opencode/omni/assets' \
  '/tmp/opencode/omni/runtime' \
  '部署参考/Rob2Nav-rolling-1199-preview/deliveries/as2w-deploy/rolling-1199-simulation-preview/policy.onnx' \
  '部署参考/as2w-flat-rerun/results/rolling_1199_measured_start_20261111.json'
```

第一次尝试使用工作站 `as2w-flat-rerun/assets` 路径，缺少 `fall-baseline/fall-recovery-contract.json`，在构建 MuJoCo 模型前失败；改用服务器既有 `/tmp/opencode/omni/assets` 后成功。`RUNTIME` 目录提供 `mujoco_screen.py`、`export_r41_onnx.py`；这些是本项目已有的仿真资产，并非 R1199 zip 自带依赖。原始逐阶段数值在 [`rolling_1199_measured_start_20261111.json`](../../部署参考/as2w-flat-rerun/results/rolling_1199_measured_start_20261111.json)。

## 2. 物理场景、初态与扰动

- MuJoCo 模型由本项目既有 `mujoco_screen.load_flat_model(True, True, seed=0)` 从 AS2-W 平地资产加载；不是同事当前训练/验收环境的精确拷贝。脚本从模型中读取 16 轴关节和电机、轮体、地面接触。
- `ROLLING_MEASURED_ONLY=1` 使脚本只跑 `measured_static`、`measured_forward`、`measured_back`；每种用种子 `101/202/303`，共 9 回合。**本轮没有独立复演转向、弧线、高速或理想趴下→起立全链**；相关数字若被引用，来源是上游 zip 的报告。
- 初始 16 轴位置按此前实机 FixedStand 稳态读数设置：hip `[-0.221,+0.217,-0.270,+0.264]`，thigh `[0.746,0.743,0.708,0.713]`，calf `[-1.720,-1.731,-1.863,-1.869]`，轮角置零；机身 pitch `−5.498°`。这反映本项目 A 键固定 PD 站姿的负载偏差，而非理想 T2 `(hip=0,thigh=0.8,calf=-1.6)`。
- 设置姿态后，脚本通过二分搜索地面接触调整根高度，未直接注入真机实测高度、轮载荷或关节力矩。也没有把实机完整速度/IMU轨迹重放进去。因此“真机初态”仅指 **q 与 pitch**，不是完整的真机状态。
- 静止例随机地面摩擦系数 `0.55–0.85`。前进/倒退调用既有 `sample_dynamics_stress(seed,...)`，改变地面摩擦、机身质量/惯量和执行增益，并在 8 s 运动段按种子插入一次水平速度扰动。具体每回合的 `friction/push_time_s/push_delta_xy_m_s` 在 JSON `rows[].stress`，脚本中的 gain_scale 也是既有压力配置。我们没有用 R1199 上游评估的扰动种子或其 Isaac Lab 物理参数。

## 3. 观测、动作和执行器近似

- 50 Hz 构造 65 维输入：`[vx,vy,wz]−[0.4,0,0]`、机身角速度、投影重力、常量高度 `0.4`、16 轴相对 T2 默认角、16 轴速度、上一拍 16 维动作、0.62 s 正余弦相位、零命令时四轮角记忆及标志。轮角在 `4π` 区间回绕，记忆以 `0.20 rad` 缩放并裁到 `±3`。这套装配来自旧 preview 复演器；虽然与 R1199 `as2w-shadow-contract.json` 的字段范围对应，**没有逐帧拿 R1199 训练观测做数值 parity**。
- ONNX raw action 裁到 `±6`。腿和轮的 **`rolling_fixed_exit()` 基础动作公式**与 R1199 包内同名函数逐行相同：它只使用 `vx,wz`，不使用 `vy`；腿 motion gate、轮半径 `0.086 m`、腿比例 `0.35`、轮速比例 `16` 均按脚本执行。
- 但是基础动作公式以外，脚本使用自己此前移植的 `stand_bias`、零命令轮角 hold、0.75 s 进入/退出 blend 和 Brake 流程；**没有调用 R1199 包内的 `rolling_precalibrated_stand()`、`rolling_wheel_hold()`、`parking_odometry()` 等函数，也没有逐行实现其完整 mode-switch supervisor**。这正是最需要同事审阅的差异，不能把我的数字说成对 R1199 官方执行链的严格复现。
- 电机近似：腿目标位置用 `kp=55,kd=2` 的 PD 力矩，轮目标速度用 `kd=2` 速度阻尼；输出按 MuJoCo actuator ctrlrange 裁剪。增益和固定站姿过渡来自本项目已实测的 R214 链，不代表 R1199 训练时或同事评估时的增益合同。此处尚未加入 CPRO/DDS 通信延迟、编码器量化或真实执行器柔顺。

## 4. 每回合的状态顺序

```text
实测 FixedStand q/pitch 初态（仍以 T2 作为 PD 目标）
  → 0.75 s 零命令 B 接管插值
  → 2.0 s 零命令策略站立
  → 运动命令：静止 4 s；前进/倒退 8 s，指令分别 0、+0.30、−0.30 m/s
  → 松杆后命令直接置零，最多 5 s 的 policy Brake
  → 0.75 s 由策略目标插值回 T2 固定 PD 站姿
  → 2.0 s 固定站姿保持
```

这里“松杆”被建模为单个 20 ms 策略步从 `±0.30` 跳到 `0`；没有模拟原厂遥控器采样、摇杆回中曲线，也没有接入 2026-11-11 新加到 R214 发布端的加减速斜率守卫。运动段持续 8 s，**不是计划中的 1–2 s 真机小幅诊断**。

Brake 退出条件：四轮最大绝对速度 `<0.5 rad/s`、水平速度模 `<0.025 m/s`、偏航速度 `<0.06 rad/s`，连续 `0.5 s`；最多运行 `5 s`。`brake_distance_m` 是松杆瞬间到 Brake 结束的水平位移。`brake_ok` 只表示上述安静条件达到，不等于整条路线安全通过，也不等于回固定站姿成功。

## 5. 本项目通过条件，以及它们为什么与上游不同

- `tracking_ok`：前后方向的运动尾段平均 vx 距目标 `<0.08 m/s`，侧移 `<0.10 m/s`，偏航 `<0.12 rad/s`。
- `stable`：除 Passive/FixStand 外，每个阶段 min upright `>cos(20°)`、机身最低高度 `>0.25 m`、地面 **非轮接触力峰 `<1 N`**。最后一项刻意严格，任何显著蹭地均令本项目 stable=false；上游可能用不同的膝地间隙、接触持续时间或碰撞容忍标准。
- `brake_ok`：上节的连续 0.5 s 安静条件。这个定义不同于上游 `speed-evaluation.json` 的 `brake`，后者还使用速度相关的刹车距离/时间门槛，例如 0.30 m/s 约 `0.1625 m` 与 `2.5 s`。
- `fixed_exit_ok`：退出后的 2 s 尾段四足腿最大目标误差 `<0.18 rad`，平均水平速度 `<0.025 m/s`、偏航 `<0.06 rad/s`、水平速度 p95 `<0.025 m/s`。`0.18 rad` 是**本项目复演器的验收阈值**，不是同事训练或交付包的定义，也不是宇树官方推荐值。
- `passed` 仅当上述 tracking、stable、brake、fixed exit **同时**为真。这里的 `0/3` 完整通过率不能与上游的 `2/4` 跟踪+刹车或 `1/4` 站姿保持直接比较。

地面接触计算只统计与 ground 相碰的 body，将四个 wheel body 接触列为轮载荷，其余 body 的地面法向力记作 `peak_nonwheel_n`；这包括膝/小腿/其他非轮结构。需要同事核对 MuJoCo geom→body 分类与其评估的 `knee_surface` / `nonwheel_frames` 是否同义。

## 6. 实测初态九条结果

| 命令 | 跟踪 | 达到安静刹车条件 | 本项目 `stable` | 回 T2 固定站姿 | 关键现象 |
|---|---:|---:|---:|---:|---|
| 0 | 3/3 | 3/3 | 3/3 | 0/3 | 最后腿角误差约 0.19–0.20 rad，仅略高于本项目 0.18 门槛；非轮接触 0 N |
| +0.30 m/s | 3/3 | 3/3 | 0/3 | 0/3 | 三次非轮接触峰约 63.5/75.5/98.9 N；Brake 位移约 0.095–0.113 m；最终腿角误差约 0.41–0.46 rad |
| −0.30 m/s | 3/3 | 3/3 | 1/3 | 0/3 | 两次非轮接触峰约 71.6/93.4 N；Brake 位移约 0.002–0.127 m；最终腿角误差约 0.25–0.34 rad |

这些九条均属于**一组诊断样本**，不是可靠的成功率估计，也不能推断真实狗会有同等接触力。上游 zip 自带的 0.30 m/s 测试另有一次前进刹车 9.16 s / 1.54 m 的长尾，本项目九条没有复现该长尾；不能用九条“brake_ok 3/3”排除其存在。

## 7. 请同事重点对齐的问题

1. R1199 实际部署期 65 维观测（尤其 `height_constant`、投影重力符号、相位周期、零命令轮角记忆）能否用一段**相同输入帧**与本脚本逐项打印比对？建议给 10–100 帧 reference trace，不只给 ONNX parity。
2. 同事评估的腿/轮 `kp,kd`、执行器饱和、物理子步、质量/惯量、摩擦、推扰分布、种子与本脚本有何差别？尤其本脚本腿 `55/2`、轮 `kd=2` 是否适用于 R1199。
3. R1199 的 `precalibrated_stand`、wheel hold、parking odometry、brake supervisor 如何逐帧工作？我的脚本只复用旧版近似，建议双方对同一初态/同一动作序列导出最终腿位置与轮速目标时间序列，再比较第一处分歧。
4. 上游 `speed-evaluation.json` 的 `hold` 是在何时、对哪个目标与多长时间验收？本脚本 `fixed_exit_ok` 用 T2 腿误差 0.18 rad。两边的“最后站稳”不是自动同义。
5. 上游是否将膝/小腿地面接触视为失败？阈值是峰值、持续时间、膝部间隙还是综合规则？请提供前进/倒退失败回合的接触部位、峰值、持续时间和运动阶段。
6. 最关心的“松杆停车”：在相同 `+0.30→0` 与 `−0.30→0` 输入下，报告每回合停车时间、停车位移、轮速/机身速度持续曲线，以及前进 1.54 m 长尾的最早偏离点。单个 `brake=true` 不足以判断极端情况。

目前可直接对齐的只有资产 SHA、ONNX 形状、基础 `rolling_fixed_exit()` 公式以及部分观测字段；**完成逐帧观测/动作 parity 与状态切换/物理设置对齐前，独立复演应被称为诊断，不应当作为上游模型的最终 MuJoCo 验收或真机失败概率。**
