"""S1 parity part2: stepping/recovery ONNX vs rebuilt torch actor on random inputs."""
import sys
from pathlib import Path
import numpy as np
import torch
import onnxruntime as ort

ROOT = Path("/home/caolin/as2w_workstation/部署参考/Rob2Nav-as2w-backup/training/as2w-backup/as2w-current")
sys.path.insert(0, str(ROOT / "code"))
from export_as2w_candidate_onnx import actor_from_state

def check(name, onnx_path, ckpt_path, clip, width, n=4000):
    so = ort.SessionOptions(); so.intra_op_num_threads = 1
    sess = ort.InferenceSession(str(onnx_path), so, providers=["CPUExecutionProvider"])
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=True)
    actor = actor_from_state(ckpt["actor_state_dict"], clip)
    rng = np.random.default_rng(20261113)
    obs = rng.uniform(-2.5, 2.5, size=(n, width)).astype(np.float32)
    outs = np.concatenate([sess.run(None, {sess.get_inputs()[0].name: o[None]})[0] for o in obs], axis=0)
    with torch.inference_mode():
        ref = np.concatenate([actor(torch.from_numpy(o[None])).numpy() for o in obs], axis=0)
    err = np.abs(outs.astype(np.float64) - ref.astype(np.float64))
    print(f"{name}: max_err={err.max():.3e} mean={err.mean():.3e}")

torch.set_num_threads(1)
step = ROOT / "runs/stepping/support-aware-reward.bp4984"
rec = ROOT / "runs/recovery/deep-side-curriculum"
check("stepping 1199 (random)", step/"onnx-diagnostic/support-aware-1199/policy.onnx", step/"formal/model_1199.pt", 2.0, 47)
check("recovery 1199 (random)", rec/"onnx/deep-side-1199/policy.onnx", rec/"formal/model_1199.pt", 2.0, 42)
print("done")
