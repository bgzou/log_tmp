# 2026-11-09 12:15 OpenCode 会话：R41 新策略验证与接入（无狗动作）

- 触发：用户指示拉取同事最新 `omni-blind-stairs`（R41），MuJoCo 验证平地后替换旧 stairs 权重。
- 环境增量：服务器 pip 安装 torch 2.15.0+cpu、gymnasium、stable_baselines3 2.9.2、scipy、
  pyyaml、onnx、onnxruntime 1.31.1（Python 侧）；ORT C++ tarball 1.22.0/1.24.2 x64（下载比对用）；
  apt libyaml-cpp-dev（服务器已有）。mujoco 3.17.0 沿用。

## 命令与实际输出（摘要）

1. 拉取：GitHub trees API 列 66 项（比上午多 17 项：r41_controller/replay/shadow/deploy.yaml/
   policy.onnx/r41-trace.csv/三份 onnx 评估 JSON 等）。raw 批量下载两次失败（302 Temporary
   Redirect + `curl -sf` 不跟随，得到 ~100 字节 HTML）；`-sfL` 重试 49/49 成功，`sha256sum -c` 通过。
2. 平地复验（`runtime/evaluate_omni_joint.py assets weights/policy.pt r41_verify --audit-inputs`，
   assets/official-model 取工作站 unitree_ros 的 as2w_description，与固定版 4005a1b 一致）：
   ```
   fixed {'flat': [41, 52, 0], 'stairs': {0.08: 1}, 'stair_total': 16}
   confirmation {'flat': [20, 52, 0], 'stairs': {0.06: 8}, 'stair_total': 64}
   Proprioception-only equivalent actions 67200
   ```
   逐指令（固定集）：stop/forward/forward_slow/reverse/turn_l/turn_r/arc_l/arc_r 全 4/4；
   forward_fast 2/4、diagonal 2/4×2、left 1/4、right 2/4；52 案零跌倒。
   与交付 README 对照：平地完全一致；楼梯独立集 6 cm 8/21 vs 同事 10/21（数值敏感）。
3. C++ 侧（README 配方，上游 wty-yy/unitree_cpp_deploy@4f71bf3 沙盒）：
   - ORT 1.24.2：加载失败 `TopK Op [ShapeInferenceError] K input must be one-dimensional size 1`。
   - ORT 1.22.0：构建+回放成功，`rows=750 max_abs_error=0 leg_and_wheel_targets=verified
     stale_state=latched_off`（与交付 cpp-replay.txt 逐字一致）。
4. 接入 cpp_deploy-as2w（服务器 x86 复验）：
   - 新增文件：`deploy/include/isaaclab/algorithms/algorithms.h`（OrtRunner，160 行，源出上游
     4f71bf3）；`deploy/robots/as2w/r41/{r41_controller.cpp,hpp,replay.cpp,shadow.cpp,CMakeLists.txt}`
     （交付原样，仅 CMake 相对路径 `../../`→`../../../` 适配 r41/ 子目录）；`models/r41/
     {policy.onnx,deploy.yaml,r41-trace.csv}`（yaml policy_file 改同目录）。
   - 根 CMakeLists 追加 `option(AS2W_R41 ...)` + add_subdirectory。
   - `cmake -DAS2W_R41=ON -DONNXRUNTIME_ROOT=<ort122>` 构建 OK；
     回放 `rows=750 max_abs_error=0 ...` ✓；根项目 CTest 7/7 ✓ 无回归。
   - manifest.json 增 `onnx_policies.r41`（接口、验证、来源、ORT 版本约束）。

## 判断与限制

- R41 平地行走正常（forward/倒退/转向/停车全过、零跌倒）→ 满足用户设定的替换条件；
  旧三份 stairs .bin 保留为离线对照，stairs 线以 R41 为准。recovery 不变。
- R41 真机部署仍未开始：需 ORT 1.22.0 aarch64、CPRO ARM 构建、shadow.cpp 接线与映射表
  （侧别/三元组/配对已定，前后 A/B 与零位未定——shadow 数值仅作链路观察）。
- 平地"正常"指 MuJoCo + 固定/独立两套验收的仿真口径，不代表真机。

## 原始产物

- `部署参考/omni-blind-stairs/`（完整交付副本 + verification_server_20261109/）
- `部署参考/cpp_deploy-as2w/models/r41/`（模型+参数+轨迹+README）
- INDEX.md 12:15 节
