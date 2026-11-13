#!/usr/bin/env python3
"""Check source integrity and record the actual Python/Isaac runtime."""
import argparse
import hashlib
import importlib.metadata as metadata
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--verify-sources", action="store_true")
args = parser.parse_args()
result = {"python": sys.version, "executable": sys.executable, "packages": {}, "sources": json.loads((ROOT / "upstream.lock.json").read_text())}
for package in ["torch", "mujoco", "numpy", "isaacsim", "isaaclab", "isaaclab_rl", "rsl-rl-lib", "gymnasium", "tensordict"]:
    result["packages"][package] = metadata.version(package)
lab = Path(importlib.util.find_spec("isaaclab").origin).parents[3]
result["isaaclab_checkout"] = str(lab)
result["isaaclab_commit"] = subprocess.check_output(["git", "-C", str(lab), "rev-parse", "HEAD"], text=True).strip()
result["isaaclab_version_file"] = (lab / "VERSION").read_text().strip()
if result["isaaclab_version_file"] != "2.3.2":
    raise RuntimeError("This reproduction expects Isaac Lab 2.3.2")
if args.verify_sources:
    manifest = json.loads((ROOT / "vendor/manifest.json").read_text())
    for file in manifest["files"]:
        digest = hashlib.sha256((ROOT / file["path"]).read_bytes()).hexdigest()
        if digest != file["sha256"]:
            raise RuntimeError(f"Modified upstream file: {file['path']}")
    result["verified_source_files"] = len(manifest["files"])
    sys.path.insert(0, str(ROOT / "source"))
    from as2w_robot_lab.morphology import model_contract, load_contract
    result["as2w_model"] = model_contract()
    assert result["as2w_model"] == load_contract(), "Regenerate config/as2w_robot.json from official assets"
(ROOT / "outputs/runtime.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
