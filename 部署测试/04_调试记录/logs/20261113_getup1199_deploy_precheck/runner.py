"""Deployment pre-check for AS2-W recovery (deep-side model_1199).

Runs the patched MuJoCo recovery evaluator with configurable start poses:
- bank_prone : first 8 heldout bank prone poses (training distribution)
- prepose    : fixed deployment pre-pose (median of bank) + perturbations
- crouch     : the real robot's post-Y pose from field logs + perturbations

Ablations: predictive guard on/off, effort 0.90/0.80, start clip safety/urdf.
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch

W = Path("/home/caolin/as2w_workstation")
BACK = W / "部署参考/Rob2Nav-as2w-backup/training/as2w-backup"
ROOT = BACK / "as2w-current"
DEP = BACK / "as2w-r284-release/deliveries/as2w-deploy"
sys.path.insert(0, str(ROOT / "code"))
for p in (DEP / "flat-r284-500-preview/runtime", DEP / "omni-blind-stairs-r152/runtime", DEP):
    sys.path.append(str(p))

spec = importlib.util.spec_from_file_location(
    "evalp", "/tmp/opencode/as2w_s2_check/rec_deploy/eval_recovery_patched.py")
evalp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evalp)

CKPT = ROOT / "runs/recovery/deep-side-curriculum/formal/model_1199.pt"
BANK = ROOT / "runs/r290-three-skills/supported-getup-holdout.json"

GUARD = os.environ.get("A_GUARD", "1") == "1"
POSE_SET = os.environ.get("A_POSE_SET", "bank_prone")
OUT = Path(os.environ["A_OUT"])
OUT.mkdir(parents=True, exist_ok=True)
N_SEED = int(os.environ.get("A_SEEDS", "5"))

torch.set_num_threads(1)
state = torch.load(CKPT, map_location="cpu", weights_only=True)
actor = evalp.actor_from_state(state["actor_state_dict"], 2.0)
env = evalp.OmniEnvironment(ROOT / "assets/r237-train-root", 1, stop_training=True)

bank = json.loads(BANK.read_text())
prone = bank["prone"]

# ---- real crouch pose from field log (20261113-114335_r4000 tail, policy order) ----
crouch_q = np.array([-0.535, 0.549, -0.552, 0.581,   # FL FR RL RR hip (policy sign)
                     1.009, 1.011, 0.993, 1.010,    # thighs
                     -2.768, -2.758, -2.755, -2.727])  # calves
crouch_quat = np.array([0.9951, 0.0027, -0.0025, 0.0985])  # wxyz, level, yaw~11deg

from prepare_as2w_supported_getup import quaternion  # noqa: E402

# ---- crouch height probe: settle with damping only ----
def probe_height(leg_q, quat):
    env.reset(seed=99, options={"scene_seed": 99, "target": (0., 0., 0.)})
    m, d = env.model, env.data
    d.qpos[2] = 0.30
    d.qpos[3:7] = quat
    d.qpos[env.qa[:12]] = np.clip(leg_q, env.leg_low + .02, env.leg_high - .02)
    d.qpos[env.qa[12:]] = 0.
    d.qvel[:] = 0.
    evalp.mujoco.mj_forward(m, d)
    for _ in range(400):  # 0.5 s at 1.25ms, damping only
        tau = -3.2 * d.qvel[env.va[:12]]
        tau = np.clip(tau, -12., 12.)
        d.ctrl[env.motors[:12]] = tau
        d.ctrl[env.motors[12:]] = np.clip(-4. * d.qvel[env.va[12:]], -12., 12.)
        evalp.mujoco.mj_step(m, d)
    return float(d.qpos[2]), float(d.xmat[env.base, 8])

if POSE_SET == "crouch_probe":
    h, up = probe_height(crouch_q, crouch_quat)
    print(json.dumps({"settled_height_m": h, "up_z": up}))
    sys.exit(0)

H_CROUCH = float(os.environ.get("A_CROUCH_H", "0")) or None
if POSE_SET.startswith("crouch") and H_CROUCH is None:
    H_CROUCH, _ = probe_height(crouch_q, crouch_quat)

# ---- build start sets ----
def perturbed(leg_q, height, quat, rng, n, leg_noise=.04, h_noise=.01, tilt=.05):
    starts = []
    for _ in range(n):
        q = np.asarray(leg_q, float) + rng.normal(0., leg_noise, 12)
        h = height + rng.uniform(-h_noise, h_noise)
        roll = rng.uniform(-tilt, tilt)
        pitch = rng.uniform(-tilt, tilt)
        starts.append(dict(height_m=float(h),
                           root_wxyz=quaternion(roll, pitch).tolist()
                           if hasattr(quaternion(roll, pitch), "tolist")
                           else list(map(float, quaternion(roll, pitch))),
                           leg_q=q.tolist()))
    return starts

rng = np.random.default_rng(20261113)
starts = []
if POSE_SET == "bank_prone":
    starts = [dict(height_m=p["height_m"], root_wxyz=p["root_wxyz"], leg_q=p["leg_q"])
              for p in prone[:8]]
    labels = [f"bank{i}" for i in range(8)]
elif POSE_SET == "prepose":
    # deployment pre-pose target: per-joint median of the heldout bank
    med_q = np.median([p["leg_q"] for p in prone], axis=0)
    med_h = float(np.median([p["height_m"] for p in prone]))
    print("prepose nominal:", np.round(med_q, 3).tolist(), "h=", med_h)
    starts = perturbed(med_q, med_h, quaternion(0., 0.), rng, 8, leg_noise=.05)
    labels = [f"pp{i}" for i in range(8)]
elif POSE_SET.startswith("crouch"):
    starts = perturbed(crouch_q, H_CROUCH, crouch_quat, rng, 8, leg_noise=.03)
    labels = [f"cr{i}" for i in range(8)]
else:
    raise SystemExit("unknown A_POSE_SET " + POSE_SET)

seeds = [9001 + i for i in range(N_SEED)]
result = {}
for label, st in zip(labels, starts):
    rows = []
    for sd in seeds:
        row = evalp.trial(env, actor, st, sd, [], GUARD, False, 0.02, GUARD, False, False)
        rows.append(row)
    result[label] = dict(total=len(rows), passed=sum(r["passed"] for r in rows),
                         rise_fail=sum(0 if r["survived"] else 1 for r in rows), rows=rows)

summary = {k: (v["passed"], v["total"], v["rise_fail"]) for k, v in result.items()}
(OUT / "diagnostic.json").write_text(json.dumps(result, indent=1))
print(json.dumps(dict(config=dict(pose=POSE_SET, guard=GUARD,
                                  effort=evalp.EFFORT_FRACTION, clip=evalp.START_CLIP,
                                  crouch_h=H_CROUCH),
                       summary=summary)))
agg_pass = sum(v["passed"] for v in result.values())
agg_tot = sum(v["total"] for v in result.values())
agg_rise = sum(v["rise_fail"] for v in result.values())
print(f"AGG pass={agg_pass}/{agg_tot} rise_fail={agg_rise}")
