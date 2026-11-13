"""Repeat the archived 39-command/four-initial-condition PhysX evaluation."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument("--workspace",type=Path,required=True,help="prepare_workspace.py --mode evaluation output")
p.add_argument("--output",type=Path,required=True)
p.add_argument("--gpu",type=int,default=1)
a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
policy=out/"policy.pt";shutil.copy2(ROOT/"model/policy.ts",policy)
metadata={"checkpoint":str(ROOT/"model/selected_checkpoint.pt"),"checkpoint_sha256":hashlib.sha256((ROOT/"model/selected_checkpoint.pt").read_bytes()).hexdigest(),"saved_update_index":2700,"input_size":57,"output_size":16,"policy":str(policy)}
policy.with_suffix('.json').write_text(json.dumps(metadata,indent=2)+'\n')
cmd=[str(a.workspace.resolve()/".venv/bin/python"),str(a.workspace.resolve()/"scripts/evaluate.py"),"--gpu",str(a.gpu),"--speed-sweep","--repeats","4","--seconds","8","--policy",str(policy),"--output",str(out/"evaluation")]
print(json.dumps(cmd,indent=2),flush=True)
raise SystemExit(subprocess.call(cmd,cwd=a.workspace))
