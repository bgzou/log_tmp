#!/usr/bin/env bash
# Bounded R270 zero-command first trial. Sticks are ignored. The policy phase
# is capped at 2 seconds because offline MuJoCo predicts ~0.25-0.30 m drift.
# Requires explicit per-run field consent after offline review.
set -u
[[ $# -eq 0 ]] || { echo 'Usage: run_r270_zero_b_trial.sh' >&2; exit 2; }
cd /root/as2w_deploy || exit 4
printf 'GO\n' | ./build-r270-zero-b/deploy/robots/as2w/r270/as2w_r270_publish \
    models/r270/deploy.yaml config/r152_measured.map eth0 \
    --i-confirm-lowcmd-publish --zero-b-trial --stand t2 \
    --interp-sec 3 --squat-sec 4 --stand-hold-seconds 15
statuses=("${PIPESTATUS[@]}")
rc=${statuses[1]}
printf 'R270_ZERO_B_TRIAL_REMOTE_RC=%d\n' "$rc"
exit "$rc"

