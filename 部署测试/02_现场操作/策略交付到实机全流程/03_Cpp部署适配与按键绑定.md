# S3 C++ 部署适配、按键绑定与 ARM64

唯一维护源码：`部署参考/cpp_deploy-as2w/`。范例：R1199（`deploy/robots/as2w/r1199/`）。

## 1. 控制器库（新策略目录）

```text
deploy/robots/as2w/rXXX/
  rXXX_controller.hpp   # Config/SensorState/Targets/Controller 接口（抄 r1199 结构）
  rXXX_controller.cpp   # load_config(yaml校验) + step(obs构建→ONNX→包装→目标)
  rXXX_replay.cpp       # 离线夹具回放（parity 用，输出 R1199_OBS/R1199_TARGET 行）
  CMakeLists.txt        # 独立选项 AS2W_RXXX(_CANDIDATE/_PUBLISH)，默认全 OFF
```

要点：
- `load_config` 硬校验 deploy.yaml（模型版本/维度/增益/限值），不符即 throw。
- 共享 Debug 接口：控制器提供 `last_observation()`（**实际送入模型**的完整输入）和 `last_raw_action()`（未经包装的模型输出）；有额外 ONNX state 输入时一并导出诊断字段。新策略不能只从 LowState 推测 Observation，历史/上一动作/命令滤波等必须从真实推理帧记录。
- 候选构建用**独立宏**隔离（如 `AS2W_R1199_JOYSTICK_CANDIDATE` + `AS2W_R1199_TRAINING_CONTRACT`），**不重编已验收旧二进制**。
- 摇杆限速从 deploy.yaml 读（`vx_limit/wz_limit`，范围 0.01–0.30；R1199 已实现可配置模式）。

## 2. 发布端与按键 FSM（共享 `deploy/robots/as2w/common/as2w_publish.cpp`）

> 2026-11-12 已完成统一命名：原名 `r214/r214_publish.cpp`（R214 时代遗留，被 R1199/R249/R270/R284 共享）→ `common/as2w_publish.cpp`。机械改名 + include 修正，已走完整重验链（x86 重编/CTest 9/9/audit/parity 1.19e-7 + 四旧策略 CMake 配置验证 + CPRO 同步/删旧文件/ARM64 重编/CTest 9/9/audit + 重打包）。新策略接入此文件只需加 `AS2W_POLICY_RXXX` 宏分支。

- 加 `#if defined(AS2W_POLICY_RXXX)` 分支（namespace alias + 控制器包含）。
- **按键语义（现行 FSM，勿改语义只加策略）**：
  - **A** = FixStand 插值 → 固定 PD Stand（策略中 A=先刹车/冻结最后目标再回站）
  - **B** = PolicyHandoff（2s 零速交接，带 gate：pose_error/轮速/upright/静止检查）→ PolicyWalk
  - **Y** = FixSquat 受控趴下；**X** = 紧急 Passive/EmergencyDamping
  - 速度上限=摇杆映射函数 `map_rXXX_joystick_command`（限幅在 deploy.yaml 包络内）
- B 门参数、stand-hold 超时（现 30s，二进制上限 30）、60s PolicyWalk 上限都是发布端参数。
- `--offline-audit` 必过（守卫注入/映射检查）。
- **POLICY_DIAG 逐帧诊断**（R1199 已内置，`AS2W_POLICY_R1199` 门控）：50Hz 本地文件 `policy_diag.log`，记 raw ONNX/包装动作/最终目标/补偿内部态/tick——推理侧↔硬件侧分流的依据。
- **通用 `--debug`**：共享发布端写 `debug_policy.csv`（每次推理的模型输入、raw/包装/滤波前后目标）和异步 `debug_lowcmd.csv`（500Hz 最终发布帧）；新策略启动器必须透传 `--debug`，会话脚本必须在 ReleaseMode 前查磁盘、启动只读 LowState/保护流并归档两个 debug 文件。`--policy-lowpass-ms` 是独立构建才接受的实验选项；不同策略需分别配置/仿真/验收，不能把滤波后的结果当作原训练合同结果。

## 3. 模型与部署配置

```text
models/rXXX/deploy.yaml   # policy_file/model_version/维度/关节名/默认角/刚度/阻尼/vx_limit/wz_limit
models/rXXX/policy.onnx
```
硬件映射沿用 `config/r152_measured.map`（16 轴 DDS 槽位/符号已实测，见 `AS2W_16轴DDS关节序速查.md`）。

## 4. 构建门槛（两台机器、双端口 SHA 一致才进 S4）

**x86（caolin）**：
```bash
rsync -a --exclude='/b/' --exclude='/build*/' <SSHFS工程>/ /tmp/opencode/<build镜像>/
cmake -S . -B b -DAS2W_RXXX=ON ... -DONNXRUNTIME_ROOT=/tmp/opencode/onnxruntime-linux-x64-1.22.0
cmake --build b -j8 && ctest --test-dir b --output-on-failure   # 必须全过
<binary> models/rXXX/deploy.yaml config/r152_measured.map --offline-audit   # AUDIT PASS
```
再跑一次 C++ parity（夹具经 `rXXX_replay` → parity 脚本 ≤1e-6）。

**ARM64（CPRO）**：
- 传文件两跳：caolin → scp 工作站 `C:\Users\zoubu\` → `hdc -t 192.168.10.180:8710 file send`（中文路径必炸，走英文中转；大文件用 scp，命令行 base64 会超长）。
- 远端执行走 base64 脚本法：`hdc shell /data/local/tmp/as2w_field/cpro_ubuntu.sh /bin/bash -lc 'echo <B64> | base64 -d > /tmp/x.sh && bash /tmp/x.sh'`。
- CPRO 上 `cmake -S /root/as2w_deploy -B build-rXXX ... -DONNXRUNTIME_ROOT=/root/ort122 -DCMAKE_PREFIX_PATH=/root/unitree_sdk2_install`，构建+CTest+audit，`sha256sum` 两端核对。

## 5. 现场入口三件套

1. `tools/run_rXXX_field_session.sh`：完整预检链（二进制/SHA/audit→LowState≥100包/s+mode_machine=2→趴下确认→控制权→16轴mode0→趴下门槛→双监测启动→发布端）。模式白名单 + dry-run 档。抄 r1199 版改路径即可。
2. `tools/run_rXXX_<mode>_trial.sh`：发布端启动器（指向新 build 目录，参数同已验证模式）。
3. Windows `部署测试/运行现场策略会话.ps1`：注册 `-Policy rXXX` 的模式白名单；**运动模式必须 `-ConfirmMotion`**。工作站上 `C:\Users\zoubu\as2w_session.ps1` 是无中文路径包装（SSH 调用时用）。

监测与归档（已在 r1199 会话脚本内置）：2ms 快采集 + 保护流 + `nice -n 10`；POLICY_DIAG 归档；会话目录自动拉回 `部署测试/04_调试记录/logs/field_sessions/`。

## 6. 打包

改任何源码后必跑 `部署测试/准备现场包.ps1`（工作站），记录 `01_现场部署包/` 里两个 tar 的 SHA。不要手工改压缩包。
