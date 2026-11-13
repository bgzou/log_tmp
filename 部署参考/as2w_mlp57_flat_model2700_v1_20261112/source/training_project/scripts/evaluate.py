#!/usr/bin/env python3
"""Evaluate a frozen AS2W actor in a private headless display."""
import argparse
import os
from pathlib import Path
import subprocess

from display import private_display

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--gpu", type=int, default=1)
parser.add_argument("--seconds", type=float, default=10)
parser.add_argument("--output", default=str(ROOT / "outputs/native_policy_evaluation"))
parser.add_argument("--policy", type=Path, required=True, help="AS2W TorchScript actor from this project")
args = parser.parse_args()
if not args.policy.is_file():
    parser.error(f"Policy does not exist: {args.policy}")
if args.seconds <= 2:
    parser.error("More than two command seconds are required for steady-state statistics")
env = dict(os.environ)
env.pop("CUDA_VISIBLE_DEVICES", None)
env["OMP_NUM_THREADS"] = "4"
command = [str(ROOT / ".venv/bin/python"), str(ROOT / "scripts/evaluate_isaac.py"), "--headless", "--device", f"cuda:{args.gpu}", "--seconds", str(args.seconds), "--output", args.output, "--kit_args=--/renderer/multiGpu/enabled=false"]
if args.policy:
    command.extend(["--policy", str(args.policy.resolve())])
with private_display(env) as private_env:
    raise SystemExit(subprocess.call(command, cwd=ROOT, env=private_env))
