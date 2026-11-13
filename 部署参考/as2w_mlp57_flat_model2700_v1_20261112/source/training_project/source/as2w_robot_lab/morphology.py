"""AS2W model contract, independent of Isaac Sim initialization."""
import hashlib
import json
from pathlib import Path
import struct
import xml.etree.ElementTree as ET

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
ASSET_DIR = ROOT / "assets/as2w/source"
LEGS = ("FR", "FL", "RR", "RL")
LEG_JOINTS = [f"{leg}_{joint}" for leg in LEGS for joint in ("hip", "thigh", "calf")]
WHEEL_JOINTS = [f"{leg}_foot" for leg in LEGS]
JOINTS = LEG_JOINTS + WHEEL_JOINTS


def model_contract():
    """Verify official asset bytes and derive kinematics, limits and floor height."""
    manifest = json.loads((ASSET_DIR / "manifest.json").read_text())
    for name, record in manifest["files"].items():
        if hashlib.sha256((ASSET_DIR / name).read_bytes()).hexdigest() != record["sha256"]:
            raise ValueError(f"AS2W source hash mismatch: {name}")
    robot = ET.parse(ASSET_DIR / "as2w.urdf").getroot()
    joints = {j.get("name"): j for j in robot.findall("joint") if j.get("type") != "fixed"}
    assert set(joints) == set(JOINTS), set(joints)
    nominal = {name: {"hip": 0.0, "thigh": 0.65, "calf": -1.3, "foot": 0.0}[name.rsplit("_", 1)[1]] for name in JOINTS}
    limits = {name: {k: float(v) for k, v in joints[name].find("limit").attrib.items()} for name in JOINTS}
    sample = json.loads((ROOT / "config/quadruped_recorded_sample.json").read_text())
    assert sample["joint_names_in_motor_slot_order"] == JOINTS
    kp, kd = sample["nearby_motor_command"]["kp"], sample["nearby_motor_command"]["kd"]
    assert kp[:12] == [40.0] * 12 and kd[:12] == [1.0] * 12
    assert kp[12:] == [0.0] * 4 and kd[12:] == [1.0] * 4

    def rotation(axis, angle):
        x, y, z = axis / np.linalg.norm(axis)
        cross = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
        return np.eye(3) + np.sin(angle) * cross + (1 - np.cos(angle)) * cross @ cross

    def origin(node):
        t = np.eye(4)
        if node is not None:
            t[:3, 3] = np.fromstring(node.get("xyz", "0 0 0"), sep=" ")
            roll, pitch, yaw = np.fromstring(node.get("rpy", "0 0 0"), sep=" ")
            t[:3, :3] = rotation(np.array([0, 0, 1]), yaw) @ rotation(np.array([0, 1, 0]), pitch) @ rotation(np.array([1, 0, 0]), roll)
        return t

    transforms = {"base_link": np.eye(4)}
    pending = list(robot.findall("joint"))
    while pending:
        ready = [j for j in pending if j.find("parent").get("link") in transforms]
        if not ready:
            raise ValueError("Disconnected AS2W URDF")
        for joint in ready:
            motion = np.eye(4)
            if joint.get("type") != "fixed":
                motion[:3, :3] = rotation(np.fromstring(joint.find("axis").get("xyz"), sep=" "), nominal[joint.get("name")])
            transforms[joint.find("child").get("link")] = transforms[joint.find("parent").get("link")] @ origin(joint.find("origin")) @ motion
            pending.remove(joint)
    floor_z = float("inf")
    wheel_geometry = {}
    for link in robot.findall("link"):
        for collision in link.findall("collision"):
            mesh = collision.find("geometry/mesh")
            if mesh is None:
                raise ValueError("Expected official mesh collision")
            raw = (ASSET_DIR / mesh.get("filename")).read_bytes()
            count = struct.unpack_from("<I", raw, 80)[0]
            if len(raw) != 84 + 50 * count:
                raise ValueError("Expected binary STL")
            vertices = np.array([v[3:12] for v in struct.iter_unpack("<12fH", raw[84:])]).reshape(-1, 3)
            transform = transforms[link.get("name")] @ origin(collision.find("origin"))
            floor_z = min(floor_z, float((vertices @ transform[:3, :3].T + transform[:3, 3])[:, 2].min()))
            if link.get("name") in WHEEL_JOINTS:
                extent = vertices.max(axis=0) - vertices.min(axis=0)
                wheel_geometry[link.get("name")] = {"mesh_radius_m": float(max(extent[0], extent[2]) / 2), "mesh_half_width_m": float(extent[1] / 2), "center_in_base_m": transforms[link.get("name")][:3, 3].tolist()}
    return {
        "robot": "Unitree AS2W", "official_asset_source": {k: manifest[k] for k in ("repository", "commit", "path")},
        "urdf_sha256": manifest["files"]["as2w.urdf"]["sha256"],
        "nominal_mass_kg": sum(float(x.get("value")) for x in robot.findall("link/inertial/mass")),
        "action_joint_order": JOINTS, "nominal_joint_pos_rad": nominal,
        "nominal_pose_source": "Symmetric simulation reference from as2w-sim/config/robot.json (0/.65/-1.3); not a measured pose or loaded B2W reference.",
        "initial_base_height_m": -floor_z + 0.005,
        "initial_clearance_m": 0.005, "joint_limits": limits, "wheels": wheel_geometry,
        "motor_pd": {"leg_kp": kp[0], "leg_kd": kd[0], "wheel_kp": kp[12], "wheel_kd": kd[12]},
        "pd_source": "config/quadruped_recorded_sample.json: mode-3 quadruped packet, 2026-11-06; one observed mode, not a universal firmware specification.",
        "actuator_model": "Same DC motor approximation as robot_lab B2W for legs; max torque/speed from AS2W URDF. Full measured torque-speed curves are unavailable. Implicit wheel velocity PD.",
    }


def load_contract():
    return json.loads((ROOT / "config/as2w_robot.json").read_text())
