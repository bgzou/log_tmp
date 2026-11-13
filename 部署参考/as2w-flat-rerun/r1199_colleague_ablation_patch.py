"""Generate a controlled local variant of the colleague's R1199 evaluator.

The source snapshot remains untouched.  Changes are limited to:
1. Ignore the unused stair_rise keyword on flat ground (runtime API drift).
2. Optionally replay the measured FixedStand joint/pitch initial condition.
3. Select one seed and forward-only case for paired comparisons.
"""
import sys
from pathlib import Path


src = Path(sys.argv[1])
dst = Path(sys.argv[2])
s = src.read_text()


def replace_once(old: str, new: str) -> None:
    global s
    assert s.count(old) == 1, (old, s.count(old))
    s = s.replace(old, new)


replace_once("import json\n", "import json\nimport os\n")
replace_once(
    "    env.apply_motion_prior = False\n",
    """    if os.environ.get("R1199_MEASURED_START") == "1":
        # Contract joint order equals the measured sequence used in the
        # independent rerun.  Pitch is from the robot's FixedStand LowState.
        measured = np.array([
            -.221, .217, -.270, .264,
            .746, .743, .708, .713,
            -1.720, -1.731, -1.863, -1.869,
            0., 0., 0., 0.,
        ])
        d = env.data
        d.qpos[env.qa] = measured
        pitch = np.deg2rad(-5.498)
        d.qpos[3:7] = [np.cos(pitch / 2.), 0., np.sin(pitch / 2.), 0.]
        d.qvel[:] = 0.
        low, high = .05, .60
        for _ in range(18):
            mid = (low + high) / 2.
            d.qpos[2] = mid
            mujoco.mj_forward(env.model, d)
            if d.ncon and min(c.dist for c in d.contact) <= 0.:
                low = mid
            else:
                high = mid
        d.qpos[2] = high + .002
        mujoco.mj_forward(env.model, d)
        obs = env.observe()
    print("COMPARE_INITIAL", seed, name,
          "measured", os.environ.get("R1199_MEASURED_START") == "1",
          "height", float(env.data.qpos[2]),
          "pitch", float(np.arcsin(-env.data.xmat[env.base, 6])),
          "q", env.data.qpos[env.qa[:12]].tolist(), flush=True)
    env.apply_motion_prior = False
""",
)
replace_once(
    "    if args.acceptance:\n        cases.update(arc_left=(.07,0.,.20),arc_right=(.07,0.,-.20))\n",
    """    if os.environ.get("R1199_COMPARE_FORWARD_ONLY") == "1":
        cases = {"forward": (args.speed, 0., 0.)}
    if os.environ.get("R1199_COMPARE_SEED"):
        seeds = (int(os.environ["R1199_COMPARE_SEED"]),)
    if args.acceptance:
        cases.update(arc_left=(.07,0.,.20),arc_right=(.07,0.,-.20))
""",
)
replace_once(
    "    else:\n        seeds = (46001,46002,47001,47002)\n    if args.vy_diagnostic:",
    "    else:\n        seeds = (46001,46002,47001,47002)\n    if os.environ.get(\"R1199_COMPARE_SEED\"):\n        seeds = (int(os.environ[\"R1199_COMPARE_SEED\"]),)\n    if os.environ.get(\"R1199_COMPARE_FORWARD_ONLY\") == \"1\":\n        cases = {\"forward\": (args.speed, 0., 0.)}\n    if args.vy_diagnostic:",
)
replace_once("    trace = []\n", "    trace = []\n    compare_trace = []\n")
replace_once(
    "        if done:\n            break\n    if trace:\n",
    """        if os.environ.get("R1199_COMPARE_TRACE") == "1" and start <= elapsed < release:
            compare_trace.append(dict(
                t_s=float(elapsed-start),
                q_actual_rad=q.tolist(),
                q_target_rad=env.data.ctrl[env.motors[:12]].tolist() if args.native_pd else (env.defaults[:12]+.35*applied[:12]).tolist(),
                wheel_dq_actual_rad_s=env.data.qvel[env.va[12:]].tolist(),
                wheel_dq_target_rad_s=env.data.ctrl[env.motors[12:]].tolist() if args.native_pd else (16.*applied[12:]).tolist(),
                pitch_rad=float(np.arctan2(-rotation[2,0],rotation[2,2])),
                wheel_load_n=loads.tolist(),
                obs_65=frame.tolist(),
                wrapped_action=current.tolist(),
            ))
        if done:
            break
    if compare_trace:
        (args.output/"compare-forward-trace.json").write_text(json.dumps(compare_trace)+"\\n")
    if trace:
""",
)
dst.write_text(s if s.endswith("\n") else s + "\n")
