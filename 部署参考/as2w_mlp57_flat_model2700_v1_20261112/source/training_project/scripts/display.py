"""Private X display for headless Kit; no dialogs appear on the desktop."""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import select
import subprocess

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def private_display(env: dict[str, str]):
    env = dict(env)
    binary = ROOT / "tools/xvfb/root/usr/bin/Xvfb"
    if not binary.exists():
        # Kit headless can run without X. Clearing DISPLAY also prevents its
        # error dialogs from appearing on the user's desktop.
        env["DISPLAY"] = ""
        yield env
        return
    read_fd, write_fd = os.pipe()
    log_dir = ROOT / "outputs"
    log_dir.mkdir(exist_ok=True)
    with (log_dir / "xvfb.log").open("a") as log:
        server = subprocess.Popen([str(binary), "-displayfd", str(write_fd), "-screen", "0", "1280x720x24", "-nolisten", "tcp", "-ac"], pass_fds=(write_fd,), stdout=log, stderr=log)
        os.close(write_fd)
        try:
            if not select.select([read_fd], [], [], 15)[0]:
                raise RuntimeError("Private X display did not start; see outputs/xvfb.log")
            display = os.read(read_fd, 32).decode().strip()
            if not display.isdigit():
                raise RuntimeError("Private X display failed; see outputs/xvfb.log")
            env["DISPLAY"] = f":{display}"
            yield env
        finally:
            os.close(read_fd)
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
