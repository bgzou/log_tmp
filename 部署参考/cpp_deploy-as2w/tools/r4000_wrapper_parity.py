#!/usr/bin/env python3
"""Offline C++ vs Python wrapper parity for the R4000 joystick candidate.

Reads the exact 65-D observations and wrapped actions produced by
as2w_r4000_joystick_replay on a recorded sensor fixture and re-drives the
training-side reference implementation (as2w_rolling_filtered +
as2w_rolling_fixed_exit, commit 9dffc8c9 == repo HEAD) on the same
observations. The chain under test is the full rolling-4000 training
contract: 5 Hz leg-residual filter, pure_turn_common_scale=0 wheel
mapping, 0.12 s wheel hold, precalibrated continuous/straight stand and
0.9 rad/s leg-target slew. Never connects to DDS or sends commands.

Usage: r4000_wrapper_parity.py <replay.log> <onnx> <training_snapshot_dir>
                              [--limit 1e-5]
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
    a = p.parse_args()
    sys.path.insert(0, str(a.training_snapshot))
    from as2w_rolling_filtered import filter_leg_residual
    from as2w_rolling_fixed_exit import (rolling_fixed_exit,
                                         rolling_precalibrated_stand,
                                         rolling_wheel_hold)

    session = ort.InferenceSession(str(a.onnx), providers=["CPUExecutionProvider"])
    observations, actions = [], []
    for row in a.replay.read_text(encoding="utf-8").splitlines():
        if row.startswith("R4000_OBS,"):
            fields = row.split(",")
            if len(fields) != 67:
                raise ValueError(f"observation fields={len(fields)}")
            observations.append(np.array(fields[2:], dtype=np.float32))
        elif row.startswith("R4000_TARGET,"):
            fields = row.split(",")
            if len(fields) != 34:
                raise ValueError(f"target fields={len(fields)}")
            actions.append(np.array(fields[2:18], dtype=np.float32))
    if len(observations) != len(actions) or not observations:
        raise ValueError(f"frame count obs={len(observations)} actions={len(actions)}")

    # Wrapper state, reset exactly like Controller::arm().
    wheel_reference = torch.zeros(1, 4)
    hold_frames = torch.zeros(1, dtype=torch.long)
    stand_bias = torch.zeros(1, 12)
    filtered_legs = torch.zeros(12)
    slew_legs = np.zeros(12, dtype=np.float32)
    previous = np.zeros(16, dtype=np.float32)
    dt = .02
    max_action = max_history = 0.0
    max_at = None
    motion_frames = 0
    for index, (obs, actual) in enumerate(zip(observations, actions), 1):
        history_error = float(np.max(np.abs(obs[42:58] - previous)))
        max_history = max(max_history, history_error)
        raw = torch.from_numpy(session.run(["actions"], {"obs": obs[None]})[0].copy())
        frame = torch.from_numpy(obs[None].copy())
        cmd = frame[:, :3].clone()
        cmd[:, 0] += .4
        if max(abs(float(cmd[0, 0])), abs(float(cmd[0, 2]))) > .005:
            motion_frames += 1
        # as2w_rolling_filtered.filter_leg_residual on the raw leg residuals.
        filtered_legs = filter_leg_residual(filtered_legs, raw[:, :12], dt, 5.0)
        action = torch.cat((filtered_legs, raw[:, 12:]), dim=1)
        legs, wheels = rolling_fixed_exit(action, cmd,
                                          pure_turn_common_scale=0.)
        wheel_reference, hold_frames, hold = rolling_wheel_hold(
            wheel_reference, hold_frames, cmd, frame[:, 22:26], frame[:, 38:42],
            frame[:, 3:6], dt, common_feedback=False, leg_speed=None)
        wheels = wheels + hold
        stand_bias, stand = rolling_precalibrated_stand(
            stand_bias, cmd, frame[:, 10:22], frame[:, 3:6], -frame[:, 8],
            frame[:, 38:42], hold_frames, frame.new_tensor([index * dt]), dt,
            continuous=True, straight_only=True)
        legs = legs + stand
        # as2w_rolling_low_speed_smooth: unconditional 0.9 rad/s slew on the
        # wrapped leg targets (after the stance addition).
        step_limit = .9 * dt / .35
        slew_legs += np.clip(legs[0].numpy() - slew_legs, -step_limit, step_limit)
        expected = np.concatenate((slew_legs, wheels[0].numpy()))
        error = float(np.max(np.abs(expected - actual)))
        if error > max_action:
            max_action, max_at = error, index
        previous = actual

    print(f"frames={len(observations)} motion_frames={motion_frames}")
    print(f"previous-action history max error={max_history:.3e}")
    print(f"wrapped action max error={max_action:.3e} at frame {max_at}")
    if max_history > a.limit or max_action > a.limit:
        print(f"PARITY FAIL (limit {a.limit:g})")
        return 1
    print("PARITY PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
