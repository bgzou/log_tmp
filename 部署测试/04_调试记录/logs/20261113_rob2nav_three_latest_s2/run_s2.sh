#!/usr/bin/env bash
# S2 closed-loop MuJoCo runs for the three latest AS2-W weights.
set -u
W=/home/caolin/as2w_workstation
BACK=$W/部署参考/Rob2Nav-as2w-backup/training/as2w-backup
ROOT=$BACK/as2w-current
DEP=$BACK/as2w-r284-release/deliveries/as2w-deploy
OUT=/tmp/opencode/as2w_s2_check
cd "$ROOT"

launch() { # name cmd...
  local name=$1; shift
  mkdir -p "$OUT/$name"
  nohup "$@" > "$OUT/$name/stdout.log" 2>&1 &
  echo "$name pid=$! "
}

RECC=$ROOT/runs/recovery/deep-side-curriculum/formal/model_1199.pt
BANK=$ROOT/runs/r290-three-skills/supported-getup-holdout.json
SHALLOW=$ROOT/runs/r290-three-skills/supported-getup-shallow-holdout.json
SIDE=$ROOT/runs/r290-three-skills/supported-getup-side-holdout.json
RPATH=runs/recovery/deep-side-curriculum/formal/model_1199.pt

for s in 7301 7401 7402; do
  launch "rec_random_$s" env -u LD_LIBRARY_PATH PYTHONPATH="$ROOT/code:$DEP/flat-r284-500-preview/runtime:$DEP/omni-blind-stairs-r152/runtime:$DEP" \
    python3 code/eval_as2w_mujoco_recovery.py assets/r237-train-root "$RPATH" runs/r290-three-skills/supported-getup-holdout.json "$OUT/rec_random_$s" \
    --seed "$s" --low-support-handoff --packet-loss .02 --predictive-guard --paired-tilt
done

launch rec_shallow_7301 env -u LD_LIBRARY_PATH PYTHONPATH="$ROOT/code:$DEP/flat-r284-500-preview/runtime:$DEP/omni-blind-stairs-r152/runtime:$DEP" \
  python3 code/eval_as2w_mujoco_recovery.py assets/r237-train-root "$RPATH" runs/r290-three-skills/supported-getup-shallow-holdout.json "$OUT/rec_shallow_7301" \
  --seed 7301 --low-support-handoff --packet-loss .02 --predictive-guard --side-pose-bank runs/r290-three-skills/supported-getup-shallow-holdout.json

launch rec_side_7301 env -u LD_LIBRARY_PATH PYTHONPATH="$ROOT/code:$DEP/flat-r284-500-preview/runtime:$DEP/omni-blind-stairs-r152/runtime:$DEP" \
  python3 code/eval_as2w_mujoco_recovery.py assets/r237-train-root "$RPATH" runs/r290-three-skills/supported-getup-side-holdout.json "$OUT/rec_side_7301" \
  --seed 7301 --low-support-handoff --packet-loss .02 --predictive-guard --side-pose-bank runs/r290-three-skills/supported-getup-side-holdout.json

# ---- rolling (archived candidate model_1200) ----
ROL=$ROOT/runs/rolling/actor-wheel-saturation-loss.Uliv0s
launch rolling_1200 env -u LD_LIBRARY_PATH PYTHONPATH="$ROL/source:$DEP/flat-r284-500-preview/runtime:$DEP/omni-blind-stairs-r152/runtime:$DEP" \
  python3 "$ROL/source/eval_heldout.py" assets/r237-train-root "$ROL/baseline/train/model_1200.pt" "$OUT/rolling_1200" \
  --speed .20 --rolling-fixed-exit --rolling-stand-compensation --rolling-wheel-hold --park-precalibrated \
  --park-continuous-bias --park-straight-bias --pure-turn-common-scale 0 --park-policy-rad 0 --rolling-leg-filter-hz 5 \
  --native-pd --substep-safety --acceptance --packet-loss .02 --trials 12

# ---- stepping (formal model_1199, same protocol as their holdout) ----
STEPP=$ROOT/runs/stepping/support-aware-reward.bp4984
launch stepping_1199 env -u LD_LIBRARY_PATH PYTHONPATH="$ROOT/code:$DEP/flat-r284-500-preview/runtime:$DEP/omni-blind-stairs-r152/runtime:$DEP" \
  python3 code/eval_as2w_mujoco_stepping.py assets/r237-train-root "$STEPP/formal/model_1199.pt" "$OUT/stepping_1199" \
  --seed 8302 --trials 8 --native-pd --leg-pd 55 2 --calf-mesh-diagnostic --down-approach .55 \
  --sequence-period 8 --sequence-stride .35 --packet-loss .02 --target-margin .05 --sequence-attitude --predictive-guard
echo "all launched"
