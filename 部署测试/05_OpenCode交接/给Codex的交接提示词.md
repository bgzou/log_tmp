# 给 Codex 的交接提示词（2026-11-09 下午 · R41 实机测试线）

> **14:56 进度覆盖：**下文 G1 是接手时的任务说明，现已由现场人员逐项完成 12 腿关节+4 轮的只读手动标定；A/B 前后候选已实测确认为 A=(FR,FL,RR,RL)，状态槽位/符号和两态读数见 `部署参考/cpp_deploy-as2w/config/r41_measured_identity_sign.md`。旧站姿 calf −2.09 是混合两态均值错误，已更正。**未解决**：R41 对齐的编码器零位、LowCmd 命令方向/模式、CRC、接管/恢复、急停等。不要重复要求用户做 G1 物理标定；先读 INDEX 14:07–14:56 新增各节。

你现在接手 AS2-W × CPRO 策略部署的实机调试。你运行在 **Windows 工作站**上（项目根
`D:\Projects\Athena\运动控制\Collie\AS2-W_CPRO`），可直接用 PowerShell/Git Bash 与
`部署测试\00_HDC工具\hdc_6.1.1.280\hdc.exe` 管理 CPRO。此前由服务器 OpenCode 完成的
分析、脚本与日志都在本项目目录内，无需访问服务器即可继续；服务器 192.168.10.163 上另
有就绪的 MuJoCo/torch 环境（账号 caolin，详见 `05_OpenCode交接/`），如需复跑仿真可让
现场人员协助，或在 Windows 本机装 Python 3.10+、MuJoCo 3.17.0、torch CPU。

## 第一步：读这些文件（按序）

1. 根 `AGENTS.md` 与 `部署测试/AGENTS.md`（协作规则，含 2026-11-09 最新更新）
2. `部署测试/02_现场操作/实机事实与命令.md`（现场已验证事实——含 16 轴结构判定）
3. `部署参考/cpp_deploy-as2w/config/hardware_contract.md`（低层合同：已填/待填逐项）
4. `部署测试/04_调试记录/INDEX.md`（重点 10:02、11:20、11:30、11:41、12:15 五节）
5. `部署参考/cpp_deploy-as2w/models/r41/README.md` + `deploy.yaml`（R41 合同）
6. `部署测试/02_现场操作/低层自测计划.md`、`明日bringup手册.md`、`现场入口使用.md`

## 硬性规则（违反即停）

- **任何可能让狗动作的命令，先告知现场人员具体动作，等其当次明确同意才发。**预告≠同意。
  只读查询（GetState/low-state/low-capture/low-remote/shadow）可继续。需要现场人员操作
  遥控器配合时，也先说明其具体操作。
- **`hardware_contract.md` 未填项补齐前，不向机器人发布 LowCmd。**影子/回放不算控制。
- 每完成一个阶段（含失败）立即追加 `INDEX.md` 并把原始日志放 `04_调试记录/logs/`；
  CPRO `field_logs/` 定期经 `cpro_ubuntu.sh /bin/tar` 打包 + HDC 回收（Windows 本地路径
  须反斜杠绝对路径）。
- **输入设备只用原厂遥控器**（用户已明确否决 Xbox/键盘方案）。遥控器同时是人工急停——
  其急停在低层接管后的有效性未验证，**验证通过前不得依赖**。
- 不从 As2/Go2-W/B2-W/URDF 顺序推断 AS2-W 映射；它们只做假设来源，结论以实测为准。

## 当前状态（2026-11-09 12:30，全部已归档）

- CPRO（鸿蒙+Ubuntu 22.04 aarch64）经 USB/HDC 由工作站管理；`eth0` 192.168.123.100/24
  连 AS2-W 主控 .161，DDS 只读链路全部通（LowState ~1 kHz、SportState 20 Hz、RPC）。
  狗现趴下（`ai_damping`）。构建 7/7 CTest 通过；20 ms 只读影子链路实测 p99 1.13 ms。
