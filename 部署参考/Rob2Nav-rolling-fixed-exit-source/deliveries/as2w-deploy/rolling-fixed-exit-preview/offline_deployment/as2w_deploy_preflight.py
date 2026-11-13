"""Offline checks for an AS2-W policy, manifest and motor binding."""
import argparse
import hashlib
import json
from pathlib import Path

import onnxruntime as ort


def validate_binding(reference, require_hardware):
    rows = reference["mapping"]
    names = [f"{leg}_{part}" for part in ("hip","thigh","calf","foot")
             for leg in ("FL","FR","RL","RR")]
    if [(r["policy_index"],r["joint_name"]) for r in rows] != list(enumerate(names)):
        raise ValueError("Unexpected AS2-W policy joint order")
    for row in rows:
        effort = row["urdf_limits"]["effort"]
        if not 0 < row["simulation_effort_90_nm"] <= .9*effort:
            raise ValueError(f"Unsafe simulated effort at {row['joint_name']}")
        bound = row["urdf_angle_rad"]
        if bound is not None:
            lo, hi = row["simulation_angle_90_rad"]
            stand = row["simulation_fixed_stand_rad"]
            lower = stand+.9*(bound[0]-stand)
            upper = stand+.9*(bound[1]-stand)
            if not (lower-1e-9 <= lo <= stand <= hi <= upper+1e-9):
                raise ValueError(f"Unsafe simulated angle at {row['joint_name']}")
    if not require_hardware:
        return
    missing = [r["joint_name"] for r in rows if any(r[k] is None for k in (
               "dds_slot","hardware_direction","hardware_zero_rad","hardware_effort_limit_nm"))]
    if missing:
        raise ValueError("Unverified hardware bindings: "+", ".join(missing))
    slots = [r["dds_slot"] for r in rows]
    if len(set(slots)) != 16 or any(not isinstance(x,int) or x<0 or x>=35 for x in slots):
        raise ValueError("Invalid HG motor slot table")
    if any(r["hardware_direction"] not in (-1,1) or r["hardware_effort_limit_nm"]<=0 for r in rows):
        raise ValueError("Invalid hardware axis sign or effort limit")
    if not reference["real_actuation_enabled"]:
        raise ValueError("Deployment manifest is simulation-only")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("reference",type=Path)
    p.add_argument("model_directory",type=Path)
    p.add_argument("--require-hardware-map",action="store_true")
    a=p.parse_args()
    try:
        reference=json.loads(a.reference.read_text())
        validate_binding(reference,a.require_hardware_map)
        model=a.model_directory/"policy.onnx"
        manifest=json.loads((a.model_directory/"onnx-parity.json").read_text())
        if hashlib.sha256(model.read_bytes()).hexdigest()!=manifest["onnx_sha256"]:
            raise ValueError("ONNX checksum mismatch")
        options=ort.SessionOptions()
        options.intra_op_num_threads=1
        r=ort.InferenceSession(str(model),sess_options=options,providers=["CPUExecutionProvider"])
        inputs,outputs=r.get_inputs(),r.get_outputs()
        for nodes,name,key in ((inputs,"obs","input_shape"),(outputs,"actions","output_shape")):
            if len(nodes)!=1 or (nodes[0].name,nodes[0].shape,nodes[0].type)!=(name,manifest[key],"tensor(float)"):
                raise ValueError(f"Unexpected ONNX {name} signature")
        if manifest["max_action_error"] > 1e-4:
            raise ValueError("Policy parity beyond tolerance")
        print("OFFLINE_PREFLIGHT_OK", manifest["input_shape"], manifest["output_shape"])
    except (ValueError, OSError, KeyError) as error:
        p.exit(2,f"AS2-W preflight: {error}\n")


if __name__=="__main__":
    main()
