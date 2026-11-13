#!/bin/sh
# Offline-only build and audits. Never starts DDS or publishes LowCmd.
set -eu
sh /data/local/tmp/as2w_field/cpro_ubuntu.sh /bin/bash -lc '
  set -euo pipefail
  cd /root/as2w_deploy
  cmake -S . -B build-r1199-forward -DCMAKE_BUILD_TYPE=Release \
    -DAS2W_R1199=ON -DAS2W_R1199_FORWARD_CANDIDATE=ON \
    -DAS2W_R1199_PUBLISH=ON -DAS2W_R1199_ZERO_B_TRIAL=OFF \
    -DONNXRUNTIME_ROOT=/root/ort122 \
    -DCMAKE_PREFIX_PATH=/root/unitree_sdk2_install
  cmake --build build-r1199-forward -j4
  ctest --test-dir build-r1199-forward --output-on-failure
  build-r1199-forward/deploy/robots/as2w/r1199/as2w_r1199_forward_publish \
    models/r1199/deploy.yaml config/r152_measured.map --offline-audit
'
