import sys
from pathlib import Path
import numpy as np

sess = Path("/home/caolin/as2w_workstation/部署测试/04_调试记录/logs/field_sessions/20261112-103110_training-contract")

# --- protection log: motor modes + warnings timeline ---
prot = []
for line in (sess/"low_protection.log").read_text(errors="replace").splitlines():
    if not line.startswith("PROTECT,"):
        continue
    f = line.split(",")
    t = float(f[1])
    modes = ""
    warn = ""
    ms_or = ""
    machine = ""
    for kv in f[3:]:
        if kv.startswith("modes="): modes = kv[6:]
        elif kv.startswith("warning_or="): warn = kv[11:]
        elif kv.startswith("motorstate_or="): ms_or = kv[14:]
        elif kv.startswith("machine="): machine = kv[8:]
    prot.append((t, modes, warn, ms_or, machine))
prot = [p for p in prot if p[1]]
# transitions of mode string
print("=== protection: motor-mode transitions (16-axis) ===")
prev = None
for t, modes, warn, ms_or, machine in prot:
    key = (modes, machine)
    if key != prev:
        print(f"t={t/1000:7.2f}s modes={modes} machine={machine} warn_or={warn} motorstate_or={ms_or}")
        prev = key
# any nonzero warn/ms?
nz = [(t,modes,warn,ms_or) for t,modes,warn,ms_or,_ in prot if warn not in ("0x0","") or ms_or not in ("0x0","")]
print(f"nonzero warning/motorstate entries: {len(nz)}")
for row in nz[:10]: print("  ", row)

# --- capture: posture timeline ---
rows = []
for line in (sess/"low_capture_fast.log").read_text(errors="replace").splitlines():
    if not line.startswith("LOW_SAMPLE,"): continue
    f = line.split(",")
    if len(f) < 14+35*6: continue
    try:
        t = float(f[1]); tick = float(f[4]); machine = f[6]
        q = [float(f[14+i*6]) for i in range(16)]
        dq = [float(f[15+i*6]) for i in range(12)]
        mm = [f[14+i*6+4] for i in range(16)]
    except ValueError:
        continue
    rows.append((t, tick, machine, q, dq, mm))
print(f"\n=== capture: {len(rows)} samples ===")
def thigh(q): return float(np.mean(q[4:8]))
def calf(q): return float(np.mean(q[8:12]))
t0 = rows[0][0]
# print every 1s summary + transitions of machine/mode-set
print("t_s   machine thigh   calf    modes16-set  max_leg_dq")
prev_key = None
for t, tick, machine, q, dq, mm in rows:
    key = (machine, "".join(mm))
    if key != prev_key:
        print(f"{(t-t0)/1000:6.2f} machine={machine} modes={''.join(mm)} thigh={thigh(q):+.3f} calf={calf(q):+.3f}")
        prev_key = key
# posture every 2s
print("\n=== posture every ~2s ===")
last_printed = -10
for t, tick, machine, q, dq, mm in rows:
    if t - last_printed >= 2000:
        print(f"t={(t-t0)/1000:6.2f}s thigh={thigh(q):+.3f} calf={calf(q):+.3f} max_leg_dq={max(abs(x) for x in dq):.3f} modes={''.join(mm)}")
        last_printed = t
