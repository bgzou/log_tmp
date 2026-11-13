#!/usr/bin/env bash
# Single entry point for staged AS2-W / CPRO field checks.
set -euo pipefail
cd "$(dirname "$0")/.."

usage() {
    cat <<'EOF'
Usage: bash tools/field.sh STAGE [ARG...]
  preflight                         Read-only CPRO, network and USB inventory
  build                             Build policy core, run model/controller tests
  sdk-build SDK_PREFIX              Build SDK2 diagnostic binaries after SDK2 install
  r152-build SDK_PREFIX ORT_ROOT    Build R152 controller+replay+shadow (needs yaml-cpp, read-only binaries)
  r152-replay                       Run the 750-frame R152 parity replay (no DDS)
  r152-shadow NIC [TOPIC]           Read-only R152 shadow with measured map (500 ticks, zero commands)
  r214-build SDK_PREFIX ORT_ROOT    Build R214 replay+read-only shadow (no publisher)
  r214-replay                       Run R214 1050-frame parity replay (no DDS)
  r214-shadow NIC [TOPIC]           Read-only R214 shadow (500 ticks, no LowCmd)
  r214-publish-build SDK_PREFIX ORT_ROOT  Build the gated R214 FSM publisher (AS2W_R214_PUBLISH=ON)
  r214-dirtest-build SDK_PREFIX ORT_ROOT  Build the gated direction verification tool
  r1199-training-contract-build SDK_PREFIX ORT_ROOT  Build isolated R1199 training-contract candidate (joystick + continuous/straight bias, no odometry/settle)
  policy-list                       List delivered recovery/stairs model names
  policy-verify NAME|all            Run model reference trace by config name
  policy-bench NAME [ITERATIONS]     Time inference on this CPU (no DDS)
  policy-shadow NAME NIC MAP SEC [TOPIC]  Read-only live preview; stairs only
  sport-state NIC [SECONDS]         Read official high-level state
  remote-state NIC [SECONDS]        Read original Unitree remote DDS topic
  low-state NIC [SECONDS] [TOPIC]   Read HG LowState (35 message slots); default rt/lowstate
  low-remote NIC [SECONDS] [TOPIC]  Read raw 40-byte remote field in HG LowState
  low-crc NIC [SECONDS] [TOPIC]     Verify LowState CRC32 algorithm (read-only)
  low-capture NIC [SECONDS] [TOPIC] [PERIOD_MS]  Record read-only HG LowState samples (default 50 ms)
  low-protection NIC [SECONDS]      Read-only mainboard/motor warning stream (5 ms)
  motion-mode NIC                   Read current motion-switcher form/mode
  motion-release NIC                GATED: one ReleaseMode RPC (control ownership changes; needs field consent)
  motion-select NIC NAME            GATED: one SelectMode RPC (restore motion mode; needs field consent)
  service-list NIC                  Read current robot services and protection flags
  package-version NIC               Read robot package/module versions
  sport-command NIC ACTION          Explicit official high-level action:
                                    get-state|stop-move|balance-stand|stand-up|stand-down|damp
  shadow NIC MODEL MAP SECONDS [TOPIC]  Read-only stairs preview; requires verified map

Each invocation writes a timestamped log and an INDEX.md entry to field_logs/.
An exit code of zero proves only that the command ran, not that hardware mapping is safe.
EOF
}

if [[ $# -lt 1 ]]; then usage; exit 2; fi
stage=$1; shift
case ${OSTYPE:-} in msys*|cygwin*) py=${AS2W_PYTHON:-python} ;; *) py=${AS2W_PYTHON:-python3} ;; esac
sdk_lib="${AS2W_SDK2_PREFIX:-$HOME/unitree_sdk2_install}/lib"
if [[ -d "$sdk_lib" ]]; then
  export LD_LIBRARY_PATH="$sdk_lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
log_dir=${AS2W_LOG_DIR:-field_logs}
mkdir -p "$log_dir"
stamp=$(date +%Y%m%d-%H%M%S)
log="$log_dir/${stamp}_${stage}_${BASHPID}.log"

