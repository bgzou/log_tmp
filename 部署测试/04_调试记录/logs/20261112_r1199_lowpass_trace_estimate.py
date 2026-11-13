"""Offline target-only EMA estimate from the recorded R1199 policy diagnostic.

This is not a closed-loop MuJoCo or hardware safety result. It measures how
the proposed leg-target low-pass changes the previously recorded target trace.
"""

import csv
import math
import statistics
import sys


def percentile(values, p):
    values = sorted(values)
    return values[round((len(values) - 1) * p)]


def evaluate(path, tau_ms):
    alpha = -math.expm1(-20.0 / tau_ms)
    original_steps = []
    filtered_steps = []
    previous_original = None
    previous_filtered = None
    walk_frames = 0
    with open(path, encoding="utf-8", errors="replace", newline="") as stream:
        for row in csv.reader(stream):
            if not row or row[0] != "POLICY_DIAG":
                continue
            if row[1] != "WALK":
                previous_original = previous_filtered = None
                continue
            q = [float(v) for v in row[39:51]]
            walk_frames += 1
            if previous_original is None:
                previous_original = previous_filtered = q
                continue
            filtered = [a + alpha * (b - a) for a, b in zip(previous_filtered, q)]
            # Largest absolute leg-target change across 12 axes per 20 ms.
            original_steps.append(max(abs(a - b) for a, b in zip(q, previous_original)))
            filtered_steps.append(max(abs(a - b) for a, b in zip(filtered, previous_filtered)))
            previous_original, previous_filtered = q, filtered
    def summarize(values):
        return {
            "mean": statistics.mean(values),
            "p99": percentile(values, 0.99),
            "peak": max(values),
        }
    print(f"walk_frames={walk_frames} tau_ms={tau_ms} alpha={alpha:.6f}")
    print("recorded_max_leg_step_rad", summarize(original_steps))
    print("ema_max_leg_step_rad", summarize(filtered_steps))
    print("warning=target-only, no robot feedback or closed-loop dynamics")


if __name__ == "__main__":
    evaluate(sys.argv[1], float(sys.argv[2]))
