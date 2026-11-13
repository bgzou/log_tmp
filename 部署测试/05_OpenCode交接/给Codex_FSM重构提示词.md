# 给 Codex 的实机控制链交接提示词（2026-11-09 晚间 · R152 发布端 FSM 重构）

你现在接手 AS2-W × CPRO R152 部署任务的**发布端控制器 FSM 重构与实机测试链实现**。你在 Windows 工作站上运行（项目根 `D:\Projects\Athena\运动控制\Collie\AS2-W_CPRO`），通过 PowerShell/Git Bash 与 `部署测试\现场入口.ps1` 管理 CPRO。服务器 OpenCode 此前完成了全部前置验证与代码骨架，你的任务是把骨架重构为**事件驱动 FSM + 遥控器控制**并最终执行实机测试。

## 第一步：按顺序通读

1. 根 `AGENTS.md` 与 `部署测试/AGENTS.md`（协作规则，2026-11-09 更新）
2. `部署测试/02_现场操作/实机测试链方案_R152.md`（S0–S9 测试链方案）
3. `部署参考/cpp_deploy-as2w/config/hardware_contract.md`（低层合同——**所有已验证项**）
4. `部署测试/04_调试记录/INDEX.md` **最新 10 节**（P2 零位→P4 释放→P6 遥控器→P8 预演→P9 骨架→P10 轨迹）
5. `部署参考/cpp_deploy-as2w/deploy/robots/as2w/r152/r152_publish.cpp`（**你要重构的代码**）
6. `部署参考/unitree_cpp_deploy-go2/deploy/include/FSM/` + `deploy/robots/go2/config/config.yaml`（**GO2 FSM 设计模式——你要仿照的架构**）
7. `部署参考/cpp_deploy-as2w/config/r41_measured_identity_sign.md`（16 轴实测身份/符号）

## 已完成状态（全部已验证）

### 16 轴映射（G1 实测）
- 腿序（DDS 槽位）：FR=(0,1,2)、FL=(3,4,5)、RR=(6,7,8)、RL=(9,10,11)，各为 (hip,thigh,calf)
- 轮：FR=12、FL=13、RR=14、RL=15
- R152 contract 序（FL,FR,RL,RR 按关节类型分组）的 DDS 槽位映射：`[3,0,9,6, 4,1,10,7, 5,2,11,8, 13,12,15,14]`
- LowState 状态 sign：hip 四轴 `−1`，其余 12 轴 `+1`
- **零位**：hip ±0.23°、thigh ±0.17° 实测 DDS=URDF；calf 旁证 ≈ +0.011 rad
- 映射文件：`config/r152_measured.map`（已在 CPRO）

### 遥控器解码（P6 完整标定）
- 40 字节内嵌 LowState.wireless_remote：头 2B(55 51) + 按键 u16 + 五个 float(lx,rx,ry,L2,ly) + 保留 16B
- **轴**：lx 左摇杆横(左−1 右+1)、ly 左摇杆纵(前+0.85 后−0.99)、rx 右摇杆横(左−0.83 右+0.92)、ry 右摇杆纵(前+1 后−0.98)、L2 恒 0
- **按键位图**：bit15..12=左组左/下/右/上、bit11..8=Y/X/B/A、bit5=L2、bit4=R2、bit1=L1、bit0=R1
- R152 行走指令映射：**vx=ly、vy=lx、wz=rx**
- **趴下态推杆/按键狗零反应**（已实测确认）

### LowCmd 合同（P3，CRC 实测 5259/5259）
- HG LowCmd_ 话题 `rt/lowcmd`：mode_pr(发 0)、**mode_machine(必须逐帧回显最新 LowState 值，实测=2)**、motor_cmd[35]、crc32
- 电机 mode：0x01=FOC；PD 律 τ=tau+kp(q_des−q)+kd(dq_des−dq) 输出侧
- CRC32：多项式 0x04c11db7、初值 0xFFFFFFFF、覆盖前 `(sizeof>>2)−1` 字
- 发布率 500 Hz 起步（B2-W 示例惯例）；失联行为未知 → watchdog 不裸停发

### 运控释放/恢复（P4 受控实测）
- **ReleaseMode()**：rc=0，狗完全不动，CheckMode 服务名变空，GetState 超时（高层 RPC 不可用），LowState 不受影响
- **SelectMode("ai")**：rc=0，CheckMode 恢复，**但会直接让狗从趴下起立**（关键安全发现）
- **SelectMode 从站立状态接管的行为未验证**——不要基于假设设计退出策略

