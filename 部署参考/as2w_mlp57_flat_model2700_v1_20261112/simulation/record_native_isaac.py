"""Bounded native PhysX I/O capture; launch through run_native.py."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--workspace", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--policy", type=Path, default=PACKAGE / "model/policy.ts")
sys.path.insert(0, str(PACKAGE / "source/evaluation_project/scripts"))
from single_gpu import isolated_app_launcher, verify_evaluation_device
AppLauncher = isolated_app_launcher()
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
workspace = args.workspace.resolve()
sys.path[:0] = [str(workspace / "source"), str(workspace / "vendor/robot_lab/source/robot_lab"), str(PACKAGE / "runtime")]
app = AppLauncher(args).app

import gymnasium as gym
import numpy as np
import torch
import robot_lab.tasks
import as2w_robot_lab
from as2w_robot_lab.env_cfg import UnitreeAS2WFlatEnvCfg
from as2w_robot_lab.audit import audit_environment
from as2w_robot_lab.morphology import JOINTS
import reference


def main():
    plan = {"stand": (0,0,0), "forward": (.5,0,0), "backward": (-.5,0,0),
            "left": (0,.3,0), "right": (0,-.3,0), "turn_left": (0,0,.5),
            "turn_right": (0,0,-.5), "low_left": (0,.1,0),
            "low_turn": (0,0,.2), "forward_limit": (1,0,0)}
    cfg = UnitreeAS2WFlatEnvCfg()
    cfg.scene.num_envs = len(plan)
    cfg.sim.device = args.device
    cfg.seed = 81200
    cfg.scene.contact_forces.history_length = cfg.decimation
    cfg.observations.policy.enable_corruption = False
    for name in list(vars(cfg.events)):
        if not name.startswith("_") and name not in {"randomize_reset_base", "randomize_reset_joints"}:
            setattr(cfg.events, name, None)
    for name in list(vars(cfg.terminations)):
        if not name.startswith("_"):
            setattr(cfg.terminations, name, None)
    cfg.events.randomize_reset_base.params["pose_range"] = {k:(0.,0.) for k in ("x","y","z","roll","pitch","yaw")}
    cfg.events.randomize_reset_base.params["velocity_range"] = {k:(0.,0.) for k in ("x","y","z","roll","pitch","yaw")}
    cfg.commands.base_velocity.heading_command = False
    cfg.commands.base_velocity.rel_heading_envs = 0.
    cfg.commands.base_velocity.rel_standing_envs = 0.
    cfg.commands.base_velocity.debug_vis = False
    assert cfg.commands.base_velocity.ranges.lin_vel_x == (-1., 1.)
    env = gym.make("RobotLab-Isaac-Velocity-Flat-Unitree-AS2W-v0", cfg=cfg)
    raw = env.unwrapped
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    try:
        audit_environment(raw, out, evaluation=True)
        from isaaclab.utils.io import dump_yaml
        dump_yaml(str(out / "resolved_env.yaml"), cfg)
        policy = torch.jit.load(str(args.policy), map_location=raw.device).eval()
        verify_evaluation_device(raw, policy, out, "initialized")
        env.reset()
        robot = raw.scene["robot"]
        ids = robot.find_joints(JOINTS, preserve_order=True)[0]
        assert [robot.joint_names[i] for i in ids] == JOINTS
        contact = raw.scene["contact_forces"]
        command_term = raw.command_manager.get_term("base_velocity")
        commands = torch.tensor(list(plan.values()), dtype=torch.float32, device=raw.device)
        collected = {}
        obs_error = target_error = previous_error = 0.
        dt = float(raw.step_dt)
        def put(key, value):
            if isinstance(value, torch.Tensor):
                value = value.detach().cpu().numpy()
            collected.setdefault(key, []).append(np.array(value, copy=True))
        with torch.inference_mode():
            for step in range(600):
                t = step * dt
                command = commands if 2 <= t < 10 else torch.zeros_like(commands)
                command_term.vel_command_b.copy_(command)
                state = {"gyro_body":robot.data.root_ang_vel_b.clone(), "gravity_body":robot.data.projected_gravity_b.clone(),
                         "joint_q":robot.data.joint_pos[:, ids].clone(), "joint_dq":robot.data.joint_vel[:, ids].clone(),
                         "previous_raw_action":raw.action_manager.action.clone(), "command_body":command.clone()}
                obs = raw.observation_manager.compute()["policy"]
                assert obs.shape == (len(plan), 57)
                physical = {k:v.cpu().numpy() for k,v in state.items()}
                rebuilt = reference.observation(**physical)
                obs_error = max(obs_error, float(np.abs(rebuilt-obs.cpu().numpy()).max()))
                np.testing.assert_allclose(rebuilt, obs.cpu().numpy(), atol=2e-6, rtol=2e-6)
                action = policy(obs)
                assert torch.isfinite(action).all()
                predicted = reference.targets(action.cpu().numpy())
                for key,value in state.items():
                    put(key,value)
                put("observation",obs)
                put("raw_action",action)
                put("root_quaternion_wxyz_before",robot.data.root_quat_w)
                put("root_position_before",robot.data.root_pos_w-raw.scene.env_origins)
                put("sim_counter_before",raw._sim_step_counter)
                next_obs, _, terminated, truncated, _ = env.step(action)
                assert not terminated.any() and not truncated.any(), "Unexpected auto-reset"
                q = torch.zeros(len(plan),16,device=raw.device)
                dq = torch.zeros_like(q)
                q[:,:12] = raw.action_manager.get_term("joint_pos").processed_actions
                dq[:,12:] = raw.action_manager.get_term("joint_vel").processed_actions
                target_error = max(target_error,float(np.abs(q.cpu().numpy()-predicted["q_des"]).max()),float(np.abs(dq.cpu().numpy()-predicted["dq_des"]).max()))
                np.testing.assert_allclose(q.cpu().numpy(),predicted["q_des"],atol=2e-6,rtol=2e-6)
                np.testing.assert_allclose(dq.cpu().numpy(),predicted["dq_des"],atol=2e-6,rtol=2e-6)
                next_previous = raw.action_manager.action
                previous_error = max(previous_error,float(torch.abs(next_previous-action).max()))
                np.testing.assert_allclose(next_obs["policy"][:,-16:].cpu().numpy(),np.clip(action.cpu().numpy(),-100,100),atol=0,rtol=0)
                put("q_des",q);put("dq_des",dq)
                for key in ("kp","kd","tau_ff"):
                    put(key,predicted[key])
                put("next_previous_raw_action",next_previous)
                put("next_observation",next_obs["policy"])
                put("root_position_after",robot.data.root_pos_w-raw.scene.env_origins)
                put("root_quaternion_wxyz_after",robot.data.root_quat_w)
                put("velocity_body_after",robot.data.root_lin_vel_b)
                put("angular_velocity_body_after",robot.data.root_ang_vel_b)
                put("joint_q_after",robot.data.joint_pos[:,ids])
                put("joint_dq_after",robot.data.joint_vel[:,ids])
                put("applied_torque_after",robot.data.applied_torque[:,ids])
                put("contact_force_history_after",contact.data.net_forces_w_history)
                put("sim_counter_after",raw._sim_step_counter)
                put("control_time",t);put("state_time_after",(step+1)*dt)
                if step % 100 == 0:
                    print(f"[HandoffReplay] {step}/600; obs max {obs_error:.3g}; target max {target_error:.3g}",flush=True)
        arrays={k:np.asarray(v) for k,v in collected.items()}
        assert all(np.isfinite(v).all() for v in arrays.values())
        assert np.array_equal(arrays["previous_raw_action"][1:],arrays["raw_action"][:-1])
        assert np.all(arrays["previous_raw_action"][0]==0)
        target = out / "native_samples.npz"
        np.savez_compressed(target,**arrays)
        record={"profiles":plan,"frames":600,"cases":len(plan),"policy_dt":dt,"physics_dt":cfg.sim.dt,
                "command_schedule":"0-2 s zero; 2-10 s listed body command; 10-12 s zero",
                "joint_names":JOINTS,"contact_body_names":contact.body_names,
                "initial_base_height":float(cfg.scene.robot.init_state.pos[2]),
                "observation_reconstruction_max_abs_error":obs_error,"processed_target_max_abs_error":target_error,
                "next_previous_action_max_abs_error":previous_error,
                "policy_sha256":hashlib.sha256(args.policy.read_bytes()).hexdigest(),
                "sample_sha256":hashlib.sha256(target.read_bytes()).hexdigest(),
                "scope":"Native PhysX nominal I/O parity capture of the selected checkpoint. No observation noise, randomization, prior or auto-reset. Not a second simulator acceptance or a new 156-case qualification."}
        (out/"summary.json").write_text(json.dumps(record,indent=2)+"\n")
        verify_evaluation_device(raw,policy,out,"completed")
        print(json.dumps(record,indent=2),flush=True)
    finally:
        env.close()


try:
    main()
finally:
    app.close()
