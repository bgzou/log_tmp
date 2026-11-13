"""MuJoCo rerun of the delivered AS2-W actors (flat + stairs crosscheck).

Modes:
  recovery-validate   Replicates the delivered flat recovery screen (poses x seeds
                      12001..12004) to validate this harness against
                      mujoco-native-report.json (recovery-r12 reference 16/16,
                      native 15/16 with right/12002 marginal at 0.98 s).
  flat-stairs         NEW protocol: flat ground + stairs observation semantics
                      (command fixed 0.4, linear-velocity slots zero, active from
                      tick 0, 9 s window, stairs-style init noise, start at 0.37 m).
  stairs-crosscheck   Replicates the delivered stairs scene (5-level stairs, seeded
                      rise/tread, dynamics stress) and its pass criteria to compare
                      per-seed visited_levels with mujoco-native-report.json.

Actor weights are parsed from the delivered .bin files (format per
cpp_deploy-as2w src/policy.cpp): AS2WMLP1 magic, mode word, defaults[16],
limits[16][3], then 4 layers (row-major float32 weights + bias).
Hidden activation ELU, linear output.

Physics/observation semantics follow the delivered as2w-deploy mujoco_screen.py
evaluate() at Rob2Nav rev e61aaf79; deviations are marked with # DEVIATION.
"""
import argparse
import json
import struct
import multiprocessing as mp
import xml.etree.ElementTree as ET
from pathlib import Path

import mujoco as mj
import numpy as np

HERE = Path(__file__).resolve().parent
WHEEL_PERIOD = 4 * np.pi
ACTION_CLIP = 6.
WHEEL_SCALE = 16.
LEG_SCALE = .35
POSES = {"back": np.pi, "left": np.pi / 2, "right": -np.pi / 2, "belly": 0.}


def load_actor(path):
    data = Path(path).read_bytes()
    if data[:8] != b"AS2WMLP1":
        raise ValueError(f"bad magic in {path}")
    off = 8
    mode, = struct.unpack_from("<I", data, off); off += 4
    defaults = np.array(struct.unpack_from("<16f", data, off)); off += 64
    limits = np.array([struct.unpack_from("<3f", data, off + 12 * i) for i in range(16)]); off += 12 * 16
    layers = []
    for w_in, w_out in zip((58, 128, 128, 128, 16)[:-1], (58, 128, 128, 128, 16)[1:]):
        W = np.frombuffer(data, "<f4", w_in * w_out, off).reshape(w_out, w_in).copy(); off += 4 * w_in * w_out
        b = np.frombuffer(data, "<f4", w_out, off).copy(); off += 4 * w_out
        layers.append((W, b))
    if off != len(data):
        raise ValueError("trailing bytes in actor file")
    return {"stairs": mode == 1, "defaults": defaults, "limits": limits, "layers": layers}


def actor_forward(actor, obs):
    x = obs.astype(np.float32)
    for i, (W, b) in enumerate(actor["layers"]):
        x = W @ x + b
        if i < 3:
            x = np.where(x < 0., np.expm1(x), x)
    return x


