# 宇树 AS2-W RL 策略部署改造指南
## 基于 Go2 v0.6.6 改造经验的全量迁移手册

> 日期：2026-11-07
> 目标读者：将 Go2 RL 策略 C++ 部署链（`unitree_cpp_deploy_v0.6.6`）迁移到宇树 AS2-W 本体的工程师
> 约束：AS2-W 具体策略细节未知（预估为 MLP 网络，参数待定），故本文聚焦**平台级差异**与**改造模式复用**，而非策略内部
> 配套文档：`Docs/Go2_v0.6.6_Migration/01_Migration_Design.md`、`02_Migration_Completed.md`、`Docs/onnxruntime_jetson_orin_crash_analysis.md`

---

## 0. 阅读导航

本文分四部分，按需阅读：

| 部分 | 内容 | 适用场景 |
|---|---|---|
| **Part 1** | golden reference 获取与 v0.6.6 改动全量对比 | 理解"v0.6.6 相对标准 reference 改了什么、为什么改" |
| **Part 2** | `go2_v066_xbox_wifi_workstation.sh` 一键脚本深度拆解 | 复用 pre-check / pre-action / launch / cleanup 模式 |
| **Part 3** | AS2-W 平台特性与 Go2 差异 | 决定"哪些必须改、哪些可复用" |
| **Part 4** | AS2-W 部署改造步骤清单 + 待验证项 | 落地执行 |

---

# Part 1 — v0.6.6 vs Upstream Golden Reference 改动对比

## 1.1 参考仓库获取

Golden reference 已拉取到：

```
/home/robot/z00959834/robogauge_5090/cpp_stack/robogauge_code/unitree_cpp_deploy_robogauge_upstream
```

- 来源：`https://github.com/wty-yy/unitree_cpp_deploy`，分支 `go2`
- HEAD commit：`4f71bf3 Update README`
- 文件数：50（纯源码 + 文档 + 模型）
- 用途：**golden reference**，后续 AS2-W 改造的起点应基于此（而非基于已重度魔改的 v0.6.6）

> ⚠️ 重要决策：AS2-W 改造应从 **upstream** 起步，按本文 Part 1 识别出的"通用改造模式"叠加，**不要**直接 fork v0.6.6——v0.6.6 含大量 Go2 专属硬编码（关节名、姿态、模型路径、UDP magic "GO2C"），直接 fork 会带入这些噪声。

## 1.2 文件级改动总览

| 类别 | upstream 文件数 | v0.6.6 文件数 | 说明 |
|---|---|---|---|
| 共享源文件（两者都有） | 40 | 40 | 其中 18 个被修改 |
| v0.6.6 新增 | — | 78（含 ~50 个 thirdparty/二进制） | 真正新增源码约 6 个 |
| v0.6.6 删除 | 8 | — | 主要是旧模型/checkpoint，无源码删除 |
| v0.6.6 新增构建产物 | — | ~160（build_bench/, benchmark/） | 非源码，应忽略 |

**真正需要关注的改动**：18 个修改文件 + 6 个新增源文件。其余是 vendored 的 onnxruntime/cnpy 二进制与 build 产物。

## 1.3 18 个修改文件分类详解

### A. 构建系统（CMakeLists.txt）

**`deploy/robots/go2/CMakeLists.txt`** — 构建系统重写

| 改动 | upstream | v0.6.6 | 性质 |
|---|---|---|---|
| SDK 链接 | 直接 link `unitree_sdk2` lib + 手动 DDS include | `find_package(unitree_sdk2 REQUIRED)`（`/opt/unitree_robotics/lib/cmake`） | **通用模式** |
| ONNX Runtime 选型 | GPU 变体（`aarch64-gpu-1.16.0`、`x64-gpu-1.24.2`） | CPU 变体（`aarch64-1.23.2`、`x64-1.23.2`），按 `CMAKE_SYSTEM_PROCESSOR` 自动切换 | **通用模式**，版本号 GO2 专属 |
| .so 定位 | 硬编码 `libonnxruntime.so` | `file(GLOB ORT_LIBS ".../libonnxruntime.so.[0-9]*.[0-9]*.[0-9]*")` | 通用 |
| fmt 链接 | 总是 link | x64 link，aarch64 skip（focal 无 libfmt，spdlog 自带） | GO2 Jetson 专属 |
| benchmark 开关 | 无 | `option(ROBOGAUGE_BENCHMARK OFF)` → `target_compile_definitions(... PRIVATE ROBOGAUGE_BENCHMARK)` | 通用模式 |

### B. FSM / 控制环

**`deploy/include/FSM/CtrlFSM.h`** — 通用加固
- `start()` 新增空 `states` 向量守卫（upstream 会越界崩溃）
- 新增 `getCurrentMode()` / `stopThread()` 访问器，供 main.cpp 优雅退出与 benchmark 退出检测
- **完全通用，AS2-W 直接复用**

**`deploy/include/FSM/State_Fix.h`** — ⚠️ 安全关键补丁：增益渐变防抖
- upstream：进入 FixStand 立即设 `kp_[i]/kd_[i]`（站立刚度 ~60-80），从 RL（kp=20）跳变 → 剧烈抖动
- v0.6.6：进入时用 `RL_KP=20.0, RL_KD=0.5`，读取**实际**关节角（非命令角）作 `q0`，保持 0.3s（`HOLD_TIME`）让步态稳定，再在 1.5s（`RAMP_TIME`）内线性渐变 kp/kd 与姿态到目标
- **模式通用**（先稳再刚），**常量 GO2 专属**：`RL_KP/RL_KD` 必须匹配 AS2-W 策略的 `deploy.yaml` stiffness/damping，目标姿态 `qs_` 必须匹配 AS2-W 站立 `default_joint_pos`
- 与 memory `[feedback_go2_exit_strategy]`（行走退出应先回 FixStand 再 Passive）一致

**`deploy/include/FSM/State_RLBase.h`** — 新功能叠加
- `#ifdef ROBOGAUGE_BENCHMARK` 块：per-RL-state CSV DataLogger，记录 `loop_period_ms / inference_ms / obs_build_ms`
- 新增 `set_keyboard_velocity(vx,vy,vyaw)` / `stop_keyboard_velocity()` / `has_env()`：绕过手柄，直接写 `env->fixed_command_*` 字段
- **通用模式**：键盘/UDP 速度注入路径；benchmark 脚手架的 `RLStats` 结构硬编码 12 关节，AS2-W 需参数化 DOF

**`deploy/robots/go2/src/State_RLBase.cpp`** — 配置扁平化 + auto_start
- `cfg["logging"]["enabled"]` → 扁平 `cfg["logging"]`（bool）/ `cfg["logging_dt"]`（double）
- 新增 `fixed_command.auto_start`：进入状态即激活 fixed_command（无需手柄 L2+Y），sim-test/benchmark 必需
- **完全通用**

### C. 观测 / 动作管理器

**`deploy/include/isaaclab/envs/manager_based_rl_env.h`**
- 新增 `motion_loader->reset()/update()` 钩子（null-safe，Go2 不构造 MotionLoader，纯惰性）
- `step()` 内加 `ROBOGAUGE_BENCHMARK` 计时（obs build vs inference 分离）
- 移除 `boost_active()` 访问器（见 VelocityCommandDamper）
- **通用**：motion_loader 钩子 null-safe 可保留；benchmark 计时通用

**`deploy/include/isaaclab/assets/articulation/articulation.h`**
- `ArticulationData` 新增 `MotionLoader* motion_loader = nullptr`
- 惰性字段，Go2 不用，**通用保留**

**`deploy/include/isaaclab/algorithms/algorithms.h`** — GO2 Jetson 专属补丁
- 新增 `session_options.SetIntraOpNumThreads(1);`
- 原因：Jetson Orin 4 核，ORT 默认线程池请求 CPU affinity mask `{6,}` 越界 → `pthread_setaffinity_np` EINVAL → cpuinfo vector OOB abort
- **GO2/Jetson-Orin 专属**：AS2-W 若用同款 Jetson 保留；x86 或大核 Jetson 无害可留
- 详见 `Docs/onnxruntime_jetson_orin_crash_analysis.md`

### D. 输入设备（keyboard.h — 259 行重写）

**`deploy/include/isaaclab/devices/keyboard/keyboard.h`** — 线程安全 + 边沿检测
- upstream：reader 线程写 `_key`，`key()` 读，存在 data race；无超时，auto-repeat 会重复触发
- v0.6.6：
  - `std::mutex` 守护所有共享状态
  - `std::atomic<bool> _running`
  - `KEY_TIMEOUT_MS=300`：`key()` 仅在 300ms 内返回上次按键，否则返回 `""` → press-to-set 语义
  - termios 在 ctor/dtor/`getString()` 集中处理
  - `_read()` 用局部 `fd_set`/`timeval`，检查 `read()` 返回值
  - 类注释明确说明 Linux 终端无 key-release 事件，推荐 press-to-set
- **完全通用，严格优于 upstream，任何机器人可复用**

### E. 安全 / 速度阻尼（VelocityCommandDamper.h）

**`deploy/include/utils/VelocityCommandDamper.h`** — 删除 boost 子系统
- 移除 `#include "unitree_joystick_dsl.hpp"`、`configure_boost()`、`boost_active_`、`boost_button_`、`boost_command_ranges_`、`boost_active()` 访问器
- `parse_range()` 同时删除了**有限性 + 跨零校验**——⚠️ 轻微安全回退
- 核心阻尼（速度相关一阶 vx 滤波 + 加减速限制）保留
- **通用**：boost 是手柄专属，AS2-W 无手柄场景不需要；**但建议 AS2-W 恢复 `parse_range()` 校验**

### F. 配置 / 参数

**`deploy/robots/go2/config/config.yaml`** — GO2 专属值 + 结构简化
- FixStand 目标姿态改为匹配 RL 策略 `default_joint_pos`（消除 FixStand↔Velocity 跳变）——**模式通用，值 GO2 专属**
- 4 个 `Velocity_*` 的 `policy_dir` 切到 `../../../logs/rsl_rl/...`（本地训练模型）
- `Velocity_Up`：移除 `boost_button: RT`，加 `fixed_command` 块（enabled:false）
- `Velocity_Down`：启用 `velocity_command_damping`（speed_points `[0,1,2,4]`，time_constants `[0,0,0.4,0.6]`，max_accel 4.0，max_decel 3.0）
- `Velocity_Right`：扁平 `logging: false / logging_dt: 0.01`


**`deploy/include/param.h`** — 11 个新 CLI 选项
- `--domain_id,-i`（默认 0，DDS 域 ID，upstream 硬编码 0）
- `--fixstand_test / --rl_zero_test / --rl_cmd_test`（仿真自动测试）
- `--cmd_x / --cmd_y / --cmd_yaw / --cmd_duration`（RL 测试命令参数）
- `--test_policy_dir`（默认 `../../../logs/rsl_rl/go2_robotlab_official_176k`，GO2 专属）
- `--keyboard` / `--udp_input` / `--udp_port`（默认 4396）/ `--benchmark` / `--policy_dir`
- `load_config_file()`：build 目录匹配从 `bin|build` 扩展为 `build*` 前缀（支持 `build_bench/`），config.yaml 缺失则 `exit(1)`
- **CLI 接口通用，默认 policy_dir GO2 专属**

### G. 新增模块（v0.6.6 独有）

