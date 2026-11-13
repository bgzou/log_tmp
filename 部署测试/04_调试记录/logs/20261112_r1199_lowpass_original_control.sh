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
export R1199_COMPARE_SEED=101
export R1199_COMPARE_CASES=forward
unset R1199_LOWPASS_MS
ckpt="$project/部署参考/Rob2Nav-rolling-1199-preview/deliveries/as2w-deploy/rolling-1199-simulation-preview/model_1199.pt"
timeout 300 python3 "$project/部署参考/as2w-flat-rerun/r1199_colleague_eval_ablation.py" \
  /tmp/opencode/omni/assets "$ckpt" "$logdir/r1199_debug_lowpass_original_forward020_10s_seed101" \
  --speed .2 --rolling-fixed-exit --rolling-stand-compensation \
  --rolling-wheel-hold --park-precalibrated --park-continuous-bias --park-straight-bias \
  --native-pd --substep-safety --push-schedule off --trials 1 --trace \
  > "$logdir/r1199_debug_lowpass_original_forward020_10s_seed101.log" 2>&1
echo ORIGINAL_DONE
