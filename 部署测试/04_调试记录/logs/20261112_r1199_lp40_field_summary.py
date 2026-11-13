"""Summarize the two R1199 40 ms filtered field sessions from archived raw files."""

import csv
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).parent / "field_sessions"
for session in ("20261112-223732_training-contract", "20261112-224151_training-contract"):
    directory = ROOT / session
    with (directory / "debug_policy.csv").open(encoding="utf-8") as stream:
        next(stream)
        rows = [r for r in csv.reader(stream) if r and r[0] == "DEBUG_POLICY" and r[2] == "WALK"]
    with (directory / "low_protection.log").open(encoding="utf-8", errors="replace") as stream:
        protection = [line for line in stream if line.startswith("PROTECT,")]
    publisher = (directory / "publisher.log").read_text(encoding="utf-8", errors="replace")
    print(f"SESSION {session}")
    print(f"  policy_walk_frames={len(rows)} protection_rows={len(protection)}")
    complete_protection = [r for r in protection if 'warning_or=' in r and 'motorstate_or=' in r]
    print(f"  protection_complete_rows={len(complete_protection)} protection_nonzero={sum('warning_or=0x0' not in r or 'motorstate_or=0x0' not in r for r in complete_protection)}")
    print(f"  guard_trips={sum(s in publisher for s in ('FIELD_SAFETY_WARN', 'FIELD_SAFETY_HARD', 'FIELD_SAFETY_SOFT_TRIP', 'REMOTE_TIMEOUT'))}")
    for label, cmd_index, predicate in (
        ("forward", 5, lambda r: float(r[5]) > 0.04),
        ("backward", 5, lambda r: float(r[5]) < -0.04),
        ("yaw_positive", 7, lambda r: float(r[7]) > 0.04),
        ("yaw_negative", 7, lambda r: float(r[7]) < -0.04),
    ):
        subset = [r for r in rows if predicate(r)]
        if subset:
            print(
                f"  {label}: frames={len(subset)} command_mean={mean(float(r[cmd_index]) for r in subset):+.4f}"
                f" gyro_z_mean={mean(float(r[17]) for r in subset):+.4f}"
            )
