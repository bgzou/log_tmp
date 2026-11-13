"""Experiment E: FixProne pre-pose transition probe (crouch -> prone) in MuJoCo.

Simulates the planned A-button: from the settled real Y-crouch, PD-position
interpolate all 12 leg joints to the deployment pre-pose over ~6 s, wheels
held at their start angle. Records contact peaks, final pose, height.
"""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

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

import torch  # noqa: E402

bank = json.loads((ROOT / "runs/r290-three-skills/supported-getup-holdout.json").read_text())
prone = bank["prone"]
prepose_q = np.median([p["leg_q"] for p in prone], axis=0)          # policy order
print("prepose target (policy order):", np.round(prepose_q, 3).tolist())

crouch_q = np.array([-0.535, 0.549, -0.552, 0.581, 1.009, 1.011, 0.993, 1.010,
                    -2.768, -2.758, -2.755, -2.727])
crouch_quat = np.array([0.9951, 0.0027, -0.0025, 0.0985])

env = evalp.OmniEnvironment(ROOT / "assets/r237-train-root", 1, stop_training=True)

def run(seed, kp, kd, dur_s, hold_s=1.5):
    env.reset(seed=seed, options={"scene_seed": seed, "target": (0., 0., 0.)})
    m, d = env.model, env.data
    defaults = env.defaults[:12]
    lo = defaults + .90 * (env.leg_low - defaults)
    hi = defaults + .90 * (env.leg_high - defaults)
    effort = .90 * env.torque_high
    # start at settled crouch
    d.qpos[2] = 0.215
    d.qpos[3:7] = crouch_quat
    d.qpos[env.qa[:12]] = np.clip(crouch_q, env.leg_low + .02, env.leg_high - .02)
    d.qpos[env.qa[12:]] = 0.
    d.qvel[:] = 0.
    wheel_ref = d.qpos[env.qa[12:]].copy()
    evalp.mujoco.mj_forward(m, d)
    # settle 0.5 s damping
    for _ in range(400):
        d.ctrl[env.motors[:12]] = np.clip(-kd * d.qvel[env.va[:12]], -effort[:12], effort[:12])
        d.ctrl[env.motors[12:]] = np.clip(-4. * d.qvel[env.va[12:]], -12., 12.)
        evalp.mujoco.mj_step(m, d)
    q0 = d.qpos[env.qa[:12]].copy()
    h0 = float(d.qpos[2])
    # transition
    n = int(dur_s / (m.opt.timestep * 1))  # per-substep ramp
    steps = int(dur_s / m.opt.timestep)
    max_force = 0.; peak_t = 0.
    def contact_peak():
        w = np.zeros(6)
        best = 0.
        for i, c in enumerate(d.contact):
            if env.ground in c.geom:
                evalp.mujoco.mj_contactForce(m, d, i, w)
                f = abs(w[0])
                if f > best: best = f
        return best
    for s in range(steps + int(hold_s / m.opt.timestep)):
        a = min(1., s / steps)
        # smoothstep
        a = a * a * (3 - 2 * a)
        target = q0 + a * (np.clip(prepose_q, lo + .06, hi - .06) - q0)
        tau = kp * (target - d.qpos[env.qa[:12]]) - kd * d.qvel[env.va[:12]]
        d.ctrl[env.motors[:12]] = np.clip(tau, -effort[:12], effort[:12])
        tau_w = 25. * (wheel_ref - d.qpos[env.qa[12:]]) - 4. * d.qvel[env.va[12:]]
        d.ctrl[env.motors[12:]] = np.clip(tau_w, -12., 12.)
        evalp.mujoco.mj_step(m, d)
        f = contact_peak()
        if f > max_force:
            max_force, peak_t = f, s * m.opt.timestep
    qf = d.qpos[env.qa[:12]].copy()
    return dict(seed=seed, kp=kp, kd=kd, dur_s=dur_s,
                start_height=h0, end_height=float(d.qpos[2]),
                end_up=float(d.xmat[env.base, 8]),
                end_err_policy_order=[round(x, 3) for x in (qf - np.clip(prepose_q, lo + .06, hi - .06)).tolist()],
                max_contact_force_n=round(max_force, 1), peak_t_s=round(peak_t, 2),
                final_q=[round(x, 3) for x in qf.tolist()])

out = []
for seed in (11, 12, 13):
    out.append(run(seed, kp=55., kd=2., dur_s=6.))
for row in out:
    print(json.dumps(row))
Path("/tmp/opencode/as2w_s2_check/rec_deploy/fixprone_probe.json").write_text(json.dumps(out, indent=1))
