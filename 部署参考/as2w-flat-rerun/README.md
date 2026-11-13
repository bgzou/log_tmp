# AS2-W 平地 MuJoCo 复测（stairs 权重平地能力验证）

日期：2026-11-09。执行环境：服务器 192.168.10.163（OpenCode），Ubuntu 24.04，Python 3.12.3，
MuJoCo 3.17.0（pip `--user --break-system-packages`），NumPy 1.26.4。无 torch/onnxruntime——actor
直接按 `cpp_deploy-as2w/src/policy.cpp` 定义的 `AS2WMLP1` 二进制格式从交付 `.bin` 解析（58→128→128→128→16，
隐藏层 ELU，输出线性）。

## 结论（一句话）

**三份交付爬楼权重在 MuJoCo 平地均能稳定行走（96/96 试次全程直立，含动力学应力），"爬楼权重可能平地能走"由假设升级为仿真验证事实；stairs-r17-3000 表现最好。**

## 资产来源（全部可追溯）

| 文件 | 来源 | 校验 |
| --- | --- | --- |
| `assets/as2w_flat.xml` | GitHub `YuTaoV5/Rob2Nav` main 分支 `deliveries/as2w-deploy/omni-blind-stairs/assets/local-step-diagnostic/as2w_flat.xml` | SHA-256 `2bf148d8e0e5722db4a581c7cf7834611121025cc1c95c14f892b83bc0fdfa01` |
| `assets/fall-recovery-contract.json` | 同上 `.../assets/fall-baseline/fall-recovery-contract.json` | SHA-256 `1e4e3fb76806e83dbe3541979fa0cb40f4b3150f5bf4de298224bf9baa9b0490` |
| 机器人 meshes/URDF | 工作站 `部署参考/unitree_ros`（HEAD `41dec58`，其 `robots/as2w_description` 与 omni 交付固定的 `4005a1b` 完全一致，`git diff` 为空） | - |
| 权重 | 工作站 `部署参考/as2w-deploy/models/*.bin` | SHA-256 与 manifest 逐一致 |

注意：工作站交付（Rob2Nav rev `e61aaf79`）本身**不含** MuJoCo 模型与 contract；两者取自 main 分支较新的
`omni-blind-stairs` 交付资产（R21 全向候选是另一代模型，本次未评估）。训练归档 `as2w-results`（含 `.pt`）
仍未获得；`.pt` 对本复测非必需。

## 脚本

`flat_stairs_rerun.py`（本目录）三个模式，语义逐行对齐交付 `mujoco_screen.py::evaluate()`（rev `e61aaf79`）：

1. `recovery-validate`：复现交付平地恢复筛选（4 姿态 × 种子 12001–12004）。
2. `flat-stairs`：**新协议**——平地 + 楼梯观测语义（command 固定 0.4、线速度槽置零、tick 0 即激活、
   9 s 窗口、楼梯式初始扰动 ±0.12 rad、0.37 m 起始高度、轮角 4π 回绕、动作 ±6 限幅、
   腿 `default+0.35a` 位置 PD 55/2、轮 `16a` 速度 PD 0/2、URDF 限位钳制）。
   "stable walk" 判据（自定，区别于恢复的站立判据）：直立 ≥20° ∧ 高度 ≥0.25 m ∧ 四轮最小接地 ≥8 N ∧
   无非轮触地 ∧ |ω| ≤1.0 rad/s。**去掉了站立判据的 |v|≤0.2 m/s 限速**（行走必然超）。
3. `stairs-crosscheck`：复现交付楼梯场景（5 级、seeded 踏步 6/8/10 cm × 31/35/39 cm、动力学应力）与
   其通过判据（依序到达 5 级 ∧ 顶部支撑 ≥0.5 s ∧ 峰值冲击 <50 N）。

复现命令（在含 `local-step-diagnostic/`、`fall-baseline/`、`models/` 的目录）：

