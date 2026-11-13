# 2026-11-09 OpenCode 会话：stairs 权重 MuJoCo 平地复测（服务器侧）

- 执行者：服务器 192.168.10.163 上的 OpenCode（caolin），经 SSHFS 使用工作站
  `D:\Projects\Athena\运动控制\Collie\AS2-W_CPRO`（挂载点 `/home/caolin/as2w_workstation`，
  `mountpoint` 校验通过）。本阶段无任何机器人命令、无 HDC、无网络变更。
- 环境：Ubuntu 24.04，Python 3.12.3，pip `--user --break-system-packages` 安装
  `mujoco==3.17.0`（omni 交付 README 标注的训练版本；先试 4.0.0 后降级），
  NumPy 1.26.4（系统自带）。无 torch/onnxruntime。

## 关键命令与实际输出（摘要）

1. 挂载与规则核对：
   - `mountpoint -q /home/caolin/as2w_workstation` → 挂载正常（`zoubu@192.168.10.61` fuse.sshfs）。
   - 通读根/现场 `AGENTS.md`、`INDEX.md`（最新 10:46 节）、`实机事实与命令.md`、`低层自测计划.md`、
     `architecture.md`、`models/manifest.json`。
2. 训练交付检索：
   - 工作站无 `as2w_flat.xml` / `fall-recovery-contract.json` / `.pt`（`find` 全盘确认）。
   - `curl api.github.com/repos/YuTaoV5/Rob2Nav` → 公开仓库，交付 rev `e61aaf79` 树中无训练归档；
     main 分支有 `deliveries/as2w-deploy/omni-blind-stairs/assets/`（含上述两文件），
     下载并记录 SHA-256（见 `部署参考/as2w-flat-rerun/README.md` 资产表）。
   - 工作站 `unitree_ros` HEAD `41dec58`；`git diff 4005a1b..HEAD -- robots/as2w_description` 为空
     （as2w URDF/meshes 与 omni 交付固定版一致；`git config --global --add safe.directory` 后可读 git）。
3. `.bin` 解析验证（`AS2WMLP1` 格式，按 `policy.cpp`）：
   - `stairs-r14.bin`：mode=1（stairs），defaults=[0×4, 0.8×4, −1.6×4, 0×4]，与 contract 完全一致；
     4 层 (128×58)(128×128)(128×128)(16×128)，无尾字节。四份 `.bin` SHA-256 与 manifest 一致。
   - MuJoCo XML 执行器顺序为**按腿分组**（FL_hip,FL_thigh,FL_calf,FL_foot,FR_…），与策略动作顺序
     （按关节类型分组）不同——复测脚本按交付代码用 `actuator(name).id` 做顺序映射。
4. 复测运行（`部署参考/as2w-flat-rerun/flat_stairs_rerun.py`，24 核并行，单轮秒级）：
   - `--mode recovery-validate --models recovery-r12 --seeds 4` →
     `passed 16/16, stable_s mean 2.76 max 3.58`；right/12002 = 1.060 s
     （交付 torch 参考=通过、C++ native=0.98 s 失败：阈值两侧的浮点抖动）。
   - `--mode flat-stairs --models stairs-r14 stairs-r17-2000 stairs-r17-3000 --seeds 16 --stress both` →
     全部 96/96 `valid`、`upright_fraction mean 1.00`；
     r14 0.590 m/s / 5.27 m；r17-2000 0.472 m/s / 4.10 m；r17-3000 **0.400 m/s** / 3.41 m（nominal），
     stress 条件几乎不变；动作限幅与 URDF 超速均为 0。
   - `--mode stairs-crosscheck ... --stress on` → 三份均 0/16（与交付一致）；
     48 种子 `visited_levels` 39 个完全一致，其余 ±1 级（均在 0–2 级失败区间）；
     r17-3000/27001 双方均到第 2 级。个别混沌种子峰值冲击差异大（843 vs 92 N），不影响判定。

## 事实/推断

- 事实（仿真口径）：三份爬楼权重在 MuJoCo 平地全部能行走且全程不倒（96/96），对动力学应力稳健；
  r17-3000 速度跟踪 0.4 m/s 指令最准、稳走占比最高（0.54–0.58）、站姿最高。
- 事实：交付 `.bin` 内嵌合同（defaults/限位/模式）与 main 分支 contract 一致，动作顺序映射关系已核实。
- 推断：若做 stairs 只读影子，r17-3000 为首选权重；横向漂移（最坏 1.07 m/9 s）是盲走策略的已知局限，
  真机影子阶段需重点观察。
- 仍然未知：真机 16 轴 DDS 槽位映射、轮轴方向/零位、低层接管协议（`hardware_contract.md` 空缺项不变）；
  本阶段不填 `calibrated.map`，不发布任何 LowCmd。

## 未解决问题 / 下一门槛

- 训练归档 `as2w-results`（`.pt` PPO 权重+优化器）仍不在工作站；已确认非平地复测必需。
- main 分支新一代 `omni-blind-stairs` R21（平地 34/52、6 cm 楼梯 0/5 固定验收）未评估，
  是否纳入候选需现场/同事确认——它代际不同且验收更低，暂不替代三份交付权重。
- 下一门槛（无需狗动作）：对 r17-3000 做更平地场景变体（不同摩擦/初始航向角）扫描 + 20 Hz 采样数据
  槽位-关节运动学关联分析（离线）；之后才是 CPRO 只读影子（仍不发命令）。

## 原始产物

- 结果 JSON：`部署参考/as2w-flat-rerun/results/{validate_recovery-r12,flat_stairs_all,stairs_crosscheck_all}.json`
- 脚本与资产：`部署参考/as2w-flat-rerun/`（README 含来源与哈希）
- 本日志即原始会话记录（命令输出摘录如上；未记录密码/令牌/序列号）
