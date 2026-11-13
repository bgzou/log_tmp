# 2026-11-13 Rob2Nav as2w-backup 三条最新权重 S0/S1/S2 离线验收

来源：用户 2026-11-13 将 GitHub `YuTaoV5/Rob2Nav`（main, commit `2de96cba…`）pull 至
`部署参考/Rob2Nav-as2w-backup/`。本次对象为该快照内三个场景的最新完整权重
（与上午已实机的 R4000/rolling-4000-stage020-research 交付包相互独立）：

| 场景 | 权重 | SHA256 | ONNX (SHA256) |
|---|---|---|---|
| rolling | `runs/rolling/actor-wheel-saturation-loss.Uliv0s/baseline/train/model_1200.pt` | `a5e79209…de0c9` | `v3-evidence/policy.onnx` (`d047a83e…08d4b`) |
| stepping | `runs/stepping/support-aware-reward.bp4984/formal/model_1199.pt` | `57af5130…d611` | `onnx-diagnostic/support-aware-1199/policy.onnx` (`b3e46280…14cb2`) |
| recovery | `runs/recovery/deep-side-curriculum/formal/model_1199.pt` | `4fe19b8e…f5aa7` | `onnx/deep-side-1199/policy.onnx` (`970e692e…ea971`) |

环境：caolin 服务器（MuJoCo 3.17.0 / ORT 1.31.1 / torch 2.15.0+cpu / numpy 1.26.4；
训练方为 MuJoCo 3.2.3 / ORT 1.23.2 / torch 2.11.0+cu130）。评估器、资产
（`assets/r237-train-root`）、姿态库全部取自快照原样；命令行与训练方 run-evaluation.sh /
mujoco.sh 一致。脚本与原始输出见本目录。

## S0 收包（快照不是 v3 交付包）

- 三份 v3-evidence manifest 自评：`scope=research diagnostic`，C7 双仿真正式验收
  `not_run`、ARM64 shadow `not_run`、实机闭环 `not_run`。
- rolling 两个 4000-iter 训练（actor-wheel-saturation、filtered-4000）只归档了
  model_1000/model_1200 中间检查点；服务器脚本评估的 model_3999（终版）未入库。
  filtered-4000 的终版 model_3999 已由上午 R4000 交付包另行验收+实机。
- 无 v3 包结构（checks/verify_package.py、runtime/observations.csv、joints.csv、
  effective_runtime.yaml、entry_exit.md 缺）；合同信息散在各 run 的 contract.json。
- 三份权重/ONNX SHA256 本机复核全部与合同一致。

## S1 ONNX↔检查点 parity（本机）

- rolling：ORT(policy.onnx) vs 录制 actor-preclip.npy，1512 帧 max err `5.96e-07`
  （与训练方记录一致）。
- stepping：真实观测 4524 帧（本机 S2 产生）max err `1.86e-05`（训练方记录 4.6e-06）。
- recovery：真实观测 1351 帧 max err `5.13e-06`（训练方记录 1.9e-06）。
- 误差为 fp32 导出量级；C++ 移植后的全链 parity（obs 构造→包装→目标）未做
  （未见 q_des 夹具，rolling v3-evidence 仅含 obs+preclip）。

## S2 闭环 MuJoCo（同训练方判据/种子）

### rolling (actor-wheel-saturation model_1200, 0.20 m/s 档, 72 例)
- 速度跟踪优秀：forward 0.192–0.195/0.20、back −0.196~−0.209、turn 实际 0.080–0.094
  （命令 0.12，约 75%——与 R1199/R4000 已知转向弱一致）。
- stable 71/72：仅 1 例 back 触发 knee_surface（safety_gate=false）；非轮触地 0/72、
  角度/站立违规 0、力矩比 ≤0.54。
- 完整 gate=false 12/72（forward 5、back 0、turn_l 1、turn_r 2、arc_l 3、arc_r 1）；
  失败集中在驻停保持：漂移 2.0–3.7cm（门限 2cm）/速度 p95 最高 0.038（门限 0.02）。
- 结论：中间检查点 model_1200 未过 S2 门槛；转向弱+驻停漂移与 R1199/R4000 同源。

### stepping (support-aware-reward model_1199, 12 案例 × 8, seed 8302)
- **0/96 全失败**，与训练方归档 holdout 完全一致。失败模式：stance（后腿 thigh 超出
  [0.18,1.40] 或轮距交叉）70 例、nonwheel_contact（小腿触地）24 例、tilt 4、
  joint_angle 4、未动 6。运动段机身高度中位 0.35m，前进进度约 0（命令 0.1 m/s）。
- 该检查点为研究中继（后续 support-and-stance 25-iter 诊断分支从它续训），
  **不可作为踏步交付候选**。

