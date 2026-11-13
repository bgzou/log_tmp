"""Read-only summary of the first R1199 Debug field session; no DDS access."""

import csv
import re
from pathlib import Path

import numpy as np

SESSION = Path(__file__).resolve().parent / "field_sessions/20261112-220051_training-contract"

policy = []
bad_policy = 0
with (SESSION / "debug_policy.csv").open(newline="", encoding="utf-8", errors="replace") as file:
    next(file)
    for row in csv.reader(file):
        try:
            obs_count = int(row[57])
            state_count = int(row[58 + obs_count])
            expected = 58 + obs_count + 1 + state_count + 16 + 16 + 64 + 64
            if len(row) != expected or obs_count != 65 or state_count != 0:
                bad_policy += 1
                continue
            raw_start = 59 + obs_count + state_count
            wrapped_start = raw_start + 16
            requested_start = wrapped_start + 16
            applied_start = requested_start + 64
            policy.append({
                "mono": int(row[1]), "phase": row[2], "tick": int(row[3]),
                "vx": float(row[5]), "vy": float(row[6]), "wz": float(row[7]),
                "ly": float(row[14]),
                "raw": np.array([float(x) for x in row[raw_start:raw_start + 16]]),
                "wrapped": np.array([float(x) for x in row[wrapped_start:wrapped_start + 16]]),
                "leg_q": np.array([float(row[applied_start + i * 4]) for i in range(12)]),
                "requested_leg_q": np.array([float(row[requested_start + i * 4]) for i in range(12)]),
            })
        except (ValueError, IndexError):
            bad_policy += 1

lowcmd_mono = []
bad_lowcmd = 0
with (SESSION / "debug_lowcmd.csv").open(newline="", encoding="utf-8", errors="replace") as file:
    next(file)
    for row in csv.reader(file):
        try:
            if len(row) != 5 + 16 * 7 or row[0] != "DEBUG_LOWCMD":
                bad_lowcmd += 1
                continue
            lowcmd_mono.append(int(row[1]))
        except (ValueError, IndexError):
            bad_lowcmd += 1

capture_tick, capture_ms, capture_thigh_dq, capture_thigh_tau = [], [], [], []
with (SESSION / "low_capture_fast.log").open(encoding="utf-8", errors="replace") as file:
    for line in file:
        if not line.startswith("LOW_SAMPLE,"):
            continue
        row = line.rstrip().split(",")
        if len(row) < 14 + 16 * 6:
            continue
        try:
            capture_ms.append(float(row[1]))
            capture_tick.append(int(row[4]))
            capture_thigh_dq.append([float(row[15 + i * 6]) for i in (1, 4, 7, 10)])
            capture_thigh_tau.append([float(row[17 + i * 6]) for i in (1, 4, 7, 10)])
        except ValueError:
            pass

protection_count = 0
protect_nonzero = []
with (SESSION / "low_protection.log").open(encoding="utf-8", errors="replace") as file:
    for line in file:
        if not line.startswith("PROTECT,") or "low_count=" not in line:
            continue
        protection_count += 1
        for field in ("warning_or", "motorstate_or"):
            match = re.search(rf"{field}=0x([0-9a-fA-F]+)", line)
            if match and int(match.group(1), 16):
                protect_nonzero.append((field, line[:180]))

walk = [p for p in policy if p["phase"] == "WALK"]
walk_mono = np.array([p["mono"] for p in walk], dtype=np.int64)
walk_vx = np.array([p["vx"] for p in walk])
walk_q = np.stack([p["leg_q"] for p in walk])
walk_raw = np.stack([p["raw"] for p in walk])
walk_steps = np.max(np.abs(np.diff(walk_q, axis=0)), axis=1)
raw_leg_steps = np.max(np.abs(np.diff(walk_raw[:, :12], axis=0)), axis=1)
raw_wheel_steps = np.max(np.abs(np.diff(walk_raw[:, 12:], axis=0)), axis=1)
requested_applied_max = max(float(np.max(np.abs(p["leg_q"] - p["requested_leg_q"]))) for p in walk)
movement = np.abs(walk_vx) >= 0.03
quiet = np.abs(walk_vx) < 0.005

print(f"policy_rows={len(policy)} bad_policy_rows={bad_policy} walk_rows={len(walk)}")
print(f"policy_phases={ {name: sum(p['phase'] == name for p in policy) for name in sorted(set(p['phase'] for p in policy))} }")
print(f"policy_obs=65 state_count=0 all_valid={bad_policy == 0}")
print(f"lowcmd_rows={len(lowcmd_mono)} bad_lowcmd_rows={bad_lowcmd}")
for name, stamps in (("policy_walk", walk_mono), ("lowcmd", np.array(lowcmd_mono, dtype=np.int64))):
    dt = np.diff(stamps) / 1e6
    print(f"{name}_dt_ms p50={np.percentile(dt, 50):.3f} p99={np.percentile(dt, 99):.3f} max={np.max(dt):.3f} gaps_gt_40ms={np.count_nonzero(dt > 40)}")
print(f"low_capture_valid_rows={len(capture_tick)} protection_rows={protection_count} nonzero_protection={len(protect_nonzero)}")
print(f"walk_vx_range=[{np.min(walk_vx):.4f},{np.max(walk_vx):.4f}] moving_frames={np.count_nonzero(movement)} quiet_frames={np.count_nonzero(quiet)}")
print(f"lowpass_off_requested_applied_leg_q_max_abs={requested_applied_max:.8f}")
for name, mask in (("moving", movement), ("quiet", quiet)):
    raw_legs = walk_raw[mask, :12]
    print(f"{name}_raw_leg_output range=[{np.min(raw_legs):.3f},{np.max(raw_legs):.3f}] fraction_abs_ge_5.9={np.mean(np.abs(raw_legs) >= 5.9):.4f} frames_any_ge_5.9={np.mean(np.any(np.abs(raw_legs) >= 5.9, axis=1)):.4f}")
