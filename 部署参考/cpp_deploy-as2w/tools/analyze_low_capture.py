#!/usr/bin/env python3
"""Summarize read-only LOW_SAMPLE rows; never infer physical joint names."""

import argparse
import math
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    args = parser.parse_args()
    rows = []
    for line in args.log.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if not line.startswith("LOW_SAMPLE,"):
            continue
        cells = line.split(",")
        if len(cells) != 84:
            continue
        try:
            values = [float(cell) for cell in cells[1:]]
        except ValueError:
            continue
        if not all(math.isfinite(value) for value in values):
            continue
        rows.append(values)
    if not rows:
        raise SystemExit("No complete LOW_SAMPLE rows")
    print(f"samples={len(rows)} elapsed_ms={rows[0][0]:.0f}..{rows[-1][0]:.0f}")
    print("slot,q_first,q_last,q_range,dq_abs_max")
    for slot in range(35):
        q_col = 13 + 2 * slot
        dq_col = q_col + 1
        q = [row[q_col] for row in rows]
        dq = [row[dq_col] for row in rows]
        print(f"{slot},{q[0]:.6g},{q[-1]:.6g},{max(q)-min(q):.6g},{max(map(abs,dq)):.6g}")
    print("Message slots are not physical motor names. Verify against this AS2-W firmware.")


if __name__ == "__main__":
    main()
