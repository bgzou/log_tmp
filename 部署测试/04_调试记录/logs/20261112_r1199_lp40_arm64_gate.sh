#!/usr/bin/env bash
# CPRO Ubuntu only. Compile/audit; never publishes LowCmd.
set -euo pipefail
cd /root/as2w_deploy
bash -n tools/run_r1199_field_session.sh tools/run_r1199_training_contract_trial.sh
sha256sum deploy/robots/as2w/common/as2w_publish.cpp \
  tools/run_r1199_field_session.sh tools/run_r1199_training_contract_trial.sh
export LD_LIBRARY_PATH=/root/unitree_sdk2_install/lib:/root/ort122/lib:${LD_LIBRARY_PATH:-}
for build in build-r1199-training-contract build-r1199-training-contract-debug build-r1199-training-contract-filter; do
  echo "=== BUILD $build ==="
  cmake --build "$build" --parallel 4
  ctest --test-dir "$build" --output-on-failure
  binary="$build/deploy/robots/as2w/r1199/as2w_r1199_joystick_publish"
  "$binary" models/r1199/deploy.yaml config/r152_measured.map --offline-audit --debug \
    | grep -aE 'DEBUG_LOWCMD_RESULT|DEBUG_CAPTURE_AUDIT|AUDIT PASS'
  sha256sum "$binary"
done
echo R1199_LP40_ARM64_GATE_PASS
