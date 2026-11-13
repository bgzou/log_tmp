"""Run a bounded native I/O replay in an already prepared pinned workspace."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"source/evaluation_project/scripts"))
from single_gpu import isolate_environment,KIT_ARGS
p=argparse.ArgumentParser(description=__doc__)
p.add_argument("--workspace",type=Path,required=True)
p.add_argument("--gpu",type=int,default=1)
p.add_argument("--output",type=Path,required=True,help="A new result directory outside the immutable handoff")
a=p.parse_args()
env=isolate_environment(os.environ,a.gpu)
env["DISPLAY"]=""
cmd=[sys.executable,str(ROOT/"simulation/record_native_isaac.py"),"--workspace",str(a.workspace.resolve()),"--output",str(a.output.resolve()),"--headless","--device","cuda:0",f"--kit_args={KIT_ARGS}"]
raise SystemExit(subprocess.call(cmd,cwd=a.workspace,env=env))
