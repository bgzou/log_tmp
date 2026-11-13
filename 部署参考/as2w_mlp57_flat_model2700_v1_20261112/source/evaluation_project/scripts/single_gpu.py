"""Evaluation helpers using the verified CUDA UUID / Vulkan ordinal mapping."""
import json
import os
from pathlib import Path
import subprocess


KIT_ARGS = "--/renderer/multiGpu/enabled=false --/validate/iommu/enabled=false --/validate/p2p/enabled=false --/validate/p2p/memoryCheck/enabled=false --/exts/omni.gpu_foundation/startup/skipErrorDialogs=true"


def isolate_environment(env, physical_gpu):
    env = dict(env)
    uuid = subprocess.check_output(["nvidia-smi", f"--id={physical_gpu}", "--query-gpu=uuid", "--format=csv,noheader"], text=True).strip()
    env.update(CUDA_VISIBLE_DEVICES=uuid, AS2W_PHYSICAL_GPU=str(physical_gpu), AS2W_PHYSICAL_GPU_UUID=uuid, OMP_NUM_THREADS="4", PYTHONNOUSERSITE="1", PYTHONUNBUFFERED="1")
    return env


def isolated_app_launcher():
    import torch
    from isaaclab.app import AppLauncher
    torch.cuda.set_device(0)

    class IsolatedAppLauncher(AppLauncher):
        def _resolve_device_settings(self, launcher_args):
            super()._resolve_device_settings(launcher_args)
            if torch.cuda.device_count() != 1:
                raise RuntimeError("Evaluation must see exactly one UUID-isolated CUDA device")
            launcher_args["active_gpu"] = int(os.environ["AS2W_PHYSICAL_GPU"])
            launcher_args["physics_gpu"] = 0
    return IsolatedAppLauncher


def verify_evaluation_device(raw, policy, output, phase):
    import torch
    import carb
    expected = torch.device("cuda:0")
    assert torch.device(raw.device) == expected
    assert all(p.device == expected for p in policy.parameters())
    assert raw.scene["robot"].data.joint_pos.device == expected
    settings = carb.settings.get_settings()
    assert settings.get("/renderer/activeGpu") == int(os.environ["AS2W_PHYSICAL_GPU"])
    allocations = []
    rows = subprocess.check_output(["nvidia-smi", "--query-compute-apps=gpu_uuid,pid,used_memory", "--format=csv,noheader,nounits"], text=True)
    for row in rows.splitlines():
        uuid, pid, memory = [v.strip() for v in row.split(",")]
        if pid == str(os.getpid()):
            allocations.append({"gpu_uuid": uuid, "pid": int(pid), "memory_mib": int(memory)})
    assert allocations and all(v["gpu_uuid"] == os.environ["AS2W_PHYSICAL_GPU_UUID"] for v in allocations), allocations
    record = {"physical_gpu": int(os.environ["AS2W_PHYSICAL_GPU"]), "logical_cuda_device": str(expected), "actor_and_physics_same_device": True, "process_allocations": allocations}
    Path(output).mkdir(parents=True, exist_ok=True)
    (Path(output) / f"device_{phase}.json").write_text(json.dumps(record, indent=2) + "\n")
    return record
