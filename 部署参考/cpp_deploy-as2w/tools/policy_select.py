#!/usr/bin/env python3
"""Select a delivered AS2-W model for offline verification or read-only shadow.

This intentionally has no motor-command or live policy-switching operation.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "deploy" / "robots" / "as2w" / "config" / "config.yaml"


def catalog():
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "models" / "manifest.json").read_text(encoding="utf-8"))
    if data.get("schema") != 1 or data.get("control_period_s") != 0.02:
        raise ValueError("Unsupported policy catalog schema or control period")
    entries = data.get("policies")
    if not isinstance(entries, dict) or set(entries) != set(manifest["models"]):
        raise ValueError("Policy catalog and delivered model manifest differ")
    for name, entry in entries.items():
        if entry.get("kind") != manifest["models"][name]["mode"]:
            raise ValueError(f"Policy mode mismatch: {name}")
        if entry.get("model") != f"models/{name}.bin" or entry.get("fixture") != f"models/{name}.fixture":
            raise ValueError(f"Unexpected model or fixture path: {name}")
        if entry.get("online_shadow") is not (entry["kind"] == "stairs"):
            raise ValueError(f"Invalid shadow eligibility: {name}")
        for key in ("model", "fixture"):
            if not (ROOT / entry[key]).is_file():
                raise FileNotFoundError(ROOT / entry[key])
    return entries


def offline_binary():
    candidates = (ROOT / "build" / "as2w_deploy", ROOT / "build_win" / "as2w_deploy.exe")
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError("Build as2w_deploy first: bash tools/field.sh build")


def benchmark_binary():
    candidates = (ROOT / "build" / "as2w_bench", ROOT / "build_win" / "as2w_bench.exe")
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError("Build as2w_bench first: bash tools/field.sh build")


def run_verify(entries, name):
    names = list(entries) if name == "all" else [name]
    if any(item not in entries for item in names):
        raise ValueError(f"Unknown policy: {name}")
    exe = offline_binary()
    for item in names:
        entry = entries[item]
        print(f"VERIFY {item} ({entry['kind']})", flush=True)
        subprocess.run([str(exe), "verify", str(ROOT / entry["model"]),
                        str(ROOT / entry["fixture"])], check=True)


def run_shadow(entries, name, nic, mapping, seconds, topic):
    if name not in entries:
        raise ValueError(f"Unknown policy: {name}")
    entry = entries[name]
    if not entry["online_shadow"]:
        raise ValueError("Recovery online shadow is blocked: verified body-frame velocity is unavailable")
    if seconds < 1 or seconds > 300:
        raise ValueError("Seconds must be 1..300")
    sdk_exe = ROOT / "build-sdk2" / "as2w_sdk2"
    if not sdk_exe.is_file():
        raise FileNotFoundError("Build the CPRO SDK2 diagnostic binary first")
    mapping_path = Path(mapping).resolve()
    if not mapping_path.is_file():
        raise FileNotFoundError(mapping_path)
    print(f"SHADOW_ONLY {name}; no LowCmd will be published", flush=True)
    subprocess.run([str(sdk_exe), "shadow", nic, topic, str(ROOT / entry["model"]),
                    str(mapping_path), str(seconds), "--imu-wxyz-body-to-world"], check=True)


def run_bench(entries, name, iterations):
    if name not in entries:
        raise ValueError(f"Unknown policy: {name}")
    if iterations < 100 or iterations > 1000000:
        raise ValueError("Iterations must be 100..1000000")
    entry = entries[name]
    print(f"BENCH {name} ({entry['kind']}); compute only, no DDS", flush=True)
    subprocess.run([str(benchmark_binary()), str(ROOT / entry["model"]),
                    str(ROOT / entry["fixture"]), str(iterations)], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="List delivered models and test eligibility")
    verify = commands.add_parser("verify", help="Run the delivered 60-frame reference trace")
    verify.add_argument("name", help="Policy name or all")
    shadow = commands.add_parser("shadow", help="Read-only live preview for a stairs policy")
    shadow.add_argument("name")
    shadow.add_argument("nic", help="CPRO Ubuntu network interface toward AS2-W")
    shadow.add_argument("mapping", help="Verified 16-axis calibrated.map")
    shadow.add_argument("seconds", type=int)
    shadow.add_argument("topic", nargs="?", default="rt/lowstate")
    bench = commands.add_parser("bench", help="Time inference on this CPU; no robot connection")
    bench.add_argument("name")
    bench.add_argument("iterations", type=int, nargs="?", default=2000)
    args = parser.parse_args()
    entries = catalog()
    if args.command == "list":
        for name, entry in entries.items():
            stage = "offline + read-only shadow" if entry["online_shadow"] else "offline only"
            print(f"{name:18} {entry['kind']:8} {stage}")
    elif args.command == "verify":
        run_verify(entries, args.name)
    elif args.command == "bench":
        run_bench(entries, args.name, args.iterations)
    else:
        run_shadow(entries, args.name, args.nic, args.mapping, args.seconds, args.topic)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, FileNotFoundError, subprocess.CalledProcessError) as error:
        print(f"policy_select: {error}", file=sys.stderr)
        sys.exit(1)
