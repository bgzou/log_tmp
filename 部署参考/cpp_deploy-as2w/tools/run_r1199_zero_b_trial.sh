#!/usr/bin/env bash
# One R1199 B cycle only: A fixed stand, B 2s zero-command strategy, automatic
# Brake/ReturnStand, Y (or 15s timeout) controlled squat. No joystick motion.
# Requires explicit consent for this individual robot experiment.
set -u
if [[ $# -ne 0 ]]; then
    echo 'Usage: run_r1199_zero_b_trial.sh' >&2
    exit 2
fi
cd /root/as2w_deploy || exit 4
printf 'GO\n' | ./build-r1199-zero-b/deploy/robots/as2w/r1199/as2w_r1199_publish \
    models/r1199/deploy.yaml config/r152_measured.map eth0 \
    --i-confirm-lowcmd-publish --zero-b-trial --stand t2 \
    --interp-sec 3 --squat-sec 4 --stand-hold-seconds 15
statuses=("${PIPESTATUS[@]}")
rc=${statuses[1]}
printf 'R1199_ZERO_B_REMOTE_RC=%d\n' "$rc"
exit "$rc"
