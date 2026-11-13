"""Recompute 6000 native frames, export outputs and independent C++ I/O mapping."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
os.environ["CUDA_VISIBLE_DEVICES"]=""
import numpy as np
import onnxruntime as ort
import torch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"runtime"))
from reference import observation,targets,gravity_from_quaternion_wxyz
p=argparse.ArgumentParser(description=__doc__)
p.add_argument("--samples",type=Path,default=ROOT/"simulation/native_replay/native_samples.npz")
p.add_argument("--report",type=Path,help="Optional new report; omit to leave the handoff unchanged")
a=p.parse_args()
torch.set_num_threads(2)
d=np.load(a.samples)
flat=lambda k:d[k].reshape(-1,d[k].shape[-1])
state_keys=("gyro_body","gravity_body","command_body","joint_q","joint_dq","previous_raw_action")
state={k:flat(k) for k in state_keys}
obs=observation(**state);original=flat("observation");raw=flat("raw_action")
np.testing.assert_allclose(obs,original,atol=2e-6,rtol=2e-6)
gravity=gravity_from_quaternion_wxyz(flat("root_quaternion_wxyz_before"))
np.testing.assert_allclose(gravity,state["gravity_body"],atol=2e-6,rtol=2e-6)
expected=targets(raw)
for key,value in expected.items():np.testing.assert_allclose(value,flat(key),atol=2e-6,rtol=2e-6)
assert np.array_equal(d["previous_raw_action"][1:],d["raw_action"][:-1])
assert np.all(d["previous_raw_action"][0]==0)
assert np.array_equal(d["next_observation"][...,-16:],np.clip(d["raw_action"],-100,100))
ts=torch.jit.load(str(ROOT/"model/policy.ts"),map_location="cpu").eval()
opts=ort.SessionOptions();opts.intra_op_num_threads=2;opts.inter_op_num_threads=1
ort_session=ort.InferenceSession(str(ROOT/"model/policy.onnx"),sess_options=opts,providers=["CPUExecutionProvider"])
with torch.inference_mode():
    ts_values=ts(torch.from_numpy(obs)).numpy()
onnx_values=ort_session.run(["raw_action_mean"],{"observation":obs})[0]
np.testing.assert_allclose(ts_values,raw,atol=2e-5,rtol=2e-5)
np.testing.assert_allclose(onnx_values,raw,atol=2e-5,rtol=2e-5)
for values in [ts_values,onnx_values]:
    for key in ["q_des","dq_des"]:np.testing.assert_allclose(targets(values)[key],flat(key),atol=2e-4,rtol=2e-5)
# Clip-order and ignored wheel-phase probes are interface checks, not new motion trials.
stress=np.random.default_rng(118200).uniform(-1000,1000,(12,73)).astype(np.float32)
native=np.concatenate([state[k] for k in state_keys]+[raw],axis=-1)
inputs=np.concatenate([native,stress],axis=0)
cpp_obs=observation(inputs[:,:3],inputs[:,3:6],inputs[:,6:9],inputs[:,9:25],inputs[:,25:41],inputs[:,41:57])
cpp_targets=targets(inputs[:,57:73])
expected_cpp=np.concatenate([cpp_obs]+[cpp_targets[k] for k in ["q_des","dq_des","kp","kd","tau_ff","next_previous_raw_action"]],axis=1)
with tempfile.TemporaryDirectory() as tmp:
    binary=Path(tmp)/"contract"
    subprocess.run(["g++","-std=c++17","-O2","-ffp-contract=off",str(ROOT/"replay/cpp_contract.cpp"),"-o",str(binary)],check=True)
    text=io.StringIO();np.savetxt(text,inputs,fmt="%.9g")
    run=subprocess.run([str(binary)],input=text.getvalue(),text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
    actual_cpp=np.loadtxt(io.StringIO(run.stdout),dtype=np.float32)
np.testing.assert_allclose(actual_cpp,expected_cpp,atol=2e-6,rtol=2e-6)
def error(actual,expected):
    delta=np.abs(actual-expected);idx=np.unravel_index(int(delta.argmax()),delta.shape)
    return {"max_absolute":float(delta[idx]),"flat_frame":int(idx[0]),"component":int(idx[1]),"first_exceedance":None}
r={"status":"passed","native_frames":len(obs),"sequence_frames":int(d['observation'].shape[0]),"cases":int(d['observation'].shape[1]),
   "samples_sha256":hashlib.sha256(a.samples.read_bytes()).hexdigest(),
   "observation":error(obs,original),"gravity_from_quaternion":error(gravity,state['gravity_body']),
   "torchscript_cpu_vs_native_gpu":error(ts_values,raw),"onnx_cpu_vs_native_gpu":error(onnx_values,raw),
   "cpp_observation_and_targets":error(actual_cpp,expected_cpp),"cpp_synthetic_clip_cases":12,
   "next_previous_action":"exact","torchscript_version":torch.__version__,"onnxruntime_version":ort.__version__,
   "thresholds":{"observation_absolute":2e-6,"raw_action_absolute":2e-5,"raw_action_relative":2e-5,"target_absolute":2e-4,"target_relative":2e-5,"cpp_absolute":2e-6},
   "tested_platform":"Linux x86_64; C++ g++; ONNX CPUExecutionProvider; native PhysX GPU",
   "arm64":"not_run","cpp_model_inference":"not_run; C++ observation/target/state mapping tested only",
   "scope":"Offline parity; no second-simulator dynamics, robot publishing, or hardware control acceptance."}
if a.report:
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(r,indent=2)+"\n")
print(json.dumps(r,indent=2))