for name, mask in (("moving", movement[1:]), ("quiet", quiet[1:])):
    x = walk_steps[mask]
    raw_leg = raw_leg_steps[mask]
    raw_wheel = raw_wheel_steps[mask]
    print(f"{name}_leg_target_step_rad p50={np.percentile(x,50):.5f} p99={np.percentile(x,99):.5f} peak={np.max(x):.5f}; raw_leg_step_p99={np.percentile(raw_leg,99):.5f}; raw_wheel_step_p99={np.percentile(raw_wheel,99):.5f}")

# Group continuous 50 Hz command segments; quote tick intervals so the raw
# 2 ms LowState file can be inspected without assuming shared wall clocks.
def segments(mask, min_rows=15):
    starts = np.flatnonzero(mask & ~np.r_[False, mask[:-1]])
    ends = np.flatnonzero(mask & ~np.r_[mask[1:], False])
    return [(int(a), int(b)) for a, b in zip(starts, ends) if b - a + 1 >= min_rows]

for name, mask in (("moving", movement), ("quiet", quiet)):
    groups = sorted(segments(mask), key=lambda pair: pair[1] - pair[0], reverse=True)
    print(f"{name}_segments_ge_0.3s={len(groups)}")
    for a, b in groups[:4]:
        t0, t1 = walk[a]["tick"], walk[b]["tick"]
        print(f"  tick={t0}-{t1} duration_s={(walk[b]['mono']-walk[a]['mono'])/1e9:.2f} vx=[{np.min(walk_vx[a:b+1]):.3f},{np.max(walk_vx[a:b+1]):.3f}]")

ticks = np.array(capture_tick)
dq = np.array(capture_thigh_dq)
tau = np.array(capture_thigh_tau)
for name, mask in (("moving", movement), ("quiet", quiet)):
    groups = sorted(segments(mask), key=lambda pair: pair[1] - pair[0], reverse=True)
    if not groups:
        continue
    a, b = groups[0]
    sel = (ticks >= walk[a]["tick"]) & (ticks <= walk[b]["tick"])
    x_dq, x_tau = dq[sel], tau[sel]
    if len(x_dq) < 50:
        continue
    print(f"{name}_longest_2ms_feedback n={len(x_dq)} thigh_dq_rms={np.sqrt(np.mean(x_dq**2)):.4f} thigh_dq_peak={np.max(np.abs(x_dq)):.4f} thigh_tau_peak={np.max(np.abs(x_tau)):.3f}")

# Same-length windows make the frequency-band contrast interpretable. Use the
# tail of the longest zero-command segment to avoid its entry transient.
moving_groups = sorted(segments(movement), key=lambda pair: pair[1] - pair[0], reverse=True)
quiet_groups = sorted(segments(quiet), key=lambda pair: pair[1] - pair[0], reverse=True)
if moving_groups and quiet_groups:
    ma, mb = moving_groups[0]
    qa, qb = quiet_groups[0]
    moving_dq = dq[(ticks >= walk[ma]["tick"]) & (ticks <= walk[mb]["tick"])]
    quiet_dq = dq[(ticks >= walk[qa]["tick"]) & (ticks <= walk[qb]["tick"])]
    n = min(len(moving_dq), len(quiet_dq))
    if n >= 500:
        fs = 500.0
        window = np.hanning(n)[:, None]
        freqs = np.fft.rfftfreq(n, 1 / fs)
        band = (freqs >= 40) & (freqs <= 120)
        def band_energy(data):
            centered = data - data.mean(axis=0)
            spectrum = np.fft.rfft(centered * window, axis=0)
            return float(np.mean(np.sum(np.abs(spectrum[band]) ** 2, axis=0) / n ** 2))
        em = band_energy(moving_dq[:n])
        eq = band_energy(quiet_dq[-n:])
        print(f"same_length_40_120Hz_thigh_dq n={n} moving_energy={em:.8g} quiet_energy={eq:.8g} ratio={em / max(eq, 1e-12):.2f} (descriptive; no microphone/sound localization)")

for direction, direction_mask in (("forward", walk_vx >= 0.03), ("backward", walk_vx <= -0.03)):
    groups = sorted(segments(direction_mask), key=lambda pair: pair[1] - pair[0], reverse=True)
    if not groups or not quiet_groups:
        continue
    a, b = groups[0]
    qa, qb = quiet_groups[0]
    motion_dq = dq[(ticks >= walk[a]["tick"]) & (ticks <= walk[b]["tick"])]
    zero_dq = dq[(ticks >= walk[qa]["tick"]) & (ticks <= walk[qb]["tick"])]
    n = min(len(motion_dq), len(zero_dq))
    if n < 300:
        continue
    window = np.hanning(n)[:, None]
    freqs = np.fft.rfftfreq(n, 1 / 500.0)
    band = (freqs >= 40) & (freqs <= 120)
    def band_energy(data):
        spectrum = np.fft.rfft((data - data.mean(axis=0)) * window, axis=0)
        return float(np.mean(np.sum(np.abs(spectrum[band]) ** 2, axis=0) / n ** 2))
    em = band_energy(motion_dq[:n])
    eq = band_energy(zero_dq[-n:])
    print(f"{direction}_40_120Hz_thigh_dq n={n} tick={walk[a]['tick']}-{walk[b]['tick']} moving_energy={em:.8g} matched_quiet_energy={eq:.8g} ratio={em / max(eq, 1e-12):.2f} (descriptive)")

if protect_nonzero:
    print(f"nonzero_protection_examples={protect_nonzero[:3]}")
