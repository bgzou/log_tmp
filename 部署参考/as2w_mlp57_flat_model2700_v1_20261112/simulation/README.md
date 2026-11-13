# 仿真与复跑

## 已有证据

- evidence156：原正式PhysX验证，同一 model_2700，39命令×4初态=156例，每例2秒零速+8秒运动+2秒停车。156/156生存、姿态/接触与停车通过，严格三轴速度56/156。逐例命令、初始状态、阈值、首个失败和完整时序均保留，失败样例未过滤。低速横移/低速转向、原地转向的额外平移和高速欠速见summary.json/报告。
- native_replay：交付时补采600帧×10例=6000帧，用同一权重做完整真实状态→观测→raw→目标与状态更新对齐。不是第二仿真器，不替代156例正式验收。
- 视频只是原PhysX轨迹用MuJoCo正向运动学/渲染绘制，没有MuJoCo闭环动力学。第二仿真器闭环 not_run，ARM64 not_run，真机控制 not_run。

## 复跑

需要已安装声明的Isaac Sim 5.1/Isaac Lab 2.3.2运行环境（PyTorch2.7+cu128、RSL-RL3.3.0实际源码快照）；大型专有二进制未随包分发。先核对 source/training_environment.json、packaging_environment.json 及747个Python源码SHA。干净新机安装未测试；包内保留bootstrap/setup等历史源码，但不要把其历史绝对路径当作安装前提。

在正确运行环境的 Python 中，以包根为当前目录：

```bash
python -B simulation/prepare_workspace.py --mode evaluation --output /tmp/as2w_handoff_eval --python /path/to/env/bin/python
python -B simulation/reproduce_156.py --workspace /tmp/as2w_handoff_eval --output /tmp/as2w_formal_replay --gpu 1
python -B simulation/run_native.py --workspace /tmp/as2w_handoff_eval --output /tmp/as2w_io_replay --gpu 1
```

workspace须为空目录；输入模式为evaluation时使用原正式评估快照，训练模式可用`--mode training`恢复训练时源码，按历史命令中的参数启动 scripts/train.py。prepare_workspace只复制包内文件并生成日志所需Git元数据；新本地Git提交不冒充历史64bc0e6，源码逐文件哈希可对照训练快照和as2w_contract.json。

资源由 --gpu 物理编号选择，UUID隔离CUDA，Vulkan映射同一物理GPU。接管只读验证不要中断其它任务。若实际运行时版本不同，先离线模型对齐再比较物理结果。package中的747份Python源码用于精确版本核对，不是包含Isaac Sim二进制/扩展/体验配置的完整安装。

正式评估保留标称26kg、腿PD40/1、轮PD0/1，关闭噪声、随机化/推力与自动复位；训练的完整材质、COM/质量/增益、外力/推扰、重置、接触与solver参数见 source/resolved_config/env.yaml。控制50Hz，物理200Hz，无显式传感/动作延迟；碰撞为官方STL凸包近似、自碰撞关闭。轮胎柔性和实测完整转矩-转速曲线未标定。

本包的50N非轮接触阈值等是这次项目验收口径，不是AS2-W官方通用门槛。停车补充量见stop_diagnostics，明确为原数据事后计算，不是新增驻停/制动试验。156例只有轮支持数量和非轮峰值；逐轮/各link的四子步接触数据仅在补采10例中保存，不将其外推为156例逐轮载荷结论。
