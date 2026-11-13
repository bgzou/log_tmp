#!/bin/bash
set -euo pipefail
cd /root/as2w_deploy
exec > /tmp/r214_guard_injection_arm64_build.log 2>&1

for build in build-r214-ab-fsm build-r214-zero-b build-r214-ab-fsm-full; do
    echo "===== BUILD $build ====="
    cmake --build "$build" --target as2w_r214_publish -j4
    echo "===== CTEST $build ====="
    ctest --test-dir "/root/as2w_deploy/$build" --output-on-failure
    echo "===== AUDIT $build ====="
    "./$build/deploy/robots/as2w/r214/as2w_r214_publish" \
        models/r214/deploy.yaml config/r152_measured.map --offline-audit \
        > "/tmp/${build}_guard_injection_audit.log"
    tail -n 2 "/tmp/${build}_guard_injection_audit.log"
done

echo "===== SHA256 ====="
sha256sum deploy/robots/as2w/r214/r214_publish.cpp \
    build-r214-ab-fsm/deploy/robots/as2w/r214/as2w_r214_publish \
    build-r214-zero-b/deploy/robots/as2w/r214/as2w_r214_publish \
    build-r214-ab-fsm-full/deploy/robots/as2w/r214/as2w_r214_publish
echo "===== DONE ====="
