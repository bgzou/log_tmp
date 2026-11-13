#!/usr/bin/env python3
"""Independently audit synthetic HG LowCmd frames; never opens DDS."""
import argparse
import re
import struct
from pathlib import Path


def unitree_crc(data: bytes) -> int:
    crc = 0xFFFFFFFF
    for (word,) in struct.iter_unpack("<I", data):
        for bit in range(31, -1, -1):
            crc = ((crc << 1) ^ (0x04C11DB7 if crc & 0x80000000 else 0)) & 0xFFFFFFFF
            if word & (1 << bit):
                crc ^= 0x04C11DB7
    return crc


def parse(text: str):
    frames = {}
    for block in text.split("FRAME ")[1:]:
        head, *lines = block.splitlines()
        name = head.split()[0]
        match = re.search(r"sizeof=(\d+) mode_pr=(\d+) mode_machine=(\d+) crc=0x([0-9a-fA-F]+)", head)
        assert match, head
        size, mode_pr, machine, crc = (int(match.group(1)), int(match.group(2)),
                                        int(match.group(3)), int(match.group(4), 16))
        slots = []
        raw = None
        for line in lines:
            if line.startswith("slot="):
                parts = dict(item.split("=", 1) for item in line.split())
                slots.append({k: float(v) for k, v in parts.items()})
            elif line.startswith("raw_hex="):
                raw = bytes.fromhex(line.removeprefix("raw_hex="))
        assert raw is not None and len(raw) == size == 1004, (name, size)
        assert size % 4 == 0 and len(slots) == 35
        assert struct.unpack_from("<I", raw, size - 4)[0] == crc
        assert unitree_crc(raw[:-4]) == crc, name
        assert mode_pr == 0 and machine == 2
        assert raw[0] == 0 and raw[1] == 2, "Unexpected HG header layout"
        frames[name] = slots
    return frames


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("audit_log", type=Path)
    args = parser.parse_args()
    frames = parse(args.audit_log.read_text(encoding="utf-8"))
    assert set(frames) == {"neutral_zero_torque", "passive_kd3"}, frames.keys()
    neutral, passive = frames["neutral_zero_torque"], frames["passive_kd3"]
    for slot, (n, p) in enumerate(zip(neutral, passive)):
        assert n["slot"] == p["slot"] == slot
        if slot < 16:
            assert n["mode"] == p["mode"] == 1
            assert n["q"] == p["q"]
            assert n["dq"] == p["dq"] == n["kp"] == p["kp"] == 0
            assert n["tau"] == p["tau"] == n["kd"] == 0
            assert p["kd"] == 3
        else:
            assert all(n[k] == p[k] == 0 for k in
                       ("mode", "q", "dq", "kp", "kd", "tau", "reserve"))
    print("PASS: 2 HG frames, 35 slots each, independent CRC, no DDS")


if __name__ == "__main__":
    main()
