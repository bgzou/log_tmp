#!/usr/bin/env bash
# Bounded R249 zero-speed first trial. Sticks are ignored. Requires explicit
# per-run field consent after offline review.
set -u
[[ $# -eq 0 ]] || { echo 'Usage: run_r249_zero_b_trial.sh' >&2; exit 2; }
cd /root/as2w_deploy || exit 4
printf 'GO\n' | ./build-r249-zero-b/deploy/robots/as2w/r249/as2w_r249_publish \
    models/r249/deploy.yaml config/r152_measured.map eth0 \
    --i-confirm-lowcmd-publish --zero-b-trial --stand t2 \
    --interp-sec 3 --squat-sec 4 --stand-hold-seconds 15
statuses=("${PIPESTATUS[@]}")
rc=${statuses[1]}
printf 'R249_ZERO_B_TRIAL_REMOTE_RC=%d\n' "$rc"
exit "$rc"
