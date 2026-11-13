#!/usr/bin/env bash
set -euo pipefail
cd /root/as2w_deploy
export LD_LIBRARY_PATH=/root/unitree_sdk2_install/lib:/root/ort122/lib:${LD_LIBRARY_PATH:-}
cmake -S . -B build-debug-validation -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DAS2W_R1199=ON -DAS2W_R1199_JOYSTICK_CANDIDATE=ON -DAS2W_R1199_TRAINING_CONTRACT=ON -DAS2W_R1199_PUBLISH=ON -DAS2W_R214=ON -DAS2W_R214_PUBLISH=ON -DAS2W_R249=ON -DAS2W_R249_PUBLISH=ON -DAS2W_R270=ON -DAS2W_R270_PUBLISH=ON -DAS2W_R284=ON -DAS2W_R284_PUBLISH=ON -DONNXRUNTIME_ROOT=/root/ort122 -DCMAKE_PREFIX_PATH=/root/unitree_sdk2_install
cmake --build build-debug-validation --parallel 4
ctest --test-dir build-debug-validation --output-on-failure
cmake -S . -B build-r1199-training-contract-filter -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DAS2W_R1199=ON -DAS2W_R1199_JOYSTICK_CANDIDATE=ON -DAS2W_R1199_TRAINING_CONTRACT=ON -DAS2W_R1199_LOWPASS_CANDIDATE=ON -DAS2W_R1199_PUBLISH=ON -DONNXRUNTIME_ROOT=/root/ort122 -DCMAKE_PREFIX_PATH=/root/unitree_sdk2_install
cmake --build build-r1199-training-contract-filter --parallel 4
ctest --test-dir build-r1199-training-contract-filter --output-on-failure
./build-r1199-training-contract-filter/deploy/robots/as2w/r1199/as2w_r1199_joystick_publish models/r1199/deploy.yaml config/r152_measured.map --offline-audit --policy-lowpass-ms 80 --debug | tail -3