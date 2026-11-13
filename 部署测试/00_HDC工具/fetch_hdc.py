"""Fetch only HDC and its DLL from a range-capable full SDK ZIP mirror.

The source is the HarmonyOS 6.1.1.280 Command Line Tools package mirrored by SDL.
ZIP central-directory metadata and each member CRC are checked before writing.
"""
from __future__ import annotations

import hashlib
import struct
import time
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

URL = "https://libsdl.org/harmonyos-devtools/commandline-tools-windows-x64-6.1.1.280.zip"
TARGETS = {
    "command-line-tools/sdk/default/openharmony/toolchains/hdc.exe",
    "command-line-tools/sdk/default/openharmony/toolchains/libusb_shared.dll",
}
OUT = Path(__file__).resolve().parent / "hdc_6.1.1.280"
CHUNK = 1 << 20


def fetch(start: int, end: int) -> bytes:
    for attempt in range(6):
        try:
            response = requests.get(URL, headers={"Range": f"bytes={start}-{end}"}, timeout=30)
            response.raise_for_status()
            if response.status_code != 206 or len(response.content) != end - start + 1:
                raise IOError(f"Unexpected range response {response.status_code}: {len(response.content)} bytes")
            return response.content
        except (requests.RequestException, IOError):
            if attempt == 5:
                raise
            time.sleep(min(2**attempt, 8))
    raise AssertionError("unreachable")


def fetch_span(start: int, size: int) -> bytes:
    ranges = [(p, min(p + CHUNK, start + size) - 1) for p in range(start, start + size, CHUNK)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        return b"".join(pool.map(lambda pair: fetch(*pair), ranges))


def main() -> None:
    head = requests.head(URL, timeout=30)
    head.raise_for_status()
    total = int(head.headers["Content-Length"])
    tail_start = total - 65536
    tail = fetch(tail_start, total - 1)
    eocd = tail.rfind(b"PK\x05\x06")
    if eocd < 0:
        raise ValueError("ZIP end of central directory not found")
    _, _, _, _, _, directory_size, directory_offset, _ = struct.unpack_from("<IHHHHIIH", tail, eocd)
    if directory_size == 0xFFFFFFFF or directory_offset == 0xFFFFFFFF:
        raise ValueError("ZIP64 directory offset handling is not implemented")
    print(f"Archive {total} bytes; central directory {directory_size} bytes", flush=True)
    directory = fetch_span(directory_offset, directory_size)
    found: dict[str, tuple[int, int, int, int, int]] = {}
    pos = 0
    while pos < len(directory):
        if directory[pos:pos+4] != b"PK\x01\x02":
            raise ValueError(f"Invalid ZIP central entry at {pos}")
        fields = struct.unpack_from("<IHHHHHHIIIHHHHHII", directory, pos)
        method, crc, compressed, expanded = fields[4], fields[7], fields[8], fields[9]
        name_len, extra_len, comment_len = fields[10], fields[11], fields[12]
        local_offset = fields[16]
        name = directory[pos+46:pos+46+name_len].decode("utf-8")
        if name in TARGETS:
            found[name] = (local_offset, method, crc, compressed, expanded)
        pos += 46 + name_len + extra_len + comment_len
    if set(found) != TARGETS:
        raise ValueError(f"Missing members: {TARGETS - set(found)}")
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (offset, method, crc, compressed, expanded) in found.items():
        local = fetch(offset, offset + 29)
        signature, _, _, local_method, _, _, _, _, _, name_len, extra_len = struct.unpack("<IHHHHHIIIHH", local)
        if signature != 0x04034B50 or local_method != method:
            raise ValueError(f"Invalid local header: {name}")
        data = fetch_span(offset + 30 + name_len + extra_len, compressed)
        content = zlib.decompress(data, -15) if method == 8 else data if method == 0 else None
        if content is None or len(content) != expanded or zlib.crc32(content) != crc:
            raise ValueError(f"CRC/length mismatch: {name}")
        target = OUT / Path(name).name
        target.write_bytes(content)
        print(f"{target.name}: {expanded} bytes SHA256 {hashlib.sha256(content).hexdigest()}", flush=True)


if __name__ == "__main__":
    main()
