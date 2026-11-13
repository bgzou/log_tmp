import importlib.util, json, sys
from pathlib import Path
import numpy as np, torch
W=Path("/home/caolin/as2w_workstation"); BACK=W/"部署参考/Rob2Nav-as2w-backup/training/as2w-backup"
ROOT=BACK/"as2w-current"; DEP=BACK/"as2w-r284-release/deliveries/as2w-deploy"
sys.path.insert(0,str(ROOT/"code"))
for p in (DEP/"flat-r284-500-preview/runtime",DEP/"omni-blind-stairs-r152/runtime",DEP):
    sys.path.append(str(p))
spec=importlib.util.spec_from_file_location("evf","/tmp/opencode/as2w_s2_check/rec_deploy/eval_fixture_gen_est.py")
ev=importlib.util.module_from_spec(spec); spec.loader.exec_module(ev)
torch.set_num_threads(1)
state=torch.load(ROOT/"runs/recovery/deep-side-curriculum/formal/model_1199.pt",map_location="cpu",weights_only=True)
actor=ev.actor_from_state(state["actor_state_dict"],2.)
env=ev.OmniEnvironment(Path("/tmp/opencode/as2w_s2_check/assets_local"),1,stop_training=True)
bank=json.loads((ROOT/"runs/r290-three-skills/supported-getup-holdout.json").read_text())
rng=np.random.default_rng(20261113)
pre_q=np.median([p["leg_q"] for p in bank["prone"]],axis=0)
from prepare_as2w_supported_getup import quaternion
start=dict(height_m=float(np.median([p["height_m"] for p in bank["prone"]])),
           root_wxyz=list(map(float,quaternion(0.,0.))),
           leg_q=(pre_q+rng.normal(0,.05,12)).tolist())
r=ev.trial(env,actor,start,9001,[],True,False,0.,True,False,False)
print("passed:",r["passed"],"survived:",r["survived"],"frames:",len(r["fix_frames"]))
OUT=Path("/home/caolin/as2w_workstation/部署测试/04_调试记录/logs/20261113_getup1199_deploy_precheck")
with open(OUT/"getup1199_fixture_est.txt","w") as fx, open(OUT/"getup1199_expected_est.txt","w") as ex:
    for (tick,quat,qpos_full,qvel_full,sensed,wrapped,command,blend) in r["fix_frames"]:
        t=tick*env.dt
        fx.write(" ".join([f"{t:.6f}"]+[f"{v:.9g}" for v in quat]+[f"{v:.9g}" for v in sensed[:3]]
                          +[f"{v:.9g}" for v in qpos_full]+[f"{v:.9g}" for v in qvel_full])+"\n")
        ex.write(" ".join([f"{t:.6f}"]+[f"{v:.9g}" for v in wrapped]
                          +[f"{v:.9g}" for v in command]+[f"{blend:.9g}"])+"\n")
print("est fixture written")
