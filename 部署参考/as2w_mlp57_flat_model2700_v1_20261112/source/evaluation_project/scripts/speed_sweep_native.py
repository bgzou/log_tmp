"""Frozen-actor speed sweep in native PhysX; import after AppLauncher."""
import csv
import hashlib
import json
import math
from pathlib import Path

import gymnasium as gym
import numpy as np
import torch

from as2w_robot_lab.env_cfg import UnitreeAS2WFlatEnvCfg
from as2w_robot_lab.audit import audit_environment
from single_gpu import verify_evaluation_device


def profiles():
    result = [("stand", "站立", (0.0, 0.0, 0.0))]
    for axis, directions, speeds in (
        (0, (("forward", "前进", 1), ("backward", "后退", -1)), (.1, .3, .5, .8, 1.0)),
        (1, (("left", "左横移", 1), ("right", "右横移", -1)), (.1, .2, .3, .5, .8)),
        (2, (("turn_left", "左转", 1), ("turn_right", "右转", -1)), (.2, .5, .8, 1.0)),
    ):
        for name, label, sign in directions:
            for speed in speeds:
                command = [0.0, 0.0, 0.0]
                command[axis] = sign * speed
                result.append((f"{name}_{speed:.2f}", f"{label} {speed:.2f}", tuple(command)))
    for sign, name, label in ((1, "arc_left", "左弧线"), (-1, "arc_right", "右弧线")):
        for speed in (.3, .5, .8):
            result.append((f"{name}_{speed:.2f}", f"{label} {speed:.2f}", (speed, 0.0, sign * speed)))
    for sign, name, label in ((1, "diagonal_left", "左斜行"), (-1, "diagonal_right", "右斜行")):
        for vx, vy in ((.3, .2), (.5, .3)):
            result.append((f"{name}_{vx:.2f}", f"{label} {vx:.2f}/{vy:.2f}", (vx, sign * vy, 0.0)))
    return result


def _quaternion(roll, pitch, yaw):
    cr, cp, cy = np.cos(np.array([roll, pitch, yaw]) / 2)
    sr, sp, sy = np.sin(np.array([roll, pitch, yaw]) / 2)
    return [cr * cp * cy + sr * sp * sy, sr * cp * cy - cr * sp * sy,
            cr * sp * cy + sr * cp * sy, cr * cp * sy - sr * sp * cy]


