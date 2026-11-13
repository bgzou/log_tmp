"""Independent AS2-W MuJoCo rehearsal for rolling-fixed-exit-preview.

This is an offline diagnostic only.  It reproduces the delivery's 65-wide
observation, rolling_fixed_exit action wrapper, pre-calibrated fixed-stand
compensation and wheel hold, then exercises the project FSM route:

    prone -> FixStand -> centered policy entry -> command -> brake ->
    policy exit -> fixed stand

No DDS or hardware interface is imported or used.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
from as2w_mujoco_pd import configure_native_pd


if len(sys.argv) != 5:
    raise SystemExit(
        "usage: rolling_fixed_exit_rehearsal.py ASSETS RUNTIME ONNX OUT.json"
    )

ASSETS, RUNTIME, ONNX, OUT = map(Path, sys.argv[1:])
sys.path.insert(0, str(RUNTIME.resolve()))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import r214_fsm_rehearsal as prior  # noqa: E402


mj = prior.mj
DT = 0.02
SIDE = np.array([1.0, -1.0, 1.0, -1.0])
COMMANDS = {
    "static": np.array([0.0, 0.0, 0.0]),
    "forward": np.array([0.30, 0.0, 0.0]),
    "back": np.array([-0.30, 0.0, 0.0]),
    "turn_left": np.array([0.0, 0.0, 0.30]),
    "turn_right": np.array([0.0, 0.0, -0.30]),
    "arc_left": np.array([0.07, 0.0, 0.20]),
    "arc_right": np.array([0.07, 0.0, -0.20]),
    "vy_probe_0.10": np.array([0.0, 0.10, 0.0]),
}
MEASURED_FIXED_Q = np.array([
    -0.221, 0.217, -0.270, 0.264,
    0.746, 0.743, 0.708, 0.713,
    -1.720, -1.731, -1.863, -1.869,
    0.0, 0.0, 0.0, 0.0,
])
MEASURED_FIXED_PITCH_RAD = np.deg2rad(-5.498)


def run_case(seed: int, scenario: str, requested_command: np.ndarray) -> dict:
    base_scenario = scenario.removeprefix("measured_")
    measured_start = scenario.startswith("measured_")
    rng = np.random.default_rng(seed)
    model = prior.sim.load_flat_model(True, True, seed=0)
    data = mj.MjData(model)
    joints = [model.joint(name) for name in prior.NAMES]
    qa = np.array([joint.qposadr[0] for joint in joints])
    va = np.array([joint.dofadr[0] for joint in joints])
    motors = np.array([model.actuator(name).id for name in prior.NAMES])
    native_pd = os.environ.get("R1199_NATIVE_PD") == "1"
    effort_limits = np.max(np.abs(model.actuator_ctrlrange[motors]), axis=1).copy()
    if native_pd:
        configure_native_pd(
            model, motors, np.r_[np.full(12, 55.0), np.zeros(4)],
            np.full(16, 2.0), np.r_[prior.LIMITS_LO[:12], np.full(4, -98.47)],
            np.r_[prior.LIMITS_HI[:12], np.full(4, 98.47)], effort_limits,
            velocity_axes=4,
        )
    wheel_bodies = {model.body(name).id for name in prior.NAMES[12:]}
    base = model.body("base_link").id
    ground = model.geom("ground").id
    stressed = base_scenario not in ("static", "vy_probe_0.10")
    stress = prior.sim.sample_dynamics_stress(seed, model.nbody - 1, len(prior.NAMES))
    model.geom_friction[ground, 0] = float(os.environ.get(
        "R1199_FRICTION_OVERRIDE",
        stress.friction if stressed else rng.uniform(0.55, 0.85),
    ))
    nominal_dynamics = os.environ.get("R1199_NOMINAL_DYNAMICS") == "1"
    if stressed and not nominal_dynamics:
        model.body_mass[1:] *= stress.mass_scale
        model.body_inertia[1:] *= stress.mass_scale[:, None]
        mj.mj_setConst(model, data)
    substeps = round(DT / model.opt.timestep)
    force = np.zeros(6)

    if measured_start:
        data.qpos[qa] = MEASURED_FIXED_Q
        half_pitch = MEASURED_FIXED_PITCH_RAD / 2.0
        data.qpos[3:7] = [np.cos(half_pitch), 0.0, np.sin(half_pitch), 0.0]
    else:
        data.qpos[qa] = prior.PRONE + rng.uniform(-0.02, 0.02, 16)
    low, high = 0.05, 0.60
    for _ in range(18):
        mid = (low + high) / 2
        data.qpos[2] = mid
        mj.mj_forward(model, data)
        if data.ncon and min(contact.dist for contact in data.contact) <= 0:
            low = mid
        else:
            high = mid
    data.qpos[2] = high + 0.002
    mj.mj_forward(model, data)

    session = prior.session_for(ONNX)
    inputs = [(item.name, item.shape) for item in session.get_inputs()]
    outputs = [(item.name, item.shape) for item in session.get_outputs()]
    if inputs != [("obs", [1, 65])] or outputs != [("actions", [1, 16])]:
        raise RuntimeError(f"rolling ONNX contract mismatch: {inputs=} {outputs=}")

    previous_action = np.zeros(16)
    phase_seconds = 0.0
    policy_age = 0.0
    stand_bias = np.zeros(12)
    hold_reference = np.zeros(4)
    hold_frames = np.zeros(1, dtype=np.int64)
    observation_reference = None
    last_command = (data.qpos[qa[:12]].copy(), np.zeros(4), 0.0, 3.0)
    last_policy_observation = None
    last_policy_action = None
    phases = []
    command_effect = []
    transition_target_jumps = []
    last_step_nonwheel = 0.0
    trace_path = os.environ.get("ROLLING_CONTACT_TRACE")
    trace_active = False
    trace_start_s = None
    trace_physics = []
    trace_control = []
    first_touch_s = None
    applied_push_s = None

    def trace_contacts():
        nonlocal first_touch_s
        wheel_loads = {model.body(body).name: 0.0 for body in wheel_bodies}
        nonwheel = []
        for index, contact in enumerate(data.contact):
            a, b = (int(model.geom_bodyid[geom]) for geom in contact.geom)
            if a and b:
                continue
            body = a or b
            if not body:
                continue
            mj.mj_contactForce(model, data, index, force)
            load = float(force[0])
            name = model.body(body).name
            if body in wheel_bodies:
                wheel_loads[name] += load
            elif load > 1.0:
                nonwheel.append({
                    "body": name,
                    "body_id": body,
                    "geom": model.geom(contact.geom[0 if a else 1]).name,
                    "geom_id": int(contact.geom[0 if a else 1]),
                    "normal_n": load,
                })
        relative_s = float(data.time - trace_start_s)
        if nonwheel and first_touch_s is None:
            first_touch_s = relative_s
        return {"t_s": relative_s, "nonwheel": nonwheel,
                "wheel_load_n": wheel_loads,
                "qpos": data.qpos.tolist(), "qvel": data.qvel.tolist()}

    def contact_metrics():
        peak_nonwheel = 0.0
        wheel_load = dict.fromkeys(wheel_bodies, 0.0)
        for index, contact in enumerate(data.contact):
            a, b = (int(model.geom_bodyid[geom]) for geom in contact.geom)
            if a and b:
                continue
            body = a or b
            if body == 0:
                continue
            mj.mj_contactForce(model, data, index, force)
            if body in wheel_load:
                wheel_load[body] += float(force[0])
            else:
                peak_nonwheel = max(peak_nonwheel, float(force[0]))
        return peak_nonwheel, list(wheel_load.values())

    def step(leg, wheel, kp=55.0, kd=2.0):
        nonlocal last_command, last_step_nonwheel
        leg = np.clip(np.asarray(leg), prior.LIMITS_LO[:12], prior.LIMITS_HI[:12])
        wheel = np.clip(np.asarray(wheel), -98.47, 98.47)
        previous_leg = last_command[0]
        previous_wheel = last_command[1]
        transition_target_jumps.append(
            max(float(np.max(np.abs(leg - previous_leg))),
                float(np.max(np.abs(wheel - previous_wheel))) * DT)
        )
        last_command = (leg.copy(), wheel.copy(), float(kp), float(kd))
        if trace_active:
            rotation = data.xmat[base].reshape(3, 3)
            trace_control.append({
                "t_s": float(data.time - trace_start_s),
                "q_actual_rad": data.qpos[qa[:12]].tolist(),
                "q_target_rad": leg.tolist(),
                "wheel_dq_actual_rad_s": data.qvel[va[12:]].tolist(),
                "wheel_dq_target_rad_s": wheel.tolist(),
                "pitch_rad": float(np.arctan2(-rotation[2, 0], rotation[2, 2])),
                "command_vx_vy_wz": requested_command.tolist(),
                "obs_65": last_policy_observation.tolist() if last_policy_observation is not None else None,
                "raw_action": last_policy_action.tolist() if last_policy_action is not None else None,
            })
        peak_effort_ratio = 0.0
        last_step_nonwheel = 0.0
        for _ in range(substeps):
            kp_scale = stress.gain_scale[0, :12] if stressed and not nominal_dynamics else np.ones(12)
            kd_scale = stress.gain_scale[1] if stressed and not nominal_dynamics else np.ones(16)
            drive = np.r_[
                kp * kp_scale * (leg - data.qpos[qa[:12]])
                - kd * kd_scale[:12] * data.qvel[va[:12]],
                2.0 * kd_scale[12:] * (wheel - data.qvel[va[12:]]),
            ]
            if native_pd:
                data.ctrl[motors] = np.r_[leg, wheel]
            else:
                limits = np.maximum(effort_limits, 1e-6)
                peak_effort_ratio = max(peak_effort_ratio, float(np.max(np.abs(drive) / limits)))
                data.ctrl[motors] = np.clip(drive, -effort_limits, effort_limits)
            mj.mj_step(model, data)
            if native_pd:
                peak_effort_ratio = max(peak_effort_ratio, float(np.max(
                    np.abs(data.actuator_force[motors]) / np.maximum(effort_limits, 1e-6))))
            last_step_nonwheel = max(last_step_nonwheel, contact_metrics()[0])
            if trace_active:
                trace_physics.append(trace_contacts())
        return peak_effort_ratio

    def policy_target(command):
        nonlocal previous_action, phase_seconds, policy_age, stand_bias
        nonlocal hold_reference, hold_frames, observation_reference
        nonlocal last_policy_observation, last_policy_action
        command = np.asarray(command, dtype=np.float64).copy()
        rotation = data.xmat[base].reshape(3, 3)
        q = data.qpos[qa].copy()
        q[12:] = (q[12:] + 2 * np.pi) % (4 * np.pi) - 2 * np.pi
        centered = bool(np.max(np.abs(command)) < 0.005)
        if centered:
            if observation_reference is None:
                observation_reference = q[12:].copy()
            delta = (q[12:] - observation_reference + 2 * np.pi) % (4 * np.pi) - 2 * np.pi
            memory = np.r_[np.clip(delta / 0.20, -3.0, 3.0), 1.0]
        else:
            observation_reference = None
            memory = np.zeros(5)

        clock = [np.sin(2 * np.pi * phase_seconds / 0.62),
                 np.cos(2 * np.pi * phase_seconds / 0.62)]
        observation = np.r_[
            command - (0.4, 0.0, 0.0), data.qvel[3:6], -rotation[2], 0.4,
            q - prior.defaults, data.qvel[va], previous_action, clock, memory,
        ].astype(np.float32)
        previous_action = session.run(
            ["actions"], {"obs": observation.reshape(1, 65)}
        )[0][0].astype(np.float64)
        previous_action = np.clip(previous_action, -6.0, 6.0)
        last_policy_observation = observation.copy()
        last_policy_action = previous_action.copy()

        vx, yaw = float(command[0]), float(command[2])
        turning = min(abs(yaw) / 0.20, 1.0)
        motion = min(max(abs(vx) / 0.10, turning), 1.0)
        raw_wheel = np.clip(previous_action[12:], -1.0, 1.0)
        common = float(raw_wheel.mean())
        steering = float((raw_wheel * SIDE).mean())
        leg_normalized = 0.18 * motion * np.clip(previous_action[:12], -1.0, 1.0)
        linear = vx + 0.10 * turning * common - (
            0.66 * (1.0 + 0.25 * steering) * yaw * SIDE
        )
        wheel_normalized = linear / (0.086 * 16.0)
        wheel_normalized += 0.035 * motion * (1.0 - turning) * (raw_wheel - common)

        wheel_speed = data.qvel[va[12:]]
        gyro = data.qvel[3:6]
        up = float(rotation[2, 2])
        activity = min(max(abs(vx) / 0.08, abs(yaw) / 0.15), 1.0)
        quiet = np.linalg.norm(gyro) < 0.20 and up > 0.92 and np.max(np.abs(wheel_speed)) < 0.55
        if policy_age < 4.0 and quiet and hold_frames[0] * DT >= 0.30 and activity < 0.05:
            q_error = q[:12] - prior.defaults[:12]
            correction = np.clip(-1.40 * DT * q_error, -0.004, 0.004)
            stand_bias = np.clip((1.0 - 0.03 * DT) * stand_bias + correction, -0.38, 0.38)
        release_blend = np.clip((hold_frames[0] * DT - 0.45) / 1.05, 0.0, 1.0)
        bias_blend = 1.0 if policy_age < 4.0 else release_blend
        leg_normalized += bias_blend * (1.0 - activity) * stand_bias / 0.35

        hold_quiet = np.max(np.abs(wheel_speed)) < 0.50 and np.linalg.norm(gyro) < 0.15
        latched = hold_frames[0] * DT >= 0.12
        hold_frames[0] = hold_frames[0] + 1 if centered and (latched or hold_quiet) else 0
        capture = hold_frames[0] * DT >= 0.12 and not latched
        if capture:
            hold_reference = q[12:].copy()
        hold_error = (q[12:] - hold_reference + 2 * np.pi) % (4 * np.pi) - 2 * np.pi
        hold_target = np.clip(-6.0 * hold_error, -1.5, 1.5) / 16.0
        if hold_frames[0] * DT >= 0.12:
            wheel_normalized += hold_target

        leg = np.clip(
            prior.defaults[:12] + 0.35 * leg_normalized,
            prior.LIMITS_LO[:12], prior.LIMITS_HI[:12],
        )
        wheel = 16.0 * np.clip(wheel_normalized, -6.0, 6.0)
        phase_seconds = (phase_seconds + DT) % 0.62
        policy_age += DT
        command_effect.append({
            "requested": command.tolist(),
            "motion_gate": motion,
            "leg_offset_max": float(np.max(np.abs(leg - prior.defaults[:12]))),
            "wheel_target_max": float(np.max(np.abs(wheel))),
        })
        if os.environ.get("R1199_WRAPPED_HISTORY") == "1":
            # Match the colleague evaluator: next obs[42:58] is the final
            # normalized post-wrapper action, not the raw actor output.
            previous_action = np.r_[leg_normalized, wheel_normalized]
        return leg, wheel, 55.0, 2.0

    def phase(name, run):
        start_t = float(data.time)
        start_xy = data.qpos[:2].copy()
        start_yaw = float(np.arctan2(data.xmat[base, 3], data.xmat[base, 0]))
        samples = []

        def capture(effort_ratio=0.0):
            nonwheel, loads = contact_metrics()
            nonwheel = max(nonwheel, last_step_nonwheel)
            yaw = float(np.arctan2(data.xmat[base, 3], data.xmat[base, 0]))
            samples.append({
                "height": float(data.qpos[2]),
                "up": float(data.xmat[base, 8]),
                "vx": float(data.qvel[0]),
                "vy": float(data.qvel[1]),
                "wz": float(data.qvel[5]),
                "yaw": yaw,
                "wheel_dq": float(np.max(np.abs(data.qvel[va[12:]]))),
                "leg_dq": float(np.max(np.abs(data.qvel[va[:12]]))),
                "nonwheel": nonwheel,
                "min_wheel_load": min(loads),
                "effort_ratio": effort_ratio,
                "leg_error": float(np.max(np.abs(data.qpos[qa[:12]] - prior.defaults[:12]))),
            })

        run(capture)
        tail = samples[max(0, len(samples) - round(2.0 / DT)):]
        end_yaw = samples[-1]["yaw"]
        yaw_delta = (end_yaw - start_yaw + np.pi) % (2 * np.pi) - np.pi
        row = {
            "name": name,
            "seconds": round(float(data.time) - start_t, 3),
            "min_height_m": min(item["height"] for item in samples),
            "min_up": min(item["up"] for item in samples),
            "peak_nonwheel_n": max(item["nonwheel"] for item in samples),
            "min_wheel_load_n": min(item["min_wheel_load"] for item in samples),
            "max_wheel_dq_rad_s": max(item["wheel_dq"] for item in samples),
            "max_leg_dq_rad_s": max(item["leg_dq"] for item in samples),
            "max_effort_ratio": max(item["effort_ratio"] for item in samples),
            "max_leg_error_rad": max(item["leg_error"] for item in samples),
            "tail_max_leg_error_rad": max(item["leg_error"] for item in tail),
            "mean_tail_vx_m_s": float(np.mean([item["vx"] for item in tail])),
            "mean_tail_vy_m_s": float(np.mean([item["vy"] for item in tail])),
            "mean_tail_wz_rad_s": float(np.mean([item["wz"] for item in tail])),
            "tail_speed_p95_m_s": float(np.percentile(
                [np.hypot(item["vx"], item["vy"]) for item in tail], 95)),
            "displacement_m": float(np.linalg.norm(data.qpos[:2] - start_xy)),
            "yaw_delta_rad": float(yaw_delta),
        }
        phases.append(row)
        print(
            f"  {scenario}/{seed} {name}: up={row['min_up']:.3f} "
            f"h={row['min_height_m']:.3f} nonwheel={row['peak_nonwheel_n']:.1f}N "
            f"v=({row['mean_tail_vx_m_s']:.3f},{row['mean_tail_vy_m_s']:.3f}) "
            f"wz={row['mean_tail_wz_rad_s']:.3f}", flush=True,
        )

    def hold(capture, seconds, target, kp=55.0, kd=2.0):
        for _ in range(round(seconds / DT)):
            capture(step(target[:12], np.zeros(4), kp, kd))

    if not measured_start:
        phase("passive", lambda capture: hold(capture, 1.0, data.qpos[qa].copy(), 0.0, 3.0))

    def fixstand(capture):
        start = data.qpos[qa].copy()
        preload = start.copy()
        preload[4:8] += 0.25
        for index in range(round(1.8 / DT)):
            alpha = (index + 1) / round(1.8 / DT)
            target = start + alpha * (preload - start)
            capture(step(target[:12], np.zeros(4), 20.0, 3.0))
        second_start = data.qpos[qa].copy()
        for index in range(round(1.2 / DT)):
            alpha = (index + 1) / round(1.2 / DT)
            target = second_start + alpha * (prior.defaults - second_start)
            capture(step(target[:12], np.zeros(4), 55.0, 2.0))

    if not measured_start:
        phase("A_fixstand", fixstand)
        phase("fixed_hold_before_B", lambda capture: hold(capture, 2.0, prior.defaults))
    else:
        # Real B starts with the T2 PD command still active while feedback is at
        # the measured loaded equilibrium.  Do not relax this snapshot toward
        # MuJoCo's ideal equilibrium before the policy blend.
        last_command = (prior.defaults[:12].copy(), np.zeros(4), 55.0, 2.0)

    fixed_start = last_command

    def enter_policy(capture):
        for index in range(round(0.75 / DT)):
            policy = policy_target(np.zeros(3))
            alpha = (index + 1) / round(0.75 / DT)
            leg = fixed_start[0] + alpha * (policy[0] - fixed_start[0])
            wheel = fixed_start[1] + alpha * (policy[1] - fixed_start[1])
            capture(step(leg, wheel, 55.0, 2.0))

    phase("B_enter_policy_centered", enter_policy)

    def policy_run(capture, command, seconds, push=False):
        nonlocal applied_push_s
        pushed = False
        for index in range(round(seconds / DT)):
            if push and not pushed and index * DT >= stress.push_time:
                applied_push_s = float(data.time - trace_start_s)
                data.qvel[:2] += stress.push_delta_xy
                mj.mj_forward(model, data)
                pushed = True
            applied_command = command
            if os.environ.get("R1199_RAMP_COMMAND") == "1" and np.any(command):
                applied_command = command * min(1.0, index * DT / 0.25)
            capture(step(*policy_target(applied_command)))

    phase("policy_static_before_motion", lambda capture: policy_run(capture, np.zeros(3), 2.0))
    motion_seconds = 8.0 if stressed else 4.0
    trace_active = bool(trace_path)
    trace_start_s = float(data.time)
    push_enabled = stressed and os.environ.get("ROLLING_DISABLE_PUSH") != "1"
    phase(f"policy_{scenario}", lambda capture: policy_run(
        capture, requested_command, motion_seconds, push=push_enabled))
    trace_active = False
    if trace_path:
        if os.environ.get("R1199_TRACE_FULL") == "1":
            window = (0.0, motion_seconds)
        elif first_touch_s is None:
            window = (0.0, motion_seconds)
        else:
            window = (max(0.0, first_touch_s - 0.5), first_touch_s + 0.5)
        Path(trace_path).write_text(json.dumps({
            "seed": seed, "scenario": scenario, "onnx": str(ONNX),
            "model_timestep_s": float(model.opt.timestep),
            "stress": {"friction": float(stress.friction),
                       "mass_scale": stress.mass_scale.tolist(),
                       "gain_scale": stress.gain_scale.tolist(),
                       "scheduled_push_s": float(stress.push_time),
                       "push_delta_xy_m_s": stress.push_delta_xy.tolist()},
            "push_enabled": push_enabled,
            "applied_push_s": applied_push_s,
            "first_nonwheel_over_1n_s": first_touch_s,
            "window_s": window,
            "physics_substeps": [row for row in trace_physics if window[0] <= row["t_s"] <= window[1]],
            "control_frames": [row for row in trace_control if window[0] <= row["t_s"] <= window[1]],
        }, indent=2) + "\n")

    brake_start_xy = data.qpos[:2].copy()
    quiet_ticks = 0

    def brake(capture):
        nonlocal quiet_ticks
        for _ in range(round(5.0 / DT)):
            capture(step(*policy_target(np.zeros(3))))
            quiet = (np.max(np.abs(data.qvel[va[12:]])) < 0.5
                     and np.linalg.norm(data.qvel[:2]) < 0.025
                     and abs(data.qvel[5]) < 0.06)
            quiet_ticks = quiet_ticks + 1 if quiet else 0
            if quiet_ticks >= round(0.5 / DT):
                break

    phase("brake_to_center", brake)
    brake_distance = float(np.linalg.norm(data.qpos[:2] - brake_start_xy))
    exit_start = last_command

    def exit_policy(capture):
        for index in range(round(0.75 / DT)):
            alpha = (index + 1) / round(0.75 / DT)
            leg = exit_start[0] + alpha * (prior.defaults[:12] - exit_start[0])
            wheel = exit_start[1] * (1.0 - alpha)
            capture(step(leg, wheel, 55.0, 2.0))

    phase("A_exit_to_fixedstand", exit_policy)
    phase("fixed_hold_after_exit", lambda capture: hold(capture, 2.0, prior.defaults))

    motion_row = next(row for row in phases if row["name"] == f"policy_{scenario}")
    brake_row = next(row for row in phases if row["name"] == "brake_to_center")
    final_row = phases[-1]
    expected = requested_command
    mapping_expected_zero = base_scenario == "vy_probe_0.10"
    passed_stability = all(
        row["min_up"] > np.cos(np.deg2rad(20.0))
        and row["min_height_m"] > 0.25
        and row["peak_nonwheel_n"] < 1.0
        for row in phases if row["name"] not in ("passive", "A_fixstand")
    )
    brake_ok = quiet_ticks >= round(0.5 / DT)
    fixed_exit_ok = (
        final_row["tail_max_leg_error_rad"] < 0.18
        and abs(final_row["mean_tail_vx_m_s"]) < 0.025
        and abs(final_row["mean_tail_wz_rad_s"]) < 0.06
        and final_row["tail_speed_p95_m_s"] < 0.025
    )
    if base_scenario in ("forward", "back"):
        tracking_ok = (abs(motion_row["mean_tail_vx_m_s"] - expected[0]) < 0.08
                       and abs(motion_row["mean_tail_vy_m_s"]) < 0.10
                       and abs(motion_row["mean_tail_wz_rad_s"]) < 0.12)
    elif base_scenario.startswith("turn_"):
        tracking_ok = (abs(motion_row["mean_tail_wz_rad_s"] - expected[2]) < 0.15
                       and np.hypot(motion_row["mean_tail_vx_m_s"],
                                    motion_row["mean_tail_vy_m_s"]) < 0.12)
    elif base_scenario.startswith("arc_"):
        tracking_ok = (abs(motion_row["mean_tail_wz_rad_s"] - expected[2]) < 0.15
                       and abs(motion_row["mean_tail_vx_m_s"] - expected[0]) < 0.10)
    elif base_scenario == "vy_probe_0.10":
        tracking_ok = abs(motion_row["mean_tail_vy_m_s"]) < 0.02
    else:
        tracking_ok = (abs(motion_row["mean_tail_vx_m_s"]) < 0.025
                       and abs(motion_row["mean_tail_vy_m_s"]) < 0.025
                       and abs(motion_row["mean_tail_wz_rad_s"]) < 0.06)
    return {
        "seed": seed,
        "scenario": scenario,
        "measured_fixedstand_start": measured_start,
        "requested_command": requested_command.tolist(),
        "command_mapping_uses_vy": False,
        "vy_mapping_expected_zero": mapping_expected_zero,
        "stable": bool(passed_stability),
        "brake_ok": bool(brake_ok),
        "fixed_exit_ok": bool(fixed_exit_ok),
        "tracking_ok": bool(tracking_ok),
        "passed": bool(passed_stability and brake_ok and fixed_exit_ok and tracking_ok),
        "motion_tracking": {
            "mean_vx_m_s": motion_row["mean_tail_vx_m_s"],
            "mean_vy_m_s": motion_row["mean_tail_vy_m_s"],
            "mean_wz_rad_s": motion_row["mean_tail_wz_rad_s"],
            "requested_vx_m_s": float(expected[0]),
            "requested_vy_m_s": float(expected[1]),
            "requested_wz_rad_s": float(expected[2]),
        },
        "brake_distance_m": brake_distance,
        "max_target_step_equivalent": max(transition_target_jumps),
        "stress": ({
            "friction": float(stress.friction),
            "push_time_s": float(stress.push_time),
            "push_delta_xy_m_s": stress.push_delta_xy.tolist(),
        } if stressed else None),
        "phases": phases,
        "mapping_tail": command_effect[-5:],
    }


results = []
trace_seed = os.environ.get("ROLLING_TRACE_SEED")
if trace_seed:
    if not os.environ.get("ROLLING_CONTACT_TRACE"):
        raise SystemExit("ROLLING_TRACE_SEED requires ROLLING_CONTACT_TRACE")
    results.append(run_case(int(trace_seed), "measured_forward", COMMANDS["forward"]))
else:
    if os.environ.get("ROLLING_MEASURED_ONLY") != "1":
        for scenario, command in COMMANDS.items():
            seeds = ((101, 202, 303) if scenario in ("static", "vy_probe_0.10")
                     else tuple(range(46001, 46011)) + tuple(range(47001, 47011)))
            for seed in seeds:
                results.append(run_case(seed, scenario, command))

    for scenario in ("static", "forward", "back"):
        for seed in (101, 202, 303):
            results.append(run_case(seed, "measured_" + scenario, COMMANDS[scenario]))

summary = {}
for scenario in dict.fromkeys(row["scenario"] for row in results):
    rows = [row for row in results if row["scenario"] == scenario]
    summary[scenario] = {
        "trials": len(rows),
        "passed": sum(row["passed"] for row in rows),
        "stable": sum(row["stable"] for row in rows),
        "brake_ok": sum(row["brake_ok"] for row in rows),
        "fixed_exit_ok": sum(row["fixed_exit_ok"] for row in rows),
        "tracking_ok": sum(row["tracking_ok"] for row in rows),
        "mean_tracking": {
            key: float(np.mean([row["motion_tracking"][key] for row in rows]))
            for key in ("mean_vx_m_s", "mean_vy_m_s", "mean_wz_rad_s")
        },
        "max_brake_distance_m": max(row["brake_distance_m"] for row in rows),
    }

OUT.write_text(json.dumps({"summary": summary, "rows": results}, indent=2) + "\n")
print(json.dumps(summary, indent=2), flush=True)
print(f"saved {OUT}", flush=True)
