#!/usr/bin/env bash
set -euo pipefail
cd /root/as2w_deploy
export LD_LIBRARY_PATH=/root/unitree_sdk2_install/lib:/root/ort122/lib:${LD_LIBRARY_PATH:-}
base=deploy/robots/as2w/r1199/as2w_r1199_joystick_publish
for build in build-r1199-training-contract build-r1199-training-contract-debug build-r1199-training-contract-filter; do
  "./$build/$base" models/r1199/deploy.yaml config/r152_measured.map --offline-audit | grep -a '^raw_hex=' > "/tmp/${build}_audit_frames.txt"
  printf '%s ' "$build"
  sha256sum "/tmp/${build}_audit_frames.txt"
done
cmp /tmp/build-r1199-training-contract_audit_frames.txt /tmp/build-r1199-training-contract-debug_audit_frames.txt
cmp /tmp/build-r1199-training-contract_audit_frames.txt /tmp/build-r1199-training-contract-filter_audit_frames.txt
echo 'OFFLINE_FRAME_PARITY PASS (filter disabled; old/debug/filter builds produce identical audit frames)'