| 文件 | 用途 | 在 Go2 是否激活 | AS2-W 处置 |
|---|---|---|---|
| `deploy/include/BenchmarkCollector.h` | header-only benchmark 统计（FixStand/RL per-joint 跟踪/力矩/计时 + p99/50Hz 合规率） | 是（benchmark 模式） | **需参数化 DOF**：`RLStats`/`FixStandStats` 硬编码 12 关节 |
| `deploy/include/isaaclab/envs/mdp/commands/motion_command.h` | `MotionLoader`：读 Unitree CSV 动作文件，有限差分算关节速度，时间索引插值 | 否（G1 Mimic 遗留，惰性） | 若 AS2-W 需动作回放则激活，否则保留惰性 |
| `deploy/include/isaaclab/envs/mdp/observations/motion_observations.h` | `motion_joint_pos/vel/command` 观测项 | 否（无任何 Go2 源 include） | 同上 |
| `deploy/thirdparty/cnpy/` | NumPy `.npy/.npz` 读写（G1 BFM/OmniXtreme 用） | 否（无 Go2 源引用） | 保留惰性 |
| `deploy/thirdparty/onnxruntime-linux-aarch64-1.20.1/` | Jetson 用 ORT 1.20.1（与 cpuinfo_jetson_fix.so 配套） | 是（Go2 本机） | AS2-W 若 Jetson 同款可复用 |
| `deploy/thirdparty/onnxruntime-linux-x64-1.23.2/` | x86 工作站用 ORT 1.23.2 | 是（工作站） | 复用 |

### H. main.cpp（928 行重写 — 最大改动）

upstream main.cpp ~57 行：`init_fsm_state()` + 构 FSM + 打印手柄说明 + `while(true) sleep(1)`。v0.6.6 main.cpp ~923 行，新增能力：

| # | 能力 | 实现 | 性质 |
|---|---|---|---|
| 1 | CLI 模式分发 | fixstand_test / rl_zero_test / rl_cmd_test / benchmark / keyboard / udp_input / policy_dir，含互斥校验与安全 clamp | **通用模式**，clamp 值 GO2 专属 |
| 2 | DDS 域 ID 参数化 | `ChannelFactory::Init(vm["domain_id"], vm["network"])` | **通用** |
| 3 | 内存 YAML 改写 | test/benchmark 模式运行时改 `Velocity_Up.policy_dir` 与 `fixed_command` | **通用** |
| 4 | MotionSwitcher 预检门 | 真机启动前检查 `MotionSwitcherClient.CheckMode()`，若 sport_mode 未释放则拒绝启动（防 lowcmd 通道冲突） | **通用，任何 Unitree 机器人复用** |
| 5 | Benchmark 生命周期 | stack 分配 `Collector`，时间戳 CSV 目录，`benchmark::global()` | 通用（DOF 需参数化） |
| 6 | UDP 输入模式 | 24 字节包 `{seq, magic=0x474F3243("GO2C"), vx, vy, vyaw, mode_request, enable, deadman, reserved}`，100ms recv 超时，300ms deadman 超时，seq 跳变检测 | **通用模式**，magic 值 GO2 专属（AS2-W 改 "AS2C"） |
| 7 | 手动 FSM `registered_checks` | 键盘 `f/r/z`、UDP `f/r/z/x`、sim-test 自动定时器（2s/6s/6+duration）、benchmark 定时器（2s/9s/14s）、`f` 从任意 Velocity 回 FixStand、SIGINT→Passive | **通用模式**，定时器值 GO2 专属 |
| 8 | 键盘速度控制 | W/A/S/D/Q/E 累加 ±0.5（clamp ±1.0），Space 归零，`last_processed_key` 边沿检测，`set_keyboard_velocity()` 注入 | **通用模式**，步长/限速 GO2 专属 |
| 9 | UDP 速度控制 | 20ms 持续注入，deadman/timeout/mode_request 处理 | **通用** |
| 10 | 优雅退出 | SIGINT 设 `g_should_exit`+`g_request_passive`，主循环退出，等 ≤3s 回 Passive，`fsm->stopThread()`，join UDP 线程，打印 benchmark summary | **通用** |
| 11 | Benchmark summary 打印器 | per-joint FixStand+RL 跟踪/力矩表、inference p99、50Hz 合规率、温度增量，存 `summary.txt` | 通用（DOF 参数化） |

## 1.4 改动模式分类总结

| 模式类别 | 通用程度 | AS2-W 处置 |
|---|---|---|
| **FSM 访问器**（getCurrentMode/stopThread） | 通用 | 直接复用 |
| **键盘重写**（线程安全 + 300ms 边沿） | 通用 | 直接复用 |
| **auto_start fixed_command** | 通用 | 直接复用 |
| **优雅退出**（SIGINT→Passive→stopThread） | 通用 | 直接复用 |
| **MotionSwitcher 预检门** | 通用 | 直接复用 |
| **手动 registered_checks 框架** | 通用 | 直接复用，重绑按键/状态名 |
| **键盘/UDP 速度注入** | 通用 | 直接复用，调步长/限速 |
| **CLI 接口**（11 个新选项） | 通用 | 直接复用，改默认 policy_dir |
| **CMake arch-conditional ORT** | 通用 | 复用，调版本/路径 |
| **扁平 logging 配置键** | 通用 | 直接复用 |
| **State_Fix 增益渐变防抖** | 模式通用 | 复用结构，调 RL_KP/KD/HOLD/RAMP + 目标姿态 |
| **FixStand 目标姿态 == RL default_joint_pos** | 模式通用 | 复用，填 AS2-W 值 |
| **benchmark 计时/统计** | 模式通用 | 复用，参数化 DOF |
| **UDP magic "GO2C"** | GO2 专属 | 改 "AS2C" |
| **JOINT_NAMES[12] / 12 关节假设** | GO2 专属 | 参数化为 AS2-W DOF |
| **kb_vel_step=0.5/limit=1.0** | GO2 专属 | 按 AS2-W 速度包络调 |
| **sim-test 定时器 2s/6s/9s/14s** | GO2 专属 | 按 AS2-W 物理稳定时间调（参考 memory `[experience_go2_fsm_test_pacing]`：FSM 切换需 5-10s 间隔） |
| **Jetson cpuinfo fix + SetIntraOpNumThreads(1)** | Jetson 专属 | AS2-W 若同款 Jetson 复用，否则去掉 |
| **policy_dir 路径 / 模型名** | GO2 专属 | 换 AS2-W 模型 |
| **VelocityCommandDamper boost 删除** | 通用 | 复用删除，但**恢复 parse_range 校验** |

---

# Part 2 — `go2_v066_xbox_wifi_workstation.sh` 一键脚本深度拆解

## 2.1 脚本定位与架构

- 文件：`cpp_stack/robogauge_code/go2_v066_xbox_wifi_workstation.sh`（291 行）
- 用途：从工作站 USB-C Xbox 手柄经 WiFi UDP 驱动 Go2 v0.6.6 RL 策略
- 架构：
  ```
  Xbox 手柄 →USB-C→ 工作站 controller_sender.py →UDP/WiFi 50Hz→ GO2 go2_ctrl --udp_input
  ```
  控制环跑在 **Go2 Orin** 上（DDS over `eth0` 到 MCU），WiFi 仅承载 SSH 启动命令与 UDP 手柄流
- 兄弟脚本对比（keyboard/benchmark）：配置块、SSH helper、pre-flight 1-3 步完全相同，仅 Step 0（手柄发现）与 Step 4（UDP 启动 + controller_sender）是 Xbox 专属

## 2.2 配置变量（L26-43）

| 变量 | 默认值 | 用途 | 可调 |
|---|---|---|---|
| `GO2_USER` | `unitree` | Go2 SSH 用户 | 硬编码（Unitree 默认） |
| `GO2_WIFI_IP` | `192.168.31.126` | Go2 wlan0 IP | 按 Go2 改 |
| `GO2_IFACE` | `eth0` | **Go2 上** DDS 网卡（朝 MCU） | 硬编码 |
| `GO2_DEPLOY_DIR` | `/home/unitree/robogauge_v066` | Go2 部署根目录 | 硬编码 |
| `GO2_CTRL_BIN` | `${DEPLOY_DIR}/deploy/robots/go2/build/go2_ctrl` | 控制器二进制 | 派生 |
| `GO2_SDK2_LIB` | `${DEPLOY_DIR}/sdk2_install/lib` | SDK2 共享库路径 | 派生 |
| `GO2_CPUINFO_FIX` | `${DEPLOY_DIR}/cpuinfo_jetson_fix.so` | Jetson cpuinfo LD_PRELOAD shim | Jetson 专属 |
| `LOCAL_WIFI_IFACE` | `enp5s0f0` | 工作站 WiFi 网卡 | 按主机改 |
| `GO2_PASS` | `${GO2_PASS:-123}` | sshpass 密码 | **用户可调（env）** |
| `GO2_POLICY_DIR_DEFAULT` | `.../go2_moe_cts_137k_0.6713` | 默认策略目录 | 硬编码 |
| `UDP_PORT` | `4396` | UDP 手柄流端口 | `--port` 可调 |
| `CONTROLLER_DIR` | `/home/robot/z00959834/go2_xbox_controller/scripts` | controller_sender.py 位置 | 硬编码 |
| `POLICY_DIR` | `${POLICY_DIR:-$DEFAULT}` | 实际策略目录 | env 或 `--policy_dir` |

参数解析（L48-66）：`--policy_dir <path>` / `--policy_dir=<path>` / `--port <n>`，未知参数 → `die`。

## 2.3 Pre-check 阶段（L87-200）

脚本用 `set -euo pipefail`（L24）作底线，但每个关键检查都是显式 `if ! ...; then die ...; fi`，**不依赖短路**。

### Pre-flight（L87-92）
- L88-90 `[ ! -t 0 ]` → `die`：**硬失败**，防止 cron/管道输入下 evdev/trap 语义失效
- L92 `unset LD_LIBRARY_PATH LD_PRELOAD`：防御性清除，防工作站环境污染 SSH 启动的 Go2 进程

### Step 0 — Xbox 手柄（L97-132，全硬失败）
| 检查 | 行 | 内容 | 失败动作 |
|---|---|---|---|
| 0a | 99-102 | `controller_sender.py` 存在 | `die` |
| 0b | 105-108 | `python3 -c "import evdev"` | `die` + 安装提示 |
| 0c | 111-126 | evdev 扫描设备名含 `xbox`/`microsoft`，设 `XBOX_DEVICE` | `die`（提示 USB-C 连接） |
| 0d | 129-132 | `which sshpass` | `die` + apt 提示 |

### Step 1 — WiFi 链路（L137-152，全硬失败）
| 检查 | 行 | 内容 |
|---|---|---|
| 1a | 139-142 | `ip link show $LOCAL_WIFI_IFACE` 含 `state UP` |
| 1b | 144-147 | `ping -c 3 -i 0.2 -W 2 $GO2_WIFI_IP` |
| 1c | 149-152 | `ssh_go2_q 'true'`（SSH 往返） |

### Step 2 — 部署校验（L157-177，全硬失败）⚠️ 最高价值模式
| 检查 | 行 | 内容 |
|---|---|---|
| 2a | 159-163 | Go2 上 `[ -x $GO2_CTRL_BIN ]`（二进制存在且可执行） |
| 2b | 166-170 | `${GO2_CTRL_BIN} --help` 输出含 `udp_input`（功能开关校验） |
| 2c | 173-177 | `[ -d $POLICY_DIR ] && [ -f $POLICY_DIR/exported/policy.onnx ] && [ -f $POLICY_DIR/params/deploy.yaml ]`（策略清单） |

