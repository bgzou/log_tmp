"""Build the self-contained R1199 teammate handoff, with hashes.

Reads local project files only. It does not connect to the robot or any server.
"""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DEST = HERE / "R1199_real_robot_feedback_20261112"
ARCHIVE = HERE / "R1199_real_robot_feedback_20261112.zip"

SOURCES: dict[str, str] = {
    "docs/robot_jitter_and_posture_analysis.md": "部署测试/02_现场操作/R1199二次实机抖动与停走姿态切换分析_20261112.md",
    "docs/policy_delivery_contract.md": "部署测试/02_现场操作/AS2-W训练到部署交付清单_v3_通用核心与按需模块.md",
    "docs/tomorrow_caolin_ablation_plan.md": "部署测试/02_现场操作/R1199明日caolin同条件停走抖动消融计划.md",
    "docs/current_opencode_fix_handoff.md": "部署测试/05_OpenCode交接/给OpenCode_R1199训练合同修复与明日实机接续_20261112.md",
    "docs/previous_mujoco_method.md": "部署测试/02_现场操作/R1199本项目MuJoCo复演方法与上游对齐问题.md",
    "docs/previous_simulation_differences.md": "部署测试/02_现场操作/R1199仿真差异同条件复演与改进方向.md",
    "docs/training_server_alignment.md": "部署测试/02_现场操作/R1199训练服务器与实机包装对齐审计_20261112.md",
    "evidence/trial1/low_capture_fast.log": "部署测试/04_调试记录/logs/field_sessions/20261111-233644_joystick/low_capture_fast.log",
    "evidence/trial1/low_protection.log": "部署测试/04_调试记录/logs/field_sessions/20261111-233644_joystick/low_protection.log",
    "evidence/trial1/publisher.log": "部署测试/04_调试记录/logs/field_sessions/20261111-233644_joystick/publisher.log",
    "evidence/trial1/session.log": "部署测试/04_调试记录/logs/field_sessions/20261111-233644_joystick/session.log",
    "evidence/trial1/windows_transcript.log": "部署测试/04_调试记录/logs/20261111-233643_windows_r1199_joystick_field_session.log",
    "evidence/trial2/low_capture_fast.log": "部署测试/04_调试记录/logs/field_sessions/20261112-000114_joystick/low_capture_fast.log",
    "evidence/trial2/low_protection.log": "部署测试/04_调试记录/logs/field_sessions/20261112-000114_joystick/low_protection.log",
    "evidence/trial2/publisher.log": "部署测试/04_调试记录/logs/field_sessions/20261112-000114_joystick/publisher.log",
    "evidence/trial2/session.log": "部署测试/04_调试记录/logs/field_sessions/20261112-000114_joystick/session.log",
    "evidence/trial2/windows_transcript.log": "部署测试/04_调试记录/logs/20261112-000113_windows_r1199_joystick_field_session.log",
    "evidence/derived/robot_state_10ms.csv": "部署测试/04_调试记录/logs/20261112_r1199_joystick_capture_10ms.csv",
    "evidence/derived/command_tracking_5hz.csv": "部署测试/04_调试记录/logs/20261112_r1199_joystick_walk_5hz.csv",
    "evidence/derived/posture_and_command.png": "部署测试/04_调试记录/logs/20261112_r1199_joystick_retest_trace.png",
    "evidence/derived/motion_jitter.png": "部署测试/04_调试记录/logs/20261112_r1199_motion_jitter_evidence.png",
    "evidence/derived/motion_jitter_metrics.txt": "部署测试/04_调试记录/logs/20261112_r1199_motion_jitter_evidence.txt",
    "evidence/derived/motion_jitter_recompute.py": "部署测试/04_调试记录/logs/20261112_r1199_motion_jitter_evidence.py",
    "evidence/derived/previous_jitter_metrics.txt": "部署测试/04_调试记录/logs/20261112_r1199_jitter_quant.txt",
    "evidence/derived/previous_jitter_recompute.py": "部署测试/04_调试记录/logs/20261112_r1199_jitter_quant.py",
    "evidence/derived/state_and_command_recompute.py": "部署测试/04_调试记录/logs/20261112_r1199_joystick_trace.py",
    "runtime/deployed_controller_candidate.cpp": "部署参考/cpp_deploy-as2w/deploy/robots/as2w/r1199/r1199_controller.cpp",
    "runtime/deployed_controller.hpp": "部署参考/cpp_deploy-as2w/deploy/robots/as2w/r1199/r1199_controller.hpp",
    "runtime/shared_r214_publisher.cpp": "部署参考/cpp_deploy-as2w/deploy/robots/as2w/r214/r214_publish.cpp",
    "runtime/r1199_replay.cpp": "部署参考/cpp_deploy-as2w/deploy/robots/as2w/r1199/r1199_replay.cpp",
    "runtime/CMakeLists.txt": "部署参考/cpp_deploy-as2w/deploy/robots/as2w/r1199/CMakeLists.txt",
    "runtime/deploy.yaml": "部署参考/cpp_deploy-as2w/models/r1199/deploy.yaml",
    "runtime/policy.onnx": "部署参考/cpp_deploy-as2w/models/r1199/policy.onnx",
    "runtime/r1199_training_forward_parity.py": "部署参考/cpp_deploy-as2w/tools/r1199_training_forward_parity.py",
    "runtime/r152_measured.map": "部署参考/cpp_deploy-as2w/config/r152_measured.map",
    "upstream/release/as2w-rolling-1199-preview.zip": "部署参考/Rob2Nav-rolling-1199-preview/as2w-rolling-1199-preview.zip",
    "upstream/release/speed-evaluation.json": "部署参考/Rob2Nav-rolling-1199-preview/deliveries/as2w-deploy/rolling-1199-simulation-preview/speed-evaluation.json",
    "upstream/release/mujoco-rolling-diagnostic-summary.json": "部署参考/Rob2Nav-rolling-1199-preview/deliveries/as2w-deploy/rolling-1199-simulation-preview/mujoco-rolling-diagnostic-summary.json",
    "upstream/release/as2w_rolling_fixed_exit.py": "部署参考/Rob2Nav-rolling-1199-preview/deliveries/as2w-deploy/rolling-1199-simulation-preview/as2w_rolling_fixed_exit.py",
    "upstream/release/README.md": "部署参考/Rob2Nav-rolling-1199-preview/deliveries/as2w-deploy/rolling-1199-simulation-preview/README.md",
    "upstream/formal/isaac_contract.json": "部署参考/Rob2Nav-rolling-fixed-exit-source/deliveries/as2w-deploy/rolling-fixed-exit-preview/isaac/contract.json",
    "upstream/formal/mujoco_contract.json": "部署参考/Rob2Nav-rolling-fixed-exit-source/deliveries/as2w-deploy/rolling-fixed-exit-preview/mujoco/mujoco-contract.json",
    "upstream/formal/as2w_rolling_fixed_exit.py": "部署参考/Rob2Nav-rolling-fixed-exit-source/deliveries/as2w-deploy/rolling-fixed-exit-preview/offline_deployment/as2w_rolling_fixed_exit.py",
    "upstream/actual_R1199_training_contract.json": "部署测试/04_调试记录/logs/20261112_r1199_actual_training_contract_readonly.json",
    "upstream/actual_R1199_training_job.log": "部署测试/04_调试记录/logs/20261112_r1199_actual_training_job_readonly.log",
    "upstream/training_helper_readonly.py": "部署参考/Rob2Nav-R1199-trainserver-readonly-snapshot/as2w_rolling_fixed_exit.py",
    "upstream/current_train_entry_readonly.py": "部署参考/Rob2Nav-R1199-trainserver-readonly-snapshot/train_as2w_isaac_robust.py",
    "upstream/current_train_speed_env_readonly.py": "部署参考/Rob2Nav-R1199-trainserver-readonly-snapshot/as2w_isaac_speed_range.py",
    "upstream/current_train_teleop_readonly.py": "部署参考/Rob2Nav-R1199-trainserver-readonly-snapshot/as2w_isaac_teleop.py",
    "upstream/current_train_robust_env_readonly.py": "部署参考/Rob2Nav-R1199-trainserver-readonly-snapshot/as2w_isaac_robust_env.py",
    "upstream/previous_measured_start_simulation.json": "部署参考/as2w-flat-rerun/results/rolling_1199_measured_start_20261111.json",
}