- **16 轴结构（已判定，证据见 11:41 节）**：腿槽 0–11 = (hip,thigh,calf)×4 按腿三元组
  （腿 k = 槽 3k..3k+2）；轮 12–15 配腿 k；**轮 12/14=右、13/15=左**（两次已知方向转向
  交叉验证）；轴分组 12/13 与 14/15。**未决**：前后分组两候选 A=腿序(FR,FL,RR,RL) vs
  B=(RR,RL,FR,FL)（A 证据更强）；每轴符号（除轮前向=正、hip 镜像外）；**零位 offset 全部未标定**。
- **下午离线复核纠错**：旧站姿 hip ±0.25 / thigh 0.83 / calf −2.09 是旧分析把趴下与站立
  静态帧混合求均值；11:41 原始日志真实长静止站姿约 hip ±0.12 / thigh 0.60 / calf −1.23，
  趴下约 ±0.57 / 0.98 / −2.75。R41 默认站姿 hip 0 / thigh 0.8 / calf −1.6；旧称
  “站姿差 0.49 rad”无效。旧影子 −1.92 rad/s 只是未标定 map 的一次输出，不能推出 offset。
  具体纠错与当前 ai_damping 姿态见 INDEX 下午 G1 节。
- 遥控器：HG LowState 内嵌 40 字节，报头 55 51，左摇杆前推→第 5 个 float（候选名 ly）
  +0.82~0.85、松开归零。**其余轴/按键全部未标定**。独立 rt/wirelesscontroller topic 0 包。
- **R41（stairs 线新基准）**：ONNX obs[1,41]+state[1,835] 递归、50 Hz、指令 vx/vy/wz
  （限幅 0.6/0.35/0.8）。平地 MuJoCo 固定集 **41/52 零跌倒**（forward 0.2/0.4、倒退、
  左右转、停车全 4/4；纯侧移弱 1–2/4）；独立集 20/52 零跌倒。C++ 回放 750 帧
  max_abs_error=0（x86）。已并入 `cpp_deploy-as2w`（根 CMake `-DAS2W_R41=ON
  -DONNXRUNTIME_ROOT=<ORT-1.22.0>`；控制器 `deploy/robots/as2w/r41/`、模型
  `models/r41/`）。**CPRO 上还没有 R41**（ORT aarch64、ARM 构建、真机 shadow 均未做）。
  旧三份 stairs .bin 已降级为离线对照；recovery 线不变（机体系速度源未解决）。
- MuJoCo 平地复测框架（服务器 `部署参考/as2w-flat-rerun/`）：已验证三锚点，可用于
  fixstand 插值预演。

## 下午使命：完成映射 → R41 上实机。按以下门槛顺序推进

### G1 关节映射标定会（用户亲自逐关节手掰，一次会话解决身份+符号+锚点）

**先写离线分析脚本** `部署参考/cpp_deploy-as2w/tools/joint_calib_analysis.py`（纯离线，输入 low-capture 日志）：

- 输入：low-capture 日志路径（100 Hz `LowCaptureFast` 输出，LOW_SAMPLE CSV 格式：35 槽 q/dq + IMU）。
- 静态段检测：全槽 |dq| 均低于阈值的连续窗口；取窗口内逐槽 q 均值为静态读数。
- 活动段切分：任一腿槽 |dq| 超阈值的连续段，段间隔 >1.5 s 分段；每段输出：主导槽（|Δq| 最大）、次主导槽、每槽 Δq（起末差）、平均 dq、持续时长。
- 汇总输出：① 段号→槽位/Δq/方向 的人类可读表；② 趴下/站立两态静态读数表（逐槽）；③ 建议映射表模板（deploy.yaml 的 contract 关节序 → DDS 槽位 + sign 列，供用户填）。
- 输出 JSON + 可读表两份到 `04_调试记录/logs/`。脚本先在今日已有日志（`20261109-114107_windows_LowCaptureFast.log`，含已知转向段）上自测：应能正确切出已知活动段并给出已知侧别结论。

**标定会流程**（用户主导、需现场人员执行；全程狗趴下 ai_damping、零命令）：

