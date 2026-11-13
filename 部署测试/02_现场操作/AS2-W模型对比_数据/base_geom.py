import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(r"D:\Projects\Athena\运动控制\Collie\AS2-W_CPRO\部署参考\unitree_ros")
C = "{http://www.collada.org/2005/11/COLLADASchema}"


def dae_bbox(path):
    root = ET.parse(path).getroot()
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
                pts.append(tuple(float(vals[i + k]) for k in range(3)))
    if not pts:
        return None
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]; zs = [p[2] for p in pts]
    return [min(xs), min(ys), min(zs)], [max(xs), max(ys), max(zs)], len(pts)


def stl_bbox(path):
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
    return [min(xs), min(ys), min(zs)], [max(xs), max(ys), max(zs)], len(pts)


def resolve(urdf, fn):
    pkg, _, rest = fn.replace("package://", "").partition("/")
    for c in (urdf.parent / ".." / rest, urdf.parent / rest, urdf.parent / fn):
        if c.exists():
            return c
    return None


for rel in ["robots/go2w_description/urdf/go2w_description.urdf",
            "robots/b2w_description/urdf/b2w_description.urdf",
            "robots/as2w_description/as2w.urdf"]:
    u = ROOT / rel
    r = ET.parse(u).getroot()
    print("=" * 78, rel)
    for link in r.findall("link"):
        if link.get("name") not in ("base", "base_link"):
            continue
        for v in link.findall("visual"):
            m = v.find("geometry/mesh")
            if m is None:
                continue
            p = resolve(u, m.get("filename"))
            if not p:
                print("  visual mesh missing:", m.get("filename"))
                continue
            bb = dae_bbox(p) if p.suffix.lower() == ".dae" else stl_bbox(p)
            if not bb:
                print("  parse fail", p)
                continue
            mn, mx, n = bb
            print(f"  visual {p.name:16s} extent={[round(mx[i]-mn[i],4) for i in range(3)]} "
                  f"min={[round(x,4) for x in mn]} max={[round(x,4) for x in mx]} n={n}")
        for c in link.findall("collision"):
            g = c.find("geometry")
            if g.find("box") is not None:
                print("  collision box:", g.find("box").get("size"))
            if g.find("mesh") is not None:
                print("  collision mesh:", g.find("mesh").get("filename"))