> **三层契约**（二进制 / 功能标志 / 策略文件）是全脚本最可复用的单点模式。AS2-W 必须复用，仅改文件清单（若 AS2-W 用 TorchScript/TRT 则换路径）。

## 2.4 Pre-action 阶段

脚本**不做**本地网络配置、cmake/make、模型 staging、日志目录创建——这些由前置 `go2_v066_wireless.sh deploy/sync` 完成。本脚本的 pre-action 仅为：
1. 环境清除（L92）
2. 参数解析（L46-66）
3. 手柄发现（Step 0c）
4. 打印操作员简报（L207-235，按键映射 + 安全提示，纯信息）

启动命令（L242）内嵌的环境设置：
- `LD_LIBRARY_PATH=${GO2_SDK2_LIB}:${LD_LIBRARY_PATH}`
- `LD_PRELOAD=${GO2_CPUINFO_FIX}`（Jetson 专属）
- `cd ${GO2_DEPLOY_DIR}/deploy/robots/go2`
- `-n ${GO2_IFACE}` / `-i 0` / `--udp_input --udp_port ${UDP_PORT}` / `--policy_dir ${POLICY_DIR}`

## 2.5 Launch 阶段（L205-277）

### 双进程架构
1. `go2_ctrl --udp_input` 跑在 **Go2** 上，`nohup` 后台（L242-248）
2. `controller_sender.py` 跑在 **工作站** 前台（L275-277）

### Go2 启动（L245-248）
```bash
sshpass -p "$GO2_PASS" ssh -o ConnectTimeout=8 -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null -o ServerAliveInterval=5 \
    "${GO2_USER}@${GO2_WIFI_IP}" \
    "nohup bash -c '${GO2_LAUNCH_CMD}' > /tmp/go2_ctrl_udp.log 2>&1 &"
```
- `nohup ... &` 脱离，SSH 会话可返回
- `bash -c` 包裹让 env-vars + cd 一起生效
- `> /tmp/go2_ctrl_udp.log 2>&1` 捕获远端输出

### 启动后验证（L249-256）
- `sleep 3` 固定等待
- `pgrep -x go2_ctrl` 复查
- 失败则 dump Go2 日志 + `die`
- **必须验证后台远端进程真的起来了**

### 工作站启动（L275-277）
```bash
python3 -u "${CONTROLLER_DIR}/controller_sender.py" "${XBOX_DEVICE}" \
    --host "${GO2_WIFI_IP}" --port "${UDP_PORT}"
RC=$?
```
- `-u` 无缓冲，操作员实时看输出
- 前台阻塞，退出捕获 `RC`

### 手柄集成机制
**非 jstest / 非 ROS joy / 非 SDL / 非 SDK joystick**。自定义 Python + **evdev** 读原始输入事件，归一化摇杆到 `{-1..1}`，UDP 50Hz 发包。Go2 侧收包后调 `set_keyboard_velocity()`。**输入在工作站，控制在 Go2**，干净分离。

### 进程管理
- Go2 后台 nohup
- 工作站前台
- `trap cleanup EXIT`（L273）在**前台命令运行前**安装
- 无 SIGINT 专属 handler，trap 在任何退出（正常/异常）时触发

## 2.6 Runtime / Monitoring

- 启动前打印按键映射 + 安全提示（L207-235），含：摇杆回中速度自然归零、低通滤波 + Go2 侧 vx 阻尼、UDP 300ms 超时自动归零（failsafe）、Y 键是软件 passive stop 非物理急停
- 运行中**不 tail 日志**，Go2 日志静默写 `/tmp/go2_ctrl_udp.log`
- 退出后拉最后 20 行（L286-289）调试

### 优雅关闭（L265-273）
```bash
cleanup() {
    log_info "停止 GO2 上的 go2_ctrl..."
    ssh_go2_q "pkill -INT -x go2_ctrl 2>/dev/null || true"
    sleep 1
    ssh_go2_q "pkill -x go2_ctrl 2>/dev/null || true"
    log_info "清理完成。"
}
trap cleanup EXIT
```
- SIGINT 先发，等 1s，SIGTERM
- 两 `pkill` 都 `|| true` + `2>/dev/null`，进程不存在不报错
- 与 Step 3 残留清理同套升级模式

## 2.7 Post-run 清理

**恢复**：仅杀 Go2 上 go2_ctrl 进程
**遗留**：`/tmp/go2_ctrl_udp.log`（下次 `>` 覆盖）、部署树、策略文件（下次复用）
**无网络状态回滚**（因为未做任何网络配置）

## 2.8 安全 / 健壮性模式

- `set -euo pipefail` 底线 + 显式 `if ! ...; then die` 检查
- 自定义 helper：`log_info/log_pass/log_fail/log_step/die`（die 写 stderr + `exit 1`）
- 所有 `die` 含**修复提示**（如 `pip3 install evdev`、`bash ... wireless.sh deploy`）
- SSH 鲁棒：`ConnectTimeout=8`（快失败）、`StrictHostKeyChecking=no` + `UserKnownHostsFile=/dev/null`（专用机器人网络可接受）、`ServerAliveInterval=5`（检测 WiFi 中断）
- **幂等**：Step 3 显式杀残留，可安全重跑
- `/tmp/go2_ctrl_udp.log` `>` 覆盖非追加，无日志膨胀
- 无回滚机制（因无破坏性 setup），唯一"回滚"是 `trap cleanup EXIT`
- 若 go2_ctrl 启动失败，`die` 在 `trap` 安装前（L252 验证在 L273 trap 前），无伪清理
- Failsafe：Go2 侧 300ms UDP 超时自动归零（`go2_ctrl` 内实现，非本脚本）

## 2.9 复用清单（AS2-W 改造）

### 直接复用（通用脚手架）
1. `set -euo pipefail` 头部
2. 配置块结构 + "keep in sync with deploy script" 注释
3. 参数解析器（`--policy_dir` / `--port` + `die "Unknown arg"`）
4. 日志 helper（`log_info`/`log_pass`/`log_fail`/`log_step`/`die`）
5. SSH helper（`sshpass` + 四个 `-o` 安全标志）—— 注意脚本里 `ssh_go2` 与 `ssh_go2_q` 字节相同，AS2-W 只保留一个
6. 交互终端守卫（`[ ! -t 0 ]`）
7. 环境清除守卫（`unset LD_LIBRARY_PATH LD_PRELOAD`）
8. Pre-flight Step 0 模式（输入设备：脚本存在 / Python 依赖 / 设备枚举 / sshpass）
9. Pre-flight Step 1 模式（网卡 UP + ping + SSH 往返，**只验证不配置网络**）
10. Pre-flight Step 2 模式（三层契约：二进制 / 功能标志 / 策略文件）
11. Pre-flight Step 3 模式（pgrep 残留 → SIGINT → sleep → SIGTERM → sleep → 复查 → die）
12. 操作员简报块（启动前打印按键/轴映射 + 安全提示）
13. 远程启动 `nohup bash -c '...' > /tmp/xxx.log 2>&1 &`
14. 启动后验证（`pgrep -x` + 失败 dump 日志 + die）
15. `trap cleanup EXIT` + SIGINT→SIGTERM 升级，**trap 在阻塞前台调用前安装**
16. 退出后日志 tail
17. 退出码透传（前台工具 RC → 脚本 RC）

### AS2-W 必改项
| 项 | Go2 值 | AS2-W 处置 |
|---|---|---|
| `GO2_USER` | `unitree` | AS2-W 用户（若仍 Unitree SDK 大概率 `unitree`） |
| `GO2_WIFI_IP` | `192.168.31.126` | AS2-W WiFi IP |
| `GO2_IFACE` | `eth0` | AS2-W 朝 MCU 的 DDS 网卡 |
| `GO2_DEPLOY_DIR` | `/home/unitree/robogauge_v066` | 新部署根，如 `robogauge_as2w_xxx` |
| `GO2_CTRL_BIN` | `.../go2/build/go2_ctrl` | `.../as2w/build/as2w_ctrl` |
| `GO2_SDK2_LIB` | `.../sdk2_install/lib` | AS2-W SDK lib 路径，**若 AS2-W 用非 SDK2 则换** |
| `GO2_CPUINFO_FIX` | `cpuinfo_jetson_fix.so` | AS2-W 非 Jetson 或无 cpuinfo bug 则去 `LD_PRELOAD` |
| `LOCAL_WIFI_IFACE` | `enp5s0f0` | 工作站网卡（同机则不变） |
| `GO2_PASS` | `123` | AS2-W 默认密码（大概率 `123`，确认） |
| `GO2_POLICY_DIR_DEFAULT` | `.../go2_moe_cts_137k_0.6713` | AS2-W 策略目录 |
| `CONTROLLER_DIR` | `.../go2_xbox_controller/scripts` | 复用同 Xbox→UDP 栈则不变 |
| `--udp_input`/`--udp_port` | go2_ctrl 功能 | AS2-W 控制器需支持同标志，否则改接收接口 |
| 策略清单契约（L173） | `exported/policy.onnx` + `params/deploy.yaml` | 若 AS2-W 用 TorchScript/TRT 换路径 |
| 简报按键映射（L211-225） | Go2 FixStand/Passive/Velocity_Up | 重写为 AS2-W FSM 状态 |
| 速度限幅（L221-223） | `vx ±2.0`/`vy ±1.0`/`vyaw ±2.0` | AS2-W 速度包络 |
| `set_keyboard_velocity()` | Go2 SDK2 API | AS2-W 速度注入 API 名可能不同 |

---

# Part 3 — AS2-W 平台特性与 Go2 差异

> ⚠️ **来源说明**：以下基于本地 SDK 代码（`cpp_stack/unitree_sdk2`、`cpp_stack/unitree_mujoco`）与已 vendored 的 `unitree_hg` IDL 头文件。**所有外部网络检索被企业网络墙阻断**，无法访问 unitree.com / GitHub / support.unitree.com。涉及在线确认的项明确标注 **未验证**。

## 3.1 命名警告（最高优先级）

本地 SDK 一致使用标识符 **`as2`**（小写，无 `-W` 后缀）。字符串 `AS2-W`、`AS2W`、`A2-W` 在 `/home/robot/z00959834/robogauge_5090` 全仓**不出现**。

**无法从本地源确认 "AS2-W" 是否等于 SDK 的 `as2`**，或是一个变体（类比 `go2`/`go2w` 轮式、`b2`/`b2w` 轮式）。SDK 有 `go2/go2w`、`b2/b2w` 对但**无 `as2w`**，故 "AS2-W" 可能是 AS2 的轮式变体——**此为推测，必须向宇树官方确认**。

> **行动项**：联系宇树确认 "AS2-W" 是否等同 SDK `as2`，或为轮式变体。这直接决定 IDL 选择与关节布局。

## 3.2 AS2 平台特性（本地 SDK 验证）

### A. 机器人形态 — 已验证：四足，12 DOF

