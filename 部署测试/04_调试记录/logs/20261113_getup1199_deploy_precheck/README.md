# 2026-11-13 起身策略 getup1199（deep-side model_1199）实机部署前置验证

对象：`runs/recovery/deep-side-curriculum/formal/model_1199.pt`（SHA 4fe19b8e…）
+ ONNX `onnx/deep-side-1199/policy.onnx`（970e692e…，obs 42 / act 12 / 20ms / clip 2.0）。
评估器：训练方 `eval_as2w_mujoco_recovery.py` 打补丁副本（`eval_recovery_patched.py`：
可调 EFFORT_FRACTION / START_CLIP，新增目标步进、dq、轮角、逐帧轨迹记录；
默认参数下与原版行为一致）。所有结果原始 JSON 在 `run_*/diagnostic.json`。

## 实验 1：真实趴姿提取与对比（field_sessions/20261113-114335_r4000 尾段）

- 实机 Y 趴姿（policy 序，hip 已乘 −1）：
  hips[−0.535,0.549,−0.552,0.581] thighs[1.009,1.011,0.993,1.010] calves[−2.768,−2.758,−2.755,−2.727]
  高度（MuJoCo settle 探测）0.215m，姿态水平。
- 训练 prone 姿态库（supported-getup-holdout）：hips≈0、thighs 2.43–2.88、calves −1.48~−1.72、
  高度 0.06–0.08（躯干平贴地面）。
- **结论：实机自然 Y 趴姿与训练 prone 分布完全不同，且 calf −2.77 超出策略 90% 包络
  （下界 −2.546）甚至超出仿真 URDF 限位（−2.651，证明 URDF 未按硬件标定）。
  直接从 Y 趴姿触发起身 = 超合同入口。**

## 实验 2：入口消融（8 起始姿态 × 5 种子 × 8 配置）

| 配置 | pass/40 | 起身失败 | 说明 |
|---|---|---|---|
| A1 姿态库prone+守卫 | 24/40 | 0 | 起身 40/40 |
| A2 姿态库prone无守卫 | 24/40 | 0 | **守卫零影响** |
| C1 预趴姿(库中位)+守卫 | 24/40 | 0 | FixProne 目标可用 |
| C2 预趴姿无守卫 | 24/40 | 0 | 守卫零影响 |
| B1 实机Y趴姿(URDF包络)+守卫 | **0/40** | 40 | **全部 joint_angle @ t=0：起始姿态违反 90% 包络被安全层拒绝** |
| B3 同上无守卫 | 0/40 | 40 | 同（守卫不是原因） |
| B2 实机Y趴姿(裁剪入包络)+守卫 | 24/40 | 0 | 裁剪后（calf−2.43）可起，但非真实入口 |
| D1 姿态库+effort 0.80 | 24/40 | 0 | **力矩预算 −11% 零影响** |

- 24/40 的失败全部是末段静止门（推扰落在 9.8–10.9s + 试验 11s 截止），起身本身 40/40。
- 预趴姿（FixProne 目标）与姿态库等价：100% 起身。

## 实验 3：FixProne 过渡预演（A 键动作，crouch→prone，kp55/kd2，6s smoothstep）

- 3 种子：终点误差 ≤0.083 rad、姿态水平（up≈1.0）、终点高度 0.063m（平贴），
  过程接触峰 650–911N（躯干落地瞬态，与原厂趴下量级相当），轮角保持。
- FixProne 目标（policy 序）= hips[0.035,−0.065,0.048,−0.007]
  thighs[2.689,2.656,2.663,2.703] calves[−1.702,−1.581,−1.687,−1.698]。

## 实验 4：部署安全阈值实测（16 例预趴姿起身，50Hz 逐帧）

| 量 | 仿真实测 | 现行行走档 warn/hard（5连/3连触发） | 判定 |
|---|---|---|---|
| 腿目标步进 | max 0.61，>0.2 最长连续 **6** 帧，>0.35 最长 2 帧 | 0.20 / 0.35 | **warn 会误触发（6≥5）→ 需 getup 档** |
| 腿 dq | max 6.5，>5 最长连续 3 | 5 / 8 | 不触发 |
| 腿 tau | max **37.2Nm**，>35 最长 1 帧 | 35 / 50 | 不触发（远低于 R284 事故 73.4） |
| 轮 | 位置保持漂移 ≤0.1rad，短暂触自身 12.15Nm 剪幅（设计内） | 8/12 | 通过 |

