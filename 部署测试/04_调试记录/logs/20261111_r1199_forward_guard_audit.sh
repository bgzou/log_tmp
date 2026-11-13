#!/bin/sh
# Offline-only rejection probes. Does not create DDS participants.
set -eu
sh /data/local/tmp/as2w_field/cpro_ubuntu.sh /bin/bash -lc '
  set -euo pipefail
  cd /root/as2w_deploy
  bin=build-r1199-forward/deploy/robots/as2w/r1199/as2w_r1199_forward_replay
  for case_name in excess back lateral turn; do
    file=field_logs/r1199_forward_reject_${case_name}.txt
    if "$bin" models/r1199/deploy.yaml "$file" > /tmp/r1199_guard.out 2>&1; then
      echo "GUARD FAIL: $case_name was accepted"
      exit 1
    fi
    grep -q "Controller disarmed" /tmp/r1199_guard.out || {
      echo "GUARD FAIL: $case_name failed for an unrelated reason"
      cat /tmp/r1199_guard.out
      exit 1
    }
    echo "GUARD PASS: $case_name rejected"
  done
'
