"""Derive an isolated caolin MuJoCo evaluator with the C++ target EMA.

The source evaluator is never edited. Run with SRC OUT paths. The filter is
applied to the final leg position targets after the 2 s handoff. The model's
previous-action observation continues to use the wrapped, unfiltered action.
"""

import hashlib
import sys
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit("usage: python patch.py SOURCE.py OUTPUT.py")
source, output = map(Path, sys.argv[1:])
code = source.read_text(encoding="utf-8")

old = "    sub_max_unload = 0\n\n    def stance_invalid(q, heading):"
new = """    sub_max_unload = 0
    lowpass_ms = float(os.environ.get("R1199_LOWPASS_MS", "0"))
    if not (0 <= lowpass_ms <= 200):
        raise ValueError("R1199_LOWPASS_MS must be 0..200")
    lowpass_previous = None

    def stance_invalid(q, heading):"""
assert code.count(old) == 1, "initialization anchor changed"
code = code.replace(old, new)

old = """        command = (1.-blend)*q_ref + blend*current
        last_obs = obs.copy()"""
new = """        command = (1.-blend)*q_ref + blend*current
        # C++ PolicyTargetLowpass: reset at Handoff->Walk (t=2s), then one-pole
        # EMA at 50 Hz on leg q only. q=default+0.35*action, so filtering the
        # action coordinates here is algebraically identical to filtering q.
        # Wheels, kp/kd, and the wrapped previous-action observation bypass it.
        if lowpass_ms > 0. and elapsed >= 2.:
            if lowpass_previous is None:
                lowpass_previous = command.copy()
            else:
                alpha = -np.expm1(-env.dt / (lowpass_ms / 1000.))
                applied_command = command.copy()
                applied_command[:12] = (lowpass_previous[:12] +
                                        alpha * (command[:12] - lowpass_previous[:12]))
                command = applied_command
                lowpass_previous = applied_command.copy()
        last_obs = obs.copy()"""
assert code.count(old) == 1, "actuation anchor changed"
code = code.replace(old, new)

output.write_text(code, encoding="utf-8")
print("source_sha256", hashlib.sha256(source.read_bytes()).hexdigest())
print("output_sha256", hashlib.sha256(output.read_bytes()).hexdigest())
print("output", output)