1. 启动 100 Hz 采样（`-Stage LowCaptureFast -Seconds 300`，一次装下全部动作；或分两段采）。
2. 趴下静止 10 s（采趴下锚点）。
3. 用户**逐个手掰 12 个腿关节**：每关节数秒、幅度适中、关节间停 2–3 s；**记录顺序与物理方向**（如 FL_hip 往外掰、FL_thigh 往前抬、FL_calf 往内折……建议按 腿→关节 顺序：先一条腿 hip/thigh/calf，再下一条）。
4. 用户**逐个手转 4 个轮**（每个数秒，注意记录转向：顶面向前转 or 向后转）。
5. （可选）遥控器起立→站立静止 10 s→趴下（采站立锚点；起立属遥控器正常操作，先说明并获同意）。
6. 停止采样，跑分析脚本；用户对照自己记录的顺序与方向，填出**关节→槽位+符号**完整映射。
7. 结果（含两态读数）更新 `hardware_contract.md`；若与 11:41 会话的侧别/轴分组/配对结论矛盾，先复查再下结论。

该会话直接解决：16 轴身份（含 A/B 前后候选判定）、每轴方向符号、两态静态锚点。**零位 offset 仍需另行设计**（站姿锚点法候选：offset_j = q_dds_站立_j − q_sim_默认_j，配合本次身份/符号结果复核）。

**遥控器全轴标定**（与标定会同场做，狗趴下无动作风险）：跑 `low-remote`，请用户逐个方向推杆（左右摇杆各轴、逐个按键），一次一个变量，记录 40 字节中每个 float/按钮位对应关系。目标产物：vx/vy/wz 三个指令轴映射 + 停止/模式按键候选。

### G2 R41 部署到 CPRO（无狗动作）

1. ORT **1.22.0** aarch64 CPU 包（GitHub releases `onnxruntime-linux-aarch64-1.22.0.tgz`
   样式；**不要**用其 CMake 默认的 aarch64-gpu-1.16.0 包名，改传 `-DONNXRUNTIME_ROOT`）
   经 `hdc file send`（**本机源绝对路径**）传入 CPRO 解压。
2. yaml-cpp：先查 CPRO Ubuntu 是否已有；没有则源码静态构建进现场包（勿依赖 CPRO 互联网）。
3. 在 CPRO 上以 `-DAS2W_R41=ON` 构建 `as2w_r41_replay`，跑
   `models/r41/deploy.yaml + r41-trace.csv` 回放，期望 `rows=750 max_abs_error=0`。
4. `-DAS2W_SDK2_SHADOW=ON` 构建 `as2w_r41_shadow`（交付自带 `shadow.cpp`，启动参数无参运行
   可查）。用 G1 证据生成 R41 专用映射表（deploy.yaml 关节序=contract 序；DDS 槽按
   三元组+轮 12–15；A/B 未定时**两个候选表都留着并显式标注**；offset 未标定前 shadow
   数值仅作链路观察）。跑趴下态只读影子，记录时延。
5. 新增 `field.sh` r41-build/r41-shadow 阶段 + `现场入口.ps1` 对应 Stage + 使用文档，Sync 重打包。

### G3 低层合同补齐（实机 LowCmd 的前置条件）

以 SDK2 源码（`部署参考/unitree_sdk2/`）+ 官方存档（`部署参考/宇树官方参考/`，特别是
`底层服务接口.html`、`As2W轮足运动服务接口.html`、`运控切换服务接口.html`）+ GO2-W
示例（**仅作假设**）逐项填 `hardware_contract.md`：

- HG `LowCmd_` 的 `mode_pr/mode_machine`、每电机 `mode` 值（腿位置模式/轮速度模式）、
  `q/dq/kp/kd/tau` 单位、**CRC 算法**（SDK2 G1/B2 示例有 crc() 实现可对照）。
- **运控释放/恢复**：`MotionSwitcher` 的 `ReleaseMode`/`CheckMode`（只读 Check 已验
  `form=1 name=ai`）；释放后 SportClient 行为、恢复路径。此步会改变狗的控制权——
  **属于需同意的动作级操作**，先出方案再执行。
- 发布频率与超时行为：固件语义未知，控制程序必须自带看门狗（丢包/超时→停发→安全过渡）。
- **遥控器急停在低层接管后是否有效**：趴下态实测（需同意），通过前不得依赖。
- R41 轮端估速输出若需验证，趴下/站立态只读对比即可初查。

### G4 起身方案（passive→fixstand 轨迹插值）——你的想法成立，按此实现

