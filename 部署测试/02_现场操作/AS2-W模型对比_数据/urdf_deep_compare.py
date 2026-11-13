"""Deep URDF comparison for unitree_ros robot descriptions.

Outputs JSON (full facts) + Markdown snippets used to build the report.
"""
import json, math, os, struct, sys, hashlib
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"D:\Projects\Athena\运动控制\Collie\AS2-W_CPRO\部署参考\unitree_ros")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else r"D:\Projects\Athena\运动控制\Collie\AS2-W_CPRO\.dsh_tmp")
OUT.mkdir(parents=True, exist_ok=True)


def fnum(s, default=0.0):
    try:
        return float(s)
    except Exception:
        return default


def vec(s, n=3):
    if not s:
        return [0.0] * n
    v = [fnum(x) for x in s.replace(",", " ").split()]
    while len(v) < n:
        v.append(0.0)
    return v[:n]


def rpy_mat(r, p, y):
    cr, sr = math.cos(r), math.sin(r)
    cp, sp = math.cos(p), math.sin(p)
    cy, sy = math.cos(y), math.sin(y)
    return [
        [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
        [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
        [-sp, cp * sr, cp * cr],
    ]


def mat_mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def mat_vec(a, v):
    return [sum(a[i][k] * v[k] for k in range(3)) for i in range(3)]


def axis_angle_mat(axis, ang):
    x, y, z = axis
    n = math.sqrt(x * x + y * y + z * z) or 1.0
    x, y, z = x / n, y / n, z / n
    c, s = math.cos(ang), math.sin(ang)
    C = 1 - c
    return [
        [x * x * C + c, x * y * C - z * s, x * z * C + y * s],
        [y * x * C + z * s, y * y * C + c, y * z * C - x * s],
        [z * x * C - y * s, z * y * C + x * s, z * z * C + c],
    ]


def stl_bbox(path: Path):
    try:
        raw = path.read_bytes()
    except Exception:
        return None
    if len(raw) < 84:
        return None
    # binary STL
    n = struct.unpack_from("<I", raw, 80)[0]
    if len(raw) == 84 + 50 * n:
        pts = [struct.unpack_from("<12f", raw, 84 + 50 * i)[3:12] for i in range(n)]
        pts = [p[0:3] for p in pts] + [p[3:6] for p in pts] + [p[6:9] for p in pts]
    else:  # ascii
        pts = []
        for line in raw.decode("utf-8", "ignore").splitlines():
            t = line.split()
            if len(t) == 4 and t[0].lower() == "vertex":
                pts.append((fnum(t[1]), fnum(t[2]), fnum(t[3])))
        if not pts:
            return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    zs = [p[2] for p in pts]
    return {"min": [min(xs), min(ys), min(zs)], "max": [max(xs), max(ys), max(zs)],
            "extent": [max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)],
            "n_vertices": len(pts)}


def resolve_mesh(urdf_path: Path, fn: str):
    fn = fn.replace("package://", "")
    # package://<pkg>/meshes/x.STL  -> <urdf_dir>/meshes/x.STL
    cands = []
    parts = fn.split("/")
    cands.append(urdf_path.parent / fn)
    if len(parts) >= 2 and parts[1] == "meshes":
        cands.append(urdf_path.parent / "meshes" / "/".join(parts[2:]))
    cands.append(urdf_path.parent / ".." / fn)
    for c in cands:
        if c.exists():
            return c
    return None


def parse(urdf: Path):
    tree = ET.parse(urdf)
    root = tree.getroot()
    links = {}
    for l in root.findall("link"):
        name = l.get("name")
        i = l.find("inertial")
        mass = fnum(i.find("mass").get("value")) if i is not None and i.find("mass") is not None else 0.0
        com = vec(i.find("origin").get("xyz")) if i is not None and i.find("origin") is not None else [0, 0, 0]
        inr = [0.0] * 6
        if i is not None and i.find("inertia") is not None:
            a = i.find("inertia").attrib
            inr = [fnum(a.get(k)) for k in ("ixx", "ixy", "ixz", "iyy", "iyz", "izz")]
        col = []
        for c in l.findall("collision"):
            g = c.find("geometry")
            d = {"origin": vec(c.find("origin").get("xyz")) if c.find("origin") is not None else [0, 0, 0]}
            if g is None:
                d["type"] = "none"
            elif g.find("mesh") is not None:
                d["type"] = "mesh"
                d["file"] = g.find("mesh").get("filename")
            elif g.find("box") is not None:
                d["type"] = "box"
                d["size"] = vec(g.find("box").get("size"))
            elif g.find("cylinder") is not None:
                d["type"] = "cylinder"
                d["radius"] = fnum(g.find("cylinder").get("radius"))
                d["length"] = fnum(g.find("cylinder").get("length"))
            elif g.find("sphere") is not None:
                d["type"] = "sphere"
                d["radius"] = fnum(g.find("sphere").get("radius"))
            else:
                d["type"] = "other"
            col.append(d)
        vis = []
        for v in l.findall("visual"):
            g = v.find("geometry")
            if g is not None and g.find("mesh") is not None:
                vis.append(g.find("mesh").get("filename"))
        links[name] = {"mass": mass, "com": com, "inertia": inr, "collision": col, "visuals": vis}

    joints = {}
    for j in root.findall("joint"):
        name = j.get("name")
        o = j.find("origin")
        lim = j.find("limit")
        ax = j.find("axis")
        joints[name] = {
            "type": j.get("type"),
            "parent": j.find("parent").get("link"),
            "child": j.find("child").get("link"),
            "xyz": vec(o.get("xyz")) if o is not None else [0, 0, 0],
            "rpy": vec(o.get("rpy")) if o is not None else [0, 0, 0],
            "axis": vec(ax.get("xyz")) if ax is not None else [0, 0, 0],
            "limit": ({k: fnum(lim.get(k)) for k in ("lower", "upper", "effort", "velocity") if lim.get(k) is not None}
                      if lim is not None else None),
        }

    # forward kinematics at q=0 (and at "legs straight" not defined) for link origins in base frame
    children = {j["child"]: (jn, j) for jn, j in joints.items()}
    base = [n for n in links if n not in children]
    base = base[0] if base else None
    world = {base: ([[1, 0, 0], [0, 1, 0], [0, 0, 1]], [0, 0, 0])}
    todo = list(joints.items())
    while todo:
        progressed = False
        for jn, j in list(todo):
            if j["parent"] in world:
                R0, p0 = world[j["parent"]]
                Rj = rpy_mat(*j["rpy"])
                R = mat_mul(R0, Rj)
                off = mat_vec(R0, j["xyz"])
                p = [p0[i] + off[i] for i in range(3)]
                world[j["child"]] = (R, p)
                todo.remove((jn, j))
                progressed = True
        if not progressed:
            break

    return {"robot": root.get("name"), "links": links, "joints": joints, "base": base,
            "world_pos": {k: v[1] for k, v in world.items()}}


def analyse(urdf: Path):
    d = parse(urdf)
    links, joints = d["links"], d["joints"]
    movable = {k: v for k, v in joints.items() if v["type"] != "fixed"}
    fixed = {k: v for k, v in joints.items() if v["type"] == "fixed"}
    total_mass = sum(l["mass"] for l in links.values())

    # wheel radius from cylinder collision, else mesh bbox
    wheels = {}
    for jn, j in movable.items():
        if j["type"] == "continuous":
            l = links[j["child"]]
            rad = None
            for c in l["collision"]:
                if c["type"] == "cylinder":
                    rad = c["radius"]
            if rad is None:
                for c in l["collision"]:
                    if c["type"] == "mesh":
                        mp = resolve_mesh(urdf, c["file"])
                        if mp:
                            bb = stl_bbox(mp)
                            if bb:
                                rad = max(bb["extent"][0], bb["extent"][2]) / 2
                                l["mesh_bbox"] = bb
                                break
            wheels[jn] = {"link": j["child"], "radius": rad,
                          "center": d["world_pos"].get(j["child"]), "limit": j["limit"]}

    # leg chains: from base, follow 3 revolute joints ending in a wheel or foot
    chains = {}
    for legroot, j in joints.items():
        if j["parent"] != d["base"]:
            continue
        chain = []
        cur = legroot
        seen = set()
        while cur not in seen:
            seen.add(cur)
            jj = joints[cur]
            chain.append((cur, jj["child"], jj["type"], jj["xyz"], jj["axis"], jj["limit"]))
            nxt = [k for k, v in movable.items() if v["parent"] == jj["child"]]
            if not nxt:
                break
            cur = nxt[0]
        chains[legroot] = chain

    # segment lengths
    legs = {}
    for root_joint, chain in chains.items():
        segs = []
        for (jn, child, typ, xyz, axis, lim) in chain:
            if typ != "fixed":
                segs.append({"joint": jn, "child": child, "origin": xyz,
                             "length": math.sqrt(sum(v * v for v in xyz))})
        if len(segs) < 2:
            continue
        legname = root_joint.rsplit("_", 1)[0]
        legs[legname] = {"chain": segs, "n_movable": len(segs),
                         "mass": sum(links[c["child"]]["mass"] for c in segs)}

    # wheel/foot positions relative to base at q=0
    feet = {}
    for legname, info in legs.items():
        last = info["chain"][-1]["child"]
        feet[legname] = d["world_pos"].get(last)

    return {
        "file": str(urdf.relative_to(ROOT)),
        "sha256": hashlib.sha256(urdf.read_bytes()).hexdigest(),
        "robot": d["robot"], "base_link": d["base"],
        "n_links": len(links), "n_joints": len(joints),
        "n_movable": len(movable), "n_fixed": len(fixed),
        "total_mass": total_mass,
        "base_mass": links[d["base"]]["mass"],
        "base_com": links[d["base"]]["com"],
        "base_inertia": links[d["base"]]["inertia"],
        "base_collision": [c["type"] for c in links[d["base"]]["collision"]],
        "base_collision_box": [c.get("size") for c in links[d["base"]]["collision"] if c["type"] == "box"],
        "link_masses": {k: v["mass"] for k, v in links.items()},
        "fixed_children": {k: v["child"] for k, v in fixed.items()},
        "legs": legs, "wheels": wheels, "feet_q0": feet,
        "joint_types": {t: sum(1 for v in joints.values() if v["type"] == t) for t in set(v["type"] for v in joints.values())},
        "movable_joints": {k: {"type": v["type"], "limit": v["limit"], "axis": v["axis"]} for k, v in movable.items()},
        "collision_types": {t: sum(1 for l in links.values() for c in l["collision"] if c["type"] == t)
                            for t in set(c["type"] for l in links.values() for c in l["collision"])},
        "has_dynamics": any("dynamics" in ET.tostring(l, encoding="unicode") for l in []) or
                        any(True for j in ET.parse(urdf).getroot().findall("joint") if j.find("dynamics") is not None),
        "imu_like": [n for n in links if any(k in n.lower() for k in ("imu", "lidar", "radar", "camera", "jt", "sensor"))],
        "sensor_links": {n: {"mass": links[n]["mass"], "pos": d["world_pos"].get(n)} for n in links
                         if n not in legs and any(k in n.lower() for k in ("imu", "lidar", "radar", "camera", "jt", "head", "dc", "sensor"))},
    }


def main():
    urdfs = sorted([p for p in ROOT.glob("robots/*/**/*.urdf") if ".git" not in str(p)])
    facts = {}
    errors = {}
    for u in urdfs:
        try:
            facts[str(u.relative_to(ROOT))] = analyse(u)
        except Exception as e:
            errors[str(u.relative_to(ROOT))] = f"{type(e).__name__}: {e}"
    (OUT / "urdf_facts.json").write_text(json.dumps({"facts": facts, "errors": errors}, indent=1, ensure_ascii=False), encoding="utf-8")

    # summary table
    lines = ["| file | robot | links | movable | total kg | base kg | wheels | wheel r |",
             "|---|---|---|---|---|---|---|---|"]
    for k, f in sorted(facts.items()):
        wr = ",".join(sorted({f"{w['radius']:.4f}" for w in f["wheels"].values() if w["radius"]})) or "-"
        lines.append(f"| {k} | {f['robot']} | {f['n_links']} | {f['n_movable']} | {f['total_mass']:.3f} | "
                     f"{f['base_mass']:.3f} | {len(f['wheels'])} | {wr} |")
    (OUT / "urdf_summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"parsed {len(facts)} urdfs, errors={len(errors)}")
    for k, v in errors.items():
        print("  ERR", k, v)


if __name__ == "__main__":
    main()
