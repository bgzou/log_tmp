"""AS2W task registration. Import only after AppLauncher has started Isaac Sim."""
import gymnasium as gym

for terrain in ("Flat", "Rough"):
    gym.register(
        id=f"RobotLab-Isaac-Velocity-{terrain}-Unitree-AS2W-v0",
        entry_point="isaaclab.envs:ManagerBasedRLEnv",
        disable_env_checker=True,
        kwargs={
            "env_cfg_entry_point": f"{__name__}.env_cfg:UnitreeAS2W{terrain}EnvCfg",
            "rsl_rl_cfg_entry_point": f"{__name__}.env_cfg:UnitreeAS2W{terrain}PPORunnerCfg",
        },
    )
