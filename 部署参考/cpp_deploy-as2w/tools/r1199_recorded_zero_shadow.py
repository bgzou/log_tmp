#!/usr/bin/env python3
"""Offline R1199 zero-command shadow against recorded AS2-W LowState.

Diagnostic only: recorded states come from another controller, so this is not a
closed-loop stability test and never publishes DDS/LowCmd. It follows the
training-side 65D previous *wrapped* action and zero-command park path.
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np
import onnxruntime as ort


DEFAULTS = np.array([0] * 4 + [.8] * 4 + [-1.6] * 4 + [0] * 4, dtype=np.float64)
SIDE = np.array([1, -1, 1, -1], dtype=np.float64)
DT = .02


def torch_frames_time(frames):
    """Torch float32 frame-time comparison used by the training wrapper."""
    return np.float32(frames) * np.float32(DT)


def wrap(angle):
    return (angle + 2 * math.pi) % (4 * math.pi) - 2 * math.pi


def read_map(path):
    rows = [line.split() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")]
    if len(rows) != 16:
        raise ValueError("Expected 16 measured motor bindings")
    return [(name, int(slot), float(sign), float(zero)) for name, slot, sign, zero in rows]


def records(path, mapping):
    for line in path.open(encoding="utf-8", errors="replace"):
        if not line.startswith("LOW_SAMPLE,"):
            continue
        fields = line.rstrip().split(",")
        if len(fields) < 14 + 35 * 6:
            continue
        try:
            elapsed = float(fields[1])
            quat = np.array([float(x) for x in fields[7:11]], dtype=np.float64)
            gyro = np.array([float(x) for x in fields[11:14]], dtype=np.float64)
            q = np.array([sign * (float(fields[14 + slot * 6]) - zero)
                          for _, slot, sign, zero in mapping])
            dq = np.array([sign * float(fields[15 + slot * 6])
                           for _, slot, sign, _ in mapping])
            modes = [int(fields[18 + slot * 6]) for _, slot, _, _ in mapping]
            if all(mode == 1 for mode in modes) and np.isfinite(quat).all():
                yield elapsed, quat, gyro, q, dq
        except (ValueError, IndexError):
            continue


def gravity_body(q):
    q = q / np.linalg.norm(q)
    w, x, y, z = q
    return np.array([-2 * (x * z - w * y), -2 * (y * z + w * x),
                     2 * (x * x + y * y) - 1], dtype=np.float64)


def parking_odometry(wheel_q, leg_error, up):
    thigh = .8 + leg_error[4:8]
    calf = -1.6 + leg_error[8:12]
    pitch = math.atan2(-up[0], math.hypot(up[1], up[2]))
    x = np.array([.2119, .2119, -.2119, -.2119])
    x -= .212 * (np.sin(thigh) + np.sin(thigh + calf))
    z = -.212 * (np.cos(thigh) + np.cos(thigh + calf))
    hub_x = math.cos(pitch) * x + math.sin(pitch) * z
    return wheel_q + leg_error[4:8] + leg_error[8:12] + pitch - hub_x / .086


def shadow(path, model, mapping, start_ms, duration_s):
    session = ort.InferenceSession(str(model), providers=["CPUExecutionProvider"])
    if [(x.name, x.shape) for x in session.get_inputs()] != [("obs", [1, 65])]:
        raise ValueError("Unexpected R1199 input contract")
    if [(x.name, x.shape) for x in session.get_outputs()] != [("actions", [1, 16])]:
        raise ValueError("Unexpected R1199 output contract")
    previous = np.zeros(16, dtype=np.float64)
    bias = np.zeros(12, dtype=np.float64)
    reference = np.zeros(4, dtype=np.float64)
    wheel_memory = np.zeros(4, dtype=np.float64)
    zero_memory_started = False
    hold_frames = 0
    tick = 0
    last_elapsed = -1e9
    result = []
    for elapsed, quat, gyro, q, dq in records(path, mapping):
        if elapsed < start_ms or elapsed > start_ms + duration_s * 1000:
            continue
        if elapsed - last_elapsed < 19.0:
            continue
        last_elapsed = elapsed
        up = -gravity_body(quat)
        frame = np.zeros(65, dtype=np.float64)
        frame[:3] = [-.4, 0, 0]
        frame[3:6] = gyro
        frame[6:9] = -up
        frame[9] = .4
        frame[10:22] = q[:12] - DEFAULTS[:12]
        frame[22:26] = wrap(q[12:])
        frame[26:42] = dq
        frame[42:58] = previous
        phase = 2 * math.pi * tick * DT / .62
        frame[58:60] = [math.sin(phase), math.cos(phase)]
        tick += 1
        if not zero_memory_started:
            wheel_memory = frame[22:26].copy()
            zero_memory_started = True
        frame[60:64] = np.clip(wrap(frame[22:26] - wheel_memory) / .20, -3, 3)
        frame[64] = 1
        raw = session.run(["actions"], {"obs": frame.astype(np.float32)[None]})[0][0].astype(np.float64)
        if not np.isfinite(raw).all():
            raise ValueError("Nonfinite ONNX output")

        # At physical zero command, rolling_fixed_exit makes the raw residual
        # motion term zero. These are the current training evaluator's park
        # odometry, 0.5 common gain, settle-joints and precalibrated stand path.
        leg_error = frame[10:22]
        wheel_q_odo = parking_odometry(frame[22:26], leg_error, up)
        quiet_hold = (np.max(np.abs(dq[12:])) < .5 and np.linalg.norm(gyro) < .15
                      and np.max(np.abs(dq[:12])) < .5)
        was_latched = torch_frames_time(hold_frames) >= np.float32(.35)
        hold_frames = hold_frames + 1 if (was_latched or quiet_hold) else 0
        is_latched = torch_frames_time(hold_frames) >= np.float32(.35)
        if is_latched and not was_latched:
            reference = wheel_q_odo.copy()
        error = wrap(wheel_q_odo - reference)
        longitudinal = np.mean(error)
        heading = np.mean(error * SIDE)
        wheel_hold = np.clip(.5 * (-2.5 * longitudinal - 1.4 * heading * SIDE),
                             -.75, .75) / 16 if is_latched else np.zeros(4)

        age = torch_frames_time(tick)
        quiet_bias = (np.linalg.norm(gyro) < .20 and up[2] > .92
                      and np.max(np.abs(dq[12:])) < .55)
        if age < np.float32(4) and quiet_bias and torch_frames_time(hold_frames) >= np.float32(.30):
            correction = np.clip(-1.4 * DT * leg_error, -.004, .004)
            bias = np.clip((1 - .03 * DT) * bias + correction, -.38, .38)
        release_blend = np.clip((float(torch_frames_time(hold_frames)) - .45) / 1.05, 0, 1)
        stand_blend = 1 if age < 4 else release_blend
        wrapped = np.r_[stand_blend * bias / .35, wheel_hold]
        previous = wrapped.copy()  # training contract: BEFORE handoff blend
        target_q = DEFAULTS[:12] + .35 * wrapped[:12]
        target_dq = 16 * wrapped[12:]
        pd = 55 * (target_q - q[:12]) - 2 * dq[:12]
        result.append(dict(t_s=round(float(age), 3), actual_q=q[:12].round(5).tolist(),
                           target_q=target_q.round(5).tolist(),
                           wheel_dq=target_dq.round(5).tolist(),
                           bias=bias.round(5).tolist(),
                           max_predicted_leg_pd_nm=round(float(np.max(np.abs(pd))), 4),
                           max_wheel_target_rad_s=round(float(np.max(np.abs(target_dq))), 4),
                           max_raw_action=float(np.max(np.abs(raw)))))
    if not result:
        raise ValueError("No active recorded samples in requested window")
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("capture", type=Path)
    ap.add_argument("model", type=Path)
    ap.add_argument("mapping", type=Path)
    ap.add_argument("--start-ms", type=float, required=True)
    ap.add_argument("--duration-s", type=float, default=10)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    rows = shadow(args.capture, args.model, read_map(args.mapping),
                  args.start_ms, args.duration_s)
    summary = dict(kind="recorded_open_loop_zero_shadow", frames=len(rows),
                   first=rows[0], last=rows[-1],
                   max_predicted_leg_pd_nm=max(x["max_predicted_leg_pd_nm"] for x in rows),
                   max_wheel_target_rad_s=max(x["max_wheel_target_rad_s"] for x in rows))
    args.output.write_text(json.dumps(dict(summary=summary, frames=rows), indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
