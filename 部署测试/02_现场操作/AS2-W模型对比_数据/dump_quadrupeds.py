import json, sys
from pathlib import Path

p = Path(r"D:\Projects\Athena\运动控制\Collie\AS2-W_CPRO\.dsh_tmp\urdf_facts.json")
d = json.loads(p.read_text(encoding="utf-8"))["facts"]
want = ["as2w_description", "as2_description", "go2w_description", "go2_description",
        "b2w_description", "b2_description\\\\urdf", "a1_description", "aliengo_description"]

def show(key):
    f = d[key]
    print("=" * 100)
    print(key, "| robot=", f["robot"], "| base=", f["base_link"], "| links=", f["n_links"],
          "| movable=", f["n_movable"], "| fixed=", f["n_fixed"], "| mass=", round(f["total_mass"], 3))
    print("  base_mass=", f["base_mass"], " base_com=", [round(x, 4) for x in f["base_com"]],
          " base_I=", [round(x, 5) for x in f["base_inertia"]])
    print("  base_collision=", f["base_collision"], " box=", f["base_collision_box"])
    print("  collision_types=", f["collision_types"], " dynamics_tag=", f["has_dynamics"])
    print("  fixed_children=", f["fixed_children"])
    print("  sensor_links=", json.dumps(f["sensor_links"], ensure_ascii=False)[:600])
    print("  link_masses:")
    for k, v in sorted(f["link_masses"].items(), key=lambda kv: -kv[1]):
        print(f"     {k:>14s} {v:9.4f}")
    print("  legs:")
    for leg, info in f["legs"].items():
        segs = " | ".join(f"{s['joint']}:{s['length']:.4f}" for s in info["chain"])
        print(f"     {leg:>4s} mass={info['mass']:.4f} n={info['n_movable']}  {segs}")
    print("  wheels:")
    for jn, w in f["wheels"].items():
        print(f"     {jn:>6s} r={w['radius']} center={[round(x,4) for x in (w['center'] or [])]} limit={w['limit']}")
    print("  feet_q0:", {k: [round(x, 4) for x in (v or [])] for k, v in f["feet_q0"].items()})
    print("  movable joints:")
    for jn, jv in f["movable_joints"].items():
        lim = jv["limit"] or {}
        print(f"     {jn:>12s} {jv['type']:>10s} axis={jv['axis']} lim=({lim.get('lower')},{lim.get('upper')}) "
              f"eff={lim.get('effort')} vel={lim.get('velocity')}")

keys = list(d)
for w in want:
    for k in keys:
        if w.replace("\\\\", "\\").lower() in k.lower():
            show(k)