- **腿力矩峰值仅 37.2Nm**（此前 max_effort_ratio=1.0 来自轮瞬态触自身剪幅，非腿需求），
  腿力矩余量充足；effort 0.8 消融亦通过。
- getup 建议安全档：leg_target_step warn 0.35 / hard 0.75；其余沿用现行档。

## 判定

1. 趴地姿势必须改变：部署需 A=FixProne（crouch→prone 慢插值，仿真已验证）后再 B 触发；
   B 入口检查 90% 包络，Y 趴姿直接按 B 会被拒绝（安全层正确行为）。
2. 安全层对成功率的影响：训练侧（预测守卫/90% 限幅，属合同必须保留）= 零；
   部署侧监控现行档位中仅步进 warn 会误杀，getup 专用档只需调整步进阈值。
3. 从预趴姿起身：仿真 40/40 起身；严格门 60% 的失败全为末段推扰时序，
   首次有界实机测试无推扰。

## 实验 5（补充诊断）：真实 Y 趴姿直接输入能否起身（回答"不用中间态行不行"）

- 修正实验 2 中 B1 的误导：B1 的 0/40 是安全审计在 t=0 判入口超包络即终止，策略从未运行。
- 本实验用模型关节范围（calf 下界 −2.7677，可基本表达真实 −2.77）+ 仅放开入口包络检查，
  命令仍剪 90% 包络（= 实机若只放开入口检查的实际行为）：
  **33/40 起身（82.5%）、28/40 完整通过、90% 包络 0.06–0.07s 内自动回归**；
  另 7/40 为起始膝贴死 −2.768 硬限位被 t=0.01s 物理限位审计拦下（策略未运行，边界伪影；
  真实 Y 趴姿正处该贴限位状态）。33 例成功者最长站稳窗口 4.0–6.7s。
- **结论：策略本身不怕真实蹲伏趴姿（能力 33/33 非贴限位起步全起）；"必须中间态"的本质
  是合同问题（入口超 90% 包络 + 膝压死硬限位），不是能力问题。**

## 实验 6（补充）：FixCrouch-lite 开膝中间态预演（比 FixProne 轻得多的方案 A'）

- 动作：2.5s smoothstep，仅小腿 −2.77→−2.43、髋收 ±0.50、大腿保持；轮位置不动。
- 3 种子：接触峰 69–73N（无躯干冲击，对比 FixProne 650–911N）、机身抬升 3cm、
  姿态水平、**终点 12 关节全部回到 90% 包络内**。
- 随后从该姿态起身 = 实验 2 的 B2 配置：40/40 起身、24/40 完整通过。
- 方案更新：v1 首选 A=FixCrouch-lite（最小动作）；FixProne 为备选（入口完全在训练分布内）。
- 证据文件：`crouch_direct_diagnostic.json`、`fixcrouch_lite_probe.json`、
  `eval_recovery_crouchdiag.py`。

## 实验 7（S3 起步）：C++ 控制器移植 + 三层 parity（2026-11-13 下午）

- 新建唯一源码线 `deploy/robots/as2w/getup1199/`（controller.hpp/cpp、replay、CMake 默认 OFF）
  + `models/getup1199/{deploy.yaml, policy.onnx}`（ONNX SHA `970e692e…ea971`），
  根 CMakeLists 加 `AS2W_GETUP1199` 选项。x86 镜像构建（`/tmp/opencode/r214_zero_b/b-getup1199`，ORT 1.22）零告警。
- **修过的移植 bug**（过程记录）：① checked_model 悬垂临时（ORT Unowned 视图）；
  ② staged 斜坡语义（yaml 存 [起点,时长]，初版误按 [起,止] 计算，extend 反向为 1 → prior 清零）。
