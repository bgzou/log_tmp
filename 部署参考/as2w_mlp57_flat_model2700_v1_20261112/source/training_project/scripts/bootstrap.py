#!/usr/bin/env python3
"""Fetch immutable upstream snapshots; verify each file's Git blob hash."""
from __future__ import annotations

import concurrent.futures
import hashlib
import json
from pathlib import Path
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def selected(name: str, path: str) -> bool:
    if path in {"LICENSE", "LICENSE.md", "README.md", "README_CN.md"}:
        return True
    if name == "robot_lab":
        return (
            path.startswith("source/robot_lab/data/Robots/unitree/b2w_description/")
            or (path.startswith("source/robot_lab/") and "/data/" not in path)
            or path.startswith("scripts/reinforcement_learning/rsl_rl/")
            or path in {"pyproject.toml", "VERSION"}
        )
    if name == "rl_sar":
        return path.startswith("policy/b2w/") or path in {
            "src/rl_sar/library/core/rl_sdk/rl_sdk.cpp",
            "src/rl_sar/library/core/rl_sdk/rl_sdk.hpp",
            "src/rl_sar/src/rl_sim_mujoco.cpp",
            "src/rl_sar/fsm_robot/fsm_b2w.hpp",
        }
    return path.startswith("b2w_description/mjcf/")


def download(url: str) -> bytes:
    for attempt in range(4):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "b2w-repro/0.1"})
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except (OSError, urllib.error.URLError):
            if attempt == 3:
                raise
            time.sleep(1 + attempt)
    raise RuntimeError("unreachable")


def git_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def main() -> None:
    lock = json.loads((ROOT / "upstream.lock.json").read_text())
    entries = []
    for name, spec in lock.items():
        cache = ROOT / "vendor" / f"{name}_tree.json"
        if cache.exists():
            tree = json.loads(cache.read_text())
            if tree.get("sha") != spec["commit"]:
                raise RuntimeError(f"Unexpected cached tree for {name}")
        else:
            tree = json.loads(download(f"https://api.github.com/repos/{spec['repo']}/git/trees/{spec['commit']}?recursive=1"))
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(tree))
        if tree.get("truncated"):
            raise RuntimeError(f"Truncated source tree: {name}")
        entries.extend((name, spec, entry) for entry in tree["tree"] if entry["type"] == "blob" and selected(name, entry["path"]))

    def fetch(job):
        name, spec, entry = job
        path = ROOT / "vendor" / name / entry["path"]
        data = path.read_bytes() if path.exists() else b""
        if git_sha(data) != entry["sha"]:
            data = download(f"https://raw.githubusercontent.com/{spec['repo']}/{spec['commit']}/{entry['path']}")
            if git_sha(data) != entry["sha"]:
                raise RuntimeError(f"Source checksum mismatch: {name}/{entry['path']}")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return {"path": str(path.relative_to(ROOT)), "git_blob": entry["sha"], "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}

    manifest = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for index, entry in enumerate(pool.map(fetch, entries), 1):
            manifest.append(entry)
            if index % 40 == 0:
                print(f"Verified {index}/{len(entries)} files", flush=True)
    (ROOT / "vendor" / "manifest.json").write_text(json.dumps({"sources": lock, "files": manifest}, indent=2) + "\n")
    print(f"Ready: {len(manifest)} verified files, {sum(x['bytes'] for x in manifest) / 1e6:.1f} MB", flush=True)


if __name__ == "__main__":
    main()