GO2 参考（`部署参考/unitree_cpp_deploy-go2/deploy/include/FSM/State_Fix.h`）：enter 时
快照当前 q 为首帧，按关键帧序列线性插值（ts/qs），结束 auto_transition。**可借鉴模式**；
GO2 的 12 轴数值/增益（kp 60~80）**不可沿用**。AS2-W 方案：

- 关键帧（标定坐标）：趴下锚点 → 经身份、方向和零位标定后的 R41 目标站姿 DDS 值；
  **不能直接把原厂静止站姿当作 R41 默认站姿**，两者的对应关系尚未验证；
  趴下本就紧凑，大概率单段插值即可，无需 GO2 的两段中转。
- 轮在插值期间发 dq 目标 0（速度阻尼），腿发位置目标。
- **先在 MuJoCo 里整链预演**（服务器 `as2w-flat-rerun/` 框架可加：趴下姿态→插值→R41
  接管 state 清零→行走），通过后再进实机门槛。增益从低值起步、限幅、限速。
- 该代码写好但**默认不启用**，进 G5 才开。

### G5 受控实机测试链（每步都先告知+等同意，事先约定中止手势/口令）

前提：G1–G4 完成、现场人员看护、急停路径明确。顺序：
1. 现场人员用遥控器让狗趴下 → 2. ReleaseMode 切低层（读回确认）→ 3. Passive 发布
（kp=0/kd 阻尼、q 跟随，验证狗不动）→ 4. FixStand 插值起身（数秒）→ 5. R41 接管
（state 清零，指令初始 0）→ 6. 现场人员轻推左摇杆前侧行走测试（短、慢）→ 7. 停止
→ 指令归零 → 回 Passive/阻尼 → 恢复原厂运控 → 遥控器接管复核。
任一步异常：立即停发+安全过渡，现场人员遥控器急停（若已验证）/断电程序按事先约定。

## 已知坑（今天踩过的，别再踩）

- ORT 必须 **1.22.0**：1.24.2 报 TopK ShapeInferenceError 拒载 R41 模型。
- 文本编辑工具可能有模糊匹配：改 C++ 后必须编译检查；不确定时 diff 现场包内已知好版本
  （今天 `src.q` 被误写成 `src.q()` 就是被编译检查拦下的）。
- Windows `现场入口.ps1` 的 `-Seconds` 上限 300（ValidateRange）。
- HDC `file send` 本机源必须绝对路径；`file recv` 的 Windows 目标须反斜杠路径。
- 远程打包 field_logs 用 `/data/local/tmp/as2w_field/cpro_ubuntu.sh /bin/tar`（宿主自带
  tar 不可靠）。
- GitHub raw 下载要 `curl -L`（302 重定向）。
- ssh→powershell 的命令里管道符会被 PowerShell 吃掉，避免在远端命令中用 `|`。
- 启动长采样前检查无残留进程（今天有两组采样并行的先例，数据等价但混乱）。
- `field.sh` 各阶段自动写 `field_logs/` 与其 INDEX；结束阶段后打包回收。

## 产物与日志位置

- 台账：`部署测试/04_调试记录/INDEX.md`（追加，不覆盖）+ `logs/`（原始）
- 合同：`部署参考/cpp_deploy-as2w/config/hardware_contract.md`（逐项证据）
- R41：`部署参考/cpp_deploy-as2w/models/r41/`（onnx/yaml/trace/README）、
  `deploy/robots/as2w/r41/`（控制器/回放/影子）、交付全量副本 `部署参考/omni-blind-stairs/`
- 分析工具：`部署参考/as2w-flat-rerun/`（MuJoCo 复测 + 采样分析脚本 + 今日结果 JSON）
- 阶段入口：`部署测试/现场入口.ps1`（Sync/SdkBuild/GetState/LowState/LowCapture(Fast)/
  LowRemote/Shadow/MotionMode/ServiceList/PackageVersion/PolicyVerify 等）

现在开始：先完成第一步的文件阅读与 5 分钟状态核对（GetState + ls field_logs），向现场
人员报告你的理解，然后立即实现 G1 的 `tools/joint_calib_analysis.py` 并在今日已有日志上
自测通过，再请现场人员安排标定会（逐关节手掰 + 遥控器全轴标定）。每关一档，写一次 INDEX。
