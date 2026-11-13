"""Rehydrate immutable source/assets into a separate, writable replay workspace."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument("--output",type=Path,required=True)
p.add_argument("--mode",choices=["training","evaluation"],default="evaluation")
p.add_argument("--python",type=Path,default=Path(sys.executable))
a=p.parse_args();out=a.output.resolve()
if out.exists() and any(out.iterdir()):p.error("Use an empty new workspace; existing files are never overwritten")
out.mkdir(parents=True,exist_ok=True)
shutil.copytree(ROOT/f"source/{a.mode}_project",out,dirs_exist_ok=True)
shutil.copytree(ROOT/"source/vendor",out/"vendor",dirs_exist_ok=True)
shutil.copytree(ROOT/"simulation/assets",out/"assets",dirs_exist_ok=True)
shutil.copy2(ROOT/"source/training_project/upstream.lock.json",out/"upstream.lock.json")
# Original source remains byte-identical. Local Git metadata only satisfies
# upstream logging; the generated commit is not the historical training commit.
subprocess.run(["git","init","-b","codex/handoff-replay",str(out)],check=True,stdout=subprocess.DEVNULL)
subprocess.run(["git","-C",str(out),"add","source","scripts","config","upstream.lock.json"],check=True)
subprocess.run(["git","-C",str(out),"-c","user.name=HandoffReplay","-c","user.email=offline@localhost","commit","-m","Rehydrate archived AS2W handoff source"],check=True,stdout=subprocess.DEVNULL)
environment=a.python.absolute().parent.parent
if not (environment/"bin/python").exists():p.error("--python must point to an installed Python environment's bin/python")
(out/".venv").symlink_to(environment,target_is_directory=True)
manifest=json.loads((out/"vendor/manifest.json").read_text())
for f in manifest["files"]:assert hashlib.sha256((out/f['path']).read_bytes()).hexdigest()==f['sha256']
body=json.loads((out/"assets/as2w/source/manifest.json").read_text())
for name,f in body["files"].items():assert hashlib.sha256((out/"assets/as2w/source"/name).read_bytes()).hexdigest()==f['sha256']
print(json.dumps({"workspace":str(out),"mode":a.mode,"python":str(a.python),"vendor_verified_files":len(manifest['files']),"asset_verified_files":len(body['files']),"note":"Install the declared Isaac runtime separately. All historical absolute paths in provenance are informational."},indent=2))
