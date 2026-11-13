# AS2-W 平台层

- `config/config.yaml`：六份交付模型的名字、类别和文件路径；目前不是 GO2 式 FSM 配置。实际由 `tools/policy_select.py` 读取。
- `src/diagnostics.cpp`：SDK2 只读状态/遥控器订阅、官方 Sport 高层动作、只读 `shadow`。构建目标为 `as2w_sdk2`。
- `src/sport_gamepad.cpp`：可选 CPRO USB Xbox 高层 Sport 控制；不向策略注入速度。构建目标为 `as2w_sport_gamepad`。
- 通用策略推理与 16 轴观测/动作逻辑保留在项目根 `src/policy.*`；真机 DDS 槽位不应写入该核心。

未来的低层状态源、命令发送端和 FSM 应在本目录实现，接口与验收顺序见 `../../../docs/architecture.md`。现有代码没有 LowCmd 发布端，也没有实时真机策略切换器。
