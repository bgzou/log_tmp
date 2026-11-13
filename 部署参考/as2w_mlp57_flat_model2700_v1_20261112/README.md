# AS2-W 四足平地 MLP57 · 已验证历史快照

| 项目 | 本包声明 |
|---|---|
| 策略身份 | as2w_mlp57_flat_model2700_v1_20261112；2026-11-12；负责人未提供，Codex整理 |
| 选中输出 | **model_2700，完成2701次PPO更新**；原±1.0m/s范围，非当前±1.5续训版本 |
| 技能 | 标称四足站姿开始的平地滚动，单一确定性Actor，无内置运动状态机 |
| 输入/输出 | float32[batch,57]→float32[batch,16]；50Hz；12腿位置偏移+4轮速，经所附包装/PD |
| 入口/终点 | 仿真参考腿角[0,0.65,-1.3]×4、零初速；零命令请求停车，无独立“动作完成”或控制权交接信号 |
| 已验证 | 原生PhysX 39命令×4初态=156例；生存/姿态/接触/停车各156/156；**严格三轴速度56/156** |
| 已知失败/未验证 | 低速横移弱、转向伴随额外平移、1m/s欠速；无楼梯/任意倒地起身/长期驻停声明；MuJoCo闭环、ARM64和真机策略控制均not_run |
| 建议用途 | **sim2sim_candidate**；已有完整接口和离线对齐材料，尚需第二仿真器及部署侧硬件合同 |

这是“之前有稳定回放的MLP”归档包，不把“未跌倒”当成全部速度跟踪成功。三轴命令范围是训练范围，不能等同每条命令均通过。没有教师、StraightRoll或StopStance接管；与当前扩大范围继续训练的任务独立。

模型SHA256：

- 选中checkpoint：`68ef6b47cf8462ffb9d01660d60159b5fd4654db3ec4e9d4be4a7863c03b78fe`
- 初始化旧checkpoint：`41718560bdd44754f6fb756156eafdd3f60ae7753e26da1e81915636a0e829af`
- TorchScript：`bc579e4380c7bc08d29d415153fc6eb481a897f60b989dcfe17fbcde9c786b84`
- ONNX：`5c2cf0c7b045dfc340ca25765c288038f64fdb5c6f213ea4b82ab8d2cb6a88ef`

## 收包与离线检查

所有入口从解压后的包根执行，无需原训练服务器路径：

```bash
python -B checks/verify_package.py
python -B replay/verify_parity.py
python -B model/export_models.py --output /tmp/as2w_export_check
```

先检查SHA，再读 manifest.yaml 的C1–C8索引。离线脚本需要numpy、PyTorch、ONNX/ONNXRuntime及g++，版本见source/packaging_environment.json。大型Isaac二进制不随包，原生仿真复跑见simulation/README.md。历史JSON和源码中的绝对路径只保留为溯源，实际交付材料与入口均可按相对路径找到。

## 核心交接点

- 模型：57→512→256→128→16，ELU；无隐变量、无观测堆叠，只有外置的上一帧raw动作16维。真实机体线速度不是Actor输入。
- 观测：逐维表runtime/observations.csv。坐标base_link前x/左y/上z；四元数wxyz、body→world；重力为Rᵀ[0,0,-1]。4个轮位置槽置零，速度仍用16轴；裁剪在缩放之前。
- 动作：髋0.125rad，大腿/膝0.25rad，偏置[0,0.65,-1.3]；轮5rad/s。**物理目标在尺度+偏置后裁剪[-100,100]**；上一动作保存raw。腿40/1、轮0/1，只表示这次标称配置。顺序和符号见runtime/joints.csv；不是已验证DDS槽位表。
- 停车：零命令由Actor自行处理，原验证只覆盖2秒停车、最后1秒阈值；没有锁轮角、固定世界站位或长期驻停结论。
- 校验：补采10例×600帧。观测/包装/上一动作和独立C++映射最大差为0；原生GPU→CPU TorchScript最大差2.86e-06、→ONNX 3.34e-06，详见checks/parity.json。
- 仿真边界：视频为PhysX轨迹离线渲染；不是MuJoCo闭环。未对本包策略做真机发布/控制，不把历史只读PD记录当成这份权重的真机通过证据。

入口、退出、松杆、缺测/失联及硬件映射的未定义边界写在runtime/entry_exit.md和hardware_mapping.md，交接负责人/待补项见handoff.md。