MuJoCo 模型 `cpp_stack/unitree_mujoco/unitree_robots/as2/as2.xml` 明确：四足，与 Go2/Aliengo 同体型。
- 4 腿：FL, FR, RL, RR
- 每腿 3 关节：`hip`（外展，X 轴）、`thigh`（屈伸，Y 轴）、`calf`（屈伸，Y 轴）
- 12 驱动 DOF + 1 floating base
- 驱动器顺序：`FR_hip, FR_thigh, FR_calf, FL_hip, FL_thigh, FL_calf, RR_hip, RR_thigh, RR_calf, RL_hip, RL_thigh, RL_calf`
- **关节命名与 Go2 完全一致**，驱动顺序也与 memory `[go2_standard_folded_pose]` 的 "policy order" 一致

### B. 关节范围与力矩（已验证，as2.xml）

| 关节类 | 范围 (rad) | 力矩 (Nm) | 阻尼 | 备注 |
|---|---|---|---|---|
| hip | [-0.785, 0.785] | ±60 | 0.2 | |
| thigh (FL/FR) | [-2.0, 3.492] | ±60 | 0.2 | |
| thigh (RL/RR) | [-1.3, 4.19] | ±60 | 0.2 | **后腿范围更宽，与 Go2 不同** |
| calf | [-2.7677, -0.8133] | ±90 | 0.5 | **力矩 90 vs hip/thigh 60** |

基座质量 **11.178 kg**（Go2 ~15 kg），**比 Go2 轻**。足半径 0.028m。大腿 0.212m，小腿 0.21344m——几何接近 Go2。

> ⚠️ 后腿 thigh 范围与前腿不同，是相对 Go2 的小不对称。calf 力矩上限 90Nm 高于 hip/thigh 60Nm——动作裁剪与力矩饱和阈值需按 AS2-W 调。

### C. 计算单元 — 未验证

本地 SDK 无硬件信息。**推测**：因 AS2 用同款 `unitree_sdk2`（CycloneDDS over ethernet），部署模型应与 Go2 一致——外部 PC 连机器人以太网，DDS 发 `LowCmd` 收 `LowState`。AS2 是否有 onboard Jetson 跑 high-level sport 服务（如 Go2 sportmode）未确认，但 `as2::SportClient` 存在暗示有。

### D. SDK 接口 — 已验证：同 `unitree_sdk2`，但 `unitree_hg` IDL

**这是 RL 部署最关键的平台差异。**

来源 `cpp_stack/unitree_mujoco/readme.md`：
> - Unitree Go2, B2, H1, B2w, Go2w 用 **unitree_go** idl 做低层通信
> - Unitree G1, H1-2, **AS2** 用 **unitree_hg** idl 做低层通信

`simulate/src/param.h:30`：
```cpp
idl_type = robot == "as2" || actuator_count > IDL_GO_MOTOR_LIMIT ? IDL_HG : IDL_GO;
```
`IDL_GO_MOTOR_LIMIT = 20`，`IDL_HG_MOTOR_LIMIT = 35`。

AS2 共享 SDK 外壳（`ChannelFactory`、CycloneDDS），但低层电机消息用**不同 IDL 命名空间**（`unitree_hg` vs `unitree_go`）。这是 Unitree 人形（G1/H1-2）同款 IDL。high-level sport client 在独立命名空间 `unitree::robot::as2::SportClient`。

### E. 网络接口 — 推测同 Go2

`as2_sport_client.cpp` 取 `argv[1]` 作 `networkInterface`，调 `ChannelFactory::Instance()->Init(0, argv[1])`——与 Go2 同模式。域 ID 0 用于真机。DDS 传输 SDK 全局，故网络约定应与 Go2 一致。**默认子网是否同 Go2 的 `192.168.123.x` 未验证**。

## 3.3 控制接口对比 vs Go2

### B.1 低层电机命令 API — 已验证：同字段，不同 IDL 命名空间

`unitree_hg::msg::dds_::MotorCmd_` 与 Go2 `unitree_go::MotorCmd_` 字段一致：

| 字段 | 类型 | Go2 | AS2 (unitree_hg) |
|---|---|---|---|
| mode | uint8 | ✓ | ✓ |
| q | float | ✓ | ✓ |
| dq | float | ✓ | ✓ |
| tau | float | ✓ | ✓ |
| kp | float | ✓ | ✓ |
| kd | float | ✓ | ✓ |
| reserve | uint32 | ✓ | ✓ |

**每电机 PD + 前馈公式 `tau + kp*(q_des - q) + kd*(dq_des - dq)` 与 Go2 完全相同。**

### B.2 LowCmd/LowState 容器差异 — 已验证，重大差异

| 方面 | Go2 `unitree_go::LowCmd_` | AS2 `unitree_hg::LowCmd_` |
|---|---|---|
| motor_cmd 数组大小 | **20** | **35** |
| Header 字段 | `head_[2]`, `level_flag`, `frame_reserve`, `sn_[2]`, `version_[2]`, `bandwidth` | `mode_pr`, `mode_machine`（更简） |
| BMS 字段 | `bms_cmd_` 有 | 无 |
| LED/风扇/gpio | 有 | 无 |
| reserve | `uint32_t` | `uint32_t[4]` |
| crc | uint32 | uint32 |

| 方面 | Go2 `unitree_go::LowState_` | AS2 `unitree_hg::LowState_` |
|---|---|---|
| motor_state 数组大小 | **20** | **35** |
| IMU | 有（quat[4]/gyro[3]/accel[3]/rpy[3]/temp） | 有（同形） |
| foot_force | **有（4 元素数组）** | **❌ 无** |
| BMS | 有 | 无 |
| wireless_remote | 有（40 字节） | 有（40 字节） |
| tick/mode_pr/mode_machine | 部分 | 有 |

**部署关键差异**：
1. 电机数组 35（非 20）。AS2 12 关节填 0-11，其余置零。**硬件电机索引映射在本地头文件未文档化**——mujoco bridge 用 `motor_cmd()[i]` 按 MJCF 驱动顺序填，但 MJCF 顺序（FR,FL,RR,RL）未必匹配硬件电机索引约定。**必须向宇树确认 AS2 `motor_cmd[0..11]` 的物理关节映射**。
2. **`unitree_hg::LowState_` 无 `foot_force`**。若 RL 策略训练时用足底接触力观测（Go2 legged_gym 常见），AS2 通过此 IDL 不可用，需替换（如用 `tau_est` 阈值估接触，或从观测向量移除）。**这是最大观测向量不兼容点**。
3. Header 协议不同：`mode_pr` + `mode_machine` 替代 Go2 `head/level_flag/frame_reserve`。Go2 的 `level_flag = 0xFF` 技巧**不适用**。AS2 LowCmd 用 `mode_pr`/`mode_machine`——**有效值需查 AS2 专属文档**，填错会静默无效命令。
4. **CRC 仍必需**，`unitree_hg` 复用同 `crc32_core` 算法（mujoco bridge 验证），但需对 AS2 文档确认。

### B.3 观测流 — 已验证

`unitree_hg::LowState_` 可用：
- IMU：四元数(4) + 陀螺(3) + 加速度(3) + rpy(3) + 温度 — **同 Go2**
- 每电机：q, dq, **ddq（额外）**, tau_est, temp[2], vol, sensor[2], motorstate — **比 Go2 丰富**

- wireless_remote(40) — 同 Go2

缺失 vs Go2：foot_force, bms, sn

### B.4 DDS topic 结构 — 部分验证

mujoco bridge `unitree_sdk2_bridge.h:160-161`：无论 IDL 类型，桥都 pub/sub `rt/lowcmd`/`rt/lowstate`——**topic 名与 Go2 相同但 IDL 类型不同**，用错 IDL 反序列化失败。

high-level sport state：`as2_sport_state.cpp` 订阅 `rt/lf/sportmodestate`（注意 `lf/` 前缀，与 Go2 的 `rt/sportmodestate` 不同），类型用 `unitree_go::msg::dds_::SportModeState_`（**sport-mode-state 复用 Go2 IDL**）。FSM 状态枚举同 14 态（PASSIVE/STAND_DOWN/STAND_UP/.../RECOVERY/BASE_HEIGHT_CTRL）。

> **重要**：memory `[go2_ctrl_no_fsm_feedback]`（Go2 无 FSM 状态反馈）对 AS2 可能不适用——AS2 的 `rt/lf/sportmodestate` 暴露 `mode/progress/position/velocity`。**这是平台改进，值得硬件验证**。

### B.5 控制频率 — 部分验证

`as2_sport_client.cpp` CLI 循环 50Hz（`dt=20000µs`），`as2_sport_state.cpp` 20Hz（`dt=0.05`）——但这是 high-level 轮询率，非低层控制率。Go2 `go2_low_level.cpp` 用 500Hz（`dt=0.002`）。**AS2 低层控制频率本地文件未指定**。推测：AS2 大概率支持 500Hz（`unitree_hg` 被 G1/H1-2 人形用，也 500Hz），**未验证**。

## 3.4 RL 策略部署差异（AS2 vs Go2）

用户已说策略细节未知（"估计就是一个 MLP 网络，但是参数目前未知"），故聚焦平台级差异对任意 MLP 的影响：

### C.1 观测向量 — 维度大概率相同，有 caveats
若策略仅用 IMU(4+3+3 或 3+3) + 关节角(12) + 关节速(12) + 上步动作(12)，**维度与 Go2 完全相同**（12 关节）。动作向量维度也 **12**。

若 Go2 训练策略用 **foot_force(4)**，AS2 通过 `unitree_hg::LowState_` **不可用**，需重训或合成。**最大观测向量不兼容点**。

若策略用 `ddq`，AS2 **提供**而 Go2 不提供——但不常见。

### C.2 动作向量 — 维度相同（12）
同 12-DOF 布局。动作缩放与裁剪范围因力矩极限差异需调（AS2 calf 90Nm vs Go2 值需对照）。

### C.3 关节顺序 / 命名 — 已验证同名，硬件索引未验证
MJCF 驱动顺序 `FR_hip, FR_thigh, FR_calf, FL_..., RR_..., RL_...`——与 memory `[go2_standard_folded_pose]` "policy order FL,FR,RL,RR" 注意：MJCF 是驱动顺序（FR 先），非腿组顺序。

**硬件电机索引映射（`motor_cmd[35]` 哪个 index 对应哪个物理关节）本地文件未文档化**。**必须向宇树索取 AS2 文档，勿假设与 Go2 一致**。

### C.4 默认站立姿态与 PD 增益 — 未验证，模型有提示
memory `[go2_standard_folded_pose]` 给 Go2 thigh≈1.29, calf≈-2.80。AS2 calf 范围 `[-2.7677, -0.8133]`，故折叠 calf 目标 ~-2.6 至 -2.7 rad 几何合理但**未确认**。`go2_low_level.cpp` 用 `sin_mid_q = {0.0, 1.2, -2.0}` 与 `Kp=5.0, Kd=1.0` 仅是示例。**AS2 站立 PD 增益须来自策略训练配置或官方文档**。

### C.5 安全考量 — 推测
- `mode_pr`/`mode_machine` 可能门控低层命令是否被接受（类比 Go2 `level_flag`）。**必须确定正确值以"激活"低层控制**，填错静默无效。SDK **无 `as2_low_level.cpp` 示例**可抄。
- memory `[feedback_go2_exit_strategy]`（FixStand→Passive）与 `[experience_go2_fsm_test_pacing]`（FSM 切换 5-10s 间隔）在 Go2 学得。AS2 FSM 状态名相同但切换动力学可能不同——**重新验证**。
- 基座更轻（11.18 vs 15 kg）→ 惯量低，同 PD 增益可能响应更脆或震荡。**保守调参**。

## 3.5 AS2-W 现有 C++ 部署模板

