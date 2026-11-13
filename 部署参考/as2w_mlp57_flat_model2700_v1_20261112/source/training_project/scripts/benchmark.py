#!/usr/bin/env python3
"""Bounded environment-scaling probe with GPU sampling and PPO timing."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]


def descendants(pid: int) -> set[int]:
    found = {pid}
    pending = [pid]
    while pending:
        parent = pending.pop()
        try:
            children = Path(f"/proc/{parent}/task/{parent}/children").read_text().split()
        except OSError:
            continue
        for value in children:
            child = int(value)
            if child not in found:
                found.add(child)
                pending.append(child)
    return found


def gpu_sample(gpu: int, pids: set[int]):
    board = subprocess.check_output(["nvidia-smi", f"--id={gpu}", "--query-gpu=uuid,memory.used,memory.free,utilization.gpu", "--format=csv,noheader,nounits"], text=True).strip().split(",")
    uuid = board[0].strip()
    processes = subprocess.check_output(["nvidia-smi", "--query-compute-apps=gpu_uuid,pid,used_gpu_memory", "--format=csv,noheader,nounits"], text=True)
    own = 0
    for line in processes.splitlines():
        parts = [x.strip() for x in line.split(",")]
        if len(parts) == 3 and parts[0] == uuid and parts[1].isdigit() and int(parts[1]) in pids and parts[2].isdigit():
            own += int(parts[2])
    return {"board_used_mib": int(board[1]), "board_free_mib": int(board[2]), "utilization_pct": int(board[3]), "own_compute_mib": own}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num-envs", type=int, default=32768)
    parser.add_argument("--iterations", type=int, default=8)
    parser.add_argument("--gpu", type=int, default=1)
    parser.add_argument("--contact-patches", type=int, default=524288)
    parser.add_argument("--timeout", type=float, default=600)
    args = parser.parse_args()
    if args.num_envs <= 0 or args.iterations < 2:
        parser.error("Positive environment count and at least two updates are required")
    stamp = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d_%H%M%S")
    name = f"scale_flat_{args.num_envs}_{args.iterations}_{stamp}"
    output = ROOT / "outputs" / name
    output.mkdir(parents=True)
    log_path = output / "train.log"
    command = [str(ROOT / ".venv/bin/python"), "-u", str(ROOT / "scripts/train.py"), "--terrain", "flat", "--num-envs", str(args.num_envs), "--iterations", str(args.iterations), "--gpu", str(args.gpu), "--run-name", name, f"env.sim.physx.gpu_max_rigid_patch_count={args.contact_patches}"]
    started = time.monotonic()
    samples = []
    timed_out = False
    with log_path.open("w") as log:
        process = subprocess.Popen(command, cwd=ROOT, env={**os.environ, "PYTHONUNBUFFERED": "1"}, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        (output / "run_state.json").write_text(json.dumps({"pid": process.pid, "command": command, "configuration": vars(args)}, indent=2) + "\n")
        print(f"Scaling probe PID {process.pid}: {output}", flush=True)
        while process.poll() is None:
            sample = gpu_sample(args.gpu, descendants(process.pid))
            samples.append({"wall_seconds": time.monotonic() - started, **sample})
            if time.monotonic() - started > args.timeout:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                break
            time.sleep(2)
        code = process.wait()
    text = re.sub(r"\x1b\[[0-9;]*m", "", log_path.read_text(errors="replace"))
    iteration_matches = re.findall(r"Learning iteration\s+(\d+)/(\d+)", text)
    durations = [float(value) for value in re.findall(r"Iteration time:\s*([0-9.]+)s", text)]
    steady = durations[1:] if len(durations) > 1 else durations
    mean_time = sum(steady) / len(steady) if steady else None
    error_lines = [line for line in text.splitlines() if any(marker in line.lower() for marker in ["traceback", "out of memory", "buffer overflow", "capacity exceeded", "increase its size", "cuda error"])]
    result = {"configuration": vars(args), "exit_code": code, "timed_out": timed_out,
              "last_logged_iteration": int(iteration_matches[-1][0]) if iteration_matches else None,
              "iteration_seconds": durations, "mean_iteration_seconds_excluding_first": mean_time,
              "control_transitions_per_update": args.num_envs * 24,
              "control_transitions_per_second": args.num_envs * 24 / mean_time if mean_time else None,
              "ppo_minibatch_size": args.num_envs * 24 // 4,
              "peak_board_used_mib": max((s["board_used_mib"] for s in samples), default=None),
              "peak_own_compute_mib": max((s["own_compute_mib"] for s in samples), default=None),
              "minimum_board_free_mib": min((s["board_free_mib"] for s in samples), default=None),
              "error_lines": error_lines, "wall_seconds": time.monotonic() - started,
              "log": str(log_path), "scope": "Bounded training throughput and memory probe; does not validate learned locomotion quality."}
    (output / "gpu_samples.json").write_text(json.dumps(samples, indent=2) + "\n")
    (output / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2), flush=True)
    raise SystemExit(0 if code == 0 and not error_lines else 1)


if __name__ == "__main__":
    main()
