# 2026-11-09 OpenCode 会话：离线映射分析 + 只读影子 20 ms 链路测试

- 执行者：服务器 OpenCode 经 SSHFS（工作站目录）+ SSH→工作站→HDC→CPRO。本阶段零实体动作：
  仅只读订阅（`rt/lowstate`）与离线计算；狗全程趴下（运行前后 `GetState` 均为 `fsm_id=0 ai_damping`）。
- 环境：服务器 Python 3.12.3/NumPy 1.26.4；服务器本地 x86 构建 SDK2+诊断程序用于编译检查；
  CPRO 端 ARM64 `sdk-build` 7/7 测试通过、`as2w_sdk2` 重新编译链接。

## 一、20 Hz 600 帧采样离线运动学分析（不动狗）

- 脚本：`部署参考/as2w-flat-rerun/analyze_capture.py`（输入 `logs/20261109-100054_windows_LowCapture.log`，
  摘要 `部署参考/as2w-flat-rerun/results/capture_analysis.json`）。
- 事实：槽 16–34 全程为零。槽 0–11 为**按腿三元组** (hip,thigh,calf)×4：趴下 ≈[±0.58, ~1.0, −2.75]、
  站立 ≈[±0.21, 0.83, −1.99]，全帧均在官方 URDF 限位内（hip ±0.785、calf [−2.7677,−0.8133]）。
  hip 符号 (−,+,−,+)：腿组 {0,2} 与 {1,3} 分属两侧（左右镜像）。慢走时四轮槽 dq 全正
  （前向全正，与 URDF 轮轴 +y 一致）；轮累计角变化 +3.44~+3.82 rad 与 0.3 m 行程/轮半径吻合。
- IMU 只读验证：四元数 wxyz、单位、body→world；陀螺与四元数差分三轴相关 0.83–0.93、斜率≈1
  （机体系角速度、符号一致）；采样全程机体水平（up cosine ≥0.9997）。
- 未解决：腿/轮绝对身份（前后分组）——起立/趴下四腿同步（20 Hz 下 <0.1–0.2 s）且 AS2-W 为轮驱滚动
  （四腿 thigh dq 互相关全部 ≥0.95，无步态对角结构）；轮左右分组被过渡段污染（dq~gyro_z 回归呈 1-vs-3 假象）。
  站立 thigh 0.83 接近训练默认 0.8（或为巧合），calf −1.99 vs 训练 −1.6 差 0.39——零位约定未验证。
- 结论写入 `部署参考/cpp_deploy-as2w/config/hardware_contract.md`（更新 6 行、新增姿态锚点行与
  hypothesis.map 说明）；`calibrated.map` 仍 UNVERIFIED，不填。

## 二、源码改动（均为只读诊断增强）

1. 新增 `config/hypothesis.map`：16 行假设映射（腿按三元组假设+族惯例腿序、轮 12–15、sign=+1、offset=0），
   **仅用于链路计时/影子连通性，不作标定结论**。
2. `diagnostics.cpp` shadow：新增 tick 计数、stale_skips、locked 标记、状态年龄与推理耗时的
   p50/p99/max 百分位，结束时输出 `SHADOW_SUMMARY`。
3. `部署测试/现场入口.ps1`：新增 `Shadow` 阶段（`policy-shadow $Model eth0 config/hypothesis.map $Seconds`），
   无任何动作能力；`现场入口使用.md` 同步更新。
- 过程记录（诚实记录）：编辑 shadow 函数时误将包内已验证的 `src.q` 写成 `src.q()`，服务器 x86 编译检查
  立即报错（`expression cannot be used as a function`）；对照 `01_现场部署包` 内可编译版本修正后，
  diff 确认源码=包+预期统计增强，x86 与 CPRO ARM64 编译均通过。此事故即为"代码变更必须跑编译检查"的例证。
- 服务器侧检查命令与结果：`cmake --build build-sdk2`（含 SDK2 头）通过；`ctest` 7/7 通过。

## 三、部署与只读影子链路测试（狗趴下，无动作）

- 命令链（服务器→工作站 SSH）：`-Stage Sync`（两包 SHA-256 OK，11:27）→ `-Stage SdkBuild`
  （7/7 测试、ARM64 重编，11:27:36）→ `-Stage GetState`（`ai_damping` 确认，11:27:48）→
  `-Stage Shadow -Model stairs-r17-3000 -Seconds 60`（11:27:56–11:28:05）。
- Shadow 实际输出（CPRO 原始日志 `field_logs/20261109-112756_policy-shadow_5340.log`，已归档回传）：
  - `SHADOW_ONLY stairs-r17-3000; no LowCmd will be published`（程序自身声明无发布）
  - 451 tick @50 Hz，`stale_skips=0`（1 kHz LowState 连续）
  - `age_ms p50=0.546 p99=1.133 max=21.717`；`compute_ms p50=0.247 p99=0.638 max=1.156`
  - `locked=1`：**stairs 策略 450 tick（9 s）视界的按设计停止**（`Controller` horizon），非链路故障；
    因此 60 s 请求只产出 9 s 有效段。首个 tick 预演轮速 8.74 rad/s（动作历史零初始化瞬态），随后收敛 ~3.93。
- 判断：**20 ms 链路（收包→解码→58 维观测→推理→内存预演编码）在 CPRO 上实测通过**，
  最坏一帧 21.7+1.2 ms 仍低于 50 ms 锁定阈值的约一半；此为趴下状态的链路验证，不代表策略语义正确
  （映射未标定、输入分布外）。轮 dq 预演值有界合理。
- Windows 侧日志：`logs/20261109-112712_windows_Sync.log`、`logs/20261109-112723_windows_SdkBuild.log`、
  `logs/20261109-112748_windows_GetState.log`（近似时刻）、`logs/20261109-112755_windows_Shadow.log`；
  CPRO 归档 `logs/cpro_field_logs_20261109_1130.tar.gz`（69,885 字节，含本轮 sdk-build/get-state/policy-shadow
  原始日志）。回收方式：宿主 tar 不可用，改经 `cpro_ubuntu.sh /bin/tar` 在 Ubuntu 内打包后 HDC file recv
  （Windows 本地路径须用反斜杠绝对路径）。

## 四、未解决问题 / 下一门槛

- 影子语义限制：stairs 视界 9 s/回合，长时影子需定义回合重置语义（动作历史归零重臂）——已列入待办。
- 待现场人员配合（**每次需明确同意、先说明具体动作**）：
  ① 站立态 60 s 只读影子（需要用原厂遥控器起立；观察站立分布下的预演目标）；
  ② 站立原地慢速左/右转各 ~10 s（分轮左右槽）；③ 1 kHz 采样起立/趴下（分前后腿次序）。
- 平地 MuJoCo 结论（stairs 三权重均能走、r17-3000 最佳）见 11:20 节；真机行走仍是第三轮受控写入，
  门槛不变：映射标定 → 硬件合同 → 看门狗/急停验证 → 现场人员当次明确同意。
