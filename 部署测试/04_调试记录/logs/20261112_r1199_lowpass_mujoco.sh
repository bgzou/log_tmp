#!/usr/bin/env bash
# caolin-only matched closed-loop MuJoCo comparison; never touches the robot.
set -euo pipefail
project=/home/caolin/as2w_workstation
logdir="$project/部署测试/04_调试记录/logs"
cp "$logdir/20261112_r1199_lowpass_mujoco_eval.py" /tmp/opencode/r1199_lowpass_eval.py
sha256sum /tmp/opencode/r1199_lowpass_eval.py
export PYTHONPATH=/tmp/opencode/r1199_eval_work:/tmp/opencode/omni/runtime
export R1199_MEASURED_START=1
export R1199_MEASURED_Q_FILE="$logdir/20261111_r1199_fresh_fixed_q.txt"
export R1199_MEASURED_PITCH_RAD=-0.08640587718296669
export R1199_COMPARE_TRACE=1
export R1199_MOTION_SECONDS=10
ckpt="$project/部署参考/Rob2Nav-rolling-1199-preview/deliveries/as2w-deploy/rolling-1199-simulation-preview/model_1199.pt"
assets=/tmp/opencode/omni/assets
speed=${R1199_TEST_SPEED:-.2}
case "$speed" in
  .2) speed_tag=020 ;;
  .05) speed_tag=005 ;;
  *) echo "unsupported matched speed $speed" >&2; exit 2 ;;
esac
if [[ $# == 0 ]]; then set -- 101; fi
read -r -a taus <<< "${R1199_TEST_TAUS:-0 60}"
for seed in "$@"; do
  for tau in "${taus[@]}"; do
    [[ $tau =~ ^(0|[1-9][0-9]?|1[0-9][0-9]|200)$ ]] || { echo "bad tau=$tau" >&2; exit 2; }
    export R1199_LOWPASS_MS=$tau
    for direction in forward back; do
      export R1199_COMPARE_SEED=$seed
      export R1199_COMPARE_CASES=$direction
      out="$logdir/r1199_debug_lowpass_${direction}${speed_tag}_10s_seed${seed}_tau${tau}"
      echo "=== tau=$tau direction=$direction seed=$seed speed=$speed ==="
      timeout 300 python3 /tmp/opencode/r1199_lowpass_eval.py \
        "$assets" "$ckpt" "$out" \
        --speed "$speed" --rolling-fixed-exit --rolling-stand-compensation \
        --rolling-wheel-hold --park-precalibrated --park-continuous-bias --park-straight-bias \
        --native-pd --substep-safety --push-schedule off --trials 1 --trace \
        > "$logdir/r1199_debug_lowpass_${direction}${speed_tag}_10s_seed${seed}_tau${tau}.log" 2>&1
      echo "completed tau=$tau direction=$direction seed=$seed"
    done
  done
done
echo ALL_DONE
