"""Verify actual tensors, rather than just launch arguments, share one GPU."""
import json
import os
from pathlib import Path
import subprocess

import torch


def audit_training_devices(runner, phase):
    expected = torch.device(runner.env.device)
    groups = {}

    def record(name, tensors):
        devices = sorted({str(t.device) for t in tensors})
        if devices != [str(expected)]:
            raise RuntimeError(f"AS2W {name} devices {devices}; expected only {expected}")
        groups[name] = devices

    record("actor_critic_parameters", list(runner.alg.policy.parameters()))
    buffers = list(runner.alg.policy.buffers())
    if buffers:
        record("actor_critic_buffers", buffers)
    record("rollout_tensors", [v for v in vars(runner.alg.storage).values() if isinstance(v, torch.Tensor)])
    record("rollout_observations", list(runner.alg.storage.observations.values()))
    raw = runner.env.unwrapped
    robot = raw.scene["robot"]
    record("physics_observations", [robot.data.joint_pos, robot.data.joint_vel, robot.data.root_pos_w])
    optimizer = [v for state in runner.alg.optimizer.state.values() for key, v in state.items() if isinstance(v, torch.Tensor) and key != "step"]
    if optimizer:
        record("optimizer_moments", optimizer)
    if torch.cuda.current_device() != expected.index:
        raise RuntimeError(f"Current CUDA device is {torch.cuda.current_device()}, expected {expected}")
    import carb
    settings = carb.settings.get_settings()
    engine = {key: settings.get(key) for key in ("/renderer/activeGpu", "/physics/cudaDevice", "/renderer/multiGpu/enabled", "/validate/iommu/enabled", "/validate/p2p/enabled", "/validate/p2p/memoryCheck/enabled")}
    physical_gpu = int(os.environ.get("AS2W_PHYSICAL_GPU", expected.index))
    if engine["/renderer/activeGpu"] != physical_gpu or engine["/physics/cudaDevice"] != expected.index:
        raise RuntimeError(f"Isaac engine GPU configuration differs: {engine}")
    rows = subprocess.check_output(["nvidia-smi", "--query-gpu=index,uuid", "--format=csv,noheader,nounits"], text=True)
    gpu_uuids = {int(row.split(",")[0]): row.split(",")[1].strip() for row in rows.splitlines()}
    own_allocations = []
    rows = subprocess.check_output(["nvidia-smi", "--query-compute-apps=gpu_uuid,pid,used_memory", "--format=csv,noheader,nounits"], text=True)
    for row in rows.splitlines():
        uuid, pid, memory = [x.strip() for x in row.split(",")]
        if pid == str(os.getpid()):
            own_allocations.append({"gpu_uuid": uuid, "pid": int(pid), "used_memory_mib": int(memory)})
    if not own_allocations or any(x["gpu_uuid"] != gpu_uuids[physical_gpu] for x in own_allocations):
        raise RuntimeError(f"Training process allocated CUDA memory on another physical GPU: {own_allocations}")
    result = {"phase": phase, "physics_device": str(runner.env.device), "ppo_device": str(runner.device), "current_cuda_device": torch.cuda.current_device(), "tensor_devices": groups, "cuda_device_name": torch.cuda.get_device_name(expected), "physical_gpu_index": physical_gpu, "physical_gpu_uuid": gpu_uuids[physical_gpu], "process_gpu_allocations": own_allocations, "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"), "engine_settings": engine, "cpu_optimizer_step_scalars_allowed": True}
    path = Path(runner.logger.log_dir) / f"device_verification_{phase}.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(f"[AS2W] Single GPU verified ({phase}): physics, Actor/Critic, rollout and optimizer on {expected}.", flush=True)
    return result
