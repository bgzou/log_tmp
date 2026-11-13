#!/usr/bin/env bash
set -euo pipefail
project=/home/caolin/as2w_workstation
logdir="$project/部署测试/04_调试记录/logs"
export PYTHONPATH=/tmp/opencode/r1199_eval_work:/tmp/opencode/omni/runtime
export R1199_MEASURED_START=1
export R1199_MEASURED_Q_FILE="$logdir/20261111_r1199_fresh_fixed_q.txt"
export R1199_MEASURED_PITCH_RAD=-0.08640587718296669
export R1199_MOTION_SECONDS=10
CKPT="$project/部署参考/Rob2Nav-rolling-1199-preview/deliveries/as2w-deploy/rolling-1199-simulation-preview/model_1199.pt"
ASSETS=/tmp/opencode/omni/assets
for rate in 0.1 0.05; do
  for seed in 101 202 303; do
    for case in turn_left turn_right; do
      out="$logdir/r1199_training_contract_${case}_r${rate}_seed${seed}"
      export R1199_COMPARE_SEED=$seed
      export R1199_COMPARE_CASES=$case
      export R1199_TURN_RATE=$rate
      echo "=== rate=$rate case=$case seed=$seed ==="
      timeout 600 python3 "$project/部署参考/as2w-flat-rerun/r1199_colleague_eval_ablation.py" \
        "$ASSETS" "$CKPT" "$out" \
        --speed .2 --rolling-fixed-exit --rolling-stand-compensation \
        --rolling-wheel-hold --park-precalibrated --park-continuous-bias --park-straight-bias \
        --native-pd --substep-safety --push-schedule off --trials 1 \
        > "$logdir/r1199_training_contract_${case}_r${rate}_seed${seed}.log" 2>&1
      echo "  rc=$?"
    done
  done
done
echo ALL_DONE
