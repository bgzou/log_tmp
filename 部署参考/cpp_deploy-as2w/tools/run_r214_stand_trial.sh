#!/usr/bin/env bash
# Candidate bounded field session: A -> FixStand -> fixed PD hold ->
# Y (or 15s timeout) -> FixSquat -> 1s prone Passive -> stop.
# B is compile-time unavailable.
# Requires a fresh separate review/consent; the old A trial used zero R214 hold.
set -u
if [[ $# -gt 1 || ( $# -eq 1 && $1 != --debug ) ]]; then
    echo 'Usage: run_r214_stand_trial.sh [--debug]' >&2
    exit 2
fi
EXTRA=()
[[ ${1:-} == --debug ]] && EXTRA+=(--debug)
BUILD=build-r214-ab-fsm
[[ ${1:-} == --debug ]] && BUILD=build-r214-debug-stand
cd /root/as2w_deploy || exit 4
printf 'GO\n' | "./$BUILD/deploy/robots/as2w/r214/as2w_r214_publish" \
    models/r214/deploy.yaml config/r152_measured.map eth0 \
    --i-confirm-lowcmd-publish --stand-trial --stand t2 \
    --interp-sec 3 --squat-sec 4 --stand-hold-seconds 15 "${EXTRA[@]}"
statuses=("${PIPESTATUS[@]}")
rc=${statuses[1]}
printf 'STAND_TRIAL_REMOTE_RC=%d\n' "$rc"
exit "$rc"
