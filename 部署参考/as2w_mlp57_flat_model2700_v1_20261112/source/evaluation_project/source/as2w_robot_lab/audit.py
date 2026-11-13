"""Fail fast on robot, observation and actuator mapping errors."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

import torch

from .morphology import ROOT, JOINTS, LEG_JOINTS, WHEEL_JOINTS, load_contract, model_contract


def audit_environment(env, out: Path, *, evaluation=False):
    contract = load_contract()
    assert model_contract() == contract, "Stale or modified AS2W contract"
    robot = env.scene["robot"]
    assert set(robot.joint_names) == set(JOINTS), robot.joint_names
    assert Path(robot.cfg.spawn.asset_path).resolve() == (ROOT / "assets/as2w/source/as2w.urdf").resolve()
    actual_terms = {}
    for term_name, names in (("joint_pos", LEG_JOINTS), ("joint_vel", WHEEL_JOINTS)):
        term = env.action_manager.get_term(term_name)
        assert term._joint_names == names, (term_name, term._joint_names)
        scales = torch.as_tensor(term._scale).flatten()[:len(names)].cpu().tolist()
        actual_terms[term_name] = {"joint_names": term._joint_names, "scale": scales}
    obs = env.observation_manager.compute()
    assert obs["policy"].shape[1] == 57, obs["policy"].shape
    if env.cfg.scene.terrain.terrain_type == "plane":
        assert obs["critic"].shape[1] == 60, obs["critic"].shape
        from robot_lab.tasks.manager_based.locomotion.velocity.config.wheeled.unitree_b2w.flat_env_cfg import UnitreeB2WFlatEnvCfg
        baseline = UnitreeB2WFlatEnvCfg()
    else:
        from robot_lab.tasks.manager_based.locomotion.velocity.config.wheeled.unitree_b2w.rough_env_cfg import UnitreeB2WRoughEnvCfg
        baseline = UnitreeB2WRoughEnvCfg()
    weights = lambda cfg: {n: v.weight for n, v in vars(cfg.rewards).items() if hasattr(v, "weight")}
    assert weights(env.cfg) == weights(baseline), "Reward recipe changed"
    if not evaluation:
        for field in ("heading_command", "heading_control_stiffness", "rel_heading_envs", "rel_standing_envs", "resampling_time_range"):
            assert getattr(env.cfg.commands.base_velocity, field) == getattr(baseline.commands.base_velocity, field)
    assert vars(env.cfg.commands.base_velocity.ranges) == vars(baseline.commands.base_velocity.ranges)
    assert env.cfg.curriculum.command_levels_lin_vel is None and env.cfg.curriculum.command_levels_ang_vel is None
    nominal_mass = float(robot.data.default_mass[0].sum())
    assert abs(nominal_mass - contract["nominal_mass_kg"]) < 1e-4, nominal_mass
    actual_physics_mass = robot.root_physx_view.get_masses().sum(dim=1)
    # Wheel spin phases must not enter the 16 position-observation slots.
    from .env_cfg import ordered_leg_position_observation
    params = copy.deepcopy(env.cfg.observations.policy.joint_pos.params)
    for selector in params.values():
        selector.resolve(env.scene)
    before = ordered_leg_position_observation(env, **params)
    wheel_ids = robot.find_joints(WHEEL_JOINTS)[0]
    phase = robot.data.joint_pos[:, wheel_ids].clone()
    try:
        robot.data.joint_pos[:, wheel_ids] += 123.456
        after = ordered_leg_position_observation(env, **params)
        assert torch.equal(before, after), "Wheel spin leaked into position observation"
    finally:
        robot.data.joint_pos[:, wheel_ids] = phase
    for kind, actuator in robot.actuators.items():
        for col, name in enumerate(actuator.joint_names):
            limits = contract["joint_limits"][name]
            if not actuator.is_implicit_model:
                assert torch.allclose(actuator.effort_limit[:, col], torch.full_like(actuator.effort_limit[:, col], limits["effort"]))
                assert torch.allclose(actuator.velocity_limit[:, col], torch.full_like(actuator.velocity_limit[:, col], limits["velocity"]))
    files = [p for base in (ROOT / "source", ROOT / "scripts", ROOT / "config") for p in base.rglob("*") if p.is_file() and p.suffix in (".py", ".json", ".sh")]
    result = {
        "contract": contract, "actual_joint_order": robot.joint_names, "body_names": robot.body_names,
        "action_terms": actual_terms,
        "active_reward_weights_equal_to_B2W": weights(env.cfg),
        "nominal_runtime_mass_kg": nominal_mass,
        "randomized_physics_mass_range_kg": [float(actual_physics_mass.min()), float(actual_physics_mass.max())],
        "wheel_phase_invariance_verified": True,
        "policy_observation_shape": list(obs["policy"].shape), "critic_observation_shape": list(obs["critic"].shape),
        "num_envs": env.num_envs, "device": str(env.device), "physics_dt": env.cfg.sim.dt, "policy_dt": env.step_dt,
        "project_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        "control": "Deterministic actor mean at evaluation; sampled actor in PPO; joint-position/velocity PD only. No StraightRoll, StopStance, motion teacher or pretrained B2W weights.",
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "as2w_contract.json").write_text(json.dumps(result, indent=2) + "\n")
    with zipfile.ZipFile(out / "as2w_source_snapshot.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for p in files:
            archive.write(p, str(p.relative_to(ROOT)))
        for name in ("as2w.urdf", "manifest.json"):
            p = ROOT / "assets/as2w/source" / name
            archive.write(p, str(p.relative_to(ROOT)))
    print(f"[AS2W] Verified {env.num_envs} AS2W models; nominal mass 26 kg; policy shape {list(obs['policy'].shape)}; ordered 12+4 actions.", flush=True)
    return result
