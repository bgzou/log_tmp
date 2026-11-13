#!/usr/bin/env bash
# Bounded R284 zero-command first trial. Sticks are ignored.
set -u
echo 'FATAL: R284 real-robot LowCmd blocked after 2026-11-10 violent oscillation incident. Offline diagnosis required.' >&2
exit 78
[[ $# -eq 0 ]] || { echo 'Usage: run_r284_zero_b_trial.sh' >&2; exit 2; }
cd /root/as2w_deploy || exit 4
printf 'GO\n' | ./build-r284-zero-b/deploy/robots/as2w/r284/as2w_r284_publish \
    models/r284/deploy.yaml config/r152_measured.map eth0 \
    --i-confirm-lowcmd-publish --zero-b-trial --stand t2 \
    --interp-sec 3 --squat-sec 4 --stand-hold-seconds 15
statuses=("${PIPESTATUS[@]}")
rc=${statuses[1]}
printf 'R284_ZERO_B_TRIAL_REMOTE_RC=%d\n' "$rc"
exit "$rc"

