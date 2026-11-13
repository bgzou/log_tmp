#!/usr/bin/env python3
"""Compare R1199 zero-command C++ adapter with the copied training helpers.

Runs offline on a Python environment with torch; reads a fixed sensor fixture
and writes the training-side q/dq targets. Never connects to the robot.
"""
import argparse
import sys
from pathlib import Path

import torch


def main():
    p = argparse.ArgumentParser()
    p.add_argument("fixture", type=Path)
    p.add_argument("training_snapshot", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    sys.path.insert(0, str(a.training_snapshot))
    from as2w_rolling_fixed_exit import (parking_odometry, rolling_fixed_exit,
                                         rolling_precalibrated_stand, rolling_wheel_hold)

    defaults = torch.tensor([0] * 4 + [.8] * 4 + [-1.6] * 4 + [0] * 4,
                            dtype=torch.float32)[None]
    command = torch.zeros(1, 3, dtype=torch.float32)
    raw = torch.zeros(1, 16, dtype=torch.float32)
    bias = torch.zeros(1, 12, dtype=torch.float32)
    reference = torch.zeros(1, 4, dtype=torch.float32)
    frames = torch.zeros(1, dtype=torch.int64)
    output = []
    for tick, line in enumerate(a.fixture.read_text().splitlines(), 1):
        values = [float(x) for x in line.split()]
        if len(values) != 40:
            raise ValueError(f"fixture line {tick}: expected elapsed + 39 sensor values")
        _, w, x, y, z, *rest = values
        quat = torch.tensor([w, x, y, z], dtype=torch.float32)
        quat /= torch.linalg.norm(quat)
        w, x, y, z = quat
        gyro = torch.tensor(rest[:3], dtype=torch.float32)[None]
        q = torch.tensor(rest[3:19], dtype=torch.float32)[None]
        dq = torch.tensor(rest[19:35], dtype=torch.float32)[None]
        gravity = torch.stack((-2 * (x*z-w*y), -2 * (y*z+w*x),
                               2 * (x*x+y*y)-1))[None]
        up = -gravity
        error = q[:, :12] - defaults[:, :12]
        wheel_angle = (q[:, 12:] + 2 * torch.pi).remainder(4 * torch.pi) - 2 * torch.pi
        odometry = parking_odometry(wheel_angle, error, up)
        legs, wheels = rolling_fixed_exit(raw, command)
        reference, frames, hold = rolling_wheel_hold(
            reference, frames, command, odometry, dq[:, 12:], gyro, .02,
            common_feedback=True, common_gain_scale=.5, leg_speed=dq[:, :12])
        bias, stand = rolling_precalibrated_stand(
            bias, command, error, gyro, up[:, 2], dq[:, 12:], frames,
            torch.tensor([tick * .02], dtype=torch.float32), .02)
        current = torch.cat((legs + stand, wheels + hold), dim=1)
        target_q = defaults[:, :12] + .35 * current[:, :12]
        target_dq = 16 * current[:, 12:]
        output.append(",".join(f"{float(v):.9g}" for v in
                               torch.cat((target_q, target_dq), dim=1)[0]))
    a.output.write_text("\n".join(output) + "\n", encoding="utf-8")
    print(f"TRAINING_ZERO_FRAMES={len(output)}")


if __name__ == "__main__":
    main()
