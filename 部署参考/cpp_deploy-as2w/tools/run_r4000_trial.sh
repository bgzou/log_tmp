#!/usr/bin/env bash
# One bounded B cycle on the R4000 joystick candidate (rolling-4000-stage020
# research weights, training-contract 5 Hz leg filter + 0.9 rad/s slew +
# pure_turn_common_scale=0 wheel mapping): A fixed stand, B 2s zero handoff,
# then up to 30s of remote LY vx and RX yaw within the deploy.yaml speed
# envelope (vx_limit/wz_limit = 0.2/0.1; the session may restrict further
# through --vx-limit/--wz-limit). Centering sticks zeroes the command, A
# brakes early, Y squats, X requests emergency damping. Debug recording is
# mandatory for this new policy until real-robot behavior is characterized.
# Requires per-action operator consent.
set -u
DEBUG=1
VX_LIMIT=0.4
WZ_LIMIT=0.1
while [[ $# -gt 0 ]]; do
    case "$1" in
        --debug) DEBUG=1; shift ;;
        --no-debug) DEBUG=0; shift ;;
        --vx-limit)
            [[ $# -ge 2 ]] && VX_LIMIT=$2; shift 2 ;;
        --wz-limit)
            [[ $# -ge 2 ]] && WZ_LIMIT=$2; shift 2 ;;
        *) echo "FATAL: unexpected trial option: $1" >&2; exit 2 ;;
    esac
done
BUILD=build-r4000-joystick
EXTRA=(--debug --vx-limit "$VX_LIMIT" --wz-limit "$WZ_LIMIT")
[[ $DEBUG == 0 ]] && EXTRA=(--vx-limit "$VX_LIMIT" --wz-limit "$WZ_LIMIT")
cd /root/as2w_deploy || exit 4
printf 'GO\n' | "./$BUILD/deploy/robots/as2w/r4000/as2w_r4000_joystick_publish" \
    models/r4000/deploy.yaml config/r152_measured.map eth0 \
    --i-confirm-lowcmd-publish --zero-b-trial --stand t2 \
    --interp-sec 3 --squat-sec 4 --stand-hold-seconds 30 "${EXTRA[@]}"
statuses=("${PIPESTATUS[@]}")
rc=${statuses[1]}
printf 'R4000_REMOTE_RC=%d\n' "$rc"
exit "$rc"