### R152 策略
- ONNX obs[1,41] + state[1,844]，50 Hz；关节序=deploy.yaml（与 R41 同）
- 12 腿位置目标 + 4 轮速度目标；腿 kp=55/kd=2、轮 kp=0/kd=2
- 指令限幅：vx≤0.6、vy≤0.35、wz≤0.8；**首测限 vx≤0.2**
- 平地 MuJoCo：固定集跟踪 44/52、严格 21/52、零跌倒；stop 4/4 严格通过
- x86 + CPRO ARM64 回放 750 帧误差 0（ORT 1.22.0 必需）

### 官方起立/趴下轨迹（P10 录制）
- **起立三段**：预冲蓄力(thigh 过冲 0.99→1.52, ~1.2s) → 爆发抬升(hip 0.4s 猛摆 25+Nm, ~1.4s) → 收敛(~0.4s)
- **趴下三段**：卸力预备(~0.8s) → 折叠下放(~0.9s) → 收拢落位(~1.5s)
- 上述已复刻为**两段策略**入 MuJoCo 预演（6/6 全绿）与 `r152_publish.cpp`：
  - FixStand 两段：B1 预冲(kp=20, thigh +0.25, ~60%时间) + B2 起升(kp=55, ~40%时间)
  - FixSquat 两段：F1 折叠(kp=35, thigh +0.6, calf 折半, hip 打开, ~50%) + F2 收拢(kp=20, ~50%)

### MuJoCo 预演（P8, 全绿）
- FixStand(两段)→R152 接管→forward_slow 行走→停车→FixSquat(两段)：6/6 零跌倒
- 高度轨迹与官方模式一致（先降蓄力→再跃升）
- 非轮触地 0–10 N（低于 50 N 严格阈）

## 当前代码骨架（`r152_publish.cpp`，你的重构起点）

文件约 400 行，当前为**顺序定时执行**：
- 500 Hz writer 线程（发布 LowCmd，CRC，mode_machine 回显）
- 50 Hz 控制线程（按时间顺序走 Passive→FixStand→R152→FixSquat→Safe Passive）
- 看门狗（状态年龄>50ms/upright<−0.2/q 键/Ctrl-C → 锁定安全 Passive，不裸停发）
- `--i-confirm-lowcmd-publish` 强制确认 + Enter

**问题**：顺序定时设计意味着——狗自动推进阶段、遥控器只在 R152 状态下有效、退出策略基于未验证的假设。**必须重构。**

## 你的任务：重构为事件驱动 FSM + 遥控器控制

### 仿照 GO2 FSM 模式（`unitree_cpp_deploy-go2/deploy/include/FSM/`）

GO2 的核心设计模式：
1. **每个状态**是一个类，有 `enter()` / `run()` / `exit()` 方法
2. **转换**由遥控器按键触发（config.yaml 声明式定义），不是定时器
3. **全局安全规则**：`lowstate->isTimeout() → Passive`（任何状态下超时都退回安全态）
4. **状态机**持有 current_state，run() 循环调用 current_state->run()，转换时调用 exit/enter

### AS2-W FSM 状态设计

```
Passive（阻尼安全态，初始/兜底）
  ├── A 键 → FixStand
  └── （enter: kp=0, kd=param, q=跟随, 轮 dq=0）

FixStand（两段插值起立）
  ├── 插值完成 → 自动 → R152
  └── B 键 → 随时 → Passive

R152（策略控制行走）
  ├── 左摇杆 vx/vy、右摇杆 wz
  ├── B 键 → Passive（随时退出）
  ├── X 键 → FixSquat
  └── Y 键 → SelectMode 退出（待验证，默认禁用）

FixSquat（两段插值趴下）
  ├── 插值完成 → 自动 → Passive
  └── B 键 → 随时 → Passive

安全规则（全局）：
  - LowState 年龄 >50 ms → Passive
  - 姿态 upright < −0.2 → Passive
  - 控制器失活 → Passive
  - q 键 / Ctrl-C → Passive
  - B 键 → Passive
```

### 遥控器按键到 FSM 转换的映射