- **三层 parity（夹具=干净传感器通道、部署估计门、预趴姿 seed 9001 起身全程 550 帧）**：
  1. obs→ONNX→staged→clip 逐帧 oracle（python 训练实现重放 C++ 自己的 obs/blend 时间线）：
     **max 1.55e-6/帧 PASS**（残差=torch vs ORT fp32 基线）；
  2. 闭环全带重放（`parity_getup1199.py`）：action max 4.4e-2——根因=ONNX fp32（训练方自身
     ONNX-vs-PT parity 1.9e-6 同源）经 previous-action 反馈放大 + ≤1 帧门边界翻转（fp64/py vs fp32/C++ 阈值比较）；
  3. 功能等价：估计门版 python 闭环 40/40 起身、24/40 严格门与真值门基线完全一致（实验 5/估计器验证）。
- 采纳判据：oracle ≤2e-6（PASS 1.55e-6）+ 闭环差异 ≤5e-2 且根因书面归档 + 功能等价证据。
- 服务器注意：`from_xml_path` 从 SSHFS 读资产在本机高负载时可达 109s（其他用户 32768-env 训练占用）；
  评估一律用本地拷贝 `/tmp/opencode/as2w_s2_check/assets_local`。
- 复现：`run_gen_est.py` 生成夹具（本地资产）；`as2w_getup1199_replay deploy.yaml fixture` →
  `parity_getup1199.py expected replay_out`；`oracle_test.py` 逐帧 oracle。
- **未完成**：共享发布端 `AS2W_POLICY_GETUP1199` 分支（FixCrouchLite/PolicyGetup 状态、getup 安全档
  步进 warn 0.35/hard 0.75、入口/成功门）、会话脚本、Windows 注册、ARM64/CPRO 同步、
  CTest/offline-audit（依赖发布端分支）。

## 实验 8（S3 完成）：发布端 getup 分支 + 双端回归（2026-11-13 晚）

- `common/as2w_publish.cpp` 新增 `AS2W_POLICY_GETUP1199` 分支（单键链落地）：
  State 追加 FixCrouchLite/PolicyGetup；B=入口门（趴姿 FK 高度/水平度/轮静默）→开膝 2.5s
  smoothstep（kp55/kd2+轮位置保持）→包络复检→PolicyGetup（控制器 50Hz 步进+成功门
  h_est/up/关节误差/gyro/轮静默持续 2s）→FixedStand 保持（姿态=策略末目标，沿 Brake 先例）
  →Y/超时趴下；15s 上限→Passive；A 在 getup 构建禁用；一个会话仅一次 B 链。
- getup 安全档仅改腿目标步进（warn 0.35/hard 0.75，来自实验 4 实测）；dq/tau 档沿用。
- `fill_targets` 轮位置模式扩展：kp!=0 的轮走位置保持（所有行走状态 kp=0 不受影响）。
- 控制器改名 LegCount→LegAxisCount（与发布端本地常量 `using namespace` 冲突）、
  增加共享发布端 3 参 step 重载（getup 无速度命令，非零命令防御性解除）。
- **过程事故（已修）**：staged 斜坡 [起点,时长] 语义修复当时误写在镜像副本上，未回写工作区，
  后续工作区→镜像同步把 bug 又带了回来（干净构建复现后定位）。教训：**编辑只发生在工作区，
  镜像永远从工作区单向同步**（AGENTS 既定规则，本条为实际违反后的复盘）。
- 验证：getup 构建 CTest 8/8（含 `getup1199-startup-audit` AUDIT PASS）；**回归构建
  （R214+R4000 候选）CTest 8/8 全过**——共享文件改动不破坏行走线；闭环 parity 4.4e-2
  （根因已归档）+ **oracle 1.552e-6 PASS**（`oracle_test.py` 对最终二进制）。
- 证据：`getup1199_replay_final.txt`；构建目录 `/tmp/opencode/getup1199_build/{b,b-regress}`。
- **剩余 S3 项**：会话三件套（run_getup1199_field_session.sh / trial 启动器 /
  Windows 注册 +ConfirmMotion）、准备现场包.ps1 重打包、CPRO 同步与 ARM64 构建/CTest/audit/SHA。
