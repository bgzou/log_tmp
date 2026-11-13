"""Read-only hash, provenance, core-index and observation-layout verification."""
import csv
import hashlib
import json
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[1]
def safe(name):
    p=(ROOT/name).resolve()
    if not p.is_relative_to(ROOT):raise ValueError(f"Path outside package: {name}")
    return p
manifest=yaml.safe_load((ROOT/"manifest.yaml").read_text())
count=0
for line in (ROOT/"SHA256SUMS.txt").read_text().splitlines():
    expected,name=line.split("  ",1)
    path=safe(name)
    if path.is_symlink() or not path.is_file():raise ValueError(name)
    actual=hashlib.sha256(path.read_bytes()).hexdigest()
    if actual!=expected:raise ValueError(f"SHA256 mismatch: {name}")
    count+=1
for name,core in manifest['core'].items():
    for path in core['paths']:
        if not safe(path).is_file():raise ValueError(f"Missing {name}: {path}")
meta=json.loads((ROOT/"model/metadata.json").read_text())
for path,key in [('model/selected_checkpoint.pt','selected_output_sha256'),('source/initialization_checkpoint_1300.pt','initialization_sha256'),('model/policy.ts','torchscript_sha256'),('model/policy.onnx','onnx_sha256')]:
    assert hashlib.sha256(safe(path).read_bytes()).hexdigest()==meta[key],path
contract=json.loads((ROOT/'model/as2w_contract.json').read_text())
for name,expected in contract['source_sha256'].items():
    assert hashlib.sha256(safe('source/training_project/'+name).read_bytes()).hexdigest()==expected,name
vendor=json.loads((ROOT/'source/vendor/manifest.json').read_text())
for f in vendor['files']:
    assert hashlib.sha256(safe('source/'+f['path']).read_bytes()).hexdigest()==f['sha256'],f['path']
runtime=json.loads((ROOT/'source/runtime_source_sha256.json').read_text())
for name,expected in runtime.items():
    assert hashlib.sha256(safe('source/runtime_sources/'+name).read_bytes()).hexdigest()==expected,name
with (ROOT/'runtime/observations.csv').open() as f:rows=list(csv.DictReader(f))
assert len(rows)==57 and [int(r['index']) for r in rows]==list(range(57))
assert len({r['name'] for r in rows})==57
for name in ['simulation/evidence156/summary.json','simulation/native_replay/summary.json']:
    report=json.loads(safe(name).read_text())
    assert report['policy_sha256']==meta['torchscript_sha256'],name
assert json.loads((ROOT/'checks/parity.json').read_text())['status']=='passed'
print(json.dumps({'status':'passed','hashed_files':count,'training_source_hashes':len(contract['source_sha256']),'vendor_files':len(vendor['files']),'runtime_python_files':len(runtime),'observation_fields':57,'checkpoint_updates':2701,'scope':'Read-only package integrity and provenance; does not assert sim2sim/hardware qualification'},indent=2))
