# 逐帧离线对齐

```bash
python -B replay/verify_parity.py
```

需要Python的numpy/torch/onnxruntime及g++。脚本只读交付物，临时编译C++，打印比较结果；只有显式给`--report /new/path.json`时写新报告。包内 checks/parity.json 是交付时结果。

native_samples.npz 保存600个控制时刻×10例；数组为时间优先、案例顺序见 simulation/native_replay/summary.json。包含同步gyro/gravity/command/q/dq/previous_raw_action、真实57维observation和raw_action、真实ActionManager物理目标、next_previous、next_observation、前后根姿态/关节状态/速度、最后物理子步的关节施加力矩和全部body四物理子步接触力。完整字段、形状和时间语义见dataset_schema.json。控制t之前采输入；step后记录t+0.02状态。next_observation是原生环境内部生成的值；外部命令在下个控制时刻、重新构建下一次模型输入前覆盖，故命令边界不应直接复用内部随机采样命令。

测试包括：物理传感值独立重建观测；wxyz重力转换；CPU TorchScript和ONNX对原生GPU Actor；Python/C++独立观测、物理目标与下一上一动作；另有12个裁剪顺序/轮角无关性边界探针，它们只验证接口不声明运动能力。4个轮位置槽训练前置零，但训练噪声仍会扰动；此数据关闭噪声，槽值为0。

误差阈值按此float32实现于校验前设置：观测2e-6；raw action绝对/相对2e-5；物理目标绝对2e-4、相对2e-5（含轮速×5）；C++映射2e-6。结果记录最大误差、时间优先展平的最差帧/字段及首次超阈值。ARM64、C++ ONNX推理、闭环第二仿真器都尚未验证。