def load_flat_model(terrain=None, seed=0):
    path = HERE / "local-step-diagnostic/as2w_flat.xml"
    if terrain is None:
        model = mj.MjModel.from_xml_path(str(path))
    elif terrain == "stairs":
        xml = ET.parse(path).getroot()
        for asset in xml.findall("./asset/mesh"):
            asset.set("file", (path.parent / asset.attrib["file"]).resolve().as_posix())
        ground_geom = xml.find("./worldbody/geom[@name='ground']")
        ground_geom.set("group", "5")
        rise = (.06, .08, .10)[seed % 3]
        tread = (.31, .35, .39)[(seed // 3) % 3]
        for level in range(1, 6):
            start = .7 + (level - 1) * tread
            length = tread if level < 5 else 2.
            top = level * rise
            ET.SubElement(xml.find("./worldbody"), "geom", name=f"stair_{level}", type="box",
                          size=f"{length/2} 1.25 {top/2}", pos=f"{start+length/2} 0 {top/2}",
                          group="5", friction=ground_geom.attrib["friction"])
        model = mj.MjModel.from_xml_string(ET.tostring(xml, encoding="unicode"))
    else:
        raise ValueError(f"unsupported terrain {terrain}")
    ground = model.geom("ground").id
    surface_ids = [ground]
    if terrain == "stairs":
        surface_ids.extend(model.geom(f"stair_{level}").id for level in range(1, 6))
    model.geom_priority[surface_ids] = int(model.geom_priority.max()) + 1
    model.geom_contype[:] = 1
    model.geom_conaffinity[:] = 0
    model.geom_contype[surface_ids] = 0
    model.geom_conaffinity[surface_ids] = 1
    return model


def sample_dynamics_stress(seed, body_count, joint_count):
    rng = np.random.default_rng([seed, 804])
    return dict(
        friction=rng.uniform(.45, .95), mass_scale=rng.uniform(.9, 1.1, body_count),
        gain_scale=rng.uniform(.85, 1.15, (2, joint_count)), push_time=rng.uniform(2.8, 4.5),
        push_delta_xy=rng.uniform(-.15, .15, 2),
    )


def run_trial(args):
    label, mode, seed, pose, stress_on, model_bin = args
    actor = load_actor(model_bin)
    stairs_scene = mode == "stairs-crosscheck"
    model = load_flat_model("stairs" if stairs_scene else None, seed)
    contract = json.loads((HERE / "fall-baseline/fall-recovery-contract.json").read_text())
    default = np.array(contract["default_joint_pos"])
    names = contract["joint_names"]
    joints = [model.joint(n) for n in names]
    qa = np.array([j.qposadr[0] for j in joints])
    va = np.array([j.dofadr[0] for j in joints])
    motors = np.array([model.actuator(n).id for n in names])
    wheel_bodies = {model.jnt_bodyid[j.id] for j in joints[12:]}
    limits = actor["limits"]
    ground = model.geom("ground").id
    stair_geoms = {model.geom(f"stair_{level}").id: level for level in range(1, 6)} if stairs_scene else {}
    surfaces = {ground, *stair_geoms}
    stairs_obs = mode in ("flat-stairs", "stairs-crosscheck")

    rng = np.random.default_rng(seed)
    data = mj.MjData(model)
    stress = sample_dynamics_stress(seed, model.nbody - 1, 16) if stress_on else None
    ground_friction = stress["friction"] if stress_on else rng.uniform(.55, .85)
    if stress_on:
        model.body_mass[1:] *= stress["mass_scale"]
        model.body_inertia[1:] *= stress["mass_scale"][:, None]
        mj.mj_setConst(model, data)
    model.geom_friction[list(surfaces), 0] = ground_friction

    surface_height = None
    if stairs_scene:
        ground_mask = np.array([0, 0, 0, 0, 0, 1], dtype=np.uint8)
        down = np.array([0., 0., -1.])
        hit_geom = np.empty(1, dtype=np.int32)

        def surface_height(x, y):
            distance = mj.mj_ray(model, data, np.array([x, y, 5.]), down, ground_mask,
                                 True, -1, hit_geom)
            return 5. - distance if distance >= 0. and hit_geom[0] in surfaces else np.nan

    if stairs_obs:
        settle, window = 0., 9.
        data.qpos[2] = .37 + (surface_height(0., 0.) if stairs_scene else 0.)
        data.qpos[:2] = rng.uniform((-.12, -.15), (.12, .15))
        yaw = rng.uniform(-.08, .08)
        data.qpos[3:7] = [np.cos(yaw / 2), 0., 0., np.sin(yaw / 2)]
        data.qpos[qa] = default + rng.uniform(-.12, .12, size=16)
    else:
        settle, window = float(contract["settle_seconds"]), float(contract["recovery_seconds"])
        data.qpos[2] = 1.1
        angle = POSES[pose] + rng.uniform(-.12, .12)
        data.qpos[3:7] = [np.cos(angle / 2), np.sin(angle / 2), 0., 0.]
        data.qpos[qa] = default + rng.uniform(-.55, .55, size=16)
    for j in joints[:12]:
        data.qpos[j.qposadr[0]] = np.clip(data.qpos[j.qposadr[0]], *j.range)
    mj.mj_forward(model, data)

    dt = contract["control_dt"]
    substeps = round(dt / model.opt.timestep)
    passive_ticks = round(settle / dt)
    kp = np.r_[np.full(12, 55.), np.zeros(4)]
    kd = np.full(16, 2.)
    push_tick = -1
    if stress_on:
        kp *= stress["gain_scale"][0]
        kd *= stress["gain_scale"][1]
        push_tick = round(stress["push_time"] / dt)
    last = np.zeros(16)
    base = model.body("base_link").id
    force = np.zeros(6)
    streak = longest = 0
    peak_impact = 0.
    max_upright = -1.
    upright_samples = active_ticks = 0
    highest_upright_height = None
    clipped_leg = clipped_wheel = 0
    wheel_contact_ticks = 0
    peak_joint_speed = np.zeros(16)
    overspeed_ticks = 0
    best_upright_ground_load = {}
    max_progress = float(data.qpos[0])
    start_y = y_at_farthest = float(data.qpos[1])
    max_lateral_excursion = 0.
    failed_while_upright = dict.fromkeys(("height", "linear_speed", "angular_speed", "wheel_support", "nonwheel_contact"), 0)
    stable_walk_ticks = 0
    speed_while_upright = []
    level_first_contact_s = {}
    level_wheel_first_contact_s = {} if stairs_scene else None
    top_wheel_load = dict.fromkeys(wheel_bodies, 0.) if stairs_scene else None

    for tick in range(round((settle + window) / dt)):
        t = tick * dt
        active = tick >= passive_ticks
        if tick == push_tick:
            data.qvel[:2] += stress["push_delta_xy"]
            mj.mj_forward(model, data)
        rotation = data.xmat[base].reshape(3, 3)
        joint_positions = data.qpos[qa].copy()
        joint_positions[12:] = (joint_positions[12:] + WHEEL_PERIOD / 2.) % WHEEL_PERIOD - WHEEL_PERIOD / 2.
        if stairs_obs:
            command = .4
            linear_velocity_obs = np.zeros(3)
        else:
            command = max(0., (t - settle) / window)
            linear_velocity_obs = rotation.T @ data.qvel[:3]
        obs = np.r_[linear_velocity_obs, data.qvel[3:6], -rotation[2],
                    command, joint_positions - default, data.qvel[va], last]
        last = actor_forward(actor, obs)
        if active:
            active_ticks += 1
            clipped_leg += np.count_nonzero(np.abs(last[:12]) > ACTION_CLIP)
            clipped_wheel += np.count_nonzero(np.abs(last[12:]) > ACTION_CLIP)
        last = np.clip(last, -ACTION_CLIP, ACTION_CLIP)
        leg_target = default[:12] + LEG_SCALE * last[:12]
        wheel_target = WHEEL_SCALE * last[12:]
        leg_target = np.clip(leg_target, *limits[:12, :2].T)
        wheel_target = np.clip(wheel_target, -limits[12:, 2], limits[12:, 2])
        for _ in range(substeps):
            if active:
                leg = kp[:12] * (leg_target - data.qpos[qa[:12]]) - kd[:12] * data.qvel[va[:12]]
                wheel = kd[12:] * (wheel_target - data.qvel[va[12:]])
                drive = np.r_[leg, wheel]
                data.ctrl[motors] = np.clip(drive, *model.actuator_ctrlrange[motors].T)
            expected_time = data.time + model.opt.timestep
            mj.mj_step(model, data)
            if abs(data.time - expected_time) > 1e-9 or not np.isfinite(data.qacc).all():
                return {"label": label, "mode": mode, "seed": seed, "pose": pose, "stress": stress_on,
                        "passed": False, "valid": False, "failure": "unstable_physics"}
        if not active:
            continue
        joint_speed = np.abs(data.qvel[va])
        peak_joint_speed = np.maximum(peak_joint_speed, joint_speed)
        overspeed_ticks += bool(np.any(joint_speed > limits[:, 2]))
        wheel_load = dict.fromkeys(wheel_bodies, 0.)
        if stairs_scene:
            top_wheel_load = dict.fromkeys(wheel_bodies, 0.)
        ground_load = {}
        impact = 0.
        for i, contact in enumerate(data.contact):
            g1, g2 = contact.geom
            surface, other = (g1, g2) if g1 in surfaces else (g2, g1)
            if surface not in surfaces or other in surfaces:
                continue
            body = model.geom_bodyid[other]
            mj.mj_contactForce(model, data, i, force)
            ground_load[body] = ground_load.get(body, 0.) + float(force[0])
            if body in wheel_load:
                wheel_load[body] += force[0]
                if stairs_scene and surface in stair_geoms and abs(contact.frame[2]) >= .7:
                    level = stair_geoms[surface]
                    if force[0] >= 8.:
                        contact_s = (tick + 1) * dt
                        level_first_contact_s.setdefault(level, contact_s)
                        level_wheel_first_contact_s.setdefault(level, {}).setdefault(body, contact_s)
                    if level == 5:
                        top_wheel_load[body] += force[0]
            else:
                impact = max(impact, force[0])
        peak_impact = max(peak_impact, impact)
        upright_cosine = float(data.xmat[base, 8])
        if upright_cosine > max_upright:
            max_upright = upright_cosine
            best_upright_ground_load = ground_load
        wheel_contact_ticks += any(load >= 8. for load in wheel_load.values())
        upright = upright_cosine >= np.cos(np.deg2rad(20.))
        height = float(data.qpos[2])
        if stairs_scene:
            height -= surface_height(*data.qpos[:2])
        checks = {
            "height": height >= .29,
            "linear_speed": np.linalg.norm(data.qvel[:3]) <= .2,
            "angular_speed": np.linalg.norm(data.qvel[3:6]) <= .4,
            "wheel_support": min(wheel_load.values()) >= 8.,
            "nonwheel_contact": impact < 1.,
        }
        if upright:
            upright_samples += 1
            if highest_upright_height is None or height > highest_upright_height:
                highest_upright_height = height
            for name_k, passed in checks.items():
                failed_while_upright[name_k] += int(not passed)
            if mode == "flat-stairs":
                speed_while_upright.append(float(np.linalg.norm(data.qvel[:3])))
        stable = upright and all(checks.values())
        if stairs_scene:
            if data.qpos[0] > max_progress:
                max_progress = float(data.qpos[0])
                y_at_farthest = float(data.qpos[1])
            max_lateral_excursion = max(max_lateral_excursion, abs(float(data.qpos[1]) - start_y))
            stable = upright and height >= .25 and impact < 1. and min(top_wheel_load.values()) >= 8.
        elif mode == "flat-stairs":
            if data.qpos[0] > max_progress:
                max_progress = float(data.qpos[0])
                y_at_farthest = float(data.qpos[1])
            max_lateral_excursion = max(max_lateral_excursion, abs(float(data.qpos[1]) - start_y))
            # DEVIATION from recovery checks: walking needs speed, so "stable walk" drops
            # the linear_speed cap and relaxes height to 0.25 (stairs criterion).
            walk_checks = {
                "height": height >= .25,
                "wheel_support": min(wheel_load.values()) >= 8.,
                "nonwheel_contact": impact < 1.,
                "angular_speed": np.linalg.norm(data.qvel[3:6]) <= 1.0,
            }
            stable = upright and all(walk_checks.values())
            stable_walk_ticks += stable
        streak = streak + 1 if stable else 0
        longest = max(longest, streak)

    result = {
        "label": label, "mode": mode, "seed": seed, "pose": pose, "stress": stress_on, "valid": True,
        "passed": longest * dt >= 1.,
        "stable_s": longest * dt,
        "peak_impact_n": peak_impact,
        "max_upright_cosine": max_upright, "upright_fraction": upright_samples / max(active_ticks, 1),
        "failed_while_upright": failed_while_upright,
        "clipped_leg_action_fraction": clipped_leg / (12 * max(active_ticks, 1)),
        "clipped_wheel_action_fraction": clipped_wheel / (4 * max(active_ticks, 1)),
        "wheel_contact_s": wheel_contact_ticks * dt,
        "best_upright_ground_load_n": {model.body(b).name: l for b, l in best_upright_ground_load.items()},
        "final_wheel_speed_rad_s": data.qvel[va[12:]].tolist(),
        "peak_joint_speed_rad_s": dict(zip(names, peak_joint_speed.tolist())),
        "urdf_joint_overspeed_s": overspeed_ticks * dt,
        "highest_upright_height_m": highest_upright_height,
        "final_base_height_m": float(data.qpos[2]),
        "final_upright_cosine": float(data.xmat[base, 8]),
        "sampled_ground_friction": ground_friction,
    }
    if mode == "flat-stairs":
        result.update(
            stable_walk_fraction=stable_walk_ticks / max(active_ticks, 1),
            mean_speed_while_upright_m_s=(float(np.mean(speed_while_upright)) if speed_while_upright else None),
            max_forward_x_m=max_progress, final_forward_x_m=float(data.qpos[0]),
            lateral_excursion_m=max_lateral_excursion, y_at_farthest_x_m=y_at_farthest,
            final_y_m=float(data.qpos[1]),
        )
    if stairs_scene:
        visited_levels = sorted(level_first_contact_s)
        ordered = len(visited_levels) == 5 and all(
            level_first_contact_s[level] <= level_first_contact_s[level + 1] for level in range(1, 5)
        )
        first_step = model.geom("stair_1")
        result.update(
            passed=ordered and longest * dt >= .5 and peak_impact < 50.,
            visited_levels=visited_levels, level_first_contact_s=level_first_contact_s,
            level_wheel_first_contact_s={
                level: {model.body(b).name: s for b, s in wheel_times.items()}
                for level, wheel_times in level_wheel_first_contact_s.items()
            },
            top_support_s=longest * dt, stair_rise_m=float(2 * first_step.size[2]),
            stair_tread_m=float(2 * first_step.size[0]),
            max_forward_x_m=max_progress, final_forward_x_m=float(data.qpos[0]),
            lateral_excursion_m=max_lateral_excursion, y_at_farthest_x_m=y_at_farthest,
            final_y_m=float(data.qpos[1]),
        )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("recovery-validate", "flat-stairs", "stairs-crosscheck"), required=True)
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--seeds", type=int, default=16, help="number of seeds")
    parser.add_argument("--first-seed", type=int, default=None)
    parser.add_argument("--stress", choices=("off", "on", "both"), default="off")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    model_dir = HERE / "models"
    jobs = []
    if args.mode == "recovery-validate":
        first = args.first_seed if args.first_seed is not None else 12001
        for label in args.models:
            for pose in POSES:
                for seed in range(first, first + args.seeds):
                    jobs.append((label, args.mode, seed, pose, False, str(model_dir / f"{label}.bin")))
    else:
        first = args.first_seed if args.first_seed is not None else 27001
        stresses = [False] if args.stress == "off" else [True] if args.stress == "on" else [False, True]
        for label in args.models:
            for stress_on in stresses:
                for seed in range(first, first + args.seeds):
                    jobs.append((label, args.mode, seed, "upright", stress_on, str(model_dir / f"{label}.bin")))

    with mp.Pool(min(len(jobs), 24)) as pool:
        rows = pool.map(run_trial, jobs)
    args.out.write_text(json.dumps(rows, indent=1), encoding="utf-8")

    print(f"== {args.mode} -> {args.out}")
    for label in args.models:
        for stress_on in sorted({r["stress"] for r in rows if r["label"] == label}):
            sub = [r for r in rows if r["label"] == label and r["stress"] == stress_on]
            ok = sum(r["passed"] for r in sub)
            valid = sum(r["valid"] for r in sub)
            print(f"{label} stress={'on ' if stress_on else 'off'}: passed {ok}/{len(sub)} (valid {valid})")
            if args.mode == "flat-stairs":
                fw = [r.get("max_forward_x_m", 0.) for r in sub]
                sw = [r.get("stable_walk_fraction", 0.) for r in sub]
                uf = [r.get("upright_fraction", 0.) for r in sub]
                print(f"  max_forward_x: mean {np.mean(fw):.2f} m  min {np.min(fw):.2f}  max {np.max(fw):.2f}"
                      f"  (ideal ~{.4*9:.1f} m)")
                print(f"  stable_walk_fraction: mean {np.mean(sw):.2f}  upright_fraction: mean {np.mean(uf):.2f}")
            elif args.mode == "stairs-crosscheck":
                lv = [len(r.get("visited_levels", [])) for r in sub]
                print(f"  visited_levels: mean {np.mean(lv):.2f}  max {max(lv)}  "
                      f"dist { {l: lv.count(l) for l in sorted(set(lv))} }")
            else:
                st = [r["stable_s"] for r in sub]
                print(f"  stable_s: mean {np.mean(st):.2f}  max {np.max(st):.2f}")


if __name__ == "__main__":
    main()