### D.1 官方低层示例 — 未找到（重大缺口）
SDK **无 `as2_low_level.cpp`**。`example/as2/` 仅含：
- `sport/as2_sport_client.cpp`（high-level sport：平衡站立/移动/翻滚/舞蹈/双手倒立）
- `sport/as2_sport_state.cpp`（FSM 状态订阅）
- `CMakeLists.txt`

对比 `example/go2/` 有 11 个示例含 `go2_low_level.cpp`（所有 Go2 RL 部署代码的模板）。**AS2 无类比低层 PD 控制示例**。

### D.2 最接近的参考
1. **`cpp_stack/unitree_sdk2/example/go2/go2_low_level.cpp`** — 结构模板（pub/sub 设置、CRC、500Hz recurrent 线程）。需适配到 `unitree_hg::LowCmd_`/`LowState_`，弃 `level_flag`/`head`，用 `mode_pr`/`mode_machine`。
2. **`cpp_stack/unitree_mujoco/simulate/src/unitree_sdk2_bridge.h`** — 桥已模板化 `<typename LowCmd_t, typename LowState_t>`，已处理 `unitree_go` 与 `unitree_hg` 两 IDL。展示电机命令公式与 IMU 填充——**AS2 兼容低层环的最佳参考**。
3. **`GO2_空翻倒立_deploy/go2_quad2hand/go2_deploy/deploy_real/include/unitree/idl/hg/`** — 已 vendored 完整 `unitree_hg` IDL 头（`LowCmd_.hpp`/`LowState_.hpp`/`MotorCmd_.hpp`/`MotorState_.hpp`/`IMUState_.hpp`）。**本仓库已有人开始 `unitree_hg` 部署**——调查 `go2_quad2hand`（名暗示"四足转倒立"，可能就是 AS2 倒立部署，因 AS2 sport client 有 `HandStand`）。

### D.3 社区模板 — 未验证
无法搜 GitHub。用户应搜 `as2_deploy`/`as2_rl_deploy`/`unitree_as2_policy`。`unitree_cpp_deploy` 仓库本地未找到，待有网络时在线确认是否有 AS2 分支。

## 3.6 AS2 vs Go2 对比总表

| 方面 | Go2 | AS2 | 置信度 |
|---|---|---|---|
| 机器人类型 | 四足 | 四足 | 已验证 |
| DOF | 12 | 12 | 已验证 |
| 关节名 | FL/FR/RL/RR hip/thigh/calf | 一致 | 已验证 |
| 基座质量 | ~15 kg | 11.178 kg | 已验证(AS2) |
| SDK | unitree_sdk2 (CycloneDDS) | unitree_sdk2 (CycloneDDS) | 已验证 |
| 低层 IDL | `unitree_go` | `unitree_hg` | 已验证 |
| 每电机命令字段 | q/dq/tau/kp/kd/mode | 一致 | 已验证 |
| 电机数组大小 | 20 | 35 | 已验证 |
| LowState 有 foot_force | 有 | **无** | 已验证 |
| LowState 有 ddq | 无 | 有 | 已验证 |
| IMU 字段 | quat/gyro/accel/rpy/temp | 一致 | 已验证 |
| LowCmd header | head/level_flag/sn/... | mode_pr/mode_machine | 已验证 |
| DDS topic (低层) | rt/lowcmd, rt/lowstate | 同名, hg 类型 | 已验证 |
| SportModeState topic | rt/sportmodestate | rt/lf/sportmodestate | 已验证(示例) |
| FSM 状态 | 14 态枚举 | 同 14 态枚举 | 已验证 |
| SDK 低层示例 | `go2_low_level.cpp` | **无** | 已验证 |
| 控制频率 | 500 Hz | 未验证(推测 500 Hz) | 推测 |
| 电机索引映射 | 文档化 | 未验证 | — |
| 默认姿态/PD 增益 | 已知 | 未验证 | — |
| onboard 计算 | Jetson Orin | 未验证 | — |
| 网络 IP 段 | 192.168.123.x | 未验证 | — |
| 官方名 "AS2-W" | n/a | 未验证(SDK 用 `as2`) | — |

## 3.7 关键文件索引

- `cpp_stack/unitree_mujoco/unitree_robots/as2/as2.xml` — AS2 MuJoCo 模型，关节范围/力矩/质量
- `cpp_stack/unitree_sdk2/include/unitree/robot/as2/sport/sport_client.hpp` — AS2 high-level API
- `cpp_stack/unitree_sdk2/include/unitree/robot/as2/sport/sport_api.hpp` — AS2 sport API ID
- `cpp_stack/unitree_sdk2/example/as2/sport/as2_sport_client.cpp` — high-level 示例(50Hz)
- `cpp_stack/unitree_sdk2/example/as2/sport/as2_sport_state.cpp` — FSM 状态订阅(`rt/lf/sportmodestate`)
- `cpp_stack/unitree_sdk2/example/go2/go2_low_level.cpp` — Go2 低层模板（需适配）
- `GO2_空翻倒立_deploy/go2_quad2hand/go2_deploy/deploy_real/include/unitree/idl/hg/LowCmd_.hpp` — `unitree_hg::LowCmd_`（35 电机数组, mode_pr/mode_machine）
- `GO2_空翻倒立_deploy/go2_quad2hand/go2_deploy/deploy_real/include/unitree/idl/hg/LowState_.hpp` — `unitree_hg::LowState_`（无 foot_force, 有 ddq）
- `GO2_空翻倒立_deploy/go2_quad2hand/go2_deploy/deploy_real/include/unitree/idl/hg/MotorCmd_.hpp` / `MotorState_.hpp` — 每电机字段
- `cpp_stack/unitree_mujoco/simulate/src/unitree_sdk2_bridge.h` — 模板化桥，两 IDL 都处理
- `cpp_stack/unitree_mujoco/simulate/src/param.h` — IDL 自动选择逻辑
- `cpp_stack/unitree_mujoco/readme.md` — 明确 AS2 用 `unitree_hg`

---

# Part 4 — AS2-W 部署改造步骤清单

## 4.1 起点选择

**从 upstream golden reference 起步**，不要 fork v0.6.6：

```
cp -r cpp_stack/robogauge_code/unitree_cpp_deploy_robogauge_upstream \
      cpp_stack/robogauge_code/unitree_cpp_deploy_as2w
```

理由：v0.6.6 含 Go2 专属硬编码（关节名、姿态、模型路径、UDP magic "GO2C"、12 关节假设），fork 会带入噪声。upstream 干净，按 Part 1 识别的通用模式叠加更可控。

## 4.2 必须向宇树确认的开放问题（最高优先级）

| # | 问题 | 影响 |
|---|---|---|
| 1 | "AS2-W" 是否等同 SDK `as2`？或轮式变体？ | 决定 IDL、关节布局、运动学 |
| 2 | AS2 `motor_cmd[0..11]` 硬件电机索引映射？ | 填错关节会失控 |
| 3 | `unitree_hg::LowCmd_` 的 `mode_pr`/`mode_machine` 有效值？ | 填错静默无效命令 |
| 4 | AS2 是否支持 500Hz 低层命令？ | 控制环频率 |
| 5 | AS2 默认站立姿态与推荐 PD 增益？ | FixStand 配置 |
| 6 | AS2 是否有 onboard Jetson？网络/IP 配置？ | 部署架构、脚本 IP |
| 7 | 是否有官方 `as2_low_level.cpp` 示例或 AS2 RL 部署模板？ | 减少适配工作量 |

## 4.3 改造步骤（按依赖序）

### Step 1 — IDL 层适配（最先，阻塞后续）
1. 复制 `GO2_空翻倒立_deploy/go2_quad2hand/.../idl/hg/` 到新仓库 `deploy/include/unitree/idl/hg/`
2. 改 `unitree_articulation.h`：`LowCmd`/`LowState` 类型别名从 `unitree_go::msg::dds_::LowCmd_` 改为 `unitree_hg::msg::dds_::LowCmd_`
3. 改低层命令填充：去 `level_flag=0xFF` / `head_` / `sn_` / `bms_cmd_`，改填 `mode_pr`/`mode_machine`（待宇树确认值）
4. 电机数组 20 → 35，填 0-11，其余置零
5. CRC 算法复用 `crc32_core`（bridge 已验证 hg 也用此算法）
6. 参考 `unitree_sdk2_bridge.h` 的 hg 分支填充逻辑

### Step 2 — 关节映射与默认姿态
1. 从宇树确认 `motor_cmd[0..11]` 物理映射
2. 在 `config.yaml` 定义 `joint_ids_map`（policy order ↔ SDK order）
3. FixStand 目标姿态填 AS2-W `default_joint_pos`（从策略训练配置或 as2.xml 几何推）
4. Passive `mode`/`kd` 数组填 12 元素（非 20）

### Step 3 — 观测向量适配
1. 确认 AS2-W 策略训练用了哪些观测项
2. **若含 foot_force**：AS2 不可用，需重训（移除 foot_force）或合成（`tau_est` 阈值估接触）
3. **若含 ddq**：AS2 `LowState_` 已提供，可启用
4. 验证 obs 维度与 ONNX input shape 匹配（参考 `02_Migration_Completed.md` 第 5 节高风险项）

### Step 4 — 叠加通用改造模式（从 v0.6.6 移植）
按 Part 1 §1.4 表，移植**通用模式**：
1. `CtrlFSM.h`：空 states 守卫 + `getCurrentMode()`/`stopThread()`
2. `keyboard.h`：直接用 v0.6.6 版（严格优于 upstream）
3. `State_RLBase.h/.cpp`：`set_keyboard_velocity()`/`auto_start`/扁平 logging
4. `param.h`：11 个 CLI 选项（改默认 `--test_policy_dir` 为 AS2-W 模型）
5. `main.cpp`：CLI 分发 / DDS 域参数 / 内存 YAML 改写 / MotionSwitcher 门 / 手动 registered_checks / 优雅退出 / 键盘+UDP 速度注入
6. `CMakeLists.txt`：`find_package(unitree_sdk2)` + arch-conditional ORT + `ROBOGAUGE_BENCHMARK` 开关
7. `VelocityCommandDamper.h`：复用 boost 删除，**但恢复 `parse_range()` 有限性/跨零校验**
8. `BenchmarkCollector.h`：参数化 DOF（`RLStats`/`FixStandStats` 硬编码 12 → `init(int n_joints)`）
9. `State_Fix.h`：增益渐变防抖，**调** `RL_KP/RL_KD/HOLD_TIME/RAMP_TIME` 匹配 AS2-W 策略 deploy.yaml
10. UDP magic `0x474F3243`("GO2C") → 改 "AS2C"（`0x41533243`）

### Step 5 — Jetson/onnxruntime 适配（若 AS2-W 用 Jetson）
1. 若 AS2-W 用同款 Jetson Orin：保留 `cpuinfo_jetson_fix.c` + `LD_PRELOAD` + `SetIntraOpNumThreads(1)`
2. 若不同 Jetson 或 x86：去掉 cpuinfo fix，保留 `SetIntraOpNumThreads(1)`（无害）
3. 详见 `Docs/onnxruntime_jetson_orin_crash_analysis.md`