case "$stage" in
  preflight) [[ $# -eq 0 ]] || { usage; exit 2; }; cmd=(bash tools/probe_cpro.sh) ;;
  build) [[ $# -eq 0 ]] || { usage; exit 2; }; cmd=(bash tools/build_on_cpro.sh) ;;
  sdk-build) [[ $# -eq 1 ]] || { usage; exit 2; }; export AS2W_SDK2_PREFIX=$1; cmd=(bash tools/build_on_cpro.sh) ;;
  r152-build)
    [[ $# -eq 2 ]] || { usage; exit 2; }
    export AS2W_SDK2_PREFIX=$1 AS2W_R152_ROOT=$2
    cmd=(bash tools/build_on_cpro.sh) ;;
  r152-replay) [[ $# -eq 0 ]] || { usage; exit 2; }
    cmd=(./build-r152/deploy/robots/as2w/r152/as2w_r152_replay models/r152/deploy.yaml models/r152/r152-trace.csv) ;;
  r152-shadow)
    [[ $# -ge 1 && $# -le 2 ]] || { usage; exit 2; }
    cmd=(./build-r152/deploy/robots/as2w/r152/as2w_r152_shadow models/r152/deploy.yaml "$1" "${2:-rt/lowstate}" config/r152_measured.map --imu-wxyz-body-to-world) ;;
  r214-build)
    [[ $# -eq 2 ]] || { usage; exit 2; }
    export AS2W_SDK2_PREFIX=$1 AS2W_R214_ROOT=$2
    cmd=(bash tools/build_on_cpro.sh) ;;
  r214-replay) [[ $# -eq 0 ]] || { usage; exit 2; }
    cmd=(./build-r214/deploy/robots/as2w/r214/as2w_r214_replay models/r214/deploy.yaml models/r214/r214-trace.csv) ;;
  r214-dirtest-build)
    [[ $# -eq 2 ]] || { usage; exit 2; }
    export AS2W_SDK2_PREFIX=$1 AS2W_R214_ROOT=$2 AS2W_R214_DIRTEST=ON
    cmd=(bash tools/build_on_cpro.sh) ;;
  r1199-training-contract-build)
    [[ $# -eq 2 ]] || { usage; exit 2; }
    export AS2W_SDK2_PREFIX=$1 AS2W_R1199_ROOT=$2
    cmd=(bash tools/build_on_cpro.sh) ;;
  r214-publish-build)
    [[ $# -eq 2 ]] || { usage; exit 2; }
    export AS2W_SDK2_PREFIX=$1 AS2W_R214_ROOT=$2 AS2W_R214_PUBLISH=ON
    cmd=(bash tools/build_on_cpro.sh) ;;
  r214-shadow)
    [[ $# -ge 1 && $# -le 2 ]] || { usage; exit 2; }
    cmd=(./build-r214/deploy/robots/as2w/r214/as2w_r214_shadow models/r214/deploy.yaml "$1" "${2:-rt/lowstate}" config/r152_measured.map --imu-wxyz-body-to-world) ;;
  policy-list) [[ $# -eq 0 ]] || { usage; exit 2; }; cmd=("$py" tools/policy_select.py list) ;;
  policy-verify) [[ $# -eq 1 ]] || { usage; exit 2; }; cmd=("$py" tools/policy_select.py verify "$1") ;;
  policy-bench) [[ $# -ge 1 && $# -le 2 ]] || { usage; exit 2; }; cmd=("$py" tools/policy_select.py bench "$@") ;;
  policy-shadow) [[ $# -ge 4 && $# -le 5 ]] || { usage; exit 2; }; cmd=("$py" tools/policy_select.py shadow "$@") ;;
  sport-state|remote-state|motion-mode|service-list|package-version)
    [[ $# -ge 1 && $# -le 2 ]] || { usage; exit 2; }
    [[ "$stage" != motion-mode && "$stage" != service-list && "$stage" != package-version || $# -eq 1 ]] || { usage; exit 2; }
    cmd=(./build-sdk2/as2w_sdk2 "$stage" "$@") ;;
  motion-release)
    [[ $# -eq 1 ]] || { usage; exit 2; }
    cmd=(./build-sdk2/as2w_sdk2 motion-release "$1") ;;
  motion-select)
    [[ $# -eq 2 ]] || { usage; exit 2; }
    cmd=(./build-sdk2/as2w_sdk2 motion-select "$1" "$2") ;;
  low-state|low-remote)
    [[ $# -ge 1 && $# -le 3 ]] || { usage; exit 2; }
    nic=$1; duration=${2:-10}; topic=${3:-rt/lowstate}
    cmd=(./build-sdk2/as2w_sdk2 "$stage" "$nic" "$topic" "$duration") ;;
  low-crc)
    [[ $# -ge 1 && $# -le 3 ]] || { usage; exit 2; }
    nic=$1; duration=${2:-5}; topic=${3:-rt/lowstate}
    cmd=(./build-sdk2/as2w_sdk2 "$stage" "$nic" "$topic" "$duration") ;;
  low-protection)
    [[ $# -ge 1 && $# -le 2 ]] || { usage; exit 2; }
    cmd=(./build-sdk2/as2w_sdk2 low-protection "$1" "${2:-10}") ;;
  low-capture)
    [[ $# -ge 1 && $# -le 4 ]] || { usage; exit 2; }
    nic=$1; duration=${2:-10}; topic=${3:-rt/lowstate}; period=${4:-50}
    cmd=(./build-sdk2/as2w_sdk2 "$stage" "$nic" "$topic" "$duration" "$period") ;;
  sport-command)
    [[ $# -eq 2 ]] || { usage; exit 2; }
    case "$2" in get-state|stop-move|balance-stand|stand-up|stand-down|damp) ;; *) usage; exit 2 ;; esac
    cmd=(./build-sdk2/as2w_sdk2 sport-command "$1" "$2") ;;
  shadow)
    [[ $# -ge 4 && $# -le 5 ]] || { usage; exit 2; }
    cmd=(./build-sdk2/as2w_sdk2 shadow "$1" "${5:-rt/lowstate}" "$2" "$3" "$4" --imu-wxyz-body-to-world) ;;
  *) usage; exit 2 ;;
esac

printf 'Stage: %s\nStarted: %s\nCommand:' "$stage" "$(date -Is)" | tee "$log"
printf ' %q' "${cmd[@]}" | tee -a "$log"
printf '\n' | tee -a "$log"
set +e
"${cmd[@]}" 2>&1 | tee -a "$log"
rc=${PIPESTATUS[0]}
set -e
printf 'Exit code: %d\nFinished: %s\n' "$rc" "$(date -Is)" | tee -a "$log"
{
  printf '\n## %s — %s\n\n' "$(date -Is)" "$stage"
  printf -- '- Exit code: `%d`\n- Raw log: `%s`\n' "$rc" "$log"
  printf -- '- Observed result: **to be reviewed**\n- Decision and next gate: **to be filled after review**\n'
} >> "$log_dir/INDEX.md"
exit "$rc"