```sh
python3 flat_stairs_rerun.py --mode recovery-validate --models recovery-r12 --seeds 4 --out validate.json
python3 flat_stairs_rerun.py --mode flat-stairs --models stairs-r14 stairs-r17-2000 stairs-r17-3000 \
    --seeds 16 --stress both --out flat.json
python3 flat_stairs_rerun.py --mode stairs-crosscheck --models stairs-r14 stairs-r17-2000 stairs-r17-3000 \
    --seeds 16 --stress on --out stairs.json
```

## 框架有效性验证（三条锚点）

1. **恢复平地**：recovery-r12 复跑 16/16 通过，交付 torch 参考亦 16/16（C++ native 15/16）；
   边缘种子 right/12002 我方 1.060 s vs 交付 native 0.98 s（阈值 1.0 s 两侧抖动，浮点/版本差异量级）。
   姿态难度排序（belly 最易、left/right 最难）与失败计数分布定性一致。
2. **楼梯场景**：三份权重均 0/16，与交付一致；48 种子中 39 个 `visited_levels` 完全一致，
   其余 ±1 级且全部处于 0–2 级失败区间；逐种子前进距离吻合（如 r17-3000/27001 双方均到第 2 级）。
   少数混沌接触种子的峰值冲击数值差异大（如 843 vs 92 N），系接触混沌对微小浮点差的放大，不影响判定。
3. **`.bin` 解析**：defaults 与 contract 完全一致（hip 0 / thigh 0.8 / calf −1.6 / 轮 0），
   文件无截断无尾字节，SHA-256 与 manifest 一致。

## 平地结果（seeds 27001–27016，各 16 试次 × {nominal, stress}）

| 权重 | 条件 | 直立率 | 平均速度 | 9 s 前进 | 稳走占比 | 横向漂移 mean/max | 动作限幅 | URDF 超速 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| stairs-r14 | nominal | 1.00 | 0.590 m/s | 5.27 m | 0.34 | 0.155 / 0.388 m | 0 | 0 |
| stairs-r14 | stress | 1.00 | 0.584 m/s | 5.18 m | 0.35 | 0.152 / 0.332 m | 0 | 0 |
| stairs-r17-2000 | nominal | 1.00 | 0.472 m/s | 4.10 m | 0.43 | 0.335 / 0.706 m | 0 | 0 |
| stairs-r17-2000 | stress | 1.00 | 0.476 m/s | 4.10 m | 0.43 | 0.349 / 0.862 m | 0 | 0 |
| stairs-r17-3000 | nominal | 1.00 | **0.400 m/s** | 3.41 m | **0.58** | 0.338 / 0.814 m | 0 | 0 |
| stairs-r17-3000 | stress | 1.00 | **0.400 m/s** | 3.37 m | 0.54 | 0.349 / 1.069 m | 0 | 0 |

- 理想前进距离 = 0.4 m/s × 9 s = 3.6 m。r17-3000 与指令几乎精确吻合；r14 超速 47% 且重心更低
  （r14 直立时高度 ≥0.29 m 的 tick 有欠账，r17-2000/3000 无）。
- stress = 摩擦 0.45–0.95、质量 ±10%、增益 ±15%、2.8–4.5 s 推扰 ±0.15 m/s——指标几乎不变。
- 前轮驱动特征：r14 末端轮速 FL/FR 明显高于 RL/RR；r17-3000 四轮较均衡。
- 已知局限：**无航向反馈的横向漂移**（盲走本性），r17-3000 最坏 1.07 m；交付框架有实验性
  `--stair-gyro-heading-gain` 航向修正选项可后续研究。

## 与"权重选择"的关系

若进入只读影子/后续受控平地验证，**首选 stairs-r17-3000**（速度跟踪最准、步态最稳、站姿最高），
次选 r17-2000。此结论仅为 MuJoCo 平地仿真，不代表真机；真机门槛仍按 `hardware_contract.md` 执行。

## 原始数据

`results/validate_recovery-r12.json`、`results/flat_stairs_all.json`（96 行逐试次全指标）、
`results/stairs_crosscheck_all.json`（48 行）。总账条目见
`部署测试/04_调试记录/INDEX.md` 2026-11-09 11:2x 节。