### Step 6 — 一键脚本改造
基于 Part 2 §2.9：
1. 复制 `go2_v066_xbox_wifi_workstation.sh` → `as2w_vXXX_xbox_wifi_workstation.sh`
2. 变量 `GO2_*` 改名 `AS2W_*`（或保留名但更新值）
3. 更新 Part 2 §2.9 表中 13 个 GO2 专属值
4. 策略清单检查（L173）改 AS2-W 实际文件布局
5. `GO2_LAUNCH_CMD`（L242）改 AS2-W 二进制/SDK lib/控制器标志，按需去 `LD_PRELOAD`
6. 简报表（L211-225）改 AS2-W 按键映射与速度限幅
7. Step 1/3、SSH helper、`trap cleanup EXIT`、退出后日志 tail、退出码透传**不变**
8. 修复 v0.6.6 脚本的 `ssh_go2`/`ssh_go2_q` 重复（AS2-W 只留一个）
9. **可考虑**：抽公共配置到 `as2w_env.sh` 供 deploy/sync/keyboard/xbox/benchmark 多脚本共享（v0.6.6 的配置块按 L26 注释跨 4 脚本复制，是已知技术债）


### Step 7 — 构建工具一致性（参考 memory `[experience_build-env_ros-workspace-build-tool-conflict]`）
若 AS2-W 部署涉及 ROS 工作区：
1. 进入陌生工作区先 `ls build/` 看 manifest，5 秒判原工具
2. 沿用原工具（Noetic=catkin_make，Foxy/Humble=colcon）
3. 隔离验证用独立目录（`--build-base build_colcon`），勿覆盖正式 `devel/`/`install/`
4. 部署回原工具写正式目录

## 4.4 验证检查点

| 检查点 | 方法 | 通过标准 |
|---|---|---|
| 编译通过 | `cmake .. && make -j8` | 无错，生成 as2w_ctrl |
| IDL 反序列化 | 订阅 `rt/lowstate` 打印 motor_state[0..11].q | 与实际关节角一致 |
| 电机索引映射 | 单关节发小 kp 命令 | 预期关节响应 |
| mode_pr/mode_machine 激活 | 发 lowcmd 检查是否被接受 | 电机响应命令 |
| obs 维度匹配 | 打印 obs vector size vs ONNX input shape | 一致 |
| FixStand→Velocity 无跳变 | 监控 kp/kd 渐变与姿态过渡 | 平滑无抖 |
| 键盘 f/r/z | 逐键测试 | 状态切换正确 |
| 速度注入 W/S/Space | 测试 | 速度响应与归零 |
| UDP 手柄流 | controller_sender.py 测试 | 50Hz 稳定，300ms 超时归零 |
| SIGINT 优雅退出 | Ctrl+C | 回 Passive → 停线程 → 退出 |
| MotionSwitcher 门 | 真机启动前检查 | sport_mode 占用时拒绝启动 |
| FSM 切换节奏 | 状态切换间隔 5-10s | 物理稳定不摔（参考 `[experience_go2_fsm_test_pacing]`） |
| benchmark | `--benchmark` | summary 含 p99/50Hz 合规率 |

## 4.5 风险矩阵

| 风险 | 严重度 | 缓解 |
|---|---|---|
| **foot_force 观测缺失** | 高 | 确认策略是否用；用则重训或合成 |
| **电机索引映射错** | 高 | 宇树确认前勿上真机，先单关节小 kp 试 |
| **mode_pr/mode_machine 填错** | 高 | 静默无效，需示波器/日志确认命令被接受 |
| **FixStand 增益跳变** | 中 | 复用 State_Fix 渐变，调常量匹配 AS2-W |
| **基座更轻导致 PD 震荡** | 中 | 保守调参，从低 kp 起步 |
| **观测维度不匹配** | 高 | 打印 obs size vs ONNX shape，先 sim2sim |
| **"AS2-W" ≠ SDK "as2"** | 高 | 联系宇树确认，决定 IDL 选择 |
| **Jetson cpuinfo 崩溃** | 中 | 同款 Jetson 则复用 cpuinfo_jetson_fix.so |
| **无 as2_low_level.cpp 示例** | 中 | 参考 go2_low_level.cpp + unitree_sdk2_bridge.h 适配 |
| **构建工具冲突**（若涉及 ROS） | 中 | 按 memory 隔离构建，沿用原工具 |

---

# 附录 A — v0.6.6 改动文件清单（完整）

修改文件（18）：
```
deploy/include/FSM/CtrlFSM.h
deploy/include/FSM/State_Fix.h
deploy/include/FSM/State_RLBase.h
deploy/include/isaaclab/algorithms/algorithms.h
deploy/include/isaaclab/assets/articulation/articulation.h
deploy/include/isaaclab/devices/keyboard/keyboard.h
deploy/include/isaaclab/envs/manager_based_rl_env.h
deploy/include/param.h
deploy/include/utils/VelocityCommandDamper.h
deploy/robots/go2/CMakeLists.txt
deploy/robots/go2/config/config.yaml
deploy/robots/go2/main.cpp
deploy/robots/go2/src/State_RLBase.cpp
docs/robot_params.md
.gitignore
README.md
README_zh.md
UPDATE.md
```

新增源文件（6，排除 thirdparty 二进制与 build 产物）：
```
deploy/include/BenchmarkCollector.h
deploy/include/isaaclab/envs/mdp/commands/motion_command.h
deploy/include/isaaclab/envs/mdp/observations/motion_observations.h
deploy/thirdparty/cnpy/cnpy.h (+ .cpp + LICENSE + README)
deploy/thirdparty/onnxruntime-linux-aarch64-1.20.1/  (Jetson ORT)
deploy/thirdparty/onnxruntime-linux-x64-1.23.2/      (x86 ORT)
```

# 附录 B — 关键脚本行号索引

| 内容 | 行号 |
|---|---|
| `set -euo pipefail` | 24 |
| 配置块 | 26-43 |
| 参数解析 | 48-66 |
| 日志 helper | 68-73 |
| SSH helper | 75-85 |
| 交互终端守卫 | 88-90 |
| 环境清除 | 92 |
| Step 0 手柄 | 97-132 |
| Step 1 WiFi | 137-152 |
| Step 2 部署校验 | 157-177 |
| Step 3 残留进程 | 182-200 |
| 操作员简报 | 207-235 |
| Go2 启动命令 | 242 |
| SSH nohup 启动 | 245-248 |
| 启动后验证 | 249-256 |
| cleanup + trap | 265-273 |
| 工作站 controller_sender | 275-277 |
| 退出码透传 | 280-291 |

# 附录 C — 关键 memory 关联

- `[go2_ctrl_no_fsm_feedback]` — Go2 无 FSM 反馈；AS2 的 `rt/lf/sportmodestate` **可能提供**，需硬件验证
- `[feedback_go2_exit_strategy]` — 行走退出应先 FixStand 再 Passive；AS2 同模式，重新验证切换动力学
- `[go2_standard_folded_pose]` — Go2 12 关节折叠值（policy order FL,FR,RL,RR）；AS2 关节名同，值需按 as2.xml 重新确认
- `[experience_go2_fsm_test_pacing]` — FSM 切换 5-10s 间隔防摔；AS2 同样需要，sim-test 定时器值据此调
- `[experience_build-env_ros-workspace-build-tool-conflict]` — 若 AS2-W 涉及 ROS 工作区，按原工具构建或隔离目录
- `[experience_testing_injectable-clock-for-time-logic]` — 时间相关测试逻辑（如超时转换）须时钟可注入；AS2-W 若新增超时判断，从设计期即注入时钟
- `[experience_esekk_frozen-state-deadlock]` — divergence guard 硬拒绝条件勿依赖被冻结状态量；AS2-W 若加安全 guard 注意冗余降级

---

> 本文档基于本地代码库分析与三路并行 agent 调研（diff 分析 / 脚本拆解 / AS2-W 平台研究）。外部网络检索被企业网络墙阻断，所有需在线确认的项已明确标注"未验证"。落地前请优先解决 §4.2 的 7 个开放问题。

---

# Part 5 — 跨 dim 策略统一部署架构（GO2_空翻倒立_deploy 实证）

本节来自对 `/home/robot/z00959834/robogauge_5090/GO2_空翻倒立_deploy/deploy` 的全量梳理。该工程在**同一个 C++ 二进制 + 同一份 `config.yaml`** 中并存了 8 种不同输入维度（45 / 60 / 69 / 275+3 / 标准 obs-group）的策略状态，是"跨 dim 策略统一部署"的成熟范式，可直接复用到 AS2-W 多策略共存场景。

## 5.1 总览：一个二进制如何容纳 8 种策略

`robots/go2/main.cpp` 编译出单一可执行文件，启动后由 `CtrlFSM` 根据 `config.yaml` 中 `FSM._.<StateName>.type` 字段动态实例化对应的 `State_*` 子类。8 种已实现状态类型：

| State 名 | type | 输入 dim | obs 构建方式 | 网络数 | 备注 |
|---|---|---|---|---|---|
| `Passive` | Passive | — | 无网络 | 0 | 仅力矩零输出 |
| `FixStand` | Fix | — | 无网络 | 0 | PD 到默认站立姿态，含 RL→Stand 增益渐变 |
| `FixSquat` | Fix | — | 无网络 | 0 | PD 到蹲伏姿态 |
| `Velocity_*` | RLBase | 由 deploy.yaml observations 决定（典型 235-dim） | observation_manager + history | 1 | 标准 IsaacLab 策略路径 |
| `LSD_Loco` | LSDLoco | 45 | 手动硬编码 | 1 | 速度可控，set_velocity 注入 |
| `LSD_Jump` / `LSD_Backflip` / `LSD_Sideflip` | LSDMotion | 69 | 手动硬编码 + MotionLoader CSV | 1 | 含 ref_q/ref_dq 运动参考 |
| `BackflipV7` | Backflip | 60 | 手动硬编码 + phase clock | 1 | 无运动参考，相位驱动 |
| `SideflipV10` | LSDMotion | 69 | 同 LSD_Jump | 1 | 复用 LSDMotion 类，CSV 不同 |
| `Quad2Hand` | Quad2Hand | 275（=55×5 帧）+ 3（estimator 输出）= 278 | 手动硬编码 + history buffer | **2**（estimator + actor） | 四足/倒立双模 |
| `StandDown` | StandDown | — | 无网络 | 0 | 受控折叠到卧倒，q_tol/dq_tol 收敛门控 |
| `HimlocoWalk` | RLBase | 同 Velocity_* | observation_manager | 1 | 复用 RLBase |

**关键观察**：策略维度差异（45~278）完全由各 `State_*` 子类**自管 obs 构建**吸收，框架层（`CtrlFSM` / `OrtRunner` / `main`）**对维度无感**。

## 5.2 工厂分发机制：YAML `type` 字段 + `REGISTER_FSM` 宏

### 5.2.1 配置侧

`robots/go2/config/config.yaml` 用统一 schema 声明每个状态：

```yaml
FSM:
  transitions: [...]          # 全局转移图（DSL 条件编译到 registered_checks）
  _:
    Passive:
      type: Passive           # ← 工厂查找键，对应类 State_Passive
      initial_mode: ...
    FixStand:
      type: Fix               # ← 对应 State_Fix
      default_q: [...]
      kp: 60
      kd: 5
    LSD_Backflip:
      type: LSDMotion         # ← 对应 State_LSDMotion（多状态复用同一类）
      policy_dir: logs/imported/lsd_go2_backflip
      joint_order: J          # J or L，决定 policy_to_motor_ 重映射
      default_q: [...]
      kp: [per-joint or scalar]
      kd: [per-joint or scalar]
      action_scale: [per-joint or scalar]
      motion:
        csv_file: ...
        time_start: 0.0
        time_end: 2.0
        fps: 50
      return_state: FixStand  # 自动返回目标
      clip_action: [-100, 100]
      duration: 2.0
    Quad2Hand:
      type: Quad2Hand
      policy_dir: logs/imported/quad2hand
      joint_order: J
      estimator: { ... }      # 双网络第二路配置
      cmd_range: { quad: [...], hand: [...] }
      ...
```

