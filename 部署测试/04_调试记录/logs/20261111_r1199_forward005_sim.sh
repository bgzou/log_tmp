#!/usr/bin/env bash
# caolin simulation server only. No training-server edits or robot commands.
set -euo pipefail
project=/home/caolin/as2w_workstation
export PYTHONPATH=/tmp/opencode/r1199_eval_work:/tmp/opencode/omni/runtime
export R1199_MEASURED_START=1
export R1199_MEASURED_Q_FILE="$project/部署测试/04_调试记录/logs/20261111_r1199_fresh_fixed_q.txt"
export R1199_MEASURED_PITCH_RAD=-0.08640587718296669
export R1199_COMPARE_FORWARD_ONLY=1
seed=${R1199_SIM_SEED:-202}
export R1199_COMPARE_SEED=$seed
export R1199_MOTION_SECONDS=2
python3 "$project/部署参考/as2w-flat-rerun/r1199_colleague_eval_ablation.py" \
  /tmp/opencode/omni/assets \
  "$project/部署参考/Rob2Nav-rolling-1199-preview/deliveries/as2w-deploy/rolling-1199-simulation-preview/model_1199.pt" \
  "$project/部署测试/04_调试记录/logs/r1199_forward005_2s_seed${seed}" \
  --speed .05 --rolling-fixed-exit --rolling-stand-compensation \
  --rolling-wheel-hold --park-precalibrated --park-odometry \
  --park-common-gain-scale .5 --park-settle-joints --native-pd \
  --substep-safety --push-schedule off --trials 1
