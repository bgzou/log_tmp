"""Check all shipped ONNX checksums and C++ actor file headers without dependencies."""
import hashlib
import json
from pathlib import Path

models = Path(__file__).resolve().parents[1] / "models"
manifest = json.loads((models / "manifest.json").read_text(encoding="utf-8"))
for name, info in manifest["models"].items():
    onnx = models / (name + ".onnx")
    actor = models / (name + ".bin")
    fixture = models / (name + ".fixture")
    assert onnx.is_file() and actor.is_file() and fixture.is_file(), name
    assert hashlib.sha256(onnx.read_bytes()).hexdigest() == info["onnx_sha256"], name
    actor_bytes = actor.read_bytes()
    assert actor_bytes[:8] == b"AS2WMLP1", name
    assert hashlib.sha256(actor_bytes).hexdigest() == info["actor_sha256"], name
    print(name, "ONNX SHA256 OK; actor SHA256 and header OK")
print("checked", len(manifest["models"]), "models")
