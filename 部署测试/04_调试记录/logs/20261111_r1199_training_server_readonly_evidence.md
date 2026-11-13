# R1199 训练服务器只读证据摘录

日期：2026-11-11；环境：训练服务器 Ubuntu 24.04.5、Isaac Lab 虚拟环境、NVIDIA L40。仅 SSH 读取，无远端文件改动。登录凭据及设备敏感信息不记录。

读到的目录：`/root/gpufree-data/Rob2Nav-runtime/as2w-current/{AGENTS.md,assets,code,runs}`。`runs/` 包含 `r290-three-skills/`、`rolling/`、`stepping/`、`recovery/`。检查时 `ps -eo pid,etime,args | grep -E 'train_as2w|eval_as2w'` 没有匹配运行进程（仅当时快照）。

训练作业目录：`runs/r290-three-skills/rolling-knee-margin-formal/`：`contract.json`、`job.log`、TensorBoard events、`model_0.pt` 至 `model_1199.pt`（大部分间隔25迭代）、`job.pid`、空 `git/`。`contract.json`：`profile=expanded`、`num_envs=384`、`iterations=1200`、`seed=303`、`physics_step_s=0.005`、`policy_step_s=0.02`、`rolling_fixed_exit=true`、`rolling_knee_margin_m=0.1`、`pose_source=simulation_proxy_no_raw_lowstate`。`job.log` 尾段：`Metrics/success_rate: 1.0000`、`Episode_Termination/as2w_nonwheel_contact: 0.0375`、`.../as2w_knee_surface: 0.1374`、`.../as2w_stance_violation: 0.0879`、`AS2W_ROBUST_COMPLETE expanded`。这几个指标来自训练，不是正式验收。

checkpoint 文件本机 `sha256sum` 输出：

```text
bb5c9735b5bd37ef4bdd2bd13f9d45395d8dc9b4c888c36955de1a345d55776d  .../rolling-knee-margin-formal/model_1199.pt
```

Isaac 同权重评估：`runs/r290-three-skills/rolling-knee-margin-isaac-1199-.30/{contract.json,speed-evaluation.json,job.log}`，`speed-evaluation.json` 的 `gate=false`；`forward` total20 / track16 / stable16 / track_and_brake15 / hold1 / track_brake_hold1；`back` total20 / track15 / stable16 / track_and_brake15 / hold2 / track_brake_hold2。

MuJoCo 同权重诊断：`runs/rolling/release-transition-motion-push-only/{mujoco-contract.json,mujoco-rolling-diagnostic.json,mujoco-rolling-diagnostic-summary.json,policy-observations.npy,job.log}`。合同：`checkpoint_sha256=bb5c...776d`、`assets=.../assets/r237-train-root`、`speed=0.3`、`native_pd=true`、`substep_safety=true`、`packet_loss=0.02`、`push_schedule=motion-only`、`park_odometry=true`、`park_settle_joints=true`、`park_common_gain_scale=0.5`。汇总 `gate=false,safety_gate=true`，六类 `passed` 都0/1；逐回合前进 `seed=47001,first_nonwheel_contact=null,nonwheel=false`。

服务器 `runs/rolling/release-park-damping025/` 是后续停车参数消融，同一 checkpoint 但 `park_common_speed_damping=0.25`，汇总仍 `gate=false`；不能与固定 release 控制器结果混为同一试验。

资产哈希：

```text
2bf148d8e0e5722db4a581c7cf7834611121025cc1c95c14f892b83bc0fdfa01  .../assets/r237-train-root/local-step-diagnostic/as2w_flat.xml
1e4e3fb76806e83dbe3541979fa0cb40f4b3150f5bf4de298224bf9baa9b0490  .../assets/r237-train-root/fall-baseline/fall-recovery-contract.json
```

上述两文件与本项目仿真服务器 `/tmp/opencode/omni/assets` 对应文件哈希相同。训练服务器代码 `code/eval_as2w_mujoco_rolling.py` 中 `stable` 是非轮触地、关节/姿态/膝净空、轮卸载和力矩综合；`passed=stable and tracked and brake_ok and held and fixed_entry>=0.4s and fixed_final>=2s`。`code/as2w_mujoco_pd.py` 配置 native actuator gain/bias、`implicitfast` 和 force clamp；本项目旧复演器采用每子步直接算 PD 力矩。

完整解释和待对齐问题：`部署测试/02_现场操作/R1199训练服务器只读审阅与仿真差异.md`。
