你现在接手 AS2-W × CPRO 的 **LowCmd 发布启动序列深度调试**任务。这是一项真机安全关键任务：现场已因错误的 LowCmd 发布序列触发两次机器人保护报警（喇叭巨响），现场人员按急停后冷启动恢复。**在你给出经过严谨论证的修复方案并通过离线审查前，禁止任何 LowCmd 真机发布。**

完整任务说明、事故经过、根因分析、官方例程对比和交付要求在 `部署测试/05_OpenCode交接/给Codex_LowCmd启动序列调试提示词.md`。请先完整读那份文件，再开始工作。

## 必读顺序

1. `部署测试/05_OpenCode交接/给Codex_LowCmd启动序列调试提示词.md`（本次任务核心交接）。
2. 根 `AGENTS.md`。
3. `部署测试/04_调试记录/INDEX.md` 最新四节（22:10 第一次事故、22:50 第二次事故、23:10 只读 35 槽位扫描、23:30 根因确认）。
4. `部署参考/unitree_sdk2/example/go2w/go2w_stand_example.cpp`（**官方轮足低层接管例程，关键参考**）。
5. `部署参考/unitree_cpp_deploy-go2/deploy/robots/go2/main.cpp` 和 `deploy/include/FSM/State_Passive.h`（GO2 RL deploy 的启动和 Passive）。
6. `部署参考/cpp_deploy-as2w/deploy/robots/as2w/r214/r214_publish.cpp`（**你要改的主文件**）。
7. `部署测试/03_官方资料/底层服务接口.html`（官方 HG LowCmd/LowState 结构定义）。

## 一句话根因

`MotionSwitcherClient::ReleaseMode()` 后所有 16 个电机从 FOC(mode=1) 切到待机(mode=0)；我们的 `fill_passive` 第一帧就设 `mode=0x01` 要求电机切回 FOC 并同时带 `q/kp/kd` 命令，**第一帧就触发保护报警**。官方 `go2w_stand_example` 的解法是先用特殊停止值（`PosStopF/VelStopF`）+ `mode=1` + `kp=0/kd=0` 持续发 500 tick（1 秒）让电机稳定唤醒，再开始插值运动。但 AS2-W 用 `unitree_hg` 类型（无 `head/level_flag`，35 motor_cmd），`PosStopF/VelStopF` 机制是否有效未验证——这是你要调查的核心。

## 你要交付的 5 项

1. **根因深度分析**：为什么从 mode=0 直接发 mode=1 + q/kp/kd 会触发保护。是否需要先发"纯 mode 唤醒帧"（mode=1 但全零增益）让电机稳定切到 FOC？
2. **正确的启动序列设计**：参照 `go2w_stand_example`，设计 AS2-W HG 类型的安全启动序列。处理 HG 无 `PosStopF/VelStopF` 的问题。
3. **可编译的 C++ 修复代码**：修改 `r214_publish.cpp`，实现新启动序列。保持现有 FSM 架构，但 Passive 进入时先走"安全唤醒"子阶段。kd 从 5 降到 3（对齐 GO2）。
4. **离线验证方法**：构造一帧 Passive LowCmd 打印全部字段，和 `go2w_stand_example` 逐项对比。
5. **真机测试方案**：分步骤安全测试计划，首测只做 Passive（狗不动）。

## 关键约束

- **禁止真机 LowCmd 发布**，直到方案通过现场人员审查。
- 修改源码后需 `hdc file send` 推送到 CPRO `/data/ubuntu_in_hm/ubuntu_rootfs/root/as2w_deploy/...` 并 ARM64 编译（`AS2W_R214_ROOT=/root/ort122 AS2W_SDK2_PREFIX=/root/unitree_sdk2_install`）。
- x86 离线编译可用 `/tmp/opencode/` 下的 ONNX Runtime x64 和 sdk2 install。
- HG LowCmd 无 `head/level_flag`（IDL 和官方文档确认），不能照搬 GO2。
- 35 个 motor_cmd 只有 0–15 有效（16 轴），16–34 固件忽略（mode=0）。
- 16 轴身份：FR 腿 0,1,2；FL 3,4,5；RR 6,7,8；RL 9,10,11；轮 FR=12、FL=13、RR=14、RL=15。
- `mode_machine` 必须从 LowState 回显（=2）。
- CRC 算法已验证正确（`crc32Core(ptr, (sizeof(LowCmd)>>2)-1)`）。
- 每次实验无论成败追加 `部署测试/04_调试记录/INDEX.md`，原始日志存 `logs/`。

交付后明确标注：哪些是已验证事实，哪些是推断，哪些需要真机实验确认。