### recovery (deep-side model_1199, 5 组 × 4 族)
| 组 | prone | left | right | near_stand |
|---|---|---|---|---|
| random seed 7301（复现训练方） | 4/8 | 4/8 | 4/8 | 7/8 |
| random seed 7401 | 7/8 | 3/8 | 3/8 | 7/8 |
| random seed 7402 | 8/8 | 8/8 | 8/8 | 8/8 |
| shallow bank 7301 | 4/8 | 4/8 | 4/8 | 8/8 |
| side bank 7301 | 4/8 | 5/8 | 6/8 | 8/8 |
| **合计** | **31/48=64.6%** | 24/40=60% | 25/40=62.5% | 38/40=95% |

- **平地趴地起身（prone）：起身本身 48/48 全成功**——全部站立(高≈0.378m)、四轮支撑、
  无翻倒/无非轮触地/无角度力矩违规；17 例"失败"全部是末段静止门：随机推扰落在
  9.8–10.9s（试验 11s 截止），残余速度 0.06–0.075 m/s 未收敛到 <0.06，非起身失败。
- 侧倾起身（left/right，roll 0.38–0.96 rad 非倒置侧倾）：14/40 真翻倒（up_z≈−0.10，
  起身过程翻成仰面）+12/40 末段未静止；种子间波动大（7402 全过、7301/7401 过半）。
- near_stand 扰动恢复 95%（失败均为末段静止门）。
- 判据细节：pass = survived(无翻倒/超限/起身后非轮触地) + 末段 2s 全门
  (h≥0.31, up≥0.95, 四轮载>2N, 无非轮触地, 关节误差<0.18, 线速<0.06, 角速度<0.12)
  + 膝面净空。

## 判定与建议

1. **stepping model_1199：S2 不过（0/96），禁止实机**；退训练侧。
2. **rolling actor-wheel-saturation model_1200：S2 不过**（gate 12/72、safety 1 例膝面）。
   且终版 model_3999 未入库无法验收；已实机的 R4000（filtered-4000 终版）在直行
   平滑度/速度跟踪上更优。rolling 线继续实机应沿用 R4000，不引入本检查点。
3. **recovery deep-side model_1199：平地趴地起身仿真可用**（起身 48/48、推扰后可
   重新站稳），侧倾起身不可靠（60–65%）。如进入实机须注意：
   - 全新接口（obs 42 维/actions 12 维腿；轮不在动作内，运行时轮位置保持 0，
     腿 kp85/kd3.2，staged-rise/stand-integral/low-support-handoff/predictive-guard
     包装链需完整 C++ 移植=新 rXXX 线）；
   - 起身是大幅全身动作+允许起身期躯干触地，实机风险量级高于行走；
   - 实机范围若只做"趴地→起身→站稳"（不做侧倾起身）与仿真证据域一致；
   - 侧倾起身需训练侧改进（翻倒集中在深侧倾）。
4. 三份权重均为 simulation candidates / research diagnostic（训练方 AGENTS/manifest
   自述），任何实机动作仍须逐次现场当次明确同意。

## 复现命令

见 `run_s2.sh`（7 个并行运行）与 `parity_check.py`/`parity_part2.py`；
原始输出在 `s2_outputs/`。

## 追加（2026-11-13 下午）：rolling 深入对照与轮饱和发现

1. **R4000 终版 model_3999 本机复跑**（`s2_outputs/rolling_3999_rerun/`，同评估器/协议/种子）：
   gate=false、safety_gate=true、总 pass 18/72、held 38/72、非轮触地 0、膝面 0
   （训练方归档 27/72，跨 MuJoCo 版本差异，结论一致）。
2. **轮饱和同条件对照**：同一批 4536 帧闭环观测分别过两个 actor——
   R4000 model_3999 轮输出 **100% 帧饱和于 ±6**（16×a=96 rad/s 上限，四轮全饱和）；
   actor-wheel-saturation **model_1200 饱和 0%**，max|a|=1.23（≈19.6 rad/s）。
   该 loss（权重 0.025、margin 0.9）为训练方针对 R4000 实机轮残差 100% 饱和问题的
   修复实验；其归档对照文档（`Rob2Nav-rolling-4000-stage020-research/evidence/
   rolling-4000-checkpoint-comparison.md`）自证：250 轮即饱和 100%→0%，但
   "低速驻停或转向完整通过的提升尚无证据"。
3. 结论修正：model_1200 的 MuJoCo 综合表现仍不如 R4000 终版（18/72 vs 12/72、
   held 38 vs 31、1 例膝面违规 vs 0），且为 4000 轮训练的中间检查点（终版
   model_3999 未归档）；轮去饱和是实质改进但未转化为门槛指标提升。不建议用
   model_1200 上实机；建议向训练方索要 actor-wheel-saturation run 的终版
   model_3999 及其服务器验收证据后再做同条件对照。
