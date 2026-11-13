# S1 移植对齐（parity）+ S2 sim2sim

全部在 caolin 服务器；只读项目目录 + `/tmp/opencode/` 缓存。

## S1 移植对齐

**什么是"离线 parity"**：拿同事包里录好的传感器数据当输入带子，同一段分别过"训练方参考实现"和"我们的移植"，逐帧比对每一步输出（obs → ONNX raw → 包装动作 → 最终 16 轴目标），全部 ≤1e-6 才算理解无误。"离线" = 不碰狗不碰 DDS 纯回放——它证明的是"我们实现的合同 == 他们训练时的实现"，这是上狗前必须闭卷对过的答案。

**目标**：用 Python 复现"观测→ONNX→包装→最终目标"全链，与同事包里的回放数据逐帧一致（≤1e-6），证明移植理解无错。

1. **写 obs/动作构建函数**（照 `runtime/` 合同逐维实现）。范例：
   - mlp57：`部署参考/as2w-flat-rerun/mlp57_mujoco_eval.py` 里的 obs 构建（57 维，含四维补零）
   - R1199：`部署参考/cpp_deploy-as2w/tools/r1199_training_forward_parity.py`（65 维，含 vx−0.4 偏移、上一动作存包装后值）
2. **逐帧比对**：加载 `simulation/native_replay/native_samples.npz`（600帧×10例真实状态），对每帧算我的 obs/目标，与录制的 `observation/raw_action/q_des` 比最大误差。报告：obs 误差、ONNX 误差、目标误差、最差帧。
3. **过门槛**：全部 ≤1e-6（数据精度内）。不达 → 定位第一处分歧再修，不要调参硬凑。

### 已知坑（两家策略实际踩过的，新策略逐项核对）

| 坑 | 说明 | 案例 |
|---|---|---|
| **轮位槽补零** | 关节位置观测的 4 个轮槽必须填 0，不能填轮角；迁移时最容易漏 | mlp57 obs[21:25]；同事 B2W MuJoCo 适配器漏了 → 1.72s 失稳 |
| **重力符号** | R1199: −Rᵀ[0,0,−1] 站立 z=+1；mlp57: Rᵀ[0,0,−1] 站立 z=−1。**相反** | 两家 |
| **上一动作** | R1199 回填**包装后**动作；mlp57 回填 **raw** ONNX 输出 | 两家 |
| **命令偏移** | R1199 观测 vx−0.4 技巧；mlp57 直接物理量 | R1199 历史上填错观测历史曾致仿真误判 |
| **关节序** | 策略序(FR-first 按腿) ≠ LowState DDS 槽位序(FL-first 按类型)；映射表在 `config/r152_measured.map` + `AS2W_16轴DDS关节序速查.md` | 全部 |
| **PD 逐子步重算** | Isaac 执行器 PD 每个物理子步(5ms)重算（目标保持、力矩刷新）；50Hz 力矩保持 + 小 kd 会轮速发散。**自定义力矩路径必须复刻此语义**（真机走 FOC 驱动器闭环则无此问题） | mlp57（帧0轮力矩 +0.077 为末子步刹车值可证） |
| **轮向** | 轴 [0,1,0] 正转=前进（轮半径 0.086 换算核对） | mlp57 forward +6.5rad/s ↔ +0.5m/s |
| **速度包络** | deploy.yaml 的 vx_limit/wz_limit（0.01–0.30），MuJoCo 新速度档必须先复验再上机 | R1199 0.2/0.1 |

## S2 sim2sim（第二仿真器闭环）

**目标**：在我们 MuJoCo 平台复现他们的正式验收（同命令矩阵、同初态、同判据），证明策略跨引擎可用。

### 平台（caolin 服务器）

- MuJoCo 模型：`/tmp/opencode/omni/assets`（官方 URDF 同源 flat 模型，26kg，轮盘位置与 STL 一致）。缓存丢失时从 `部署参考/` 的 omni 线交付重建。
- 范例评估器：
  - **mlp57**（157 例矩阵复现型）：`部署参考/as2w-flat-rerun/mlp57_mujoco_eval.py` —— 复现他们 39命令×4初态（含 `np.random.default_rng(81200+r)` 精确初态）、12s 时序（2零速+8运动+2停车）、五项判据（fall/velocity/stop/posture/contact）。
  - **R1199**（训练开关对照型）：`部署参考/as2w-flat-rerun/r1199_colleague_eval_ablation.py` —— 实测 FixedStand 初态注入、训练合同开关组合、前进/后退/转向多种子。
- PYTHONPATH：`/tmp/opencode/r1199_eval_work:/tmp/opencode/omni/runtime`（训练快照 + omni 运行时缓存）。

### 关键前置判断：轮控性质（决定 sim2sim 成败）

- **主动轮控**（停车时轮速=强反馈，如 R1199 的 `-6×error/16`）→ MuJoCo 通常能过。
- **被动静摩擦**（低速稳定完全靠地面摩擦顶住轮子，如 mlp57）→ **MuJoCo 大概率失败**：软化摩擦约束对 0.6kg 轻轮给不出"锁死"（单元测试：57N/μ=1/1Nm 下 PhysX 锁死 vs MuJoCo 爬 1.5-2.3rad/s）。失败不是移植错误——按 v3 合同 R2 记未通过，分流给训练侧（选项：出主动轮控包装版 / 他们自跑第二仿真器 / 换引擎），**不要无限调接触参数**（solref/impratio/noslip/solimp/积分器已全试过无效）。

### 判据与记录

- 用他们包里的判据定义（mlp57 在 `source/evaluation_project/scripts/speed_sweep_native.py` 的 criteria 字段；阈值勿自造）。
- 每次运行输出逐例 CSV + 汇总 JSON 到 `部署测试/04_调试记录/logs/<policy>_sim2sim_<日期>/`。
- 结果写 INDEX；失败附根因分析（范例：`logs/mlp57_2700_sim2sim_debug/README.md`）。

## 过/不过的处理

- **过** → 进 S3（C++ 适配）。
- **不过且根因在引擎保真**（如静摩擦）→ 不绑实机；给训练侧一页纸反馈（范例：`部署测试/06_训练协作/mlp57_mujoco_sim2sim_failure_analysis_20261112.md`）。
- **不过且根因在策略本身**（同引擎也崩、或多引擎一致崩）→ 退回训练侧，附回放夹具。
