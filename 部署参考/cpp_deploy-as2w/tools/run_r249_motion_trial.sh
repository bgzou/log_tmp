#!/usr/bin/env bash
# Supervised R249 flat low-speed session. Use only after zero-B acceptance.
# A=fixed stand/return, B=R249, Y=controlled squat, X=emergency passive.
set -u
[[ $# -eq 0 ]] || { echo 'Usage: run_r249_motion_trial.sh' >&2; exit 2; }
cd /root/as2w_deploy || exit 4
printf 'GO\n' | ./build-r249-full/deploy/robots/as2w/r249/as2w_r249_publish \
    models/r249/deploy.yaml config/r152_measured.map eth0 \
    --i-confirm-lowcmd-publish --enable-fsm-motion --stand t2 \
    --interp-sec 3 --squat-sec 4 --vx-limit 0.1
statuses=("${PIPESTATUS[@]}")
rc=${statuses[1]}
printf 'R249_MOTION_TRIAL_REMOTE_RC=%d\n' "$rc"
exit "$rc"
