"""Offline R214 A=fixed PD, B=policy, Y=two-stage squat rehearsal.

Run on the server with the same asset/runtime/model inputs as
r214_fsm_rehearsal.py. This models the C++ phase timings and target blends;
it does not authorize real LowCmd publishing.
"""
import json
import sys
from pathlib import Path

import numpy as np

if len(sys.argv) != 5:
    raise SystemExit("usage: r214_ab_fsm_rehearsal.py ASSETS RUNTIME ONNX OUT.json")

assets, runtime, onnx, output = map(Path, sys.argv[1:])
import r214_fsm_rehearsal as prior  # noqa: E402 - shares pinned asset/model setup

mj = prior.mj
DT = 0.02


def run_case(seed: int, route: str, variant: str) -> dict:
    rng = np.random.default_rng(seed)
    model = prior.sim.load_flat_model(True, True, seed=0)
    data = mj.MjData(model)
    joints = [model.joint(name) for name in prior.NAMES]
    qa = np.array([joint.qposadr[0] for joint in joints])
    va = np.array([joint.dofadr[0] for joint in joints])
    motors = np.array([model.actuator(name).id for name in prior.NAMES])
    wheels = {model.body(name).id for name in prior.NAMES[12:]}
    base = model.body("base_link").id
    model.geom_friction[model.geom("ground").id, 0] = rng.uniform(.55, .85)
    substeps = round(DT / model.opt.timestep)
    force = np.zeros(6)

    data.qpos[qa] = prior.PRONE + rng.uniform(-.02, .02, 16)
    low, high = .05, .60
    for _ in range(18):
        mid = (low + high) / 2
        data.qpos[2] = mid
        mj.mj_forward(model, data)
        if data.ncon and min(contact.dist for contact in data.contact) <= 0:
            low = mid
        else:
            high = mid
    data.qpos[2] = high + .002
    mj.mj_forward(model, data)

    actor = prior.OnnxActor(prior.session_for(onnx), prior.defaults)
    stand_pose = prior.STAND_T1 if variant == "T1" else prior.defaults
    previous_action = np.zeros(16)
    phases = []
    last_command = (data.qpos[qa[:12]].copy(), np.zeros(4), 0., 3.)

    def sample_contact():
        peak = 0.
        for index, contact in enumerate(data.contact):
            a, b = (int(model.geom_bodyid[geom]) for geom in contact.geom)
            if a and b:
                continue
            body = a or b
            if body not in wheels and body != 0:
                mj.mj_contactForce(model, data, index, force)
                peak = max(peak, float(force[0]))
        return peak

    def phase(name, fn):
        start = float(data.time)
        heights, up, peaks, vz = [], [], [], []

        def capture():
            heights.append(float(data.qpos[2]))
            up.append(float(data.xmat[base, 8]))
            peaks.append(sample_contact())
            vz.append(float(data.qvel[2]))

        fn(capture)
        row = dict(name=name, seconds=round(float(data.time) - start, 2),
                   start_height=heights[0], end_height=heights[-1],
                   min_height=min(heights), min_up=min(up),
                   peak_nonwheel_n=max(peaks), min_vz=min(vz))
        phases.append(row)
        print(f"  {name}: h={row['start_height']:.3f}->{row['end_height']:.3f} "
              f"min_up={row['min_up']:.3f} contact={row['peak_nonwheel_n']:.1f}N")

    def step(leg, wheel, kp, kd=2.):
        nonlocal last_command
        leg = np.clip(np.asarray(leg), prior.LIMITS_LO[:12], prior.LIMITS_HI[:12])
        wheel = np.asarray(wheel)
        last_command = (leg.copy(), wheel.copy(), float(kp), float(kd))
        for _ in range(substeps):
            torque = np.r_[kp * (leg - data.qpos[qa[:12]]) - kd * data.qvel[va[:12]],
                           2. * (wheel - data.qvel[va[12:]])]
            data.ctrl[motors] = np.clip(torque, *model.actuator_ctrlrange[motors].T)
            mj.mj_step(model, data)

    def policy_target(command):
        nonlocal previous_action
        rot = data.xmat[base].reshape(3, 3)
        q = data.qpos[qa].copy()
        q[12:] = (q[12:] + 2 * np.pi) % (4 * np.pi) - 2 * np.pi
        observation = np.r_[command - (.4, 0., 0.), data.qvel[3:6],
                            -rot[2], .4, q - prior.defaults, data.qvel[va],
                            previous_action]
        observation[3:9] = observation[3:9].astype(np.float32)
        observation[10:26] = ((observation[10:26] + prior.defaults)
                              .astype(np.float32).astype(np.float64)
                              - prior.defaults)
        observation[26:42] = observation[26:42].astype(np.float32)
        previous_action = actor.plan(None, None, observation, command, 0, None)
        leg = np.clip(prior.defaults[:12] + .35 * previous_action[:12],
                      prior.LIMITS_LO[:12], prior.LIMITS_HI[:12])
        wheel = np.clip(16. * previous_action[12:], -98.47, 98.47)
        return leg, wheel, 55., 2.

    def hold(capture, seconds, target, kp=55., kd=2.):
        for _ in range(round(seconds / DT)):
            step(target[:12], np.zeros(4), kp, kd)
            capture()

    phase("passive", lambda capture: hold(capture, 2., data.qpos[qa].copy(), 0., 3.))

    def fixstand(capture):
        start = data.qpos[qa].copy()
        preload = start.copy()
        preload[4:8] += .25
        for index in range(round(1.8 / DT)):
            alpha = (index + 1) / round(1.8 / DT)
            target = start + alpha * (preload - start)
            step(target[:12], np.zeros(4), 20., 3.)
            capture()
        start_b2 = data.qpos[qa].copy()
        for index in range(round(1.2 / DT)):
            alpha = (index + 1) / round(1.2 / DT)
            target = start_b2 + alpha * (stand_pose - start_b2)
            step(target[:12], np.zeros(4), 55., 2.)
            capture()

    phase("A_fixstand", fixstand)
    phase("fixed_hold", lambda capture: hold(capture, 2., stand_pose))

    if route.startswith("A_B"):
        fixed_start = last_command
        actor.state[:] = 0
        previous_action = np.zeros(16)

        def policy_handoff(capture):
            for index in range(round(2. / DT)):
                policy = policy_target(np.zeros(3))
                alpha = (index + 1) / round(2. / DT)
                leg = fixed_start[0] + alpha * (policy[0] - fixed_start[0])
                wheel = fixed_start[1] + alpha * (policy[1] - fixed_start[1])
                kp = fixed_start[2] + alpha * (policy[2] - fixed_start[2])
                kd = fixed_start[3] + alpha * (policy[3] - fixed_start[3])
                step(leg, wheel, kp, kd)
                capture()

        phase("B_policy_handoff", policy_handoff)

        def walk(capture):
            for _ in range(round(2. / DT)):
                step(*policy_target(np.array([.1, 0., 0.])))
                capture()

        phase("policy_forward", walk)

        def brake(capture):
            stable = 0
            for _ in range(round(3. / DT)):
                step(*policy_target(np.zeros(3)))
                capture()
                stable = stable + 1 if np.abs(data.qvel[va[12:]]).max() < .5 else 0
                if stable >= round(.3 / DT):
                    break

        phase("Y_policy_brake" if route == "A_B_Y" else "A_policy_brake", brake)
        brake_ok = np.abs(data.qvel[va[12:]]).max() < .5
        return_start = last_command
        return_pose = (data.qpos[qa].copy() if "snapshot" in route
                       else np.r_[last_command[0], np.zeros(4)]
                       if "freeze" in route else stand_pose.copy())
        return_seconds = 4. if "slow" in route else 2.5

        def return_stand(capture):
            for index in range(round(return_seconds / DT)):
                alpha = (index + 1) / round(return_seconds / DT)
                leg = return_start[0] + alpha * (return_pose[:12] - return_start[0])
                wheel = return_start[1] * (1. - alpha)
                kp = return_start[2] + alpha * (55. - return_start[2])
                kd = return_start[3] + alpha * (2. - return_start[3])
                step(leg, wheel, kp, kd)
                capture()

        if brake_ok and route != "A_B_Y":
            phase("A_return_stand", return_stand)
            phase("returned_fixed_hold", lambda capture: hold(capture, 1., return_pose))
    else:
        brake_ok = True

    if brake_ok:
        squat_start = last_command

        def squat(capture):
            fold = squat_start[0].copy()
            fold[4:8] += .2
            fold[8:12] -= .3
            for index in range(round(1.5 / DT)):
                alpha = (index + 1) / round(1.5 / DT)
                leg = squat_start[0] + alpha * (fold - squat_start[0])
                kp = squat_start[2] + alpha * (35. - squat_start[2])
                step(leg, np.zeros(4), kp, 3.)
                capture()
            start_f2 = data.qpos[qa].copy()
            for index in range(round(2.5 / DT)):
                alpha = (index + 1) / round(2.5 / DT)
                leg = start_f2[:12] + alpha * (prior.PRONE[:12] - start_f2[:12])
                step(leg, np.zeros(4), 20., 3.)
                capture()
            for _ in range(round(1. / DT)):
                step(prior.PRONE[:12], np.zeros(4), 10., 3.)
                capture()
            for index in range(round(2. / DT)):
                kp = 10. * (1. - (index + 1) / round(2. / DT))
                step(prior.PRONE[:12], np.zeros(4), kp, 3.)
                capture()

        phase("Y_fixsquat", squat)

    standing = [row for row in phases if row["name"] not in
                ("passive", "Y_fixsquat")]
    return dict(seed=seed, route=route, variant=variant, brake_ok=bool(brake_ok),
                standing_min_up=min(row["min_up"] for row in standing),
                standing_min_height=min(row["min_height"] for row in standing),
                standing_peak_nonwheel_n=max(row["peak_nonwheel_n"] for row in standing),
                final_height=float(data.qpos[2]), phases=phases)


results = []
for variant in ("T1", "T2"):
    routes = ("A_Y", "A_B_A_Y") if variant == "T1" else (
        "A_Y", "A_B_Y", "A_B_A_Y", "A_B_A_Y_snapshot", "A_B_A_Y_slow",
        "A_B_A_Y_freeze")
    for route in routes:
        for seed in (101, 202, 303):
            print(f"variant={variant} route={route} seed={seed}", flush=True)
            results.append(run_case(seed, route, variant))
output.write_text(json.dumps(results, indent=2))
print(f"saved {output}")
