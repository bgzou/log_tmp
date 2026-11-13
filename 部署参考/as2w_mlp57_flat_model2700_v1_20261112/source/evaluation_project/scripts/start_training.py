#!/usr/bin/env python3
"""Start one persistent, bounded AS2W robot_lab training run."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--gpu", type=int, default=1)
parser.add_argument("--terrain", choices=["flat", "rough"], default="flat")
parser.add_argument("--num-envs", type=int, default=4096)
parser.add_argument("--iterations", type=int, default=5000)
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--contact-patches", type=int)
parser.add_argument("--resume-checkpoint", type=lambda value: str(Path(value).resolve()))
args = parser.parse_args()
state_path = ROOT / "logs/active_training.json"
if state_path.exists():
    old = json.loads(state_path.read_text())
    proc = Path(f"/proc/{old['pid']}/stat")
    alive = proc.exists() and proc.read_text().split(") ", 1)[1].split()[0] != "Z"
    cmdline = Path(f"/proc/{old['pid']}/cmdline")
    same_job = cmdline.exists() and str(ROOT / "scripts/train.py").encode() in cmdline.read_bytes()
    if alive and same_job:
        raise SystemExit(f"An AS2W training run is already active: PID {old['pid']}")
    history = ROOT / "logs/history"
    history.mkdir(exist_ok=True)
    (history / f"run_{old['pid']}.json").write_text(json.dumps(old, indent=2) + "\n")
stamp = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d_%H%M%S")
name = f"as2w_{args.terrain}_{args.num_envs}_{args.iterations}_{stamp}"
log_path = ROOT / "logs" / f"{name}.log"
log_path.parent.mkdir(parents=True, exist_ok=True)
command = [str(ROOT / ".venv/bin/python"), "-u", str(ROOT / "scripts/train.py"), "--gpu", str(args.gpu), "--terrain", args.terrain, "--num-envs", str(args.num_envs), "--iterations", str(args.iterations), "--seed", str(args.seed), "--run-name", name]
if args.contact_patches is not None:
    command.extend(["--contact-patches", str(args.contact_patches)])
if args.resume_checkpoint:
    if not Path(args.resume_checkpoint).is_file():
        parser.error(f"Checkpoint does not exist: {args.resume_checkpoint}")
    command.extend(["--resume-checkpoint", args.resume_checkpoint])
env = {**os.environ, "PYTHONUNBUFFERED": "1"}
with log_path.open("w") as output:
    process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
state = {"pid": process.pid, "process_group": process.pid, "command": command, "log": str(log_path), "started_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(), "configuration": vars(args), "project_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()}
state_path.write_text(json.dumps(state, indent=2) + "\n")
print(json.dumps(state, indent=2))
