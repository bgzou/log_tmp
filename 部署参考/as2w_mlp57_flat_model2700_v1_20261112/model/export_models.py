"""Reconstruct the selected actor and export portable inference artifacts on CPU."""
import argparse
import hashlib
import json
import os
from pathlib import Path
os.environ["CUDA_VISIBLE_DEVICES"]=""
import numpy as np
import onnx
import onnxruntime as ort
import torch

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument("--checkpoint",type=Path,default=ROOT/"model/selected_checkpoint.pt")
p.add_argument("--output",type=Path,required=True,help="New writable export directory; keep the delivered artifacts immutable")
a=p.parse_args()
torch.set_num_threads(2)
saved=torch.load(a.checkpoint,map_location="cpu",weights_only=False)
state={k.removeprefix("actor."):v for k,v in saved["model_state_dict"].items() if k.startswith("actor.")}
actor=torch.nn.Sequential(torch.nn.Linear(57,512),torch.nn.ELU(),torch.nn.Linear(512,256),torch.nn.ELU(),torch.nn.Linear(256,128),torch.nn.ELU(),torch.nn.Linear(128,16)).eval()
actor.load_state_dict(state,strict=True)
assert saved["iter"]==2700
a.output.mkdir(parents=True,exist_ok=True)
ts_path=a.output/"policy.ts"
if not ts_path.exists():torch.jit.script(actor).save(str(ts_path))
ts=torch.jit.load(str(ts_path),map_location="cpu").eval()
assert all(torch.equal(value,ts.state_dict()[key]) for key,value in state.items())
x=torch.tensor(np.random.default_rng(81200).normal(0,.3,(512,57)).astype(np.float32))
with torch.inference_mode():
    expected=actor(x).numpy();scripted=ts(x).numpy()
    np.testing.assert_allclose(scripted,expected,atol=0,rtol=0)
onnx_path=a.output/"policy.onnx"
torch.onnx.export(actor,torch.zeros(1,57),str(onnx_path),input_names=["observation"],output_names=["raw_action_mean"],dynamic_axes={"observation":{0:"batch"},"raw_action_mean":{0:"batch"}},opset_version=17,dynamo=False)
onnx.checker.check_model(str(onnx_path))
options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
session=ort.InferenceSession(str(onnx_path),sess_options=options,providers=["CPUExecutionProvider"])
max_error=0.
for batch in [1,4,512]:
    actual=session.run(["raw_action_mean"],{"observation":x[:batch].numpy()})[0]
    np.testing.assert_allclose(actual,expected[:batch],atol=2e-5,rtol=2e-5)
    max_error=max(max_error,float(np.abs(actual-expected[:batch]).max()))
digest=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
report={"checkpoint_sha256":digest(a.checkpoint),"checkpoint_saved_iteration":2700,"completed_updates":2701,
        "torchscript_sha256":digest(ts_path),"onnx_sha256":digest(onnx_path),"opset":17,
        "input":{"name":"observation","shape":["batch",57],"dtype":"float32"},
        "output":{"name":"raw_action_mean","shape":["batch",16],"dtype":"float32"},
        "tested_platform":"Linux x86_64 CPU","torch_version":torch.__version__,"onnx_version":onnx.__version__,"onnxruntime_version":ort.__version__,
        "batch_sizes_tested":[1,4,512],"random_seed":81200,"torchscript_max_absolute_error":float(np.abs(scripted-expected).max()),
        "onnx_max_absolute_error":max_error,"threshold":{"absolute":2e-5,"relative":2e-5},
        "arm64":"not_run","scope":"Export equivalence only; random inputs do not qualify motion capability. Raw actor mean, no normalization, action noise, tanh, residual or external controller."}
(a.output/"export_equivalence.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
