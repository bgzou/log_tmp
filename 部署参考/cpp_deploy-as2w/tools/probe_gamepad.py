"""Read Linux /dev/input/js* events in the CPRO Ubuntu rootfs. No robot commands."""
import argparse
import os
import struct
import time

EVENT = struct.Struct("<IhBB")  # Linux js_event: timestamp ms, value, type, number
JS_EVENT_BUTTON = 0x01
JS_EVENT_AXIS = 0x02


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("device", nargs="?", default="/dev/input/js0")
    parser.add_argument("--seconds", type=int, default=15)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 300:
        parser.error("--seconds must be 1..300")
    fd = os.open(args.device, os.O_RDONLY | os.O_NONBLOCK)
    deadline = time.monotonic() + args.seconds
    try:
        while time.monotonic() < deadline:
            try:
                raw = os.read(fd, EVENT.size)
            except BlockingIOError:
                time.sleep(0.02)
                continue
            if len(raw) != EVENT.size:
                continue
            stamp, value, typ, number = EVENT.unpack(raw)
            kind = "button" if typ & JS_EVENT_BUTTON else "axis" if typ & JS_EVENT_AXIS else "other"
            print(f"{stamp}ms {kind} {number} value={value}", flush=True)
    finally:
        os.close(fd)


if __name__ == "__main__":
    main()
