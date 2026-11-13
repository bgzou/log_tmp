#!/usr/bin/env bash
# Bounded B zero-speed policy trial: A -> FixStand -> fixed PD hold ->
# B (gate-checked, once) -> 2s PolicyHandoff -> forced-zero policy hold 2.5s
# -> auto Brake -> ReturnStand -> fixed PD -> (Y or 15s timeout) -> repaired
# FixSquat -> 1s prone Passive -> stop. Stick deflection never maps to
# velocity in this trial. Requires a fresh separate review/consent.
set -u
if [[ $# -gt 1 || ( $# -eq 1 && $1 != --debug ) ]]; then
    echo 'Usage: run_r214_zero_b_trial.sh [--debug]' >&2
    exit 2
fi
EXTRA=()
[[ ${1:-} == --debug ]] && EXTRA+=(--debug)
BUILD=build-r214-zero-b
[[ ${1:-} == --debug ]] && BUILD=build-r214-debug-zero-b
cd /root/as2w_deploy || exit 4
printf 'GO\n' | "./$BUILD/deploy/robots/as2w/r214/as2w_r214_publish" \
    models/r214/deploy.yaml config/r152_measured.map eth0 \
    --i-confirm-lowcmd-publish --zero-b-trial --stand t2 \
    --interp-sec 3 --squat-sec 4 --stand-hold-seconds 15 "${EXTRA[@]}"
statuses=("${PIPESTATUS[@]}")
rc=${statuses[1]}
printf 'ZERO_B_TRIAL_REMOTE_RC=%d\n' "$rc"
exit "$rc"
