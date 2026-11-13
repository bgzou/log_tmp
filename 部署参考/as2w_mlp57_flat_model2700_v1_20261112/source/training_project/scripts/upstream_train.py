#!/usr/bin/env python3
"""Run unchanged upstream train.py with a narrow RSL config compatibility shim."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import sys

import torch

# Select CUDA's current device before any simulator or policy construction.
# --device by itself configures Isaac Lab, not the separate RSL agent config.
if "--distributed" in sys.argv:
    raise ValueError("AS2W training requires simulation and PPO on one GPU")
if "--device" in sys.argv:
    selected_device = torch.device(sys.argv[sys.argv.index("--device") + 1])
    if selected_device.type == "cuda":
        torch.cuda.set_device(selected_device)

from rsl_rl.runners import OnPolicyRunner
import rsl_rl.runners

ROOT = Path(__file__).resolve().parents[1]


class CompatibleRunner(OnPolicyRunner):
    def __init__(self, env, train_cfg, log_dir=None, device="cpu"):
        cfg = copy.deepcopy(train_cfg)
        expected_device = torch.device(os.environ.get("AS2W_EXPECTED_DEVICE", env.device))
        if torch.device(env.device) != expected_device or torch.device(device) != expected_device:
            raise RuntimeError(f"AS2W single-GPU contract violated: physics={env.device}, PPO={device}, expected={expected_device}")
        if torch.device(cfg["device"]) != expected_device:
            raise RuntimeError(f"Agent config device {cfg['device']} differs from {expected_device}")
        removed = {}
        # The local Isaac Lab checkout exposes fields introduced after RSL 3.3.
        # RSL 3.3 already uses Adam and no shared CNN encoder. Reject any request
        # that would silently change the intended optimizer or architecture.
        for key, expected in {"optimizer": "adam", "share_cnn_encoders": False}.items():
            if key in cfg["algorithm"]:
                value = cfg["algorithm"].pop(key)
                if value != expected:
                    raise ValueError(f"Unsupported non-default RSL compatibility field: {key}={value}")
                removed[key] = value
        if log_dir:
            Path(log_dir).mkdir(parents=True, exist_ok=True)
            (Path(log_dir) / "compatibility.json").write_text(json.dumps({"removed_default_fields": removed, "reason": "Isaac Lab config API / RSL-RL 3.3 compatibility; no reward, model or PPO hyperparameter change."}, indent=2) + "\n")
        super().__init__(env, cfg, log_dir=log_dir, device=device)
        if log_dir:
            from as2w_robot_lab.audit import audit_environment
            audit_environment(env.unwrapped, Path(log_dir))
            self._audit_devices("initialized")
        original_update = self.alg.update
        self._first_update_audited = False
        def checked_update():
            result = original_update()
            if not self._first_update_audited:
                self._audit_devices("after_first_update")
                self._first_update_audited = True
            return result
        self.alg.update = checked_update

    def _audit_devices(self, phase):
        from as2w_robot_lab.device_audit import audit_training_devices
        return audit_training_devices(self, phase)

    def load(self, path, load_optimizer=True, map_location=None):
        # Load through CPU so a checkpoint saved on cuda:0 cannot allocate a
        # context or stale optimizer storage on the old physical GPU.
        result = super().load(path, load_optimizer=load_optimizer, map_location="cpu")
        devices = self._audit_devices("resumed")
        reference = torch.load(path, weights_only=False, map_location="cpu")
        def equal_state(left, right):
            if isinstance(left, torch.Tensor):
                return isinstance(right, torch.Tensor) and torch.equal(left.detach().cpu(), right.detach().cpu())
            if isinstance(left, dict):
                return isinstance(right, dict) and left.keys() == right.keys() and all(equal_state(left[k], right[k]) for k in left)
            if isinstance(left, (list, tuple)):
                return isinstance(right, (list, tuple)) and len(left) == len(right) and all(equal_state(a, b) for a, b in zip(left, right))
            return left == right
        model_equal = equal_state(reference["model_state_dict"], self.alg.policy.state_dict())
        optimizer_equal = equal_state(reference["optimizer_state_dict"], self.alg.optimizer.state_dict()) if load_optimizer else None
        if not model_equal or (load_optimizer and not optimizer_equal):
            raise RuntimeError("Checkpoint model or optimizer did not restore exactly across GPU devices")
        # RSL 3.3 stores the zero-based index of the update just completed.
        # Start at the following update instead of repeating its label.
        saved_iteration = int(self.current_learning_iteration)
        self.current_learning_iteration = saved_iteration + 1
        steps = [float(state["step"]) for state in self.alg.optimizer.state.values() if "step" in state]
        if load_optimizer and steps:
            self.alg.learning_rate = float(self.alg.optimizer.param_groups[0]["lr"])
        resume = {
            "checkpoint": str(Path(path).resolve()),
            "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            "saved_zero_based_iteration": saved_iteration,
            "completed_updates": self.current_learning_iteration,
            "optimizer_loaded": load_optimizer,
            "device_verification": devices,
            "model_state_exactly_restored": model_equal,
            "optimizer_state_exactly_restored": optimizer_equal,
            "optimizer_step_min": min(steps) if steps else None,
            "optimizer_step_max": max(steps) if steps else None,
            "restored_learning_rate": self.alg.learning_rate,
            "note": "Model and optimizer resumed; simulator state and RNG are initialized anew by upstream training.",
        }
        (Path(self.logger.log_dir) / "resume.json").write_text(json.dumps(resume, indent=2) + "\n")
        print(f"[AS2W] Resume: {resume}", flush=True)
        return result

    def learn(self, num_learning_iterations, init_at_random_ep_len=False):
        target = int(os.environ.get("AS2W_TARGET_TOTAL_UPDATES", num_learning_iterations))
        remaining = target - self.current_learning_iteration
        if remaining <= 0:
            raise ValueError(f"Target {target} does not exceed completed updates {self.current_learning_iteration}")
        (Path(self.logger.log_dir) / "training_budget.json").write_text(json.dumps({
            "target_total_updates": target,
            "completed_updates_at_start": self.current_learning_iteration,
            "remaining_updates": remaining,
        }, indent=2) + "\n")
        print(f"[AS2W] Target {target} total updates; completed {self.current_learning_iteration}; executing {remaining} updates.", flush=True)
        super().learn(num_learning_iterations=remaining, init_at_random_ep_len=init_at_random_ep_len)
        from isaaclab_rl.rsl_rl import export_policy_as_jit
        policy = self.alg.policy
        normalizer = getattr(policy, "actor_obs_normalizer", None)
        export_policy_as_jit(policy, normalizer, str(Path(self.logger.log_dir) / "exported"))


if __name__ == "__main__":
    import isaaclab.app
    class SinglePhysicalGpuLauncher(isaaclab.app.AppLauncher):
        def _resolve_device_settings(self, launcher_args):
            super()._resolve_device_settings(launcher_args)
            if "AS2W_PHYSICAL_GPU" in os.environ:
                if torch.cuda.device_count() != 1:
                    raise RuntimeError("AS2W must expose exactly one CUDA device")
                # CUDA ordinal 0 is UUID-isolated; Vulkan retains native ordinals.
                launcher_args["active_gpu"] = int(os.environ["AS2W_PHYSICAL_GPU"])
                launcher_args["physics_gpu"] = 0
                print(f"[AS2W] Isolated CUDA 0 -> physical GPU {launcher_args['active_gpu']} ({os.environ['AS2W_PHYSICAL_GPU_UUID']}); matching Vulkan renderer.", flush=True)
    isaaclab.app.AppLauncher = SinglePhysicalGpuLauncher
    rsl_rl.runners.OnPolicyRunner = CompatibleRunner
    upstream = ROOT / "vendor/robot_lab/scripts/reinforcement_learning/rsl_rl/train.py"
    sys.path.insert(0, str(upstream.parent))
    # Register the extension after AppLauncher and before Hydra resolves tasks.
    # Upstream files remain byte-identical to the pinned manifest.
    source = upstream.read_text()
    anchor = "import robot_lab.tasks  # noqa: F401  # isort: skip"
    if source.count(anchor) != 1:
        raise RuntimeError("Pinned training entry point changed")
    source = source.replace(anchor, anchor + "\nimport as2w_robot_lab  # AS2W project task registration", 1)
    exec(compile(source, str(upstream), "exec"), {"__name__": "__main__", "__file__": str(upstream)})
