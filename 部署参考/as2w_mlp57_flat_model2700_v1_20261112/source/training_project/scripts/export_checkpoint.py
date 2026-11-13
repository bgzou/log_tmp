#!/usr/bin/env python3
"""Export a saved, non-normalized ELU MLP actor for frozen evaluation."""
import argparse
import hashlib
import json
from pathlib import Path

import torch
import yaml

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("checkpoint", type=Path)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
checkpoint = args.checkpoint.resolve()
cfg = yaml.safe_load((checkpoint.parent / "params/agent.yaml").read_text())["policy"]
if cfg["activation"] != "elu" or cfg["actor_obs_normalization"] or cfg.get("state_dependent_std", False):
    parser.error("This exporter supports the pinned unnormalized, fixed-std ELU MLP only")
saved = torch.load(checkpoint, map_location="cpu", weights_only=False)
state = {key.removeprefix("actor."): value for key, value in saved["model_state_dict"].items() if key.startswith("actor.")}
sizes = [state["0.weight"].shape[1], *cfg["actor_hidden_dims"], state["6.weight"].shape[0]]
layers = []
for index, (source, target) in enumerate(zip(sizes[:-1], sizes[1:])):
    layers.append(torch.nn.Linear(source, target))
    if index < len(sizes) - 2:
        layers.append(torch.nn.ELU())
actor = torch.nn.Sequential(*layers).eval()
actor.load_state_dict(state, strict=True)
with torch.inference_mode():
    result = actor(torch.zeros(2, sizes[0]))
if not torch.isfinite(result).all():
    raise RuntimeError("Nonfinite checkpoint actor output")
args.output.parent.mkdir(parents=True, exist_ok=True)
torch.jit.script(actor).save(str(args.output))
metadata = {"checkpoint": str(checkpoint), "checkpoint_sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest(), "saved_update_index": saved["iter"], "input_size": sizes[0], "output_size": sizes[-1], "policy": str(args.output.resolve()), "scope": "Unmodified deterministic actor mean; no exploration noise, no fine tuning."}
args.output.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
print(json.dumps(metadata, indent=2))
