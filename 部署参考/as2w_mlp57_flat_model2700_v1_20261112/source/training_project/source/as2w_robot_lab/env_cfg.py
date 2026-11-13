"""AS2W morphology with the pinned robot_lab B2W learning recipe."""
from isaaclab.actuators import DCMotorCfg, ImplicitActuatorCfg
from isaaclab.utils import configclass
from robot_lab.assets.unitree import UNITREE_B2W_CFG
from robot_lab.tasks.manager_based.locomotion.velocity.config.wheeled.unitree_b2w.rough_env_cfg import UnitreeB2WRoughEnvCfg
from robot_lab.tasks.manager_based.locomotion.velocity.config.wheeled.unitree_b2w.agents.rsl_rl_ppo_cfg import UnitreeB2WFlatPPORunnerCfg, UnitreeB2WRoughPPORunnerCfg

from .morphology import ASSET_DIR, ROOT, LEG_JOINTS, WHEEL_JOINTS, JOINTS, load_contract

CONTRACT = load_contract()


def as2w_asset():
    cfg = UNITREE_B2W_CFG.copy()
    cfg.spawn.asset_path = str(ASSET_DIR / "as2w.urdf")
    cfg.spawn.usd_dir = str(ROOT / "outputs/as2w_usd")
    cfg.spawn.usd_file_name = "as2w.usd"
    cfg.init_state.pos = (0.0, 0.0, CONTRACT["initial_base_height_m"])
    cfg.init_state.joint_pos = CONTRACT["nominal_joint_pos_rad"].copy()
    cfg.init_state.joint_vel = {".*": 0.0}
    cfg.actuators = {}
    for kind in ("hip", "thigh", "calf"):
        names = [f"{leg}_{kind}" for leg in ("FR", "FL", "RR", "RL")]
        effort = {n: CONTRACT["joint_limits"][n]["effort"] for n in names}
        speed = {n: CONTRACT["joint_limits"][n]["velocity"] for n in names}
        assert len(set(effort.values())) == 1
        cfg.actuators[kind] = DCMotorCfg(
            joint_names_expr=names, effort_limit=effort, saturation_effort=next(iter(effort.values())),
            velocity_limit=speed, effort_limit_sim=effort, velocity_limit_sim=speed,
            stiffness=CONTRACT["motor_pd"]["leg_kp"], damping=CONTRACT["motor_pd"]["leg_kd"], friction=0.0,
        )
    cfg.actuators["wheel"] = ImplicitActuatorCfg(
        joint_names_expr=WHEEL_JOINTS,
        effort_limit_sim={n: CONTRACT["joint_limits"][n]["effort"] for n in WHEEL_JOINTS},
        velocity_limit_sim={n: CONTRACT["joint_limits"][n]["velocity"] for n in WHEEL_JOINTS},
        stiffness=CONTRACT["motor_pd"]["wheel_kp"], damping=CONTRACT["motor_pd"]["wheel_kd"], friction=0.0,
    )
    return cfg


def ordered_leg_position_observation(env, asset_cfg, wheel_asset_cfg):
    """Keep 16 slots with wheel phases zeroed, independent of PhysX joint order."""
    robot = env.scene[asset_cfg.name]
    value = robot.data.joint_pos[:, asset_cfg.joint_ids] - robot.data.default_joint_pos[:, asset_cfg.joint_ids]
    ids = list(range(len(robot.joint_names)))
    selected = ids[asset_cfg.joint_ids] if isinstance(asset_cfg.joint_ids, slice) else asset_cfg.joint_ids
    wheels = ids[wheel_asset_cfg.joint_ids] if isinstance(wheel_asset_cfg.joint_ids, slice) else wheel_asset_cfg.joint_ids
    ordered = [robot.joint_names[i] for i in selected]
    wheel_names = {robot.joint_names[i] for i in wheels}
    value[:, [i for i, n in enumerate(ordered) if n in wheel_names]] = 0
    return value


@configclass
class UnitreeAS2WRoughEnvCfg(UnitreeB2WRoughEnvCfg):
    leg_joint_names = LEG_JOINTS
    wheel_joint_names = WHEEL_JOINTS
    joint_names = JOINTS

    def __post_init__(self):
        super().__post_init__()
        self.scene.robot = as2w_asset().replace(prim_path="{ENV_REGEX_NS}/Robot")
        for group in (self.observations.policy, self.observations.critic):
            group.joint_pos.func = ordered_leg_position_observation
        # AS2W has no '_joint' suffix. All other selectors use self.* names in
        # the inherited recipe and already refer to the AS2W names above.
        self.actions.joint_pos.scale = {".*_hip": 0.125, "^(?!.*_hip).*": 0.25}
        self.rewards.joint_mirror.params["mirror_joints"] = [
            ["FR_(hip|thigh|calf)", "RL_(hip|thigh|calf)"],
            ["FL_(hip|thigh|calf)", "RR_(hip|thigh|calf)"],
        ]
        # These height terms remain inactive, as in the original B2W recipe.
        self.rewards.base_height_l2.params["target_height"] = CONTRACT["initial_base_height_m"] - CONTRACT["initial_clearance_m"]
        self.rewards.feet_height_body.params["target_height"] = next(iter(CONTRACT["wheels"].values()))["center_in_base_m"][2]
        self.disable_zero_weight_rewards()


@configclass
class UnitreeAS2WFlatEnvCfg(UnitreeAS2WRoughEnvCfg):
    def __post_init__(self):
        super().__post_init__()
        self.scene.terrain.terrain_type = "plane"
        self.scene.terrain.terrain_generator = None
        self.scene.height_scanner = None
        self.observations.policy.height_scan = None
        self.observations.critic.height_scan = None
        self.curriculum.terrain_levels = None


@configclass
class UnitreeAS2WRoughPPORunnerCfg(UnitreeB2WRoughPPORunnerCfg):
    experiment_name = "unitree_as2w_rough"


@configclass
class UnitreeAS2WFlatPPORunnerCfg(UnitreeB2WFlatPPORunnerCfg):
    def __post_init__(self):
        super().__post_init__()
        self.experiment_name = "unitree_as2w_flat"
