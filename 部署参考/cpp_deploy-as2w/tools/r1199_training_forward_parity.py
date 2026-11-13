#!/usr/bin/env python3
"""Offline C++ vs Python wrapper parity for R1199 motion candidates.

Reads the ARM64 replay's exact 65-D observations and final actions. It never
connects to DDS or sends commands. Run in an environment with torch and ORT.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch


def main():
    p = argparse.ArgumentParser()
    p.add_argument("replay", type=Path)
    p.add_argument("onnx", type=Path)
    p.add_argument("training_snapshot", type=Path)
    p.add_argument("--limit", type=float, default=1e-5)
    p.add_argument("--training-runtime", action="store_true",
                   help="Match model_1199 training: continuous/straight bias on; odometry/settle/common feedback off")
    a = p.parse_args()
    sys.path.insert(0, str(a.training_snapshot))
    from as2w_rolling_fixed_exit import (
        parking_odometry, rolling_fixed_exit, rolling_precalibrated_stand,
        rolling_wheel_hold,
    )

    session = ort.InferenceSession(str(a.onnx), providers=["CPUExecutionProvider"])
    observations = []
    actions = []
    for row in a.replay.read_text(encoding="utf-8").splitlines():
        if row.startswith("R1199_OBS,"):
            fields = row.split(",")
            if len(fields) != 67:
                raise ValueError(f"observation fields={len(fields)}")
            observations.append(np.array(fields[2:], dtype=np.float32))
        elif row.startswith("R1199_TARGET,"):
            fields = row.split(",")
            if len(fields) != 34:
                raise ValueError(f"target fields={len(fields)}")
            actions.append(np.array(fields[2:18], dtype=np.float32))
    if len(observations) != len(actions) or not observations:
        raise ValueError(f"frame count obs={len(observations)} actions={len(actions)}")

    reference = torch.zeros(1, 4, dtype=torch.float32)
    frames = torch.zeros(1, dtype=torch.long)
    bias = torch.zeros(1, 12, dtype=torch.float32)
    previous = np.zeros(16, dtype=np.float32)
    max_action = max_history = 0.0
    max_at = None
    motion_frames = 0
    for tick, (obs, actual) in enumerate(zip(observations, actions), 1):
        history_error = float(np.max(np.abs(obs[42:58] - previous)))
        max_history = max(max_history, history_error)
        raw = torch.from_numpy(session.run(["actions"], {"obs": obs[None]})[0].copy())
        frame = torch.from_numpy(obs[None].copy())
        cmd = frame[:, :3].clone()
        cmd[:, 0] += .4
        if max(abs(float(cmd[0, 0])), abs(float(cmd[0, 2]))) > .005:
            motion_frames += 1
        legs, wheels = rolling_fixed_exit(raw, cmd)
        odometry = (frame[:, 22:26] if a.training_runtime else
                    parking_odometry(frame[:, 22:26], frame[:, 10:22], -frame[:, 6:9]))
        reference, frames, hold = rolling_wheel_hold(
            reference, frames, cmd, odometry, frame[:, 38:42], frame[:, 3:6], .02,
            common_feedback=not a.training_runtime,
            common_gain_scale=.5,
            leg_speed=None if a.training_runtime else frame[:, 26:38])
        bias, stand = rolling_precalibrated_stand(
            bias, cmd, frame[:, 10:22], frame[:, 3:6], -frame[:, 8],
            frame[:, 38:42], frames, frame.new_tensor([tick * .02]), .02,
            continuous=a.training_runtime, straight_only=a.training_runtime)
        expected = torch.cat((legs + stand, wheels + hold), dim=1)[0].numpy()
        error = float(np.max(np.abs(expected - actual)))
        if error > max_action:
            max_action, max_at = error, tick
        previous = actual
    print(f"TRAINING_FORWARD_PARITY runtime={'training' if a.training_runtime else 'old_diagnostic'} "
          f"frames={len(actions)} motion_frames={motion_frames} "
          f"max_action_error={max_action:.9g} at_frame={max_at} "
          f"max_previous_action_error={max_history:.9g} threshold={a.limit:.9g}")
    if max_action > a.limit or max_history > 1e-5 or motion_frames < 50:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