README = """# R1199 实机抖动反馈与策略交付合同（可独立阅读）

2026-11-12。请先读 `docs/robot_jitter_and_posture_analysis.md`、
`docs/training_server_alignment.md`、`docs/current_opencode_fix_handoff.md`
和 `docs/policy_delivery_contract.md`。
本包含两次真实机器人前后滚动的原始日志、
提取后的 10 ms/5 Hz 表、图、复算脚本、当前部署控制器源码、R1199 权重和上游合同。
**无需访问工作站、CPRO 或 caolin 服务器。** `MANIFEST.sha256` 列出包内全部文件校验值。

## 要解决的两个不同现象

1. **前后滚动过程中真实可闻的关节抖动**：现场人员两次都听到，不只是起步/停车。
   第二轮持续前进窗口（10 ms 状态采样时钟 53–67 s）12 腿轴 `dq` RMS
   0.1113 rad/s，对照安静零速 0.0066；去 0.2 s 慢变化的 `tau_est` RMS
   0.6799 Nm，对照 0.0181。前进中 59.35–59.95 s 的 FR 髋 `dq` 正负交替，
   同段 FR 髋估算力矩峰谷差 3.225 Nm。见 `evidence/derived/motion_jitter.png`。
   这些是运动中实机反馈波动的证据；100 Hz 采样无法确定声音频率或唯一声源。
2. **停走切换时身高/腿姿态变化**：见 `evidence/derived/posture_and_command.png`。
   第一次推杆两轮分别触发 0.272911/0.254249 rad 腿目标单帧软件预警；
   停车后髋目标误差再次增大。当前 C++ 的站立补偿在非零速度时可一帧撤掉，
   是姿态突变的直接候选原因，不能据此解释所有持续滚动抖动。

两轮主板/电机保护位均为 0，软件守卫各一次 warn，均未触发自动制动。
没有硬件报警并不表示抖动不存在。

## 重要配置差异

`upstream/formal/{isaac_contract,mujoco_contract}.json` **及真正的 R1199 训练运行**
`upstream/actual_R1199_training_contract.json` 均记录
`park_continuous_bias=true, park_straight_bias=true`、
`park_odometry=false, park_settle_joints=false`；现有实机 C++ 默认分支
相当于补偿 false/false，并启用后两项，与训练不一致。
训练权重 SHA 与发布 `model_1199.pt` 相同；此前拿较早 `model_550.pt`
合同判断“训练开关未知”已纠正。训练服务器当前 `code/` 源码在该训练完成后
被修改，运行目录 `git/` 为空，仍需补**训练当时的不可变源码快照**。当前 C++ 源码
`runtime/deployed_controller_candidate.cpp` 已含一个**默认关闭、未编译验证**的
`AS2W_R1199_TRAINING_CONTRACT` 候选，修正补偿和停车四项；它不是已上狗版本。实际发布端是共享的
`runtime/shared_r214_publisher.cpp`，R1199 的 CMake 为它加策略编译开关。
原来的 950 帧 parity 仅覆盖 false/false。

## 请训练同事先做的事

1. 补交本次 `model_1199.pt` 的实际启动命令、**训练时不可变源码快照**、
   权重/代码/资产哈希和命令分布统计。四个关键开关的训练实值已由正确合同核实，
   见 `docs/training_server_alignment.md`，不要再用较早权重的合同代替。
2. 用户已确认旧故障两次实机足够，**不再复演旧版故障**。请协助用正确训练合同
   核对新候选的动作包装，并只对修复版跑同初态的零速、持续 +0.05 m/s、
   `0→+0.05→0→−0.05→0`；保留原始 ONNX 动作、包装后16轴目标、
   PD目标力矩、实际 q/dq、轮载/非轮接触。勿同时改权重和执行器参数。
3. 对**运动中**抖动溯源：若原始动作振荡，处理训练奖励和停走/低速命令分布；
   若包装后才振荡，处理包装器；若目标平顺但真实关节/力矩振荡，
   比对执行器、PD、延迟、速度噪声及轮地接触。给出与本包相同窗口的曲线和
   峰值/频谱，不只给视频或通过率。
4. 按 `docs/policy_delivery_contract.md` 提交下一个策略版本。训练服务器绝对
   路径只可作为溯源信息，不能替代可复制的模型、源码、配置和逐例证据。

## 复算

包内可直接运行 `python evidence/derived/motion_jitter_recompute.py`
（需 numpy+matplotlib；读取同目录 `robot_state_10ms.csv`）。
若需要从原始日志重提取，使用 `state_and_command_recompute.py`，其 `session`
路径需设为本包 `evidence/trial2/`。原始日志保持未改。

`evidence/derived/posture_and_command.png` 上两组时间轴起点不同，不能用上下图
相同横坐标做毫秒级因果对齐。没有实测机身高度、接触力和高频电流/录音。
任何后续实机动作仍须重新完成离线验收并由现场人员对当次动作明确同意。
`ORIGIN_MAP.tsv` 对应项目原路径与包内相对路径；包内文件已经全部复制，
无需依赖这些原路径。
"""

