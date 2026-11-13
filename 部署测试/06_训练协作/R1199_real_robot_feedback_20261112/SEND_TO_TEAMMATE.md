请先看本包 README.md、docs/robot_jitter_and_posture_analysis.md、
evidence/derived/motion_jitter.png 和 docs/policy_delivery_contract.md。
我们在 R1199 两次真机前后滚动中均听到真实关节抖动；第二次持续前进段的
10 ms 关节速度/估算力矩曲线可见成串正负波动，而零速时明显安静。
停走抬升/下降是另一个问题，现有部署动作包装的站立补偿分支与正式评估
合同不同。正确的 R1199 训练合同已核实补偿 `true/true`、停车里程计/关节
检查 `false/false`；实机 C++ 相反。请用包内原始日志和源码复核，补齐
训练当时的不可变源码、命令分布、逐帧原始/包装动作和修复版同初态验收。
用户已实机测试两次，不要求再复现旧版故障。尤其请区分：
ONNX 输出本身、动作包装、PD/执行器/接触哪一层产生运动中的抖动。
请不要只用“没有保护报警”或“仿真通过”否定现场抖动。
本包 SHA256 校验见 MANIFEST.sha256；无需访问我的 Windows/CPRO。
