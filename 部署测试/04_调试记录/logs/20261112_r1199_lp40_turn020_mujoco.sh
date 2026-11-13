#!/usr/bin/env bash
set -euo pipefail
project=/home/caolin/as2w_workstation
logdir="$project/部署测试/04_调试记录/logs"
export PYTHONPATH=/tmp/opencode/r1199_eval_work:/tmp/opencode/omni/runtime
export R1199_MEASURED_START=1
export R1199_MEASURED_Q_FILE="$logdir/20261111_r1199_fresh_fixed_q.txt"
export R1199_MEASURED_PITCH_RAD=-0.08640587718296669
export R1199_COMPARE_TRACE=1
export R1199_MOTION_SECONDS=10
turn_rate=${R1199_TEST_WZ:-.2}
case "$turn_rate" in
  .1) turn_tag=010 ;;
  .2) turn_tag=020 ;;
  *) echo "unsupported turn rate $turn_rate" >&2; exit 2 ;;
esac
export R1199_TURN_RATE=$turn_rate
export R1199_LOWPASS_MS=40
ckpt="$project/部署参考/Rob2Nav-rolling-1199-preview/deliveries/as2w-deploy/rolling-1199-simulation-preview/model_1199.pt"
for seed in 101 202 303; do
  for direction in turn_left turn_right; do
    export R1199_COMPARE_SEED=$seed
    export R1199_COMPARE_CASES=$direction
    out="$logdir/r1199_debug_lowpass_${direction}${turn_tag}_10s_seed${seed}_tau40"
    echo "=== seed=$seed direction=$direction wz=$turn_rate tau=40 ==="
    timeout 300 python3 /tmp/opencode/r1199_lowpass_eval.py \
      /tmp/opencode/omni/assets "$ckpt" "$out" \
      --speed .2 --rolling-fixed-exit --rolling-stand-compensation \
      --rolling-wheel-hold --park-precalibrated --park-continuous-bias --park-straight-bias \
      --native-pd --substep-safety --push-schedule off --trials 1 --trace \
      > "$logdir/r1199_debug_lowpass_${direction}${turn_tag}_10s_seed${seed}_tau40.log" 2>&1
    echo "completed seed=$seed direction=$direction"
  done
done
echo ALL_DONE
