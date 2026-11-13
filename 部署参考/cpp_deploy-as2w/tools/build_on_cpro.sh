#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
if ! command -v cmake >/dev/null || ! command -v g++ >/dev/null; then
    echo 'Need cmake and g++ inside the CPRO Ubuntu rootfs.' >&2
    exit 1
fi
python3 tools/check_models.py

cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DAS2W_WITH_SDK2=OFF
cmake --build build --parallel "$(nproc)"
ctest --test-dir build --output-on-failure

if [[ "${AS2W_SDK2_PREFIX:-}" != "" ]]; then
    bash tools/fix_sdk2_links.sh "$AS2W_SDK2_PREFIX/lib"
    cmake -S . -B build-sdk2 -DCMAKE_BUILD_TYPE=Release -DAS2W_WITH_SDK2=ON \
        -DCMAKE_PREFIX_PATH="$AS2W_SDK2_PREFIX"
    cmake --build build-sdk2 --parallel "$(nproc)"
fi

if [[ "${AS2W_R152_ROOT:-}" != "" && "${AS2W_SDK2_PREFIX:-}" != "" ]]; then
    cmake -S . -B build-r152 -DCMAKE_BUILD_TYPE=Release -DAS2W_R152=ON \
        -DAS2W_SDK2_SHADOW=ON -DONNXRUNTIME_ROOT="$AS2W_R152_ROOT" \
        -DCMAKE_PREFIX_PATH="$AS2W_SDK2_PREFIX"
    cmake --build build-r152 --parallel "$(nproc)"
fi

if [[ "${AS2W_R214_ROOT:-}" != "" && "${AS2W_SDK2_PREFIX:-}" != "" ]]; then
    cmake -S . -B build-r214 -DCMAKE_BUILD_TYPE=Release -DAS2W_R214=ON \
        -DAS2W_SDK2_SHADOW=ON -DONNXRUNTIME_ROOT="$AS2W_R214_ROOT" \
        -DCMAKE_PREFIX_PATH="$AS2W_SDK2_PREFIX"
    cmake --build build-r214 --parallel "$(nproc)"
fi

# R214 direction test (gated)
if [[ "${AS2W_R214_DIRTEST:-}" == "ON" && "${AS2W_R214_ROOT:-}" != "" && "${AS2W_SDK2_PREFIX:-}" != "" ]]; then
    cmake -S . -B build-r214-dirtest -DCMAKE_BUILD_TYPE=Release -DAS2W_R214=ON \
        -DAS2W_R214_DIRECTION_TEST=ON -DONNXRUNTIME_ROOT="$AS2W_R214_ROOT" \
        -DCMAKE_PREFIX_PATH="$AS2W_SDK2_PREFIX"
    cmake --build build-r214-dirtest --parallel "$(nproc)"
fi

# R214 FSM publisher (gated, default OFF in normal builds)
if [[ "${AS2W_R214_PUBLISH:-}" == "ON" && "${AS2W_R214_ROOT:-}" != "" && "${AS2W_SDK2_PREFIX:-}" != "" ]]; then
    cmake -S . -B build-r214-publish -DCMAKE_BUILD_TYPE=Release -DAS2W_R214=ON \
        -DAS2W_R214_PUBLISH=ON -DONNXRUNTIME_ROOT="$AS2W_R214_ROOT" \
        -DCMAKE_PREFIX_PATH="$AS2W_SDK2_PREFIX"
    cmake --build build-r214-publish --parallel "$(nproc)"
fi

# Debug-only isolated binaries keep all accepted R214 builds untouched.
if [[ "${AS2W_R214_DEBUG_BUILD:-}" == "ON" && "${AS2W_R214_ROOT:-}" != "" && "${AS2W_SDK2_PREFIX:-}" != "" ]]; then
    for variant in stand zero-b full; do
        opts=()
        case "$variant" in
            stand) opts+=(-DAS2W_R214_STAND_TRIAL=ON) ;;
            zero-b) opts+=(-DAS2W_R214_ZERO_B_TRIAL=ON) ;;
            full) opts+=(-DAS2W_R214_FULL_MOTION=ON) ;;
        esac
        cmake -S . -B "build-r214-debug-$variant" -DCMAKE_BUILD_TYPE=Release \
            -DAS2W_R214=ON -DAS2W_R214_PUBLISH=ON "${opts[@]}" \
            -DONNXRUNTIME_ROOT="$AS2W_R214_ROOT" \
            -DCMAKE_PREFIX_PATH="$AS2W_SDK2_PREFIX"
        cmake --build "build-r214-debug-$variant" --parallel "$(nproc)"
        ctest --test-dir "build-r214-debug-$variant" --output-on-failure
    done
