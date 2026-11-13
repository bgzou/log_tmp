#!/usr/bin/env python3
"""Print the active run and the most recent completed PPO iteration."""
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
state_path = ROOT / "logs/active_training.json"
if not state_path.exists():
    raise SystemExit("No persistent training run has been started.")
state = json.loads(state_path.read_text())
proc = Path(f"/proc/{state['pid']}/stat")
cmdline = Path(f"/proc/{state['pid']}/cmdline")
state["process_alive"] = bool(proc.exists() and proc.read_text().split(") ", 1)[1].split()[0] != "Z" and cmdline.exists() and str(ROOT / "scripts/train.py").encode() in cmdline.read_bytes())
with Path(state["log"]).open("rb") as log:
    log.seek(0, 2)
    log.seek(max(0, log.tell() - 65536))
    tail = log.read().decode(errors="replace")
matches = re.findall(r"Learning iteration\s+(\d+)/(\d+)", tail)
state["last_logged_iteration"] = int(matches[-1][0]) if matches else None
state["training_time_reported"] = "Training time:" in tail
state["error_in_recent_log"] = "Traceback (most recent call last)" in tail
print(json.dumps(state, indent=2))
