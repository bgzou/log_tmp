#!/usr/bin/env bash
# R1199 filter-comparison: paired tau=0 vs tau=40 MuJoCo yaw runs (2026-11-12).
# Same weight / measured start / contract / friction / actuator gains as the
# archived tau=40 turn runs; the ONLY difference is R1199_LOWPASS_MS.
# Read-only for the project; outputs stay in /tmp unless copied deliberately.
# The archived tau=40 counterparts are
#   部署测试/04_调试记录/logs/r1199_debug_lowpass_turn_{left,right}010_10s_seed{101,202,303}_tau40/
# produced with the identical evaluator (SHA 698d9552...) and R1199_TURN_RATE=0.10.
set -euo pipefail
project=/home/caolin/as2w_workstation
logdir="$project/部署测试/04_调试记录/logs"
out=/tmp/opencode/r1199_filter_compare/mujoco_tau0
mkdir -p "$out"
cp "$logdir/20261112_r1199_lowpass_mujoco_eval.py" /tmp/opencode/r1199_lowpass_eval.py
sha256sum /tmp/opencode/r1199_lowpass_eval.py   # expect 698d95528f19b331...
export PYTHONPATH=/tmp/opencode/r1199_eval_work:/tmp/opencode/omni/runtime
export R1199_MEASURED_START=1
export R1199_MEASURED_Q_FILE="$logdir/20261111_r1199_fresh_fixed_q.txt"
export R1199_MEASURED_PITCH_RAD=-0.08640587718296669
export R1199_COMPARE_TRACE=1
export R1199_MOTION_SECONDS=10
export R1199_LOWPASS_MS=0          # <- the only difference vs the archived tau40 runs
export R1199_TURN_RATE=0.10
ckpt="$project/部署参考/Rob2Nav-rolling-1199-preview/deliveries/as2w-deploy/rolling-1199-simulation-preview/model_1199.pt"
assets=/tmp/opencode/omni/assets
for direction in turn_left turn_right; do
  for seed in 101 202 303; do
    export R1199_COMPARE_CASES=$direction R1199_COMPARE_SEED=$seed
    timeout 300 python3 /tmp/opencode/r1199_lowpass_eval.py \
      "$assets" "$ckpt" "$out/${direction}010_10s_seed${seed}_tau0" \
      --speed 0.2 --rolling-fixed-exit --rolling-stand-compensation \
      --rolling-wheel-hold --park-precalibrated --park-continuous-bias --park-straight-bias \
      --native-pd --substep-safety --push-schedule off --trials 1 --trace \
      > "$out/${direction}010_10s_seed${seed}_tau0.log" 2>&1
    echo "completed $direction seed$seed"
  done
done
echo ALL_DONE
