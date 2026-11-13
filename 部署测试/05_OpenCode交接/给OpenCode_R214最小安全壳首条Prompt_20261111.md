你现在接手 AS2-W × CPRO 的 R214 最小安全壳审查、离线故障注入和后续有界现场验收。项目唯一权威根目录在工作站，经 SSHFS 挂载为 `/home/caolin/as2w_workstation`；服务器 `/tmp/opencode` 只作构建/仿真缓存，所有源码、文档和日志必须写回工作站。

先执行 `mountpoint -q /home/caolin/as2w_workstation`，然后按顺序完整读取：

1. `/home/caolin/as2w_workstation/AGENTS.md`
2. `/home/caolin/as2w_workstation/部署测试/AGENTS.md`
3. `/home/caolin/as2w_workstation/部署测试/05_OpenCode交接/给OpenCode_R214最小安全壳接续_20261111.md`
4. `/home/caolin/as2w_workstation/部署测试/04_调试记录/INDEX.md` 最新章节
5. 任务书列出的源码、T1评审和R214现场文档

首阶段只做无动作工作：审查 `r214_publish.cpp` 的线程安全、FSM转移与守卫测量点，补齐 warning/hard/remote-timeout/command-slew 的离线故障注入，跑 x86 增量构建、CTest 和 offline-audit，更新指南、INDEX 与原始日志。不要 ReleaseMode，不要启动任何 LowCmd 发布端。

当前权威源码 SHA256 是 `3a022ca8fa489efc350732a03f5a9283bff730510c72aaa3aaade532612fac63`；CPRO stand/zero-B/full 三构建已 8/8 且 audit PASS，但新的运行中阈值尚未真机验收。`rolling-fixed-exit-preview`、R284、R270 仍硬阻断，安全壳不能解除禁令。

任何可能让狗动作的后续实验，都必须先把唯一具体动作、持续时间、自动退出和风险告诉现场人员，并等其对该次实验明确同意；每项实验重新申请。先完成任务书 P0–P2 并汇报，再讨论 P3，不要自行推进真机动作。
