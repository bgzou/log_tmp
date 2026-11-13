#!/bin/sh
# Offline-only build, CTest and audit. No DDS participant or LowCmd publication.
set -eu
sh /data/local/tmp/as2w_field/cpro_ubuntu.sh /bin/bash -lc '
  set -euo pipefail
  cd /root/as2w_deploy
  cmake -S . -B build-r1199-joystick -DCMAKE_BUILD_TYPE=Release \
    -DAS2W_R1199=ON -DAS2W_R1199_JOYSTICK_CANDIDATE=ON \
    -DAS2W_R1199_PUBLISH=ON -DAS2W_R1199_ZERO_B_TRIAL=OFF \
    -DONNXRUNTIME_ROOT=/root/ort122 \
    -DCMAKE_PREFIX_PATH=/root/unitree_sdk2_install
  cmake --build build-r1199-joystick -j4
  ctest --test-dir build-r1199-joystick --output-on-failure
  build-r1199-joystick/deploy/robots/as2w/r1199/as2w_r1199_joystick_publish \
    models/r1199/deploy.yaml config/r152_measured.map --offline-audit | tail -1
'
