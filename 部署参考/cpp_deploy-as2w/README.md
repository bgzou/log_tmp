# AS2-W / CPRO 部署工程（2026-11-08）

这个目录包含已在 **CPRO 鸿蒙内 ARM64 Ubuntu 22.04.5** 构建通过的策略核心、模型、AS2 SDK2 状态诊断和手柄高层控制工具。实机进入 Ubuntu 要用 `tools/cpro_ubuntu.sh` 的 UTS+mount namespace；已验证网卡 `eth0`、DDS 收包与原厂高层起立。现场目录、PC 单脚本入口与阶段清单在 `../../部署测试/`。

**当前边界：宇树离线资料确认 AS2-W 是 16 轴，但底层服务页只给标准 AS2 的 12 轴表；本工程不发布 LowCmd，也不自动释放官方运控。** 先在 CPRO 上部署本工程做模型校验、官方高层控制和只读/影子观测；拿到 AS2-W 四轮 DDS 槽位、轮速语义、CRC、控制权和故障退出合同后，才能把低层发送端接上。不要把 `as2w_sdk2 shadow` 当成会控制机器人的程序。逐页资料核对见 [`docs/official_findings.md`](docs/official_findings.md)。

`deploy/robots/as2w/config/config.yaml` 是可执行的策略目录，`tools/policy_select.py` 与 `tools/field.sh policy-*` 会读取它；六份权重可按名字做离线验证，三份盲爬楼权重可在映射核实后逐一只读影子推理。它还不是 GO2 的遥控器 FSM 或真机策略切换器。完整架构、迁移指南勘误和分阶段路线见 [`docs/architecture.md`](docs/architecture.md)，具体测试命令见 [`docs/policy_testing.md`](docs/policy_testing.md)。

GO2 upstream `deploy/` 的头文件与脚本逐组用途、是否需要移植，见 [`docs/go2_deploy_audit.md`](docs/go2_deploy_audit.md)。

现场完整顺序见 `../../部署测试/02_现场操作/明日bringup手册.md`；整个参考目录的来源审计和取舍见同目录 `参考资料总审计.md`。交付报告中三份爬楼权重的原生 MuJoCo 结果均为 **0/16**，不可把模型数值复现或影子推理当作真机楼梯通过。

## 来源与适配