fi

# R1199 training-contract candidate (isolated; matches model_1199 training
# runtime_flags: continuous/straight stand bias on, parking odometry/settle off,
# per-wheel -6*error hold, no common wheel feedback). Never rebuilds the old
# zero-b/forward/joystick binaries.
if [[ "${AS2W_R1199_ROOT:-}" != "" && "${AS2W_SDK2_PREFIX:-}" != "" ]]; then
    cmake -S . -B build-r1199-training-contract -DCMAKE_BUILD_TYPE=Release \
        -DAS2W_R1199=ON -DAS2W_R1199_JOYSTICK_CANDIDATE=ON \
        -DAS2W_R1199_TRAINING_CONTRACT=ON -DAS2W_R1199_PUBLISH=ON \
        -DONNXRUNTIME_ROOT="$AS2W_R1199_ROOT" \
        -DCMAKE_PREFIX_PATH="$AS2W_SDK2_PREFIX"
    cmake --build build-r1199-training-contract --parallel "$(nproc)"
fi

# Separate filtered trial binary. OFF unless explicitly requested; never
# replaces the accepted unfiltered R1199 training-contract build.
if [[ "${AS2W_R1199_DEBUG_BUILD:-}" == "ON" && "${AS2W_R1199_ROOT:-}" != "" && "${AS2W_SDK2_PREFIX:-}" != "" ]]; then
    cmake -S . -B build-r1199-training-contract-debug -DCMAKE_BUILD_TYPE=Release \
        -DAS2W_R1199=ON -DAS2W_R1199_JOYSTICK_CANDIDATE=ON \
        -DAS2W_R1199_TRAINING_CONTRACT=ON -DAS2W_R1199_PUBLISH=ON \
        -DONNXRUNTIME_ROOT="$AS2W_R1199_ROOT" \
        -DCMAKE_PREFIX_PATH="$AS2W_SDK2_PREFIX"
    cmake --build build-r1199-training-contract-debug --parallel "$(nproc)"
fi
if [[ "${AS2W_R1199_FILTER_BUILD:-}" == "ON" && "${AS2W_R1199_ROOT:-}" != "" && "${AS2W_SDK2_PREFIX:-}" != "" ]]; then
    cmake -S . -B build-r1199-training-contract-filter -DCMAKE_BUILD_TYPE=Release \
        -DAS2W_R1199=ON -DAS2W_R1199_JOYSTICK_CANDIDATE=ON \
        -DAS2W_R1199_TRAINING_CONTRACT=ON -DAS2W_R1199_LOWPASS_CANDIDATE=ON \
        -DAS2W_R1199_PUBLISH=ON -DONNXRUNTIME_ROOT="$AS2W_R1199_ROOT" \
        -DCMAKE_PREFIX_PATH="$AS2W_SDK2_PREFIX"
    cmake --build build-r1199-training-contract-filter --parallel "$(nproc)"
fi

# R4000 joystick candidate (rolling-4000-stage020-research weights, training
# runtime: 5 Hz leg-residual filter + 0.9 rad/s leg-target slew +
# pure_turn_common_scale=0 wheel mapping; command domain up to 0.20 m/s).
# Isolated build; never touches any R1199 binary.
if [[ "${AS2W_R4000_BUILD:-}" == "ON" && "${AS2W_ORT_ROOT:-}" != "" && "${AS2W_SDK2_PREFIX:-}" != "" ]]; then
    cmake -S . -B build-r4000-joystick -DCMAKE_BUILD_TYPE=Release \
        -DAS2W_R4000=ON -DAS2W_R4000_JOYSTICK_CANDIDATE=ON \
        -DAS2W_R4000_PUBLISH=ON \
        -DONNXRUNTIME_ROOT="$AS2W_ORT_ROOT" \
        -DCMAKE_PREFIX_PATH="$AS2W_SDK2_PREFIX"
    cmake --build build-r4000-joystick --parallel "$(nproc)"
    ctest --test-dir build-r4000-joystick --output-on-failure
fi