| 按键 | 位 | FSM 转换 |
|---|---|---|
| A | bit 8 | Passive → FixStand（前进） |
| B | bit 9 | **任何状态 → Passive（安全退出）** |
| X | bit 10 | R152 → FixSquat（受控趴下） |
| Y | bit 11 | R152 → SelectMode 退出（**默认禁用**，待验证后启用） |
| 左摇杆 ly | float 5 | R152 vx（限幅 0.2 起步） |
| 左摇杆 lx | float 1 | R152 vy |
| 右摇杆 rx | float 2 | R152 wz |

### 具体实现要求

1. **FSM 类结构**：每个状态独立类/结构体，enter() 里做快照/初始化，run() 每 tick 调用
2. **遥控器输入**：从 LowState 的 wireless_remote[40] 解码，**按 P6 标定的位图/浮点位置**
3. **命令解码**：ly→vx（×0.2 首测限幅）、lx→vy（×0.35）、rx→wz（×0.65），死区 ±0.05，松杆归零
4. **FixStand 两段**已在代码里（B1 kp=20 预冲 + B2 kp=55 起升），保留
5. **FixSquat 两段**已在代码里（F1 kp=35 折叠 + F2 kp=20 收拢），保留
6. **R152**：controller.arm() 清零 state（FixStand→R152 转换时调用一次），指令从遥控器实时读取
7. **Passive**：kp=0、kd=参数化（`--passive-kd`，默认 5）、q=跟随当前、轮 dq=0
8. **全局安全**：看门狗逻辑保留（年龄/姿态/键/q→Passive），**Passive 是唯一安全态**
9. **SelectMode 退出**：默认禁用（`#define` 或 bool 开关）；启用时：停止 writer → 调 RPC → 等待 rc → 退出程序
10. **发布端**：保持 500 Hz writer 线程结构，mode_machine 逐帧回显最新 LowState，CRC 每帧计算
11. **CMake 选项** `AS2W_R152_PUBLISH` 默认 OFF 保持不变
12. **日志**：每次状态转换打印一行（时间、旧状态、新状态、触发原因）

### 不要做的事

- 不要发布任何 LowCmd 到真机（除非现场人员明确同意当前具体动作）
- 不要假设 SelectMode 从站立接管的行为（未验证）
- 不要用 Xbox/键盘替代原厂遥控器（用户明确否决）
- 不要改动 R152 控制器/ONNX/映射文件的内容
- 不要去掉 `--i-confirm-lowcmd-publish` 强制确认

## 已知开发环境

- 源码唯一维护位置：`部署参考/cpp_deploy-as2w/`（Windows 工作站）
- 修改源码后：`部署测试/现场入口.ps1 -Stage Sync`（重打包传 CPRO）→ `-Stage SdkBuild`（CPRO ARM64 编译）
- 修改源码前在 Windows 或 WSL 编译检查（cmake + CTest 7 项应全通过）
- CPRO 上 ORT 1.22.0 aarch64 位于 `/root/ort122`
- yaml-cpp 0.7.0 已在 CPRO Ubuntu 预装
- R152 模型/映射在 CPRO `/root/as2w_deploy/models/r152/` 和 `config/r152_measured.map`
- `现场入口.ps1` 现有阶段：Sync/SdkBuild/GetState/LowState/LowRemote/LowCapture(Fast)/LowCrc/MotionMode/MotionRelease/MotionSelect/R152Build/R152Replay/R152Shadow

## 硬性规则

- **任何可能让狗动作的命令，先告知现场人员具体动作，等其当次明确同意才发**
- `hardware_contract.md` 未填项（SelectMode 从站立的行为、LowCmd 命令方向、失联超时）补齐前不发布 LowCmd 到真机
- 每完成阶段或失败，立即追加 `INDEX.md` 并把原始日志放 `04_调试记录/logs/`
- C++ 改动后必须编译检查（至少 ctest 7/7 通过）再 Sync
- 现场入口 `-Seconds` 上限 300

## 产出顺序

1. 重构 `r152_publish.cpp` 为 FSM + 遥控器事件驱动
2. Windows/WSL 编译检查通过（ctest 7/7）
3. Sync + SdkBuild 到 CPRO ARM64
4. **向现场人员报告重构完成，等待同意后才上真机**
5. 真机测试按 `实机测试链方案_R152.md` S0–S9 逐步执行

现在开始：先通读文件（尤其 `r152_publish.cpp` 现有代码和 GO2 FSM 参考），然后直接重构。完成后报告我，等我确认再进实机。