MESSAGE = """请先看本包 README.md、docs/robot_jitter_and_posture_analysis.md、
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
"""


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    if DEST.resolve().parent != HERE.resolve() or not HERE.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError("refusing to clean package folder outside this project")
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True, exist_ok=True)
    for name, rel in SOURCES.items():
        source = ROOT / rel
        if not source.is_file():
            raise FileNotFoundError(source)
        target = DEST / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    (DEST / "README.md").write_text(README, encoding="utf-8")
    (DEST / "SEND_TO_TEAMMATE.md").write_text(MESSAGE, encoding="utf-8")
    (DEST / "ORIGIN_MAP.tsv").write_text(
        "package_path\tproject_original_path\n" +
        "".join(f"{name}\t{rel}\n" for name, rel in sorted(SOURCES.items())),
        encoding="utf-8",
    )
    files = sorted(p for p in DEST.rglob("*") if p.is_file() and p.name != "MANIFEST.sha256")
    manifest = "".join(f"{sha(p)}  {p.relative_to(DEST).as_posix()}\n" for p in files)
    (DEST / "MANIFEST.sha256").write_text(manifest, encoding="utf-8")
    with ZipFile(ARCHIVE, "w", ZIP_DEFLATED, compresslevel=6) as output:
        for path in sorted(p for p in DEST.rglob("*") if p.is_file()):
            output.write(path, path.relative_to(DEST).as_posix())
    print("files", len(files) + 1, "unpacked", DEST)
    print("archive", ARCHIVE, "bytes", ARCHIVE.stat().st_size, "sha256", sha(ARCHIVE))


if __name__ == "__main__":
    main()
