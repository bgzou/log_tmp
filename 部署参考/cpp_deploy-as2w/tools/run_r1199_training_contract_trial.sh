#!/usr/bin/env bash
# One bounded B cycle on the isolated R1199 training-contract candidate:
# A fixed stand, B 2s zero handoff, then up to 60s of remote LY vx and RX
# yaw within the deploy.yaml speed envelope (vx_limit/wz_limit, default 0.2;
# CLI --vx-limit/--wz-limit may only restrict further). Stand-bias continuous/
# straight and parking odometry/settle follow the model_1199 training runtime.
# Releasing sticks returns commands to zero; A brakes early, Y squats,
# X requests emergency damping. Requires per-action operator consent.
set -u
DEBUG=0
LOWPASS_MS=0
LOWPASS_WHEELS=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --debug) DEBUG=1; shift ;;
        --lowpass-wheels) LOWPASS_WHEELS=1; shift ;;
        --lowpass-ms)
            [[ $# -ge 2 && $2 =~ ^[0-9]+$ && $2 -ge 1 && $2 -le 200 ]] || {
                echo 'FATAL: --lowpass-ms must be an integer in 1..200' >&2; exit 2;
            }
            LOWPASS_MS=$2; shift 2 ;;
        *) echo "FATAL: unexpected trial option: $1" >&2; exit 2 ;;
    esac
done
[[ $LOWPASS_WHEELS == 0 || $LOWPASS_MS -gt 0 ]] || {
    echo 'FATAL: --lowpass-wheels requires --lowpass-ms' >&2; exit 2;
}
BUILD=build-r1199-training-contract
EXTRA=()
[[ $DEBUG == 1 ]] && EXTRA+=(--debug)
[[ $DEBUG == 1 && $LOWPASS_MS -eq 0 ]] && BUILD=build-r1199-training-contract-debug
if [[ $LOWPASS_MS -gt 0 ]]; then
    BUILD=build-r1199-training-contract-filter
    EXTRA+=(--policy-lowpass-ms "$LOWPASS_MS")
    [[ $LOWPASS_WHEELS == 1 ]] && EXTRA+=(--policy-lowpass-wheels)
    # First filtered field candidate: preserve the reviewed deploy.yaml caps
    # (vx 0.2 m/s, wz 0.1 rad/s) and use the independent 15 s C++ cap.
    EXTRA+=(--vx-limit 0.2 --wz-limit 0.1)
fi
cd /root/as2w_deploy || exit 4
printf 'GO\n' | "./$BUILD/deploy/robots/as2w/r1199/as2w_r1199_joystick_publish" \
    models/r1199/deploy.yaml config/r152_measured.map eth0 \
    --i-confirm-lowcmd-publish --zero-b-trial --stand t2 \
    --interp-sec 3 --squat-sec 4 --stand-hold-seconds 30 "${EXTRA[@]}"
statuses=("${PIPESTATUS[@]}")
rc=${statuses[1]}
printf 'R1199_TRAINING_CONTRACT_REMOTE_RC=%d\n' "$rc"
exit "$rc"
