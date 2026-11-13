# 两类策略如何选择与测试

## 与 GO2 工程的关系

GO2 `deploy/robots/go2/config/config.yaml` 的 `FSM` 把遥控器按键、固定姿态、多个 `RLBase` 状态和 `policy_dir` 连成持续控制程序。这里的 `deploy/robots/as2w/config/config.yaml` 是**交付权重目录**，由 `tools/policy_select.py` 实际读取，用于选择某个模型做离线核对或只读影子推理。当前没有低层 LowCmd 发布端、没有真机 FSM，也没有遥控器按键切换策略功能。仅修改配置或选择模型不会让狗执行动作。

模型一共六份，不是两份。`recovery-r09/r12/r13` 属于翻正恢复；`stairs-r14/r17-2000/r17-3000` 属于盲爬楼。`models/manifest.json` 保留来源检查点和模型哈希，`deploy/robots/as2w/config/config.yaml` 给现场命令提供名字、文件路径和测试资格。每个 `.fixture` 是训练交付的 60 帧参考输入输出；通过它只说明推理结果与交付参考一致。

交付的 `mujoco-native-report.json` 中，恢复 r09/r13 为 16/16，r12 为 15/16；三份爬楼均为 **0/16**。完整训练/仿真归档未在当前参考目录，无法只凭 fixture 重新复核该物理通过率。现场不安排楼梯实测，先向训练同事获取更新检查点和固定场景复测。

| 阶段 | 翻正恢复 | 盲爬楼 | 狗会动吗 |
| --- | --- | --- | --- |
| 离线模型校验 | 六十帧夹具逐模型核对 | 同左 | 否 |
| DDS 状态与原厂遥控器检查 | 采集未来需要的状态 | 同左 | 仅原厂高层动作阶段可能运动 |
| 在线影子推理 | 暂停：缺低层接管后可信的机体系线速度 | 验证 16 轴映射及 IMU 后，50 Hz 计算并记录目标 | 否 |
| 低层实机策略 | 待 16 轴、轮速、速度源、运控切换、失联处理与紧急退出合同通过 | 待相同合同及楼梯场地条件 | 是；当前未实现 |

## 现在即可运行：按名字选择与核对

在工程目录运行（Windows 可直接用 `python tools/policy_select.py ...`；CPRO Ubuntu 用 `python3`）：

```bash
bash tools/field.sh build
bash tools/field.sh policy-list
bash tools/field.sh policy-verify all
bash tools/field.sh policy-verify recovery-r12
bash tools/field.sh policy-verify stairs-r17-3000
bash tools/field.sh policy-bench recovery-r12 3000
bash tools/field.sh policy-bench stairs-r17-3000 3000
```

`policy-list` 会显示六个模型的类别和可测阶段。`policy-verify` 用真实模型跑交付夹具，退出码非零表示校验失败。每次 `field.sh` 调用的日志存于 `field_logs/`，完成阶段后复制回本机 `部署测试/04_调试记录/` 并写判断。
`policy-bench` 在当前 CPU 上反复运行固定观测，仅计纯推理的 p50/p99/max；必须在 CPRO 上重跑，低于 20 ms 仍不代表包含 DDS 和系统调度的闭环达标。

## 到 CPRO / AS2-W 后的顺序

1. 按现场清单完成 CPRO Ubuntu 构建、SDK2 编译、DDS 只读收包、原厂遥控器话题和原厂高层站立/趴下测试。此时两个策略都没有接管电机。
2. 依据现场硬件合同填写 `config/calibrated.map`，核实 IMU 四元数方向。选**一份**爬楼模型做只读影子推理：

   ```bash
   bash tools/field.sh policy-shadow stairs-r17-3000 eth0 config/calibrated.map 10
   ```

   若需比较其他交付权重，分别运行 `stairs-r14` 或 `stairs-r17-2000`，保留各次日志。`SHADOW_ONLY` 表示程序只打印轮速等目标，不发送 LowCmd；不要把输出当作真机爬楼效果。
3. 翻正模型目前只做 `policy-verify recovery-r09|r12|r13`。程序会拒绝 `policy-shadow recovery-r12 ...`，因为恢复策略需要机体系线速度，而当前低层接管后尚无已验证的持续来源。
4. 真机翻正和爬楼都等低层控制端完成及硬件合同通过后，另写有明确启动、停止、超时、遥控器和运控恢复规则的 FSM。翻正不能通过随意推倒机器人来“试一下”；爬楼需先在受控平地验证起停与制动，再安排楼梯场地。当前交付包没有这一步的执行命令。

原厂遥控器现阶段用于机器人原厂高层运动与 `remote-state` 观测；它不会自动切换这六个模型。将来若要类似 GO2 的按键切换，需要在经验证的低层控制程序中明确设计按钮映射、状态门槛和切换过渡。