**`type` 字段是分发键**：同名状态可复用同一 type（如 `LSD_Jump` / `LSD_Backflip` / `LSD_Sideflip` 都是 `LSDMotion`），仅 `policy_dir` / `motion` / `default_q` 等 per-state 配置不同。这样新增一个"同结构不同权重"的策略只需加一条 YAML，**无需新写 C++ 类**。

### 5.2.2 工厂侧

`include/FSM/CtrlFSM.h` 在初始化时遍历 `FSM._` 节，按 `type` 查全局工厂表：

```cpp
// CtrlFSM.h L38-44（简化）
for (auto it = states_cfg.begin(); it != states_cfg.end(); ++it) {
    std::string fsm_name = it->first.as<std::string>();
    std::string fsm_type = it->second["type"]
        ? it->second["type"].as<std::string>()
        : fsm_name;                              // type 缺省 = 状态名
    auto factory = getFsmMap().find("State_" + fsm_type);
    if (factory == getFsmMap().end()) {
        throw std::runtime_error("Unknown FSM type: State_" + fsm_type);
    }

    auto instance = factory->second(id, fsm_name);   // 构造，传入 fsm_name 作 per-state 配置键
    states_.push_back(instance);
}
```

### 5.2.3 注册侧

`include/FSM/BaseState.h` 定义宏实现静态注册：

```cpp
// BaseState.h L45-53（简化）
using FsmFactory = std::function<std::shared_ptr<BaseState>(int, std::string)>;
using FsmMap = std::unordered_map<std::string, FsmFactory>;

#define REGISTER_FSM(Derived)                                          \
    static bool __registered_##Derived = []() {                        \
        getFsmMap()[#Derived] = [](int id, std::string name) {         \
            return std::make_shared<Derived>(id, name);                \
        };                                                            \
        return true;                                                  \
    }();

// 每个状态头文件末尾：
// State_LSDMotion.h
REGISTER_FSM(State_LSDMotion)
// State_Quad2Hand.h
REGISTER_FSM(State_Quad2Hand)
// ...
```

**新增策略类型的工作量**：
1. 写 `State_ASWXxx.h`，继承 `BaseState`，实现 `init()` / `run()` / `is_completed()`（可选）
2. 文件末尾 `REGISTER_FSM(State_ASWXxx)`
3. `config.yaml` 加 `ASWXxx: { type: ASWXxx, ... }`
4. 若需 velocity 注入或自动返回，在 `main.cpp` 加对应 `dynamic_cast` 分支

**无需改动** `CtrlFSM` / `BaseState` / `OrtRunner` 任何代码。

## 5.3 OrtRunner：维度无关的 ONNX 推理

`include/isaaclab/algorithms/algorithms.h` 的 `OrtRunner` 在构造时**运行时动态检测** ONNX 模型的输入/输出 shape 与名称，框架不写死任何维度：

```cpp
// algorithms.h L49-107（关键逻辑）
OrtRunner(const std::string& model_path, int intra_op_threads = 1) {
    env_ = std::make_unique<Ort::Env>(ORT_LOGGING_LEVEL_WARNING, "runner");
    Ort::SessionOptions opts;
    opts.SetIntraOpNumThreads(intra_op_threads);    // Jetson 4 核 → 1 线程防崩溃
    session_ = std::make_unique<Ort::Session>(*env_, model_path.c_str(), opts);

    // 动态扫描输入
    for (size_t i = 0; i < session_->GetInputCount(); ++i) {
        auto name = session_->GetInputNameAllocated(i, allocator);
        input_names_.push_back(name.get());
        auto info = session_->GetInputTypeInfo(i).GetTensorTypeAndShapeInfo();
        auto shape = info.GetShape();
        // 动态 batch 维（-1 / 字符串）→ 1
        if (!shape.empty() && shape[0] < 0) shape[0] = 1;
        input_shapes_.push_back(shape);
    }
    // 同理扫描输出，优先选名为 "actions" 的输出，否则取第一个
    ...
}

// 单输入推理
std::vector<float> act(const std::vector<float>& obs);

// 多输入推理（Quad2Hand actor 用）
std::vector<float> act(std::unordered_map<std::string, std::vector<float>> obs);
```

**为什么这能跨 dim**：
- OrtRunner 不知道也不关心 obs 向量是 45 还是 278 维
- 每种策略的 `State_*` 自己负责把观测填到正确长度的 `std::vector<float>`，传给 `act()`
- ONNX 模型自身的 input shape 即是校验：若 obs 长度不匹配，ORT 在 Run() 时抛异常

**对 AS2-W 的意义**：AS2-W 的 MLP 策略（无论 dim 多少）可直接复用 `OrtRunner`，**不需要改 algorithms.h**。

## 5.4 两种 obs 构建路径对比

跨 dim 部署的关键设计是**两条并存的 obs 构建路径**，按策略结构复杂度选择：

### 路径 A：RLBase + deploy.yaml observations 节（声明式）

适用：标准 IsaacLab / RSL-RL 训练的策略，obs 是若干"观测组"的拼接，每组可有 history。

`logs/rsl_rl/<policy>/params/deploy.yaml`：
```yaml
observations:
  base_ang_vel:
    clip: [-100, 100]
    scale: [0.25, 0.25, 0.25]
    history_length: 10           # ← 该组重复 10 帧
  projected_gravity:
    scale: [1, 1, 1]
    history_length: 10
  velocity_commands:
    params: { command_name: base_velocity }
    scale: [1, 1, 1]
    history_length: 10
  joint_pos_rel:
    scale: [1×12]
    history_length: 10
  joint_vel_rel:
    scale: [0.05×12]
    history_length: 10
  last_action:
    scale: [1×12]
    history_length: 10
# 总 dim = (3+3+3+12+12+12) × 10 = 450（每帧 45 × 10 history）
```

`State_RLBase` 通过 `observation_manager_` 按上述声明自动拼装 obs 向量，**dim 完全由 YAML 决定**。新增同结构策略只需换 `policy_dir` 指向新 `deploy.yaml`。

### 路径 B：自定义 State_* 手动硬编码 obs（命令式）

适用：非标准 obs 结构（含 motion reference / phase clock / gait clock / 双网络 history 等）。

`State_LSDLoco.h`（45-dim，无 history）：
```cpp
obs_.resize(45);
// [0:3]   base_ang_vel * 0.2
// [3:6]   projected_gravity
// [6:9]   velocity_commands
// [9:21]  joint_pos - default_q
// [21:33] joint_vel * 0.05
// [33:45] last_action
```

`State_LSDMotion.h`（69-dim，含 CSV 参考）：
```cpp
obs_.resize(69);
// [0:12]   ref_q          ← MotionLoader 当前帧
// [12:24]  ref_dq         ← MotionLoader 有限差分
// [24:30]  orientation 6D ← 从 IMU quat 转 6D 表示
// [30:33]  base_ang_vel
// [33:45]  q - default_q
// [45:57]  dq
// [57:69]  last_action
```

`State_Backflip.h`（60-dim，phase clock）：
```cpp
obs_.resize(60);
// [0:3]    ang_vel * 0.25
// [3:6]    projected_gravity
// [6:18]   q - default
// [18:30]  dq * 0.05
// [30:42]  current_action
// [42:54]  last_action
// [54:60]  phase_features = [sin/cos(phase, phase/2, phase/4)]
//          phase = pi * clamp(t, 0, 2.0) / 2.0
```

`State_Quad2Hand.h`（275+3=278-dim，双网络 + 5 帧 history）：
```cpp
// 单帧 obs 55-dim:
//   [0:3]   ang_vel*0.25
//   [3:6]   gravity
//   [6:9]   cmd_scaled
//   [9:21]  q_obs
//   [21:33] dq_obs
//   [33:45] action
//   [45:53] clock (sin/cos 双相, quad period 0.5 / hand period 0.4)
//   [53:55] mode one-hot
// history_buffer_ 滚动存 5 帧 → 拼成 275-dim 输入 estimator
// estimator 输出 3-dim → 拼到 275 后 = 278-dim → 输入 actor → 12-dim action
```

**选择规则**（AS2-W 复用指引）：

| 策略 obs 特征 | 推荐路径 |
|---|---|
| 标准 IsaacLab obs group + history | 路径 A（RLBase + deploy.yaml） |
| 含 motion reference / CSV 轨迹 | 路径 B（自定义 State，用 MotionLoader） |
| 含 phase / gait clock | 路径 B（自定义 State，自管 clock） |
| 双网络（estimator + actor） | 路径 B（自定义 State，两个 OrtRunner 实例） |
| 非标准 history 拼装 | 路径 B |
| 简单单网络 MLP，无 history | 两条都行，**路径 A 更省代码**（只写 YAML） |

AS2-W 若策略是简单 MLP（用户预估），**优先尝试路径 A**：把 obs group 写到 `deploy.yaml`，用 `type: RLBase` 即可。若 ONNX 模型的输入结构与 IsaacLab 标准组不一致，再降级到路径 B 写自定义 `State_ASWWalk`。

## 5.5 关节顺序重映射：J / L / SDK 三套坐标系

策略训练时的关节顺序可能与 SDK 下发顺序不同，需 `policy_to_motor_` 数组重映射。该工程支持两种 policy order，加 SDK 原生 order 共三套：

| Order | 含义 | 映射数组（policy idx → motor idx） | 训练框架 |
|---|---|---|---|
| **L** (Leg) | 按腿分组：FL,FR,RL,RR，每腿 hip-thigh-calf | `[3,4,5,0,1,2,9,10,11,6,7,8]` | LSD / 部分 IsaacLab |
| **J** (Joint) | 按关节类型分组：4 hip, 4 thigh, 4 calf | `[3,0,9,6,4,1,10,7,5,2,11,8]` | 部分 IsaacLab / Backflip |
| **SDK** | unitree_sdk2 原生：FR,FL,RR,RL | 恒等 `[0..11]` | 下发侧 |

`config.yaml` 每个状态声明 `joint_order: J` 或 `joint_order: L`，State 子类构造时据此初始化 `policy_to_motor_`。下发时：

```cpp
for (int i = 0; i < 12; ++i) {
    motor_q[policy_to_motor_[i]] = policy_q[i];   // policy → motor
}
```

`deploy.yaml` 的 `joint_ids_map` 字段也表达同一映射（如 `[3,4,5,0,1,2,9,10,11,6,7,8]` 即 L order），但作用于 RLBase 路径的 observation_manager。

**AS2-W 注意**：
- AS2-W 同为 12-DOF 四足，关节命名与 Go2 一致（FL/FR/RL/RR × hip/thigh/calf），L/J 顺序定义可直接复用

- 但**电机索引在 SDK 侧可能不同**：AS2 用 `unitree_hg` IDL，`LowState.motor()[i]` 的 i 到物理腿的映射需从 `as2.xml` 或宇树文档确认（**未验证**，见 §4.2 开放问题 #2）
- 落地步骤：先在 sim 中打印 `motor()[i].q()` 与已知关节扰动对应，确认 motor order，再定 `policy_to_motor_`

