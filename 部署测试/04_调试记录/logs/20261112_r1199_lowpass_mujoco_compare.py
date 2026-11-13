"""Compare matched R1199 MuJoCo no-filter/60-ms results on local logs."""

import json
from pathlib import Path

import numpy as np

base = Path(__file__).resolve().parent
for speed_tag in ("005", "020"):
  for seed in (101, 202, 303):
    for direction in ("forward", "back"):
      for tau in ((0, 20, 40, 60) if speed_tag == "005" else (0, 40, 60)):
        folder = base / f"r1199_debug_lowpass_{direction}{speed_tag}_10s_seed{seed}_tau{tau}"
        d = json.loads((folder / "mujoco-rolling-diagnostic.json").read_text())[0]
        trace = json.loads((folder / "compare-forward-trace.json").read_text())
        q = np.array([frame["q_target_rad"] for frame in trace])
        dq = np.max(np.abs(np.diff(q, axis=0)), axis=1)
        loads = np.array([frame["wheel_load_n"] for frame in trace])
        actual = np.array([frame["q_actual_rad"] for frame in trace])
        print(
            f"speed_tag={speed_tag} seed={seed} case={direction} tau_ms={tau} frames={len(trace)} "
            f"stable={d['stable']} tracked={d['tracked']} held={d['held']} "
            f"nonwheel={d['nonwheel']} terminated={d['terminated']} "
            f"angle_violation={d['angle_violation']} stance_violation={d['stance_violation']} "
            f"mean_vx={d['mean_velocity'][0]:.4f} "
            f"hold_displacement_m={d['hold_displacement_m']:.4f} "
            f"brake_distance_m={d['brake_distance_m']:.4f} "
            f"max_effort_ratio={d['max_sim_effort_ratio']:.3f} "
            f"min_wheel_load_N={loads.min():.2f} "
            f"target_step_p99_rad={np.percentile(dq,99):.5f} "
            f"target_step_peak_rad={dq.max():.5f} "
            f"actual_q_peak_abs_rad={np.abs(actual).max():.4f} "
            f"first_nonwheel={d['first_nonwheel_contact']}"
        )
