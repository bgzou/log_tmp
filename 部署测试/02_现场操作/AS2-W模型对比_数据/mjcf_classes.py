import re
from pathlib import Path

ROOT = Path(r"D:\Projects\Athena\运动控制\Collie\AS2-W_CPRO\部署参考\unitree_ros")
files = ["robots/as2_description/as2.xml", "robots/a2_description/a2.xml",
         "robots/b2_description_mujoco/xml/b2.xml", "robots/h1_description/mjcf/h1.xml"]
for f in files:
    p = ROOT / f
    if not p.exists():
        print(f, "MISSING")
        continue
    t = p.read_text(encoding="utf-8", errors="ignore")
    print("=" * 72, f)
    for m in re.finditer(r'<default\s+class="([^"]+)">(.*?)</default>', t, re.S):
        body = " ".join(m.group(2).split())
        if "armature" in body or "frictionloss" in body or "damping" in body:
            print(f"  default[{m.group(1)}] {body[:260]}")
    for m in re.finditer(r'<joint\s+class="([^"]+)"', t):
        pass
    for m in re.finditer(r"<joint\s+([^>]*)/>", t):
        s = m.group(1)
        if "armature" in s or "frictionloss" in s:
            print("  joint:", " ".join(s.split())[:240])
