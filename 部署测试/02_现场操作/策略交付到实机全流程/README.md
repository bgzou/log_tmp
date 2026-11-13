# 策略交付到实机全流程（总览）

适用：任何同事按《AS2-W训练到部署交付清单 v3》交付的新策略（新权重/新包装/新开关）。目的：**新策略到手后照本节走完，不用从头摸索**。本目录是流程索引与门槛说明；具体脚本路径见 `参考文件索引.md`。

三个执行环境（命令在哪跑要看清楚）：
- **caolin 服务器**：项目挂载在 `/home/caolin/as2w_workstation`（= 工作站 `D:\Projects\Athena\运动控制\Collie\AS2-W_CPRO`）；编译/仿真缓存在 `/tmp/opencode/`（不随项目走，丢了按各阶段文档重建）。
- **Windows 工作站**：唯一能碰 CPRO 的机器（HDC）；打包、现场会话入口都在 `部署测试/`。
- **CPRO**：Ubuntu rootfs 内 `/root/as2w_deploy`，ARM64 构建/发布端运行地。

## 阶段总览与门槛

```
[S0 收包验收] → [S1 移植对齐(parity)] → [S2 sim2sim] → [S3 C++适配+ARM64] → [S4 实机验证]
     门槛:            门槛:                 门槛:            门槛:               门槛:
  包完整/SHA/       obs≤1e-6 /ONNX        无跌倒/无非轮     CTest全过/audit     逐次现场
  自带校验通过      对齐他们录制数据        接触/判据复现     PASS/SHA两端口一致   当次同意
```

**硬规则（任何阶段不可绕过）**：
1. **训练合同三方一致**：训练 `actual_runtime_flags` == 仿真验收开关 == 部署 C++ 编译宏，逐项核对；任何差异即新版本，重走全流程（本次 R1199 停走跳步的教训）。
2. **逐次动作同意**：任何可能使狗动作的命令，先说明该次具体动作/风险，等现场人员当次明确同意。Ctrl+C 不是运动急停（X/物理急停才是）。
3. **唯一维护源码**是 `部署参考/cpp_deploy-as2w/`；改完必须重跑 `部署测试/准备现场包.ps1`。
4. 失败也要记 `部署测试/04_调试记录/INDEX.md` 并归档原始日志。

## 新策略到来时的快速清单

1. **收包**：跑同事包里的 `checks/verify_package.py`（或等价物）核 SHA；读 manifest/handoff/README，确认技能范围与已验证域。→ `01_收包验收.md`
2. **读运行时合同**：`runtime/observations.csv`（逐维）、`joints.csv`（关节序/缩放/增益）、`effective_runtime.yaml`、`entry_exit.md`。**列出与已知策略的差异点**（重力符号、上一动作 raw/wrapped、命令偏移、轮位槽补零…）。→ `02_移植对齐与sim2sim.md` 的"差异点清单"
3. **建 Python 移植 + parity**：用他们包里的回放数据（native_samples.npz 或 replay/ 夹具）做逐帧比对，obs/action 双双 ≤1e-6 才算过。
4. **sim2sim**：在 caolin 的 MuJoCo 平台上闭环跑他们的验收场景（命令矩阵、初态、判据全复现）。**先判断轮控性质**：被动静摩擦型策略在 MuJoCo 大概率失败（摩擦保真问题，见 mlp57 案例）——失败时按文档分流，不是无限调参。
5. **C++ 适配**：在 `cpp_deploy-as2w/deploy/robots/as2w/` 新建 rXXX 控制器 + CMake 选项 + `models/rXXX/deploy.yaml`；共享发布端 `r214_publish.cpp` 加 `AS2W_POLICY_RXXX` 宏；x86 编译+CTest+audit。→ `03_Cpp部署适配与按键绑定.md`
6. **ARM64 + 现场入口**：同步到 CPRO、ARM64 构建/CTest/audit、核两端口 SHA；新建 `tools/run_rXXX_field_session.sh` + 试验启动器；Windows `运行现场策略会话.ps1` 注册模式（带 `-ConfirmMotion` 门）。速度包络写 `deploy.yaml` 的 `vx_limit/wz_limit`。
7. **重新打包**：`准备现场包.ps1`，记录包 SHA。
8. **实机验证阶梯**：dry-run（只读）→ 零速 zero-B → 有界低速 → 短时摇杆，每步单独同意、双监测+POLICY_DIAG 全程记录、会话自动归档。→ `04_实机验证阶梯.md`
9. **每阶段后**：INDEX 记录 + 原始日志归档 + 给训练侧反馈（如有问题）。
10. **两个工作范例**：R1199（完整走过 S1–S4 全链，含训练合同修复）和 mlp57（走到 S2 失败、失败分析方法论）。

## 目录

- `01_收包验收.md` — S0：包结构、校验、合同阅读要点
- `02_移植对齐与sim2sim.md` — S1+S2：parity 方法、MuJoCo 平台、已知差异点与坑、失败分流
- `03_Cpp部署适配与按键绑定.md` — S3：控制器/发布端/CMake/部署yaml/按键FSM/现场入口/ARM64
- `04_实机验证阶梯.md` — S4：dry-run→zero-B→有界→摇杆的阶梯、监测、归档、恢复
- `05_CPRO数据同步与远程操作.md` — caolin↔工作站↔CPRO 全链 cookbook：连通恢复、两跳传文件、base64 脚本法、整包/定点同步选择、ARM64 远端构建、日志回收、坑清单
- `参考文件索引.md` — 全部脚本/文档按用途索引（哪台机器、什么作用、哪个范例用过）
