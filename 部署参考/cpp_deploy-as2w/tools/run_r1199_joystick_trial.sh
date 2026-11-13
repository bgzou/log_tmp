#!/usr/bin/env bash
# One bounded B cycle: A fixed stand, 2s zero handoff, then up to 60s of
# remote LY forward/back +/-0.05m/s and RX yaw +/-0.05rad/s. LX/RY ignored.
# Releasing sticks returns commands to zero; A brakes early, Y squats,
# X requests emergency damping. Requires per-action operator consent.
set -u
if [[ $# -ne 0 ]]; then
    echo 'Usage: run_r1199_joystick_trial.sh' >&2
    exit 2
fi
cd /root/as2w_deploy || exit 4
printf 'GO\n' | ./build-r1199-joystick/deploy/robots/as2w/r1199/as2w_r1199_joystick_publish \
    models/r1199/deploy.yaml config/r152_measured.map eth0 \
    --i-confirm-lowcmd-publish --zero-b-trial --stand t2 \
    --vx-limit .05 --interp-sec 3 --squat-sec 4 --stand-hold-seconds 15
statuses=("${PIPESTATUS[@]}")
rc=${statuses[1]}
printf 'R1199_JOYSTICK_REMOTE_RC=%d\n' "$rc"
exit "$rc"
