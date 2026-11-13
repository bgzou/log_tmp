# 最小运行时

`reference.py` 是无噪声、确定性推理的观测/动作/上一动作参考；`reference.hpp` 是独立C++观测和目标转换。两者只处理策略顺序数据，没有网络、DDS或电机命令发布。每一维输入见 observations.csv，逐关节单位/符号见 joints.csv。

先读 effective_runtime.yaml、velocity_command.yaml 和 mode_differences.csv。重要顺序是：观测物理量→训练噪声（部署/评估关闭）→每项裁剪[-100,100]→缩放；输出 raw→尺度+偏置→物理目标裁剪[-100,100]。上一动作保存 raw，不保存裁剪后的目标。不能自行加 tanh 或把4个轮位置槽填成轮角。

输入的机体系线速度不是必需项；真实线速度只在训练Critic中使用。投影重力来自姿态四元数，不直接以有线加速度污染的加速度计读数替代。四元数为body→world、wxyz；站立时投影重力约[0,0,-1]。全部传感器输入需转换到同一base_link坐标系/时刻。训练未定义硬件最大数据龄和缺测容错，本参考对缺失/非有限值拒绝计算，由外层负责控制退出。

模型输入 float32[B,57]，ONNX 名为 observation；输出 float32[B,16]，名为 raw_action_mean。TorchScript用位置参数 input。CPU运行版本和误差见 model/export_equivalence.json；ARM64及C++模型推理均 not_run，只有C++观测/目标映射已验证。
