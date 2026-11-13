"""Run the R152 strict flat audit criteria against the R41 delivery.

Same harness logic as Rob2Nav R152 runtime/audit_flat_geometry.py (filtered model
with nominal-overlap self contacts excluded, identical contact capture, identical
seeds/commands, identical `qualified` criteria), executed entirely inside the R41
runtime tree so R41's own python controller and ONNX actor drive the episodes.

Usage: python3 r41_audit_strict.py <assets> <r41_runtime_dir> <r41_policy_pt> <r41_onnx> <output_dir>
"""
import json
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from pathlib import Path

import numpy as np
import torch

R41_RUNTIME = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(R41_RUNTIME))

from export_r41_onnx import OnnxActor, session_for  # noqa: E402
import evaluate_omni_stairs as ev  # noqa: E402
from evaluate_omni_joint import make_controller  # noqa: E402
from train_omni_stop_transition import load  # noqa: E402

ASSETS = Path(sys.argv[1]).resolve()
SOURCE = Path(sys.argv[3]).resolve()
ONNX = Path(sys.argv[4]).resolve()
OUTPUT = Path(sys.argv[5]).resolve()

# 与 R152 audit 完全一致的命令表（逐项断言防漂移）
R152_COMMANDS = {
    "stop": (0., 0., 0.),
    "forward_slow": (.2, 0., 0.),
    "forward": (.4, 0., 0.),
    "forward_fast": (.6, 0., 0.),
    "reverse": (-.4, 0., 0.),
    "left": (0., .3, 0.),
    "right": (0., -.3, 0.),
    "turn_left": (0., 0., .65),
    "turn_right": (0., 0., -.65),
    "diagonal_left": (.35, .25, 0.),
    "diagonal_right": (.35, -.25, 0.),
    "arc_left": (.35, 0., .5),
    "arc_right": (.35, 0., -.5),
}
assert dict(ev.FLAT_COMMANDS) == R152_COMMANDS, f"R41 FLAT_COMMANDS 与 R152 不一致: {dict(ev.FLAT_COMMANDS)}"
for t in (0., 0.31, 0.62):
    a = ev.gait_clock(t)
    expect = (np.sin(2 * np.pi * t / .62), np.cos(2 * np.pi * t / .62))
    assert np.allclose(a, expect), f"R41 gait_clock 与 R152 不一致: {a} vs {expect}"

NOMINAL_OVERLAPS = {("FL_thigh", "base_link"), ("FR_thigh", "base_link")}


def exclude_nominal_overlaps(spec):
    for first, second in sorted(NOMINAL_OVERLAPS):
        spec.add_exclude(bodyname1=first, bodyname2=second)
    return spec


@lru_cache(maxsize=2)
def runtime(checkpoint):
    return load(ASSETS, checkpoint)


@lru_cache(maxsize=1)
def ort_session():
    return session_for(ONNX)


@lru_cache(maxsize=1)
def flat_model():
    spec = ev.sim.mj.MjSpec.from_file(str(ASSETS / "local-step-diagnostic/as2w_flat.xml"))
    model = exclude_nominal_overlaps(spec).compile()
    ground = model.geom("ground").id
    model.geom_priority[ground] = int(model.geom_priority.max()) + 1
    return model


def evaluate(job):
    checkpoint, split, name, target, seed = job
    policy, contract, limits, base, controller = runtime(SOURCE if checkpoint.suffix == ".onnx" else checkpoint)
    actor = (OnnxActor(ort_session(), np.asarray(contract["default_joint_pos"]))
             if checkpoint.suffix == ".onnx" else make_controller(policy, contract, controller, base()))
    model = flat_model()
    body = model.body("base_link").id
    wheels = [model.body(n).id for n in contract["joint_names"][12:]]
    force = np.zeros(6)
    front_sides = []
    rear_sides = []
    peak_self = peak_nonwheel = 0.
    first_ground_hit = None
    defaults = np.asarray(contract["default_joint_pos"])

    def plan(unused_model, unused_data, obs, command, tick, advance):
        frame = obs.copy()
        frame[3:9] = frame[3:9].astype(np.float32)
        frame[10:26] = (frame[10:26] + defaults).astype(np.float32).astype(np.float64) - defaults
        frame[26:42] = frame[26:42].astype(np.float32)
        return actor.plan(None, None, frame, command, tick, None)

    def capture(model, data, command):
        nonlocal peak_self, peak_nonwheel, first_ground_hit
        rotation = data.xmat[body].reshape(3, 3)
        wheel_centers = (data.xpos[wheels] - data.xpos[body]) @ rotation
        front_sides.append(float(min(wheel_centers[0, 1], -wheel_centers[1, 1])))
        rear_sides.append(float(min(wheel_centers[2, 1], -wheel_centers[3, 1])))
        for i, c in enumerate(data.contact):
            a, b = (int(model.geom_bodyid[g]) for g in c.geom)
            if a and b:
                ev.sim.mj.mj_contactForce(model, data, i, force)
                peak_self = max(peak_self, force[0])
            elif (a or b) not in wheels:
                ev.sim.mj.mj_contactForce(model, data, i, force)
                peak_nonwheel = max(peak_nonwheel, force[0])
                if first_ground_hit is None and force[0] >= 50.:
                    first_ground_hit = dict(tick=len(front_sides) - 1, body=model.body(a or b).name,
                                            force_n=float(force[0]))

    row = ev.flat_episode(None, contract, limits, np.asarray(target), seed, ev.gait_clock, plan, capture)
    qualified = row["passed"] and min(front_sides) > 0. and peak_self < 1. and peak_nonwheel < 50.
    return dict(row, split=split, command=name, seed=seed, target=list(target),
                front_min=min(front_sides), rear_min=min(rear_sides),
                front_cross_ticks=sum(v <= 0. for v in front_sides), qualified=qualified,
                peak_self=float(peak_self), peak_nonwheel=float(peak_nonwheel), first_ground_hit=first_ground_hit)


if __name__ == "__main__":
    ev.sim.ROOT = ASSETS
    torch.set_num_threads(1)
    fixed = [("fixed", name, target, seed) for name, target in ev.FLAT_COMMANDS.items()
             for seed in range(81201, 81205)]
    rng = np.random.default_rng(91291)
    held = [("independent", f"mixed_{i:02d}", target, 91101 + i)
            for i, target in enumerate(rng.uniform((-.6, -.35, -.8), (.6, .35, .8), size=(48, 3)))]
    held.extend(("independent", "stop", np.zeros(3), seed) for seed in range(91201, 91205))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(8) as pool:
        for checkpoint in (SOURCE, ONNX):
            tasks = [(checkpoint, *case) for case in fixed + held]
            rows = list(pool.map(evaluate, tasks, chunksize=2))
            label = "onnx-flat" if checkpoint.suffix == ".onnx" else "python-flat"
            (OUTPUT / f"{label}.json").write_text(json.dumps(rows, indent=2, default=lambda x: x.item()))
            for split in ("fixed", "independent"):
                batch = [r for r in rows if r["split"] == split]
                print(label, split, len(batch), "tracking", sum(r["passed"] for r in batch),
                      "qualified", sum(r["qualified"] for r in batch), "crossing",
                      Counter(r["command"] for r in batch if r["front_cross_ticks"]),
                      "falls", sum(r["fallen"] for r in batch), flush=True)
