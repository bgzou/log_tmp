#!/usr/bin/env bash
# One bounded B getup chain on the getup1199 build (recovery deep-side
# model_1199, staged-rise + low-support latch + integral stand + predictive
# guard training contract): from prone, B = knee-open (~2.5s) -> staged rise
# (~3-5s) -> FixedStand hold (auto-squat after --stand-hold-seconds) -> Y
# squat. A is disabled in this build. One B chain per session. X requests
# emergency damping. Debug recording is mandatory until real-robot getup
# behavior is characterized. Requires per-action operator consent.
set -u
DEBUG=1
HOLD_SECONDS=30
while [[ $# -gt 0 ]]; do
    case "$1" in
        --debug) DEBUG=1; shift ;;
        --no-debug) DEBUG=0; shift ;;
        --stand-hold-seconds)
            [[ $# -ge 2 ]] && HOLD_SECONDS=$2; shift 2 ;;
        *) echo "FATAL: unexpected trial option: $1" >&2; exit 2 ;;
    esac
done
BUILD=build-getup1199
EXTRA=(--debug)
[[ $DEBUG == 0 ]] && EXTRA=()
cd /root/as2w_deploy || exit 4
printf 'GO\n' | "./$BUILD/deploy/robots/as2w/getup1199/as2w_getup1199_publish" \
    models/getup1199/deploy.yaml config/r152_measured.map eth0 \
    --i-confirm-lowcmd-publish --getup-trial \
    --stand-hold-seconds "$HOLD_SECONDS" "${EXTRA[@]}"
statuses=("${PIPESTATUS[@]}")
rc=${statuses[1]}
printf 'GETUP1199_REMOTE_RC=%d\n' "$rc"
exit "$rc"