def run_speed_sweep(args):
    if args.repeats < 1 or args.seconds <= 2:
        raise ValueError("At least one repeat and more than two movement seconds are required")
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    plan = profiles()
    cases = [(name, label, cmd, r) for name, label, cmd in plan for r in range(args.repeats)]
    policy_path = args.policy.resolve()
    metadata = json.loads(policy_path.with_suffix(".json").read_text())
    contract_path = Path(metadata["checkpoint"]).parent / "as2w_contract.json"
    trained = json.loads(contract_path.read_text())
    cfg = UnitreeAS2WFlatEnvCfg()
    cfg.scene.num_envs = len(cases)
    cfg.sim.device = args.device
    cfg.seed = 42
    cfg.observations.policy.enable_corruption = False
    cfg.scene.contact_forces.history_length = cfg.decimation
    for name in list(vars(cfg.events)):
        if not name.startswith("_") and name not in {"randomize_reset_base", "randomize_reset_joints"}:
            setattr(cfg.events, name, None)
    cfg.events.randomize_reset_base.params["pose_range"] = {k: (0.0, 0.0) for k in ("x", "y", "z", "roll", "pitch", "yaw")}
    cfg.events.randomize_reset_base.params["velocity_range"] = {k: (0.0, 0.0) for k in ("x", "y", "z", "roll", "pitch", "yaw")}
    for name in list(vars(cfg.terminations)):
        if not name.startswith("_"):
            setattr(cfg.terminations, name, None)
    cfg.commands.base_velocity.heading_command = False
    cfg.commands.base_velocity.rel_heading_envs = 0.0
    cfg.commands.base_velocity.rel_standing_envs = 0.0
    cfg.commands.base_velocity.debug_vis = False
    env = gym.make("RobotLab-Isaac-Velocity-Flat-Unitree-AS2W-v0", cfg=cfg)
    raw = env.unwrapped
    try:
        audit = audit_environment(raw, output, evaluation=True)
        assert trained["contract"] == audit["contract"], "Frozen actor / AS2W body contract mismatch"
        policy = torch.jit.load(str(policy_path), map_location=raw.device).eval()
        verify_evaluation_device(raw, policy, output, "initialized")
        env.reset()
        robot = raw.scene["robot"]
        contact = raw.scene["contact_forces"]
        nonwheel_ids = [i for i, n in enumerate(contact.body_names) if not n.endswith("_foot")]
        wheel_ids = [i for i, n in enumerate(contact.body_names) if n.endswith("_foot")]
        assert len(wheel_ids) == 4 and nonwheel_ids
        root = robot.data.default_root_state.clone()
        root[:, :3] += raw.scene.env_origins
        root[:, 7:] = 0
        q = robot.data.default_joint_pos.clone()
        leg_ids = robot.find_joints(raw.cfg.leg_joint_names, preserve_order=True)[0]
        initial_conditions = []
        for repeat in range(args.repeats):
            rng = np.random.default_rng(81200 + repeat)
            rpy = [0.0, 0.0, 0.0] if repeat == 0 else [*rng.uniform(-math.radians(.25), math.radians(.25), 2), rng.uniform(-math.pi, math.pi)]
            delta = np.zeros(12) if repeat == 0 else rng.uniform(-.005, .005, 12)
            condition = {"repeat": repeat, "seed": 81200 + repeat, "root_rpy_rad": list(rpy), "leg_position_delta_rad": delta.tolist()}
            initial_conditions.append(condition)
            indices = torch.arange(repeat, len(cases), args.repeats, device=raw.device)
            root[indices, 3:7] = torch.tensor(_quaternion(*rpy), device=raw.device, dtype=root.dtype)
            q[indices[:, None], torch.tensor(leg_ids, device=raw.device)[None, :]] += torch.tensor(delta, device=raw.device, dtype=q.dtype)
        robot.write_root_state_to_sim(root)
        robot.write_joint_state_to_sim(q, torch.zeros_like(q))
        raw.scene.write_data_to_sim()
        raw.sim.forward()
        raw.scene.update(raw.physics_dt)
        commands = torch.tensor([case[2] for case in cases], device=raw.device, dtype=torch.float32)
        command_term = raw.command_manager.get_term("base_velocity")
        settle, moving, stopping = 2.0, args.seconds, 2.0
        total = settle + moving + stopping
        dt = raw.step_dt
        keys = ("command", "position", "quaternion", "joint_pos", "velocity_body", "angular_velocity_body", "tilt", "nonwheel_force_peak", "wheel_support_count", "action")
        collected = {key: [] for key in keys}
        times = []
        with torch.inference_mode():
            for step in range(round(total / dt)):
                t = step * dt
                command = commands if settle <= t < settle + moving else torch.zeros_like(commands)
                command_term.vel_command_b.copy_(command)
                obs = raw.observation_manager.compute()["policy"]
                action = policy(obs)
                if not torch.isfinite(action).all():
                    raise RuntimeError("Nonfinite frozen actor action")
                _, _, terminated, truncated, _ = env.step(action)
                if terminated.any() or truncated.any():
                    raise RuntimeError("An evaluation episode auto-reset")
                position = robot.data.root_pos_w - raw.scene.env_origins
                tilt = torch.acos(torch.clamp(-robot.data.projected_gravity_b[:, 2], -1, 1))
                history = torch.linalg.vector_norm(contact.data.net_forces_w_history[:, :, nonwheel_ids, :], dim=-1)
                peak = history.amax(dim=(1, 2))
                support = (torch.linalg.vector_norm(contact.data.net_forces_w[:, wheel_ids, :], dim=-1) > 5).sum(dim=1)
                values = (command, position, robot.data.root_quat_w, robot.data.joint_pos,
                          robot.data.root_lin_vel_b, robot.data.root_ang_vel_b, tilt, peak, support, action)
                for key, value in zip(keys, values):
                    collected[key].append(value.cpu().numpy().copy())
                times.append((step + 1) * dt)
                if step % 100 == 0:
                    print(f"[SpeedSweep] {step}/{round(total / dt)} steps, {len(cases)} frozen-actor cases", flush=True)
        arrays = {key: np.asarray(value) for key, value in collected.items()}
        arrays["time"] = np.asarray(times)
        if not all(np.isfinite(value).all() for value in arrays.values()):
            raise RuntimeError("Nonfinite evaluation trajectory")
        np.savez_compressed(output / "trajectory.npz", **arrays)
        steady = (arrays["time"] > settle + 2) & (arrays["time"] <= settle + moving)
        stop_mask = arrays["time"] > total - 1
        assert steady.any() and stop_mask.any()
        results = {}
        for index, (name, label, command, repeat) in enumerate(cases):
            cmd = np.array(command)
            actual = np.column_stack((arrays["velocity_body"][:, index, :2], arrays["angular_velocity_body"][:, index, 2]))
            mean = actual[steady].mean(axis=0)
            mae = np.abs(actual[steady] - cmd).mean(axis=0)
            failed = (arrays["position"][:, index, 2] < .20) | (arrays["tilt"][:, index] > math.pi / 3)
            thresholds = np.array([max(.03, .2 * abs(cmd[i])) if cmd[i] else .05 for i in range(2)] + [max(.05, .2 * abs(cmd[2])) if cmd[2] else .10])
            stop_xy = np.linalg.norm(actual[stop_mask, :2], axis=1).mean()
            stop_wz = np.abs(actual[stop_mask, 2]).mean()
            min_height = arrays["position"][steady, index, 2].min()
            max_tilt = np.degrees(arrays["tilt"][steady, index]).max()
            nonwheel_peak = arrays["nonwheel_force_peak"][:, index].max()
            velocity_pass = not failed.any() and bool(np.all(mae <= thresholds))
            stop_pass = not failed.any() and stop_xy <= .1 and stop_wz <= .15
            posture_pass = min_height >= .28 and max_tilt <= 25
            contact_pass = nonwheel_peak < 50
            results[f"{name}__r{repeat}"] = {
                "profile": name, "label": label, "repeat": repeat, "command": list(command),
                "mean_actual_vx_vy_wz": mean.tolist(), "mae_vx_vy_wz": mae.tolist(),
                "rmse_vx_vy_wz": np.sqrt(((actual[steady] - cmd) ** 2).mean(axis=0)).tolist(),
                "first_failure_seconds": float(arrays["time"][np.flatnonzero(failed)[0]]) if failed.any() else None,
                "min_base_height_m": float(arrays["position"][:, index, 2].min()),
                "moving_min_height_m": float(min_height), "moving_mean_height_m": float(arrays["position"][steady, index, 2].mean()),
                "max_tilt_deg": float(np.degrees(arrays["tilt"][:, index]).max()), "moving_max_tilt_deg": float(max_tilt),
                "nonwheel_contact_peak_N": float(nonwheel_peak),
                "stop_mean_xy_speed_m_s": float(stop_xy), "stop_mean_abs_yaw_rate_rad_s": float(stop_wz),
                "velocity_pass": bool(velocity_pass), "stop_pass": bool(stop_pass), "posture_pass": bool(posture_pass), "contact_pass": bool(contact_pass),
                "fully_qualified": bool(velocity_pass and stop_pass and posture_pass and contact_pass),
            }
        aggregates = {}
        for name, label, command in plan:
            records = [v for v in results.values() if v["profile"] == name]
            aggregates[name] = {"label": label, "command": list(command), "samples": len(records),
                "mean_actual_vx_vy_wz": np.mean([r["mean_actual_vx_vy_wz"] for r in records], axis=0).tolist(),
                "mae_vx_vy_wz": np.mean([r["mae_vx_vy_wz"] for r in records], axis=0).tolist(),
                "mean_moving_height_m": float(np.mean([r["moving_mean_height_m"] for r in records])),
                "worst_min_height_m": min(r["min_base_height_m"] for r in records),
                "worst_tilt_deg": max(r["max_tilt_deg"] for r in records),
                "max_nonwheel_contact_N": max(r["nonwheel_contact_peak_N"] for r in records),
                **{key: sum(r[key] for r in records) for key in ("velocity_pass", "stop_pass", "posture_pass", "contact_pass", "fully_qualified")},
                "survived": sum(r["first_failure_seconds"] is None for r in records)}
        result = {"profiles": results, "aggregates": aggregates, "num_profiles": len(plan), "num_cases": len(cases),
            "joint_names": robot.joint_names, "policy_path": str(policy_path), "policy_sha256": hashlib.sha256(policy_path.read_bytes()).hexdigest(),
            "checkpoint_metadata": metadata, "physics_dt": cfg.sim.dt, "policy_dt": dt,
            "schedule_seconds": {"settle": settle, "move": moving, "stop": stopping, "steady_window": [settle + 2, settle + moving], "stop_window": [total - 1, total]},
            "initial_conditions": initial_conditions,
            "criteria": {"fall": "any height <.20 m or tilt >60 deg over entire rollout", "velocity": "per-axis MAE <=max(.03 m/s,20% command) for commanded translation; <=.05 m/s on zero translation axes; yaw <=max(.05 rad/s,20% command), zero-yaw <=.10 rad/s; no fall", "stop": "last-second mean horizontal speed <=.1 m/s and mean absolute yaw rate <=.15 rad/s; no fall", "posture": "moving steady-window height >=.28 m and tilt <=25 deg", "contact": "all-rollout peak nonwheel net contact force <50 N, using a full four-physics-step sensor history"},
            "scope": "Native PhysX frozen deterministic Actor only. Flat nominal AS2W mass/PD; no dynamics randomization, observation noise, pushes, prior, teacher, hand-coded motion takeover, or auto-reset. Repeat0 nominal, remaining fixed small-pose perturbations and random headings; not a broad robustness study."}
        (output / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
        flat_rows = [{"case": name, **{k: v for k, v in record.items() if not isinstance(v, (list, dict))}, **{f"command_{axis}": record["command"][i] for i, axis in enumerate(("vx", "vy", "wz"))}, **{f"actual_{axis}": record["mean_actual_vx_vy_wz"][i] for i, axis in enumerate(("vx", "vy", "wz"))}} for name, record in results.items()]
        with (output / "cases.csv").open("w") as f:
            writer = csv.DictWriter(f, fieldnames=list(flat_rows[0]))
            writer.writeheader(); writer.writerows(flat_rows)
        verify_evaluation_device(raw, policy, output, "completed")
        print(json.dumps({"profiles": len(plan), "cases": len(cases), "survived": sum(v["first_failure_seconds"] is None for v in results.values()), "velocity_pass": sum(v["velocity_pass"] for v in results.values()), "fully_qualified": sum(v["fully_qualified"] for v in results.values())}), flush=True)
    finally:
        env.close()
