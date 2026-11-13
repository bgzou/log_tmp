# R214 离线与只读部署候选

来源：`YuTaoV5/Rob2Nav` 分支 `codex/as2w-deploy`，提交 `b5b4add5b2ce9fe18690c0dee047dbc8eb2f7ea5`，交付目录 `deliveries/as2w-deploy/omni-blind-stairs-r214`。工作站保留 sparse clone `部署参考/Rob2Nav-r214-source`；交付文档/原始证据以该目录为准。

- `policy.onnx` SHA-256 `b13ed59864fbcde46a6a4d986c2a3552edf2cc9523cfd136a0cf60091aa8f746`
- `r214-trace.csv` SHA-256 `9499d25f2f9c0cd713e0402a2128bb1db7ebb46431b842e18969d14452e1ab01`
- `deploy.yaml` 与交付同内容，唯 `policy_file` 改成同目录 `policy.onnx`。
- ONNX：`obs[1,41]`、`state[1,1196]`、`actions[1,16]`、`next_state[1,1196]`。与 R152 的 844 维状态**不能互换**；本树使用独立 `deploy/robots/as2w/r214` C++ 适配器。
- 关节名、默认姿态、限位、动作缩放与 R152 同；`config/r152_measured.map` 的物理轴映射可供 R214 **只读 shadow**，不等于 LowCmd 命令方向已验证。

交付自述的固定集 `stop`、`forward_slow` 各 4/4 严格通过；楼梯通过 1/80。以上为交付方的 MuJoCo 结果，仍需本地 C++ 回放、CPRO ARM64 和独立仿真复核。R214 当前**没有 LowCmd 发布端目标**；既有 R152 发布 FSM 的固定 PD Stand/ReturnStand 与 FixSquat 安全问题必须先解决，不能改个模型名就上机。
