#!/usr/bin/env bash
set -euo pipefail
bash /root/as2w_deploy/tools/build_debug_lowpass_final.sh
cd /root/as2w_deploy
export LD_LIBRARY_PATH=/root/unitree_sdk2_install/lib:/root/ort122/lib:${LD_LIBRARY_PATH:-}
for variant in stand zero-b full; do
  opts=()
  case "$variant" in
    stand) opts+=(-DAS2W_R214_STAND_TRIAL=ON) ;;
    zero-b) opts+=(-DAS2W_R214_ZERO_B_TRIAL=ON) ;;
    full) opts+=(-DAS2W_R214_FULL_MOTION=ON) ;;
  esac
  cmake -S . -B "build-r214-debug-$variant" -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DAS2W_R214=ON -DAS2W_R214_PUBLISH=ON "${opts[@]}" -DONNXRUNTIME_ROOT=/root/ort122 -DCMAKE_PREFIX_PATH=/root/unitree_sdk2_install
  cmake --build "build-r214-debug-$variant" --parallel 4
  ctest --test-dir "build-r214-debug-$variant" --output-on-failure
  "./build-r214-debug-$variant/deploy/robots/as2w/r214/as2w_r214_publish" models/r214/deploy.yaml config/r152_measured.map --offline-audit --debug | grep -aE 'DEBUG_LOWCMD_RESULT|DEBUG_CAPTURE_AUDIT|AUDIT PASS'
done