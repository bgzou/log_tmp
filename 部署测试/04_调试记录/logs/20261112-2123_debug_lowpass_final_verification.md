# 2026-11-12 21:23 Debug / 策略目标低通最终离线核验

环境：Windows 工作站；CPRO Ubuntu 容器（经 HDC `192.168.10.180:8710` 执行 ARM64 构建及只读命令）。狗未上电，LowState 为 0 包。本阶段没有 ReleaseMode、LowCmd 或任何机器人动作。

## 实现与范围

- 共享发布端 `deploy/robots/as2w/common/as2w_publish.cpp` 增加 `--debug`：每次策略推理记录实际 Observation（R214 另含 state 输入）、原始/包装动作、命令、传感器值、策略目标及滤波后目标；成功 DDS Write 后以有界队列异步记录约 500 Hz 的 16 轴最终 LowCmd。现场会话仍独立采集 LowState 和保护流。新策略须在控制器提供实际模型输入与 raw 输出，并在会话脚本透传 `--debug`。
- 同一共享发布端增加可选一阶低通，时间常数由 `--policy-lowpass-ms` 指定。只滤 PolicyWalk/Brake 的腿位置目标；默认轮速不滤，轮速若显式选择也只滤 PolicyWalk；Brake 轮速、X、Passive、固定站立、趴下和所有增益不滤。R1199 仅在隔离构建中开放此候选，Windows 与 CPRO 脚本均在发布前锁住滤波运动入口。
- 滤波属于新的执行合同；模型 previous-action 仍回填包装动作（滤波前）。闭环仿真必须复制这个细节，不能继承无滤波版本通过率。

## 核验

- CPRO ARM64 最终构建日志：`20261112-2120_debug_lowpass_tick_fix_build.log`。共享构建 CTest 16/16；R1199 独立 filter/debug 各 9/9；R214 debug stand/zero-b/full 各 8/8；五个 Debug 构建各做 500 帧/500 Hz 离线写盘审计，均 `dropped=0 file_ok=1`、`AUDIT PASS`。这是合成帧测试，未验证真实 DDS 负载与设备接受性。
- `20261112-2140_debug_lowpass_frame_parity.log`：旧 R1199、Debug 构建、filter 构建在**滤波关闭**的离线帧 SHA 相同。之后只改 Debug 所记录的 sensor tick；最终 ARM64 构建/audit 已重跑。
- PowerShell 会话入口语法解析 PASS；CPRO 上三个相关 shell 脚本 `bash -n` PASS。Windows 与 CPRO 两层滤波运动拒绝已离线试过。`20261112-2230_r1199_debug_filter_dryrun.log`：远端审计 PASS、LowState 0 包处 FATAL，未 ReleaseMode；Windows 已修为识别远端 `FATAL`，不能把 HDC 退出码 0 当成功。
- 源码 SHA256（Windows = CPRO = 最终现场包）：`0b019509477200c1abcd0afdedaf835cf96ce616589acc5a85451d1424faa674`。R1199 会话脚本 SHA `fb8dadd63655fb6ae16817655c96c555e26d753a7e0c20b7375be0ceaaa6e07b`，R214 会话脚本 SHA `580e74b0f2191d0e964c526dd7ae349c4a58df3c7eafb57257279fecb364d5da`，三者 Windows/CPRO/现场包一致。最终现场包 `cpp_deploy-as2w.tar.gz` SHA `29a20d66f4778231be66aa0fe4d2c1ae43db6896a9f04205bd86359a10039e9a`，打包日志 `20261112-2125_debug_lowpass_final_package.log`。
- 历史 R1199 真机目标的开环重算：`20261112_r1199_lowpass_trace_estimate.py`、`.txt`。腿目标最大单帧步进 p99 从 0.12341 rad 降到 60 ms 滤波估算 0.02766 rad，80 ms 为 0.02139 rad。此估算未含反馈，不能推断稳定性或抖动声源消失。

## 待做 / 门槛

1. caolin 服务器本次 SSH 连续超时，且 CPRO Python 没有 MuJoCo；尚未完成相同滤波参数、相同 previous-action 语义的闭环 MuJoCo，**滤波运动入口继续锁定**。
2. Debug 在真实 DDS/磁盘负载下的控制周期、丢帧和看门狗仍需单独有界验收；首次实际 R1199 对照应 `-Debug -LowPassMs 0`，再比较开启滤波的独立候选。任何会使狗动作的步骤须现场人员当次明确同意。
3. 现场日志以本机 `04_调试记录/logs/field_sessions/` 和 INDEX 为准。滤波/Debug 结果不得覆盖旧 R1199 验收结论。
