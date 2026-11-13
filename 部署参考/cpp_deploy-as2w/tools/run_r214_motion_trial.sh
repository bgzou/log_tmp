#!/usr/bin/env bash
# Supervised, one-cycle low-speed R214 field session. Requires per-session
# operator consent before invocation. A rises to fixed PD; B enters R214 after
# a zero-command blend; A brakes and returns to fixed PD; Y squats and exits.
# X is emergency passive. This launcher remains offline until the new FSM's
# stand/return handoffs have passed simulation and separate field acceptance.
set -u
if [[ $# -gt 1 || ( $# -eq 1 && $1 != --debug ) ]]; then
    echo 'Usage: run_r214_motion_trial.sh [--debug]' >&2
    exit 2
fi
EXTRA=()
[[ ${1:-} == --debug ]] && EXTRA+=(--debug)
BUILD=build-r214-ab-fsm-full
[[ ${1:-} == --debug ]] && BUILD=build-r214-debug-full
cd /root/as2w_deploy || exit 4
printf 'GO\n' | "./$BUILD/deploy/robots/as2w/r214/as2w_r214_publish" \
    models/r214/deploy.yaml config/r152_measured.map eth0 \
    --i-confirm-lowcmd-publish --enable-fsm-motion --stand t2 \
    --interp-sec 3 --squat-sec 4 --vx-limit 0.1 "${EXTRA[@]}"
statuses=("${PIPESTATUS[@]}")
rc=${statuses[1]}
printf 'MOTION_TRIAL_REMOTE_RC=%d\n' "$rc"
exit "$rc"