- `src/policy.*`、`src/main.cpp`、`src/controller_test.cpp`、`models/` 来自 [Rob2Nav 交付提交 e61aaf7](https://github.com/YuTaoV5/Rob2Nav/tree/e61aaf79445fb2e2fdc996910cf0bd2e2f53b200/deliveries/as2w-deploy)，拷贝时保持原样。核心为 50 Hz、58 维观测、16 维输出，C++17 标准库推理 `.bin`，无需 ONNX Runtime。模型有翻正恢复与盲爬楼两类；盲爬楼权重还没通过交付的完整仿真关卡。
- `deploy/robots/as2w/src/diagnostics.cpp` 按宇树 [AS2 Sport 状态示例](https://github.com/unitreerobotics/unitree_sdk2/blob/main/example/as2/sport/as2_sport_state.cpp) 订阅 `rt/lf/sportmodestate`，按 [官方 MuJoCo AS2 消息说明](https://github.com/unitreerobotics/unitree_mujoco/blob/main/readme.md) 改用 `unitree_hg::LowState_` 订阅低层状态。**这只确定 As2 的消息家族，尚未验证 As2W 当前固件的具体 topic 和轮电机槽位。** 本工具的 `low-state` 可以传现场核实的 topic。
- 同一诊断文件可只读订阅原厂遥控器的 `rt/wirelesscontroller`，但现场 10 秒实收 0 包；`unitree_hg::LowState_.wireless_remote[40]` 则有数据。左摇杆前推与其中第 5 个 float 的正值相关，松开归零；其他轴/按键仍待标定。原厂遥控器可直接操作原厂高层运动，无需 Xbox。当前模型没有把手柄速度作为训练输入，**手柄不能直接改变恢复/爬楼策略方向**，未来可用于人工启停与模式选择。
- `deploy/robots/as2w/src/sport_gamepad.cpp` 是可选 Xbox 备选路径，使用 CPRO Linux `/dev/input/js*` 经 `SportClient` 发高层 Move/StopMove；默认 `--dry-run`。
- 上游代码已拉到 `../unitree_sdk2`（提交 `8e1b927`）和 `../unitree_mujoco`（提交 `1eb6642`，稀疏检出 As2 模型及仿真源码）。MuJoCo 的 As2 是 12 关节模型，不能充当 As2W 16 轴真机映射。
- 已拉取官方 `../unitree_ros/robots/as2w_description/as2w.urdf`，可验证四个轮轴确为连续旋转关节，但 URDF 中的关节顺序不能当成 DDS 电机槽位。官方离线页面 `底层服务接口` 与 `设备状态服务接口` 对内置服务名分别写 `ai_sports`/`ai_sport`，本工程不依据任一拼写自动关闭服务。

## 本地检查和打包

在个人 PC 的 PowerShell 中：

```powershell
python tools/check_models.py
powershell -ExecutionPolicy Bypass -File tools/package_for_cpro.ps1
```

输出 `dist/cpp_deploy-as2w.tar.gz`、`dist/unitree_sdk2-src.tar.gz` 和各自的 SHA-256。Windows 上的 `build_win/*.exe` 只是离线验证程序，**不能复制到 ARM64 Ubuntu 上运行**。已在本机对六个模型的 60 帧夹具与控制器测试执行验证；CPRO 上仍须重跑。

## CPRO 首次部署

**2026-11-09 实机补充：**这台 CPRO 已通过 USB/HDC 连通。实际 Ubuntu 在 `/data/ubuntu_in_hm/ubuntu_rootfs`；鸿蒙宿主须用 `tools/cpro_ubuntu.sh` 的 UTS+mount namespace 入口运行 Ubuntu SDK2。CPRO `eth0` 到 AS2-W PC1 和 DDS 已通；官方高层 `StandUp` 已由现场人员观察确认，遥控器仍能正常行走/趴下。详见 `../../部署测试/02_现场操作/实机事实与命令.md`。

1. Windows PC 已通过 USB/HDC 与 CPRO 连接。可在项目根目录运行 `powershell.exe -ExecutionPolicy Bypass -File .\部署测试\现场入口.ps1 -Stage Sync` 一次完成重打包、绝对路径 HDC 传输、CPRO 两包 SHA-256 校验和解包；其余阶段见 `../../部署测试/02_现场操作/现场入口使用.md`。HDC 本机传输源**必须是绝对路径**，否则可能在目标目录下创建相对路径树而没有更新旧包。工具来源与校验见 `../../部署测试/00_HDC工具/README.md`。
2. Ubuntu rootfs 入口是鸿蒙宿主 `/data/local/tmp/as2w_field/cpro_ubuntu.sh`；直接 chroot 会因鸿蒙 UTS 报 `kernel too old`，SDK2 还需隔离挂载 `/proc`、`/sys`、`/dev`。以下命令在该入口内运行；Windows 单脚本的 `-Stage Build`、`PolicyVerify`、`PolicyBench` 可直接替代：

   ```bash
   mkdir -p "$HOME/as2w_deploy"
   cd "$HOME/as2w_deploy"
   tar -xzf /实际路径/cpp_deploy-as2w.tar.gz
   bash tools/field.sh preflight
   bash tools/field.sh build
   bash tools/field.sh policy-verify all
   bash tools/field.sh policy-bench recovery-r12 3000
   bash tools/field.sh policy-bench stairs-r17-3000 3000
   ```

3. `build_on_cpro.sh` 先构建纯 C++ 策略并运行 7 项 CTest。SDK2 压缩包应解压到本工程同级目录；按官方 README 在 **CPRO 的 Ubuntu rootfs** 中安装，确认预编译 ARM64 库与实际 GCC/GLIBC 兼容、`unitree_sdk2Config.cmake` 可找到后，再执行：

   ```bash
   cd "$HOME"
   tar -xzf unitree_sdk2-src.tar.gz
   cmake -S unitree_sdk2 -B unitree_sdk2/build -DBUILD_EXAMPLES=OFF \
     -DCMAKE_INSTALL_LIBDIR=lib \
     -DCMAKE_INSTALL_PREFIX="$HOME/unitree_sdk2_install"
   cmake --build unitree_sdk2/build --parallel "$(nproc)"
   cmake --install unitree_sdk2/build
   cd "$HOME/as2w_deploy"
   bash tools/fix_sdk2_links.sh "$HOME/unitree_sdk2_install/lib"
   bash tools/field.sh sdk-build "$HOME/unitree_sdk2_install"
   ```

4. 现场已验证 CPRO 宿主 `eth0`→PC1 `192.168.123.161`，`192.168.123.100/24` 加局部策略路由后 ping 及 DDS 正常。宿主 `tools/cpro_host_net.sh status|apply` 可重现这一步，**不改默认路由**；Windows 单脚本使用 `-Stage NetworkStatus` / `NetworkApply`。仅在确认现场仍为 `eth0` 和该子网时执行 `apply`。

## 无电机写入的现场验收

推荐使用单一入口 `bash tools/field.sh STAGE ...`，自动留下时间戳日志；完整阶段和门槛见 `../../部署测试/02_现场操作/明日bringup手册.md`。下列底层命令仍可单独运行。

```bash
# 先验证官方 As2 高层状态
./build-sdk2/as2w_sdk2 sport-state eth0 10
./build-sdk2/as2w_sdk2 motion-mode eth0
./build-sdk2/as2w_sdk2 remote-state eth0 20

# 再使用官方高层 API 做基础动作；每次调用前确认本体状态和场地
./build-sdk2/as2w_sdk2 sport-command eth0 get-state
./build-sdk2/as2w_sdk2 sport-command eth0 stand-up
./build-sdk2/as2w_sdk2 sport-command eth0 stop-move
./build-sdk2/as2w_sdk2 sport-command eth0 stand-down

# 确认本机固件 LowState 的 IDL/topic 后，先只读 35 槽数据
./build-sdk2/as2w_sdk2 low-state eth0 rt/lowstate 10 | tee lowstate.log
```

官方 DDS 页列出 `rt/lowstate` 的 HG 类型，`rt/lf/lowstate` 是低频版本；现场要验证当前固件能否收到。`low-state` 打印全部 35 个消息槽位，不代表 35 个实装电机。测得 **16 个目标轴的槽位、符号、编码器零位**后，复制 `config/calibrated.map.example` 为 `config/calibrated.map` 并逐行填真实数值。官方资料给出 IMU 四元数顺序 wxyz，但 body/world 旋转方向仍需对照实机；确认是 `body-to-world` 后才运行：

```bash
./build-sdk2/as2w_sdk2 shadow eth0 rt/lowstate \
  models/stairs-r17-3000.bin config/calibrated.map 10 --imu-wxyz-body-to-world
```

`shadow` 只计算并打印目标，从不下发电机命令。恢复策略在低层接管后必须有持续可用的机体系线速度，当前工具拒绝对恢复模型做在线影子推理。`Controller::step()` 的空输出不能充当物理机器人安全保持/制动语义。

若现场能用个人 PC SSH 到 Orin，可把 `tools/probe_orin.sh` 复制过去运行，收集只读系统、网口、路由与相关服务清单。**PC 直连 Orin 用于排查，不承担策略推理**；最终仍应从 CPRO 的实际有线网口重复 DDS 收包验证。

## 原厂手柄与可选 Xbox

**优先使用 AS2-W 原厂遥控器。** 它直接和机器人配对；CPRO 无需接蓝牙或 USB 手柄。这台固件实测 `rt/wirelesscontroller` 订阅 10 秒 0 包，但 HG `LowState_.wireless_remote[40]` 有报头和变化。用 `bash tools/field.sh low-remote eth0 10` 只读记录候选轴/键，逐项确认后才能用作未来 FSM 输入。原厂遥控器的高层运动由机器人原厂程序处理；原厂运控退出后该字段和实体急停是否仍有效，必须另行实测。

**可选备选：Xbox 手柄用 USB 线直接插 CPRO**，而不是插个人 PC，也不是连机载 Orin。鸿蒙宿主识别之后，检查 Ubuntu 的 `/dev/input/js0` 和 `/dev/input/event*`。若设备节点没有透传，先核实 `/dev` 挂载和宿主 HID 支持。蓝牙方案是先在 **CPRO 鸿蒙系统**完成配对，再检查同样的 Linux 输入节点。

```bash
python3 tools/probe_gamepad.py /dev/input/js0 --seconds 15
./build-sdk2/as2w_sport_gamepad eth0 /dev/input/js0 1 0 3 4 --dry-run
```

`probe_gamepad.py` 会打印按键和轴编号。把示例的 `1 0 3 4` 按实际 Xbox 手柄输出改为“前后轴、左右轴、转向轴、持续按住的 deadman 按钮”。确认坐标方向、原厂 Sport 模式和 `StopMove` 后，先在可控场地显式运行 `./build-sdk2/as2w_sdk2 sport-command eth0 balance-stand` 解锁运动，再把最后一个参数改为 `--enable-sport`。官方 As2W 轮足高层页说明 `BalanceStand` 是从锁定站立切到可移动状态。高层测试限速为前后 `0.15 m/s`、左右 `0.10 m/s`、转向 `0.20 rad/s`，会话最长 120 秒；松开按钮或输入 350 ms 不更新就调用 `StopMove`。为了触发 Linux joystick 的事件更新，测试时需持续轻微移动摇杆。原厂遥控器应留在现场作应急操作，但低层接管后的作用需另行核实。

**键盘也是备选**，可以用 `sport-command` 逐项做站立、停止和趴下测试。当前没有可由手柄调速的普通行走策略；恢复和盲爬楼策略内部有固定指令，不能把手柄轴值直接塞入观测代替训练时的定义。`StopMove` 只是停止运动，官方轮足文档所述的阻尼急停对应 `Damp`。

## 真机低层控制仍需核实

用户现场可用个人 PC 接入 AS2-W Orin 收集证据，逐项填写 [`config/hardware_contract.md`](config/hardware_contract.md)：设备型号/固件、DDS topic 与 domain、LowState IDL、16 轴槽位和轮速单位、`mode_pr/mode_machine`、电机 `mode`、CRC、运控释放/恢复、失联后制动和急停。只有这些与训练的 16 轴坐标、IMU、机体速度合同吻合后，才可编写并启用 LowCmd 发送端。公开 SDK2 的 `example/as2` 没有 As2W 低层写入示例；Go2-W 的 `unitree_go` 写入不能照抄。
