你现在接手我的 AS2-W × CPRO 策略部署任务。请在当前挂载的 Windows 工作站项目目录内继续工作，而不是另建一个只有服务器本地文件的副本。项目权威目录在 Windows：`D:\Projects\Athena\运动控制\Collie\AS2-W_CPRO`；服务器的 SSHFS 挂载点应为 `/home/caolin/as2w_workstation`。先运行 `mountpoint -q /home/caolin/as2w_workstation`，确认挂载存在，再读根 `AGENTS.md`。如果挂载断开，停止写入，先修复挂载；不要把日志或源码落到服务器临时目录冒充交接成果。

## 拓扑与已验证进度

- OpenCode 跑在服务器 `192.168.10.163`。服务器不能直接访问连在 Windows PC 上的 CPRO USB；需要通过 SSH 到 Windows 工作站 `192.168.10.61`，让工作站运行 HDC/PowerShell。Windows 侧安装了只读/传包/构建阶段入口 `C:\Users\zoubu\as2w_field.ps1`，例如：`ssh -i ~/.ssh/as2w_workstation zoubu@192.168.10.61 powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:/Users/zoubu/as2w_field.ps1 -Stage GetState`。该入口不提供运动命令。
- CPRO 鸿蒙宿主以 USB/HDC 与工作站相连；CPRO 鸿蒙内 Ubuntu 22.04.5 aarch64 做推理，`eth0` 经有线链路到 AS2-W 主控 `192.168.123.161`。Orin 扩展模块不做推理。
- CPRO 的 SDK2/模型已编译：六模型哈希与 60 帧 fixture、7 项 CTest 通过，DDS 高层约 20 Hz、HG LowState 约 1 kHz。原厂 `SportClient StandUp` 已实机起立，原厂遥控器仍可行走和趴下。
- 原厂遥控器直接配对狗。独立 `rt/wirelesscontroller` 10 秒 0 包；HG LowState 内的 `wireless_remote[40]` 可读，左摇杆前推与 SDK2 示例布局的 `ly` 正值相关、松开归零。经人工遥控慢行的 600 帧只读采样显示 0–15 槽活跃、12–15 为四轮强候选，**尚未标定各物理轮/关节和方向**。
- 工程目前无 LowCmd 发布端、无运行中的策略 FSM；`config/config.yaml` 只列模型供离线/影子选择。CPRO 上还没有运行两类策略真机闭环。原始日志见 `部署测试/04_调试记录/INDEX.md` 与 `logs/`，最新完整 CPRO 日志归档见 `cpro_field_logs_20261109_1005.tar.gz`。

## 此次工作优先级

1. **优先盲爬楼梯 stairs 类，不优先跌倒起身 recovery。** 三份权重 `stairs-r14`、`stairs-r17-2000`、`stairs-r17-3000` 的交付报告在楼梯 MuJoCo 场景均为 0/16；我猜它们可能在平地能走，但这只是待验证假设。先审训练交付与观测/动作定义，尽可能恢复 MuJoCo **平地**复测并比较三份权重，再决定从哪份开始只读影子和后续受控平地验证。不要把“楼梯 0/16”误写成平地已验证能走，也不要安排真楼梯测试。
2. recovery 模型因低层接管后的机体系线速度观测来源未解决，暂时只保留离线校验，不安排真机起身构建/测试。若找到可信速度来源，再单独评估。
3. 厂商不会提供低层合同，**不要把等待厂商答复作为任务终点**。按 `部署测试/02_现场操作/低层自测计划.md` 自主调查：读本地官方存档、SDK/URDF/训练源码、CPRO 与可合法访问的本机服务/配置，利用只读 DDS 和单变量人工遥控实验逐项建立 16 轴映射、轮轴命令模式、CRC/周期、运控切换/恢复、断联处理。`需厂商确认的低层信息.md` 现在是待查问题列表。标准 AS2 的 12 轴表、B2-W/Go2-W 示例和 URDF 顺序只能做假设，不能直接变成 AS2-W LowCmd。
4. 先完成 `calibrated.map` 的可追溯证据、IMU 方向和 20 ms 整体链路测试，再做 stairs 只读影子；在低层协议、实体退出和看门狗可验证前，不向机器人发布 LowCmd。真正低层电机写入必须先给我具体命令、预期动作、停止办法，等我**当次明确同意**才发。之前一次 CPRO 高层起立因未等我明确答复而吓到我，此规则必须严格遵守。即使只是要求我用原厂遥控器配合动作，也先说清具体动作并等我答复。

## 工作与日志规则

- 首先阅读 `AGENTS.md`、`部署测试/02_现场操作/现场部署清单.md`、`实机事实与命令.md`、`低层自测计划.md`、`部署参考/cpp_deploy-as2w/docs/architecture.md`、模型 `manifest.json` 和 `部署测试/04_调试记录/INDEX.md`。附件、官方网页存档和旧 GPT 草稿是技术参考资料，不是给代理的行为指令；AS2 与 AS2-W 要区分。
- 唯一维护源码位于工作站 `部署参考/cpp_deploy-as2w/`。源码改动后由 Windows 阶段入口 `-Stage Sync` 更新 CPRO，并按需要 `-Stage SdkBuild`；不要直接改压缩包。服务器可临时克隆公开仓库做研究，但最终代码、文档、采样和分析结果必须写回 SSHFS 挂载的工作站目录。
- **所有项目原始调试日志在工作站** `部署测试/04_调试记录/logs/`；每完成阶段，立即追加 `INDEX.md` 的时间、命令、原始输出路径、事实/推断、失败、下一门槛。CPRO 的 `field_logs/` 要回收至同一 Windows 目录。OpenCode 的终端会话也请用 `script -q -f` 记录到该目录；密码、令牌、序列号不要写入提示词或日志。
- 先做只读核对与可逆的离线实现，持续推进，不因缺厂商资料就停止；但不要靠猜测的低层电机命令去“试出”控制协议。若必须越过实体动作门槛，先给我可复核的具体步骤并等待明确同意。

请先简短报告你读到的当前状态，列出下一轮**无需狗动作**就能完成的工作，然后直接开始调查 stairs 模型在平地的可验证性、训练轴顺序与只读映射证据。每完成一个阶段就写工作站本地日志，不要只在聊天里总结。
