import re, sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(r"D:\Projects\Athena\运动控制\Collie\AS2-W_CPRO\部署参考\unitree_ros")
C = "{http://www.collada.org/2005/11/COLLADASchema}"


def dae_bbox(path: Path):
    root = ET.parse(path).getroot()
    unit = 1.0
    u = root.find(f".//{C}asset/{C}unit")
    if u is not None and u.get("meter"):
        unit = float(u.get("meter"))
    src = {s.get("id"): s for s in root.iter(f"{C}source")}
    pts = []
    for verts in root.iter(f"{C}vertices"):
        for inp in verts.findall(f"{C}input"):
            if inp.get("semantic") != "POSITION":
                continue
            s = src.get(inp.get("source", "").lstrip("#"))
            if s is None:
                continue
            fa = s.find(f"{C}float_array")
            acc = s.find(f"{C}technique_common/{C}accessor")
            stride = int(acc.get("stride")) if acc is not None and acc.get("stride") else 3
            vals = (fa.text or "").split()
            for i in range(0, len(vals) - (stride - 1), stride):
                pts.append(tuple(float(vals[i + k]) * unit for k in range(3)))
    if not pts:
        return None
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]; zs = [p[2] for p in pts]
    return {"n": len(pts), "unit": unit,
            "min": [min(xs), min(ys), min(zs)], "max": [max(xs), max(ys), max(zs)],
            "extent": [max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)],
            "id": verts.get("id")}


def stl_bbox(path: Path):
    import struct
    raw = path.read_bytes()
    n = struct.unpack_from("<I", raw, 80)[0]
    if len(raw) != 84 + 50 * n:
        return None
    pts = []
    for i in range(n):
        f = struct.unpack_from("<12f", raw, 84 + 50 * i)
        pts += [f[3:6], f[6:9], f[9:12]]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]; zs = [p[2] for p in pts]
    return {"n": len(pts), "unit": 1.0, "min": [min(xs), min(ys), min(zs)],
            "max": [max(xs), max(ys), max(zs)],
            "extent": [max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)], "id": path.name}


def resolve(urdf: Path, fn: str):
    fn = fn.replace("package://", "")
    cands = [urdf.parent / fn, urdf.parent / ".." / fn,
             urdf.parent.parent / "/".join(fn.split("/")[1:])]
    for c in cands:
        if c.exists():
            return c
    return None


targets = {
    "go2w": "robots/go2w_description/urdf/go2w_description.urdf",
    "b2w": "robots/b2w_description/urdf/b2w_description.urdf",
    "as2w": "robots/as2w_description/as2w.urdf",
}
for name, rel in targets.items():
    urdf = ROOT / rel
    txt = urdf.read_text(encoding="utf-8", errors="ignore")
    print("=" * 70, name)
    for link in ["FL_foot", "FR_foot", "RL_foot", "RR_foot"]:
        m = re.search(r'<link\s+name="%s">(.*?)</link>' % link, txt, re.S)
        if not m:
            continue
        coll = re.search(r"<collision>(.*?)</collision>", m.group(1), re.S)
        mesh = re.search(r'filename="([^"]+)"', coll.group(1)) if coll else None
        if not mesh:
            continue
        p = resolve(urdf, mesh.group(1))
        if not p:
            print(f"  {link}: mesh not found {mesh.group(1)}")
            continue
        bb = dae_bbox(p) if p.suffix.lower() == ".dae" else stl_bbox(p)
        if not bb:
            print(f"  {link}: parse fail {p}")
            continue
        r = max(bb["extent"][0], bb["extent"][2]) / 2
        print(f"  {link:8s} {p.name:22s} extent={[round(x,4) for x in bb['extent']]} "
              f"center={[round((bb['min'][i]+bb['max'][i])/2,4) for i in range(3)]} "
              f"radius={r:.4f} unit={bb['unit']} n={bb['n']}")