## 5.6 per-state 配置驱动：避免硬编码到 C++

每个 State 子类在构造函数从 `param::config["FSM"][state_string]` 读自己的覆盖配置，**所有可调参数集中在 YAML**：

```cpp
// State_LSDMotion.h 构造（简化）
State_LSDMotion(int id, std::string name) : BaseState(id, name) {
    auto cfg = param::config["FSM"]["_"][name];
    policy_dir_     = cfg["policy_dir"].as<std::string>();
    joint_order_    = cfg["joint_order"].as<std::string>("J");
    default_q_      = parse_vec(cfg["default_q"], 12);
    kp_             = parse_vec_or_scalar(cfg["kp"], 12, 60.0);
    kd_             = parse_vec_or_scalar(cfg["kd"], 12, 5.0);
    action_scale_   = parse_vec_or_scalar(cfg["action_scale"], 12, 0.25);
    return_state_   = cfg["return_state"].as<std::string>("FixStand");
    clip_action_    = cfg["clip_action"].as<std::vector<float>>({-100, 100});
    duration_       = cfg["duration"].as<double>(2.0);
    auto motion_cfg = cfg["motion"];
    motion_loader_.load(
        motion_cfg["csv_file"].as<std::string>(),
        motion_cfg["time_start"].as<double>(0.0),
        motion_cfg["time_end"].as<double>(2.0),
        motion_cfg["fps"].as<double>(50.0)
    );
    // joint_order → policy_to_motor_
    if (joint_order_ == "J") policy_to_motor_ = {3,0,9,6,4,1,10,7,5,2,11,8};
    else                     policy_to_motor_ = {3,4,5,0,1,2,9,10,11,6,7,8};
    // 加载 ONNX
    runner_ = std::make_unique<OrtRunner>(policy_dir_ + "/policy.onnx", 1);
}
```

`kp` / `kd` / `action_scale` 支持**标量或 12 向量**两种写法（`parse_vec_or_scalar`），覆盖"全腿统一"与"per-joint 调整"两种需求。

**AS2-W 复用**：直接照搬此配置 schema，per-state 声明 `policy_dir` / `joint_order` / `default_q` / `kp` / `kd` / `action_scale` / `return_state` / `clip_action`。

## 5.7 特技状态自动返回 + StandDown 停止链

### 5.7.1 is_completed() + return_state_

`LSDMotion` / `Backflip` 等有限时长特技状态实现 `is_completed()`：

```cpp
bool is_completed() const override {
    return t_ >= duration_;   // 或 motion_loader_ 播完
}
```

`main.cpp` 主循环轮询激活状态：

```cpp
// main.cpp 简化
auto active = fsm.getActiveState();
if (active->is_completed()) {
    auto return_name = active->return_state();   // 通常 "FixStand"
    fsm.switchTo(return_name);
    // 若 return_state 是 StandDown，继续触发停止链
}
```

### 5.7.2 StandDown 受控折叠

`StandDown` 不是纯时间到点切换，而是**基于收敛门控**：

```yaml
StandDown:
  type: StandDown
  default_q: [折叠姿态 12 值]
  kp: 40
  kd: 4
  q_tol: 0.1        # |q - target_q| < tol 视为收敛
  dq_tol: 0.1       # |dq| < tol 视为静止
  confirm_time: 0.3 # 连续满足上述条件 0.3s 才算真收敛
  max_time: 5.0     # 兜底超时
  next_state: Passive
```

收敛后切 `Passive`（力矩零输出），机器人物理趴下。这条 `特技 → FixStand → StandDown → Passive` 链是安全停止的标准模式。

### 5.7.3 main.cpp dynamic_cast 多态调度

`main.cpp` 用 `dynamic_cast` 按状态类型分发特殊操作：

```cpp
// 速度注入：找当前激活的速度可控状态
std::shared_ptr<State_RLBase>   rlbase   = std::dynamic_pointer_cast<State_RLBase>(active);
std::shared_ptr<State_LSDLoco>  lsdloco  = std::dynamic_pointer_cast<State_LSDLoco>(active);
std::shared_ptr<State_Quad2Hand> quad2h  = std::dynamic_pointer_cast<State_Quad2Hand>(active);
if (rlbase)   rlbase->set_keyboard_velocity(vx, vy, vyaw);
if (lsdloco)  lsdloco->set_velocity(vx, vy, vyaw);
if (quad2h)   quad2h->set_velocity(vx, vy, vyaw);

// 模式切换（Quad2Hand 四足↔倒立）
if (quad2h) quad2h->request_mode_switch(target_mode);

// UDP mode_request '1'-'9' 映射各特技
switch (mode_req) {
    case '1': fsm.switchTo("LSD_Loco");     break;
    case '2': fsm.switchTo("LSD_Jump");     break;
    case '3': fsm.switchTo("LSD_Backflip"); break;
    // ...
}
```

**AS2-W 复用**：
- 若 AS2-W 策略是速度行走型，用 `dynamic_cast<State_RLBase>` 路径即可（无需改 main.cpp）
- 若新增特技类（如 `State_ASWFlip`），在 main.cpp 加一条 `dynamic_cast` 分支处理其特殊接口
- 自动返回链 `特技 → FixStand → StandDown → Passive` 直接复用，仅 `StandDown.default_q` 需按 AS2-W 折叠姿态重定（参考 memory `go2_standard_folded_pose` 的方法但值需重测）

## 5.8 三种特技策略模式总结

| 模式 | 代表状态 | obs 关键特征 | 适用场景 |
|---|---|---|---|
| **Motion Reference** | LSDMotion (69-dim) | ref_q / ref_dq 来自 CSV 轨迹 | 有示范动作的技能（跳跃、空翻） |
| **Phase Clock** | Backflip (60-dim) | sin/cos(phase, phase/2, phase/4) | 无需参考轨迹、相位驱动的周期/瞬态技能 |
| **Dual-Network** | Quad2Hand (278-dim) | estimator 提取 latent → actor 输出 action | 需要从 obs 推断隐藏状态（如接触相）的复杂技能 |

AS2-W 若要部署特技策略，按技能特征选其一：
- 有动作捕捉 / 示范数据 → Motion Reference 模式（复用 `MotionLoader`）
- 纯相位驱动 → Phase Clock 模式（参考 `State_Backflip`）
- 需 latent 估计 → Dual-Network 模式（参考 `State_Quad2Hand`）

## 5.9 AS2-W 复用 checklist

把上述跨 dim 架构应用到 AS2-W 的具体步骤：

### 5.9.1 若 AS2-W 策略是标准 IsaacLab 训练的 MLP

1. 把 ONNX 权重放 `logs/rsl_rl/as2_walk/policy.onnx`
2. 把训练侧 `deploy.yaml` 放 `logs/rsl_rl/as2_walk/params/deploy.yaml`（含 observations 节、joint_ids_map、default_joint_pos、action scale/offset）
3. `config.yaml` 加：
   ```yaml
   ASWWalk:
     type: RLBase
     policy_dir: logs/rsl_rl/as2_walk
     initial_mode: false
   ```
4. 确认 `deploy.yaml` 的 `joint_ids_map` 与 AS2-W SDK motor order 一致（**未验证，需硬件确认**）
5. 编译运行，框架自动按 `deploy.yaml` observations 节构建 obs 并推理

**工作量**：~1 个 YAML 文件，零 C++ 改动。

### 5.9.2 若 AS2-W 策略 obs 结构非标准

1. 写 `include/FSM/State_ASWWalk.h`，继承 `BaseState`
2. 构造函数读 `config.yaml` 的 `ASWWalk` 节（policy_dir / joint_order / default_q / kp / kd / action_scale）
3. 实现 `run()`：
   - 从 `low_state_` 读 IMU / 关节状态
   - 按 policy obs 布局填 `std::vector<float> obs_`
   - 调 `runner_->act(obs_)` 得 action
   - `action * action_scale + default_q` → 经 `policy_to_motor_` 重映射 → 下发 `motor_cmd`
4. 文件末尾 `REGISTER_FSM(State_ASWWalk)`
5. `config.yaml` 加 `ASWWalk: { type: ASWWalk, ... }`
6. 若需速度注入，加 `set_velocity(double, double, double)` public 方法，并在 `main.cpp` 加 `dynamic_cast<State_ASWWalk>` 分支

**工作量**：1 个头文件（参考 `State_LSDLoco.h` 190 行作模板）+ 1 段 YAML + 可选 main.cpp 一行 cast。

### 5.9.3 通用注意事项

- **IDL 切换**：AS2-W 用 `unitree_hg`（非 `unitree_go`），`low_state_` 类型从 `unitree_go::msg::LowState` 改为 `unitree_hg::msg::LowState`，motor 数组 20 → 35，无 `foot_force`，header 用 `mode_pr` / `mode_machine`（见 §3.2 与 memory `unitree_hg-vs-go-idl`）
- **电机索引验证**：AS2-W 的 `motor()[i]` i→物理腿映射需在 sim 中实测确认（**未验证**）
- **PD 增益起点**：参考 Go2 的 kp=60/kd=5（FixStand）、kp=25/kd=1（RL 行走），AS2-W 因本体质量 11.178kg 接近 Go2，可作起点再调
- **增益渐变**：RL→站立切换必须保留 `State_Fix` 的 RL_KP/RL_KD → 目标 kp/kd 线性 ramp（见 memory `coding-pattern_rl-to-stand-gain-ramp`），否则剧烈抖动
- ** StandDown 折叠值**：AS2-W 的折叠姿态 q 值需按 `as2.xml` 重新实测（不能直接用 Go2 的 thigh≈1.29 / calf≈-2.80）
- **Jetson ORT 线程**：若 AS2-W 也跑 Jetson Orin，`OrtRunner` 构造时 `SetIntraOpNumThreads(1)` 必须保留（见 memory `onnxruntime_jetson_orin_crash_analysis`）

## 5.10 跨 dim 部署模式核心要点（一页纸）

```
┌─────────────────────────────────────────────────────────────┐
│  单一二进制 main.cpp                                         │
│    └─ CtrlFSM 按 config.yaml FSM._.<name>.type 实例化状态    │
│         └─ REGISTER_FSM(State_Xxx) 静态注册到全局 FsmMap      │
│                                                              │
│  每种策略一个 State_* 子类：                                  │
│    ├─ 标准 obs-group 策略 → State_RLBase（deploy.yaml 驱动） │
│    └─ 非标准 obs 策略   → State_Xxx（手动硬编码 obs 布局）   │
│                                                              │
│  OrtRunner 维度无关：运行时检测 ONNX shape，不写死 dim        │
│                                                              │
│  关节顺序：policy_to_motor_ 数组，J/L/SDK 三套，YAML 配置     │
│                                                              │
│  per-state 配置：policy_dir / kp / kd / scale / motion 全在  │
│  YAML，C++ 仅读不写死                                        │
│                                                              │
│  特技自动返回：is_completed() + return_state_ →              │
│    特技 → FixStand → StandDown → Passive 安全链              │
│                                                              │
│  速度注入多态：main.cpp dynamic_cast 按状态类型分发          │
└─────────────────────────────────────────────────────────────┘
```

**核心收益**：新增策略只动 YAML（标准型）或 1 个头文件 + YAML（非标准型），框架层零改动。AS2-W 多策略共存（行走 / 跳跃 / 待机 / 安全停止）可在同一二进制内实现，无需多份部署代码。
