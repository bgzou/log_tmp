你现在在 caolin 服务器上接手 AS2-W × CPRO 的 R1199 直接修复与明日实机接续。Windows 工作站项目根是 `D:\Projects\Athena\运动控制\Collie\AS2-W_CPRO`，通常挂载到本机 `/home/caolin/as2w_workstation`。先检查挂载确实存在，再完整通读该项目的根 `AGENTS.md`、`部署测试/AGENTS.md`、`部署测试/04_调试记录/INDEX.md` 最后两节，以及**当前任务书** `部署测试/05_OpenCode交接/给OpenCode_R1199训练合同修复与明日实机接续_20261112.md`，随后按任务书持续执行。

用户已两次实机确认前后滚动抖动及停走姿态跳变，**不要再复现旧故障或运行旧版 R1199 摇杆**。真正 R1199 训练合同已查明：站姿补偿 continuous/straight=true/true，停车 odometry/settle=false/false；旧实机 C++相反。工作站源码已有默认关闭的独立修复候选 `AS2W_R1199_TRAINING_CONTRACT` 和 `r1199_training_forward_parity.py --training-runtime`，但尚未编译/仿真/同步。你先静态审查并完善修复，完成独立构建、逐帧 parity 和仅修复版的 MuJoCo 验收，再准备独立现场入口；不要覆盖旧二进制或解除旧入口锁。两次实机原始数据和训练合同在 `部署测试/06_训练协作/R1199_real_robot_feedback_20261112.zip`，它可独立阅读。

任何 ReleaseMode、SelectMode、LowCmd 或可能使狗动作的命令，都必须先告知现场人员该次具体动作和风险，等其**当次明确同意**后才执行；只读可先做。每阶段原始日志回收到 Windows `部署测试/04_调试记录/logs/` 并立即更新 `INDEX.md`。CPRO 由 Windows HDC 访问，caolin 不直接运行 Windows hdc；Ctrl+C不是可靠运动急停。若挂载/设备当前不可达，完成可做的离线工作并记录实际阻点，不要在空挂载目录编辑。
