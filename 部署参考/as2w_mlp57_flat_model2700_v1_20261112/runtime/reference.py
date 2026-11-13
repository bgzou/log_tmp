"""Nominal deterministic MLP57 interface. No DDS, motor publishing or motion FSM."""
from pathlib import Path
import json
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BODY = json.loads((ROOT / "source/training_project/config/as2w_robot.json").read_text())
JOINTS = BODY["action_joint_order"]
Q0 = np.array([BODY["nominal_joint_pos_rad"][n] for n in JOINTS], dtype=np.float32)
SCALE = np.array([.125 if n.endswith("_hip") else .25 for n in JOINTS[:12]], dtype=np.float32)


def _array(value, size):
    value = np.asarray(value, dtype=np.float32)
    if value.shape[-1] != size or not np.isfinite(value).all():
        raise ValueError(f"Expected finite trailing dimension {size}")
    return value


def gravity_from_quaternion_wxyz(quaternion):
    """Quaternion rotates body vectors into world; gravity is R(q)^T [0,0,-1]."""
    q = _array(quaternion, 4)
    norm = np.linalg.norm(q, axis=-1, keepdims=True)
    if np.any(np.abs(norm - 1) > 1e-3):
        raise ValueError("Expected unit body-to-world quaternion")
    q = q / norm
    w, x, y, z = np.moveaxis(q, -1, 0)
    return np.stack((2*(w*y-x*z), -2*(w*x+y*z), 2*(x*x+y*y)-1), axis=-1).astype(np.float32)


def observation(gyro_body, gravity_body, command_body, joint_q, joint_dq, previous_raw_action):
    """Exact noise-off policy term order: physical value -> [-100,100] -> scale."""
    gyro = _array(gyro_body, 3)
    gravity = _array(gravity_body, 3)
    command = _array(command_body, 3)
    q = _array(joint_q, 16)
    dq = _array(joint_dq, 16)
    previous = _array(previous_raw_action, 16)
    position_error = q - Q0
    position_error = position_error.copy()
    position_error[..., 12:] = 0
    blocks = [np.clip(gyro, -100, 100)*np.float32(.25), np.clip(gravity, -100, 100),
              np.clip(command, -100, 100), np.clip(position_error, -100, 100),
              np.clip(dq, -100, 100)*np.float32(.05), np.clip(previous, -100, 100)]
    return np.concatenate(blocks, axis=-1).astype(np.float32)


def targets(raw_action):
    """Clip physical processed targets, not raw actions. Previous action stays raw."""
    raw = _array(raw_action, 16)
    shape = raw.shape
    q = np.broadcast_to(Q0, shape).copy()
    q[..., :12] = np.clip(raw[..., :12] * SCALE + Q0[:12], -100, 100)
    # Wheel q is unused because Kp=0. It has no integrated/locked wheel-angle state.
    dq = np.zeros(shape, dtype=np.float32)
    dq[..., 12:] = np.clip(raw[..., 12:] * np.float32(5), -100, 100)
    kp = np.broadcast_to(np.array([40]*12+[0]*4, dtype=np.float32), shape).copy()
    kd = np.ones(shape, dtype=np.float32)
    return {"q_des": q, "dq_des": dq, "kp": kp, "kd": kd,
            "tau_ff": np.zeros(shape, dtype=np.float32), "next_previous_raw_action": raw.copy()}


def direct_velocity_command(vx, vy, wz):
    """Physical body-frame units; no joystick mapping, slope limiter or timeout."""
    value = _array([vx, vy, wz], 3)
    if np.any(np.abs(value) > 1):
        raise ValueError("This archived policy was trained only within +/-1 per axis")
    return value


def training_command_postprocess(command):
    """Only the training sampler's XY radial threshold; NOT used by direct replay."""
    value = _array(command, 3).copy()
    value[..., :2] *= (np.linalg.norm(value[..., :2], axis=-1) > .2)[..., None]
    return value


class Runtime:
    """One controller instance; infer accepts [B,57] and returns raw [B,16]."""
    def __init__(self, infer):
        self.infer = infer
        self.reset()

    def reset(self):
        self.previous_raw_action = np.zeros(16, dtype=np.float32)

    def step(self, gyro_body, gravity_body, command_body, joint_q, joint_dq):
        obs = observation(gyro_body, gravity_body, command_body, joint_q, joint_dq, self.previous_raw_action)
        raw = _array(self.infer(obs[None])[0], 16)
        result = targets(raw)
        self.previous_raw_action = raw.copy()
        return {"observation": obs, "raw_action": raw, **result}
