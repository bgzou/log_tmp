"""S1 parity check for the three latest AS2-W weights (Rob2Nav as2w-backup).

- rolling:  ORT(v3-evidence/policy.onnx) vs recorded actor-preclip.npy
- stepping: ORT(onnx-diagnostic/support-aware-1199/policy.onnx) vs torch actor rebuilt from formal/model_1199.pt (clip 2)
- recovery: ORT(onnx/deep-side-1199/policy.onnx) vs torch actor rebuilt from formal/model_1199.pt (clip 2)
"""
import sys
from pathlib import Path
import numpy as np
import torch
import onnxruntime as ort

ROOT = Path("/home/caolin/as2w_workstation/部署参考/Rob2Nav-as2w-backup/training/as2w-backup/as2w-current")
sys.path.insert(0, str(ROOT / "code"))
from export_as2w_candidate_onnx import actor_from_state

def ort_outputs(onnx_path, obs):
    so = ort.SessionOptions()
    so.intra_op_num_threads = 1
    sess = ort.InferenceSession(str(onnx_path), so, providers=["CPUExecutionProvider"])
    assert len(sess.get_inputs()) == 1, sess.get_inputs()
    return np.concatenate([sess.run(None, {sess.get_inputs()[0].name: o[None]})[0] for o in obs], axis=0)

def report(name, a, b):
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    err = np.abs(a - b)
    print(f"{name}: shape={a.shape} max_err={err.max():.3e} mean_err={err.mean():.3e}")

torch.set_num_threads(1)

# ---- rolling ----
roll = ROOT / "runs/rolling/actor-wheel-saturation-loss.Uliv0s/v3-evidence"
obs = np.load(roll / "policy-observations.npy", allow_pickle=False).astype(np.float32)
preclip = np.load(roll / "actor-preclip.npy", allow_pickle=False).astype(np.float32)
report("rolling ONNX vs actor-preclip.npy", ort_outputs(roll / "policy.onnx", obs), preclip)

# ---- stepping ----
step_run = ROOT / "runs/stepping/support-aware-reward.bp4984"
obs = np.load(step_run / "support-aware-mujoco-holdout-1199/policy-observations.npy", allow_pickle=False).astype(np.float32)
ckpt = torch.load(step_run / "formal/model_1199.pt", map_location="cpu", weights_only=True)
actor = actor_from_state(ckpt["actor_state_dict"], 2.0)
with torch.inference_mode():
    ref = np.concatenate([actor(torch.from_numpy(o[None])).numpy() for o in obs], axis=0)
report("stepping ONNX vs torch actor (model_1199)", ort_outputs(step_run / "onnx-diagnostic/support-aware-1199/policy.onnx", obs), ref)

# ---- recovery ----
rec = ROOT / "runs/recovery/deep-side-curriculum"
obs = np.load(rec / "deep-side-mujoco-1199-random/policy-observations.npy", allow_pickle=False).astype(np.float32)
ckpt = torch.load(rec / "formal/model_1199.pt", map_location="cpu", weights_only=True)
actor = actor_from_state(ckpt["actor_state_dict"], 2.0)
with torch.inference_mode():
    ref = np.concatenate([actor(torch.from_numpy(o[None])).numpy() for o in obs], axis=0)
report("recovery ONNX vs torch actor (model_1199)", ort_outputs(rec / "onnx/deep-side-1199/policy.onnx", obs), ref)

print("done")
