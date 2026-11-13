#!/usr/bin/env python3
"""Launch the pinned robot_lab learning recipe with the AS2W model."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys

from display import private_display

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--terrain", choices=["flat", "rough"], default="flat")
    parser.add_argument("--num-envs", type=int, default=4096)
    parser.add_argument("--iterations", type=int, default=5000, help="Target total updates, including completed updates when resuming")
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--run-name", default="as2w_robot_lab")
    parser.add_argument("--smoke", action="store_true", help="16 environments and two PPO updates")
    parser.add_argument("--contact-patches", type=int)
    parser.add_argument("--resume-checkpoint", type=Path)
    args, extra = parser.parse_known_args()
    if "--distributed" in extra:
        parser.error("This launcher runs simulation and PPO on one physical GPU")
    if any(value.startswith("agent.device=") for value in extra):
        parser.error("Use --gpu to select both simulation and PPO devices")
    if args.smoke and args.resume_checkpoint:
        parser.error("Smoke mode cannot resume a full-size training run")
    if args.iterations <= 0 or args.num_envs <= 0:
        parser.error("Environment count and target updates must be positive")
    checkpoint = args.resume_checkpoint.resolve() if args.resume_checkpoint else None
    if checkpoint and not checkpoint.is_file():
        parser.error(f"Checkpoint does not exist: {checkpoint}")
    task = f"RobotLab-Isaac-Velocity-{args.terrain.title()}-Unitree-AS2W-v0"
    command = [
        str(ROOT / ".venv/bin/python"),
        str(ROOT / "scripts/upstream_train.py"),
        "--task", task, "--num_envs", str(16 if args.smoke else args.num_envs),
        "--max_iterations", str(2 if args.smoke else args.iterations),
        "--device", "cuda:0", "--seed", str(args.seed), "--headless",
        "--logger", "tensorboard", "--run_name", args.run_name,
        "--kit_args=--/renderer/multiGpu/enabled=false --/validate/iommu/enabled=false --/validate/p2p/enabled=false --/validate/p2p/memoryCheck/enabled=false --/exts/omni.gpu_foundation/startup/skipErrorDialogs=true",
        "agent.device=cuda:0",
        *extra,
    ]
    if args.contact_patches is not None:
        if args.contact_patches <= 0:
            parser.error("Contact patch capacity must be positive")
        command.append(f"env.sim.physx.gpu_max_rigid_patch_count={args.contact_patches}")
    if checkpoint:
        log_root = ROOT / "logs/rsl_rl" / f"unitree_as2w_{args.terrain}"
        if checkpoint.parent.parent != log_root:
            parser.error(f"Resume checkpoint must be directly under a run folder in {log_root}")
        command.extend(["--resume", "--load_run", f"^{re.escape(checkpoint.parent.name)}$", "--checkpoint", f"^{re.escape(checkpoint.name)}$"])
    env = dict(os.environ)
    # Isolate CUDA by UUID. Vulkan uses physical ordinals; the project
    # AppLauncher adapter selects its GPU separately to match this same card.
    gpu_uuid = subprocess.check_output(["nvidia-smi", f"--id={args.gpu}", "--query-gpu=uuid", "--format=csv,noheader"], text=True).strip()
    env["CUDA_VISIBLE_DEVICES"] = gpu_uuid
    env["OMP_NUM_THREADS"] = "4"
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    env["AS2W_TARGET_TOTAL_UPDATES"] = str(2 if args.smoke else args.iterations)
    env["AS2W_EXPECTED_DEVICE"] = "cuda:0"
    env["AS2W_PHYSICAL_GPU"] = str(args.gpu)
    env["AS2W_PHYSICAL_GPU_UUID"] = gpu_uuid
    source = str(ROOT / "vendor/robot_lab/source/robot_lab")
    env["PYTHONPATH"] = str(ROOT / "source") + os.pathsep + source + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    print(f"Physical GPU {args.gpu}; task {task}; command: {command}", flush=True)
    with private_display(env) as headless_env:
        result = subprocess.call(command, cwd=ROOT, env=headless_env)
    raise SystemExit(result)


if __name__ == "__main__":
    main()
