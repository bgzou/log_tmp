"""Fetch the pinned AS2-W delivery subtree through GitHub CLI and verify blobs."""
import hashlib
import base64
import json
import subprocess
from pathlib import Path

REPO = "YuTaoV5/Rob2Nav"
REV = "e61aaf79445fb2e2fdc996910cf0bd2e2f53b200"
PREFIX = "deliveries/as2w-deploy/"
DEST = Path(__file__).resolve().parent / "as2w-deploy"


def api(path: str, raw: bool = False) -> bytes:
    args = ["gh", "api"]
    if raw:
        args += ["-H", "Accept: application/vnd.github.raw+json"]
    return subprocess.check_output(args + [path])


tree = json.loads(api(f"repos/{REPO}/git/trees/{REV}?recursive=1"))["tree"]
blobs = [item for item in tree if item["type"] == "blob" and item["path"].startswith(PREFIX)]
if not blobs:
    raise SystemExit("Delivery subtree missing")
for item in blobs:
    relative = item["path"][len(PREFIX):]
    target = DEST / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        data = target.read_bytes()
    else:
        blob = json.loads(api(f"repos/{REPO}/git/blobs/{item['sha']}"))
        if blob["encoding"] != "base64":
            raise SystemExit(f"Unexpected encoding: {relative}")
        data = base64.b64decode(blob["content"])
    actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    if actual != item["sha"]:
        raise SystemExit(f"Git blob SHA mismatch: {relative}")
    target.write_bytes(data)
    print(relative, len(data))
print("Verified", len(blobs), "files from", REV)
