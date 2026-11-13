#!/usr/bin/env python3
"""Evaluate a frozen AS2W actor in a private headless display."""
import argparse
import os
from pathlib import Path
import subprocess

from display import private_display
from single_gpu import KIT_ARGS, isolate_environment

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--gpu", type=int, default=1)
parser.add_argument("--seconds", type=float, default=10)
parser.add_argument("--output", default=str(ROOT / "outputs/native_policy_evaluation"))
parser.add_argument("--policy", type=Path, required=True, help="AS2W TorchScript actor from this project")
parser.add_argument("--speed-sweep", action="store_true")
parser.add_argument("--repeats", type=int, default=4)
args = parser.parse_args()
if not args.policy.is_file():
    parser.error(f"Policy does not exist: {args.policy}")
if args.seconds <= 2:
    parser.error("More than two command seconds are required for steady-state statistics")
env = isolate_environment(os.environ, args.gpu)
command = [str(ROOT / ".venv/bin/python"), str(ROOT / "scripts/evaluate_isaac.py"), "--headless", "--device", "cuda:0", "--seconds", str(args.seconds), "--output", args.output, f"--kit_args={KIT_ARGS}"]
if args.speed_sweep:
    command.extend(["--speed-sweep", "--repeats", str(args.repeats)])
if args.policy:
    command.extend(["--policy", str(args.policy.resolve())])
with private_display(env) as private_env:
    code = subprocess.call(command, cwd=ROOT, env=private_env)
    if code == 0 and not (Path(args.output) / "summary.json").is_file():
        raise SystemExit("Evaluation exited without a summary; see its failure.json or log")
    raise SystemExit(code)
