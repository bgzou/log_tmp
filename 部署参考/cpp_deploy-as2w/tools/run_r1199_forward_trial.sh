#!/usr/bin/env bash
# One bounded B cycle: A fixed stand, B 2s zero handoff followed by 2s
# automatic forward vx=0.05m/s (with command slew), then Brake/ReturnStand.
# Y or 15s timeout squats. Sticks have no motion effect in this build.
# Requires per-action operator consent; never call from an unattended task.
set -u
if [[ $# -ne 0 ]]; then
    echo 'Usage: run_r1199_forward_trial.sh' >&2
    exit 2
fi
cd /root/as2w_deploy || exit 4
printf 'GO\n' | ./build-r1199-forward/deploy/robots/as2w/r1199/as2w_r1199_forward_publish \
    models/r1199/deploy.yaml config/r152_measured.map eth0 \
    --i-confirm-lowcmd-publish --zero-b-trial --stand t2 \
    --vx-limit .05 --interp-sec 3 --squat-sec 4 --stand-hold-seconds 15
statuses=("${PIPESTATUS[@]}")
rc=${statuses[1]}
printf 'R1199_FORWARD_REMOTE_RC=%d\n' "$rc"
exit "$rc"
