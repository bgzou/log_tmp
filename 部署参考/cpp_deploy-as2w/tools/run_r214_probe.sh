#!/usr/bin/env bash
# Bounded one-axis diagnostic launcher inside the CPRO Ubuntu rootfs.
# Operator consent is a separate field gate; this script only preserves the
# publisher's real status across the GO pipe. Do not use for FSM motion.
set -u
if [[ $# -eq 1 && $1 == --selftest ]]; then
    printf 'GO\n' | /bin/bash -c 'exit 134'
    statuses=("${PIPESTATUS[@]}")
    rc=${statuses[1]}
    printf 'PROBE_REMOTE_RC=%d\n' "$rc"
    exit "$rc"
fi
if [[ $# -ne 3 ]]; then
    echo 'Usage: run_r214_probe.sh CONTRACT_INDEX AMPLITUDE PROBE_KP' >&2
    exit 2
fi
index=$1 amplitude=$2 probe_kp=$3
printf 'Probe contract index=%s amplitude=%s kp=%s. Type GO: ' \
    "$index" "$amplitude" "$probe_kp"
read -r confirmation || exit 3
if [[ "$confirmation" != GO ]]; then
    echo 'Probe aborted before DDS initialization.' >&2
    exit 3
fi
cd /root/as2w_deploy || exit 4
printf 'GO\n' | ./build-r214-publish/deploy/robots/as2w/r214/as2w_r214_publish \
    models/r214/deploy.yaml config/r152_measured.map eth0 \
    --i-confirm-lowcmd-publish --probe-index "$index" \
    --probe-amplitude "$amplitude" --probe-kp "$probe_kp"
statuses=("${PIPESTATUS[@]}")
rc=${statuses[1]}
printf 'PROBE_REMOTE_RC=%d\n' "$rc"
exit "$rc"
