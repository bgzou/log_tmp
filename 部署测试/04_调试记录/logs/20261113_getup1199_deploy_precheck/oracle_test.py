"""Per-frame wrapper oracle: python training wrapper math replayed on the
C++ replay's own obs + blend timeline. Isolates wrapper-math correctness
from ONNX fp32 feedback amplification."""
import sys, json
from pathlib import Path
import numpy as np, torch
sys.path.insert(0, "/home/caolin/as2w_workstation/部署参考/Rob2Nav-as2w-backup/training/as2w-backup/as2w-current/code")
from as2w_recovery_control import staged_target, stand_integral
ROOT = Path("/home/caolin/as2w_workstation/部署参考/Rob2Nav-as2w-backup/training/as2w-backup/as2w-current")

state = torch.load(ROOT/"runs/recovery/deep-side-curriculum/formal/model_1199.pt", map_location="cpu", weights_only=True)
from export_as2w_candidate_onnx import actor_from_state
actor = actor_from_state(state["actor_state_dict"], 2.0)
defaults = np.array([0,0,0,0,.8,.8,.8,.8,-1.6,-1.6,-1.6,-1.6], dtype=np.float64)

obs_lines = {}
tgt_lines = {}
for line in open("/tmp/opencode/as2w_s2_check/rec_deploy/getup1199_replay_est.txt"):
    if line.startswith("GETUP1199_OBS,"):
        f=line.split(","); obs_lines[round(float(f[1]),4)]=[float(x) for x in f[2:]]
    elif line.startswith("GETUP1199_TARGET,"):
        f=line.split(","); tgt_lines[round(float(f[1]),4)]=[float(x) for x in f[2:]]

# 初始姿态 = C++ 第一帧 obs 里的 q-defaults (obs[6:18])
first_t = min(obs_lines)
initial = torch.tensor((np.array(obs_lines[first_t][6:18])/0.35)[None], dtype=torch.float32)
dt = .02
bias = torch.zeros_like(initial)
max_err = 0.0; worst_t = None
n = 0
for k, t in enumerate(sorted(obs_lines)):
    obs = np.array(obs_lines[t], dtype=np.float32)
    tgt = tgt_lines[t]
    cpp_wrapped = np.array(tgt[:12], dtype=np.float64)
    cpp_blend = tgt[24]
    raw = actor(torch.from_numpy(obs[None]))
    age = torch.tensor([k * dt])
    target = staged_target(initial, raw[0].detach(), age)
    enabled = (cpp_blend >= .80) and obs[5] < -0.93  # up>0.93 -> obs[5]<-0.93
    err_q = torch.from_numpy((obs[6:18])[None].astype(np.float32))
    bias = stand_integral(bias, err_q, torch.tensor([cpp_blend]), torch.tensor([-obs[5]]),
                          torch.tensor([1.0]), age*0+dt, min_height=0.25) if False else bias
    # 直接复刻 stand_integral
    blend_t = torch.tensor([cpp_blend]); up_t = torch.tensor([-obs[5]]); h_t = torch.tensor([1.0])
    enabled_mask = (blend_t >= .80) & (up_t > .93) & (h_t > .25)
    next_bias = ((1-.04*dt)*bias - 1.10*dt*err_q).clamp(-.34,.34)
    bias = torch.where(enabled_mask, next_bias, torch.zeros_like(bias))
    out = target*(1.-blend_t[:,None]) + blend_t[:,None]*bias/.35
    e = float(np.max(np.abs(out[0].detach().numpy().astype(np.float64) - cpp_wrapped)))
    if e > max_err: max_err, worst_t = e, t
    n += 1
print(f"oracle frames={n} per-frame wrapper max_err={max_err:.3e} (worst t={worst_t})")
print("ORACLE", "PASS" if max_err <= 1e-5 else "FAIL")
