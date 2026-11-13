#!/usr/bin/env python3
"""Evaluate the AS2W actor in the pinned native PhysX task."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor/robot_lab/source/robot_lab"))
sys.path.insert(0, str(ROOT / "source"))

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--seconds", type=float, default=10)
parser.add_argument("--output", default=str(ROOT / "outputs/native_policy_evaluation"))
parser.add_argument("--policy", type=Path, required=True)
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
app = AppLauncher(args).app

import gymnasium as gym
import numpy as np
import torch

import robot_lab.tasks  # noqa: F401
import as2w_robot_lab  # noqa: F401
from as2w_robot_lab.env_cfg import UnitreeAS2WFlatEnvCfg
from as2w_robot_lab.audit import audit_environment


def main():
    profiles = {"stand": (0, 0, 0), "forward": (0.5, 0, 0), "backward": (-0.3, 0, 0), "left": (0, 0.3, 0), "right": (0, -0.3, 0), "turn_left": (0, 0, 0.5), "turn_right": (0, 0, -0.5), "arc_left": (0.5, 0, 0.5)}
    cfg = UnitreeAS2WFlatEnvCfg()
    cfg.scene.num_envs = len(profiles)
    cfg.sim.device = args.device
    cfg.seed = 42
    cfg.observations.policy.enable_corruption = False
    # Nominal evaluation: retain explicit root/joint reset operations only.
    for name in list(vars(cfg.events)):
        if not name.startswith("_") and name not in {"randomize_reset_base", "randomize_reset_joints"}:
            setattr(cfg.events, name, None)
    cfg.events.randomize_reset_base.params["pose_range"] = {k: (0.0, 0.0) for k in ["x", "y", "z", "roll", "pitch", "yaw"]}
    cfg.events.randomize_reset_base.params["velocity_range"] = {k: (0.0, 0.0) for k in ["x", "y", "z", "roll", "pitch", "yaw"]}
    cfg.commands.base_velocity.heading_command = False
    cfg.commands.base_velocity.rel_heading_envs = 0.0
    cfg.commands.base_velocity.rel_standing_envs = 0.0
    env = gym.make("RobotLab-Isaac-Velocity-Flat-Unitree-AS2W-v0", cfg=cfg)
    raw = env.unwrapped
    policy_path = args.policy.resolve()
    metadata_path = policy_path.with_suffix(".json")
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text())
        policy_contract_path = Path(metadata["checkpoint"]).parent / "as2w_contract.json"
    else:
        policy_contract_path = policy_path.parent.parent / "as2w_contract.json"
    if not policy_contract_path.is_file():
        raise ValueError("Policy has no AS2W training contract; refusing to apply B2W weights to AS2W")
    output = Path(args.output).resolve()
    audited = audit_environment(raw, output, evaluation=True)
    trained = json.loads(policy_contract_path.read_text())
    if trained["contract"] != audited["contract"]:
        raise ValueError("Policy / AS2W morphology contract mismatch")
    policy = torch.jit.load(str(policy_path), map_location=raw.device).eval()
    commands = torch.tensor(list(profiles.values()), dtype=torch.float32, device=raw.device)
    term = raw.command_manager.get_term("base_velocity")
    env.reset()
    robot = raw.scene["robot"]
    dt = raw.step_dt
    rows = []
    first_failure = [None] * len(profiles)
    initial_obs = None
    try:
        with torch.inference_mode():
            for step in range(round((args.seconds + 2) / dt)):
                cmd = torch.zeros_like(commands) if step * dt < 2 else commands
                term.vel_command_b.copy_(cmd)
                obs = raw.observation_manager.compute()["policy"]
                if initial_obs is None:
                    initial_obs = obs.cpu().numpy().tolist()
                action = policy(obs)
                env.step(action)
                position = robot.data.root_pos_w - raw.scene.env_origins
                tilt = torch.acos(torch.clamp(-robot.data.projected_gravity_b[:, 2], -1, 1))
                fail = ((tilt > math.pi / 3) | (position[:, 2] < 0.20)).cpu().tolist()
                for index, failed in enumerate(fail):
                    if failed and first_failure[index] is None:
                        first_failure[index] = (step + 1) * dt
                rows.append({
                    "time": (step + 1) * dt, "command": cmd.cpu().numpy(),
                    "position": position.cpu().numpy(), "quaternion": robot.data.root_quat_w.cpu().numpy(),
                    "joint_pos": robot.data.joint_pos.cpu().numpy(),
                    "velocity_body": robot.data.root_lin_vel_b.cpu().numpy(),
                    "angular_velocity_body": robot.data.root_ang_vel_b.cpu().numpy(),
                    "tilt": tilt.cpu().numpy(),
                })
        arrays = {key: np.asarray([row[key] for row in rows]) for key in rows[0]}
        out = Path(args.output).resolve()
        out.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(out / "trajectory.npz", **arrays)
        evaluation = {}
        mask = arrays["time"] > 4.0
        for index, (name, command) in enumerate(profiles.items()):
            actual = np.column_stack([arrays["velocity_body"][:, index, :2], arrays["angular_velocity_body"][:, index, 2]])
            evaluation[name] = {
                "command": list(command), "first_failure_seconds": first_failure[index],
                "mean_actual_vx_vy_wz": actual[mask].mean(axis=0).tolist(),
                "rmse_vx_vy_wz": np.sqrt(((actual[mask] - command) ** 2).mean(axis=0)).tolist(),
                "max_tilt_deg": float(np.degrees(arrays["tilt"][:, index].max())),
                "min_base_height_m": float(arrays["position"][:, index, 2].min()),
            }
        result = {"profiles": evaluation, "physics_dt": cfg.sim.dt, "policy_dt": dt,
                  "joint_names": robot.joint_names, "initial_policy_observations": initial_obs,
                  "policy_path": str(policy_path), "policy_sha256": hashlib.sha256(policy_path.read_bytes()).hexdigest(),
                  "fall_criteria": "Base height < 0.20 m or tilt > 60 degrees; this checks survival, not posture quality or tracking acceptance.",
                  "scope": "Frozen deterministic AS2W actor, nominal native robot_lab flat task, noise and domain randomization disabled only for evaluation. No teacher, StraightRoll or stop controller; no training."}
        (out / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(evaluation, indent=2), flush=True)
    finally:
        env.close()


try:
    main()
finally:
    app.close()
