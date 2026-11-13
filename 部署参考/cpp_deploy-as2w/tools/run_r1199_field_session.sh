#!/usr/bin/env bash
# R1199 bounded zero-B field session: verify -> control-rights -> safe remote state.
#
# Strictly follows the sequence that passed on the real robot (INDEX
# 2026-11-09 23:xx .. 2026-11-10 12:35). NO step is skippable:
#   1. preflight: publisher binary exists + offline-audit PASS + SHA record
#   2. DDS probe: LowState alive, mode_machine=2, no other LowCmd process
#   3. control rights:
#      - factory (name=ai): verify prone (stand-down if standing), then
#        ReleaseMode and confirm name empty
#      - already released (name empty): go straight ahead
#   4. LowState 2s quality check (~1 kHz, 16-axis mode=0)
#   5. optional local monitoring (low-capture + low-protection)
#   6. launch the gated publisher (its own wake sequence: 500 ms observe ->
#      neutral FOC request -> FOC ack -> kd ramp -> Passive ready -> remote)
#
# Usage: run_r1199_field_session.sh zero-b [monitor_seconds]
#        run_r1199_field_session.sh forward [monitor_seconds]
#        run_r1199_field_session.sh forward-dry-run [monitor_seconds]
#        run_r1199_field_session.sh joystick [monitor_seconds]
#        run_r1199_field_session.sh joystick-dry-run [monitor_seconds]
#        run_r1199_field_session.sh training-contract [monitor_seconds]
#        run_r1199_field_session.sh training-contract-dry-run [monitor_seconds]
#        run_r1199_field_session.sh dry-run [monitor_seconds]
# Requires per-session field consent before invoking, per AGENTS.md.
set -u

MODE=zero-b
MONITOR_SECONDS=150
DRY_RUN=0
case "${1:-}" in
    zero-b) MODE=$1 ;;
    forward) MODE=$1 ;;
    forward-dry-run) MODE=forward; DRY_RUN=1 ;;
    joystick) MODE=$1 ;;
    joystick-dry-run) MODE=joystick; DRY_RUN=1 ;;
    training-contract) MODE=$1 ;;
    training-contract-dry-run) MODE=training-contract; DRY_RUN=1 ;;
    dry-run) DRY_RUN=1 ;;
    *) echo "usage: $0 [zero-b|forward|forward-dry-run|joystick|joystick-dry-run|training-contract|training-contract-dry-run|dry-run] [monitor_seconds]" >&2; exit 2 ;;
esac
[[ $# -ge 2 ]] && MONITOR_SECONDS=$2
DEBUG=0
LOWPASS_MS=0
LOWPASS_WHEELS=0
shift $(( $# < 2 ? $# : 2 ))
while [[ $# -gt 0 ]]; do
    case "$1" in
        --debug) DEBUG=1; shift ;;
        --lowpass-wheels) LOWPASS_WHEELS=1; shift ;;
        --lowpass-ms)
            [[ $# -ge 2 && $2 =~ ^[0-9]+$ && $2 -ge 1 && $2 -le 200 ]] || {
                echo 'FATAL: --lowpass-ms must be an integer in 1..200' >&2; exit 2;
            }
            LOWPASS_MS=$2; shift 2 ;;
        *) echo "FATAL: unexpected session option: $1" >&2; exit 2 ;;
    esac
done
[[ $LOWPASS_WHEELS == 0 || $LOWPASS_MS -gt 0 ]] || {
    echo 'FATAL: --lowpass-wheels requires --lowpass-ms' >&2; exit 2;
}
if [[ $DEBUG == 1 || $LOWPASS_MS -gt 0 ]]; then
    [[ $MODE == training-contract ]] || {
        echo 'FATAL: Debug/low-pass currently use only the isolated R1199 training-contract entry' >&2; exit 2;
    }
fi
if [[ $LOWPASS_MS -gt 0 && $DRY_RUN != 1 ]]; then
    [[ $MODE == training-contract && $LOWPASS_MS == 40 && $LOWPASS_WHEELS == 0 && $DEBUG == 1 ]] || {
        echo 'FATAL: filtered motion permits only the reviewed R1199 40ms leg-only Debug candidate; all other filtered motion remains locked' >&2
        exit 5
    }
fi
if ! [[ $MONITOR_SECONDS =~ ^[0-9]+$ ]] || (( MONITOR_SECONDS < 90 || MONITOR_SECONDS > 300 )); then
    [[ $DRY_RUN == 1 && $MONITOR_SECONDS =~ ^[0-9]+$ && $MONITOR_SECONDS -ge 10 && $MONITOR_SECONDS -le 300 ]] || {
        echo 'FATAL: monitor seconds must be 90..300 for zero-b (10..300 for dry-run)' >&2
        exit 2
    }
fi

cd /root/as2w_deploy || { echo "FATAL: /root/as2w_deploy missing" >&2; exit 4; }
STAMP=$(date +%Y%m%d-%H%M%S)
SESSION_LABEL=$MODE
[[ $DRY_RUN == 1 ]] && SESSION_LABEL=${1:-dry-run}
SESS=/root/field_sessions/${STAMP}_${SESSION_LABEL}
mkdir -p "$SESS"
LOG=$SESS/session.log
log() { echo "[field-session] $*" | tee -a "$LOG"; }

if [[ $MODE == joystick ]]; then
    BUILD=build-r1199-joystick
    LAUNCH="bash tools/run_r1199_joystick_trial.sh"
    BIN=$BUILD/deploy/robots/as2w/r1199/as2w_r1199_joystick_publish
elif [[ $MODE == training-contract ]]; then
    BUILD=build-r1199-training-contract
    LAUNCH="bash tools/run_r1199_training_contract_trial.sh"
    [[ $DEBUG == 1 && $LOWPASS_MS -eq 0 ]] && BUILD=build-r1199-training-contract-debug
    [[ $LOWPASS_MS -gt 0 ]] && BUILD=build-r1199-training-contract-filter
    BIN=$BUILD/deploy/robots/as2w/r1199/as2w_r1199_joystick_publish
elif [[ $MODE == forward ]]; then
    BUILD=build-r1199-forward
    LAUNCH="bash tools/run_r1199_forward_trial.sh"
    BIN=$BUILD/deploy/robots/as2w/r1199/as2w_r1199_forward_publish
else
    BUILD=build-r1199-zero-b
    LAUNCH="bash tools/run_r1199_zero_b_trial.sh"
    BIN=$BUILD/deploy/robots/as2w/r1199/as2w_r1199_publish
fi
SDK="env LD_LIBRARY_PATH=/root/unitree_sdk2_install/lib ./build-sdk2/as2w_sdk2"
NIC=eth0

log "mode=$MODE monitor=${MONITOR_SECONDS}s dry_run=$DRY_RUN debug=$DEBUG lowpass_ms=$LOWPASS_MS lowpass_wheels=$LOWPASS_WHEELS dir=$SESS"
if [[ $DEBUG == 1 ]]; then
    AVAILABLE_MB=$(df -Pm /root/as2w_deploy | awk 'END{print $4}')
    [[ $AVAILABLE_MB =~ ^[0-9]+$ && $AVAILABLE_MB -ge 1024 ]] || {
        log "FATAL: debug requires >=1024 MB free before control release (available=${AVAILABLE_MB:-?} MB)"; exit 5;
    }
fi
if [[ $MODE == joystick && $DRY_RUN != 1 ]]; then
    log "FATAL: old R1199 joystick binary is paused after two real rolling-jitter and posture-jump trials. Use a separately built, audited training-contract candidate; never bypass this launcher."
    exit 4
fi

# ── 1. preflight: binary + audit + SHA (never skipped) ─────────────────────
if [[ ! -x $BIN ]]; then
    log "FATAL: publisher binary missing: $BIN (build it first)"
    exit 4
fi
log "step1 binary: $BIN"
sha256sum deploy/robots/as2w/common/as2w_publish.cpp \
  deploy/robots/as2w/r1199/r1199_controller.cpp \
  deploy/robots/as2w/r1199/r1199_controller.hpp \
  tools/run_r1199_forward_trial.sh \
  tools/run_r1199_joystick_trial.sh \
  tools/run_r1199_training_contract_trial.sh \
  models/r1199/policy.onnx "$BIN" 2>/dev/null | tee -a "$LOG"
if [[ ! -x build-sdk2/as2w_sdk2 ]]; then
    log "FATAL: build-sdk2/as2w_sdk2 missing (run sdk-build first)"
    exit 4
fi
AUDIT=$($BIN models/r1199/deploy.yaml config/r152_measured.map --offline-audit 2>&1 | tail -1)
log "step1 audit: $AUDIT"
[[ "$AUDIT" == *"AUDIT PASS"* ]] || { log "FATAL: offline audit FAILED"; exit 5; }

# ── 2. DDS probe: LowState alive (read-only) ───────────────────────────────
PROBE=$($SDK low-state $NIC rt/lowstate 1 2>&1 | grep -a '^low ' | tail -1)
log "step2 probe: ${PROBE:-<no packets>}"
PACKETS=$(echo "$PROBE" | grep -oP 'packets=\K[0-9]+' || echo 0)
MACHINE=$(echo "$PROBE" | grep -oP 'mode_machine=\K[0-9]+' || echo 0)
[[ "$PACKETS" -ge 100 ]] || { log "FATAL: LowState not flowing (got $PACKETS pkts/s). Robot/link down?"; exit 5; }
[[ "$MACHINE" == 2 ]] || { log "FATAL: mode_machine=$MACHINE (expected 2). Unexpected firmware state."; exit 5; }

# ── 3. control rights ──────────────────────────────────────────────────────
check_mode() { $SDK motion-mode $NIC 2>&1 | grep -a 'CheckMode'; }
get_fsm() { $SDK sport-command $NIC get-state 2>&1 | grep -a 'fsm_name'; }

MM=$(check_mode)
log "step3 motion-mode: $MM"
RC_PARSE=$(echo "$MM" | grep -oP 'rc=\K[0-9]+' || echo 999)
[[ "$RC_PARSE" == 0 ]] || { log "FATAL: CheckMode rc=$RC_PARSE (main controller unreachable?)"; exit 5; }
NAME=$(echo "$MM" | grep -oP 'name=\K\S*' || true)

if [[ -n "$NAME" ]]; then
    # factory motion service active -> must prone first, then release
    [[ $DRY_RUN == 1 ]] && { log "dry-run: factory mode ($NAME); would stand-down-if-standing + ReleaseMode here"; exit 0; }
    log "step3 factory control ($NAME): ensure prone before releasing"
    FSM=$(get_fsm)
    log "step3 current fsm: ${FSM:-<unreachable>}"
    if ! echo "$FSM" | grep -q 'ai_damping'; then
        log "step3 not prone -> official stand-down"
        $SDK sport-command $NIC stand-down >>"$LOG" 2>&1
        for i in $(seq 1 15); do
            sleep 2
            FSM=$(get_fsm)
            log "step3 wait prone ($i): ${FSM:-<unreachable>}"
            echo "$FSM" | grep -q 'ai_damping' && break
        done
        if ! echo "$FSM" | grep -q 'ai_damping'; then
            log "step3 stand-down RPC did not reach ai_damping; use the FACTORY REMOTE to prone the dog now."
            log "step3 waiting up to 60s for ai_damping via remote..."
            for i in $(seq 1 30); do
                sleep 2
                FSM=$(get_fsm)
                echo "$FSM" | grep -q 'ai_damping' && break
            done
            echo "$FSM" | grep -q 'ai_damping' || { log "FATAL: dog not prone; aborting, no ReleaseMode"; exit 5; }
        fi
    fi
    log "step3 prone confirmed -> ReleaseMode"
    REL=$($SDK motion-release $NIC 2>&1 | grep -a 'ReleaseMode')
    log "step3 release: $REL"
    echo "$REL" | grep -q 'rc=0' || { sleep 5; REL=$($SDK motion-release $NIC 2>&1 | grep -a 'ReleaseMode'); log "step3 release retry: $REL"; }
    echo "$REL" | grep -q 'rc=0' || { log "FATAL: ReleaseMode failed"; exit 5; }
    MM2=$(check_mode)
    log "step3 recheck: $MM2"
    echo "$MM2" | grep -q 'name=$' || echo "$MM2" | grep -qE 'name= *$' || { log "FATAL: service still active after release"; exit 5; }
else
    log "step3 already released (name empty) -> continue"
fi

# ── 4. LowState quality check: ~1 kHz + 16-axis mode=0 (no other writer) ──
CAP=$($SDK low-capture $NIC rt/lowstate 2 200 2>&1 | grep -a '^LOW_SAMPLE,' | tail -1)
log "step4 sample: $(echo "$CAP" | cut -c1-120)"
N=$(echo "$CAP" | grep -oP '^\s*LOW_SAMPLE,[0-9.]+,\K[0-9]+' || echo 0)
MODES16=$(echo "$CAP" | python3 -c '
import sys
line = sys.stdin.read().strip()
f = line.split(",")
if len(f) < 14 + 35*6: print("?"); sys.exit()
modes = set(f[14+i*6+4] for i in range(16))
print(",".join(sorted(modes)))' 2>/dev/null || echo '?')
log "step4 packets=$N 16-axis modes={$MODES16}"
[[ "$N" -ge 1500 ]] || { log "FATAL: LowState degraded ($N/2s, expect >=1500)"; exit 5; }
[[ "$MODES16" == "0" ]] || { log "FATAL: 16-axis mode={$MODES16} but expected all 0 — another LowCmd writer is active! Close it first."; exit 5; }
if [[ $MODE == forward || $MODE == joystick || $MODE == training-contract ]]; then
    # On an already released robot there is no factory FSM prone label. Use
    # the measured AS2-W four calf slots as an extra conservative gate.
    PRONE_Q=$(echo "$CAP" | python3 -c '
import sys
f=sys.stdin.read().strip().split(",")
try:
 q=[float(f[14+i*6]) for i in (2,5,8,11)]
 print("yes" if all(-3.0 < x < -2.4 for x in q) else "no:"+",".join(f"{x:.3f}" for x in q))
except (ValueError,IndexError):
 print("invalid")' 2>/dev/null || echo invalid)
    log "step4 forward prone calf gate=$PRONE_Q"
    [[ $PRONE_Q == yes ]] || { log "FATAL: forward trial requires measured prone four-calf baseline"; exit 5; }
fi

if [[ $DRY_RUN == 1 ]]; then
    log "dry-run: steps 1-4 PASS; would now start monitoring + $MODE launcher"
    exit 0
fi

# ── 5. local monitoring (background, CPRO-local files) ─────────────────────
# Fast joint capture at 2 ms (500 Hz, resolves up to ~250 Hz — covers the
# audible-jitter band a 10 ms capture cannot see). Both monitors run niced
# so they can never steal CPU from the publisher's control loop.
log "step5 starting ${MONITOR_SECONDS}s monitoring (low-capture 2ms + low-protection)"
nice -n 10 $SDK low-capture $NIC rt/lowstate $MONITOR_SECONDS 2 >"$SESS/low_capture_fast.log" 2>&1 &
MON1=$!
nice -n 10 $SDK low-protection $NIC $MONITOR_SECONDS >"$SESS/low_protection.log" 2>&1 &
MON2=$!
# Offline audits may leave synthetic debug_lowcmd.csv in the worktree. Never
# archive a stale audit file as if it came from this live publisher session.
if [[ $DEBUG == 1 ]]; then
    rm -f debug_policy.csv debug_lowcmd.csv
fi

# ── 6. launch publisher (its own verified wake sequence) ──────────────────
log "step6 launching: $LAUNCH"
log "    >>> Passive ready expected in ~3-5s; then hand the remote to the operator."
if [[ $MODE == joystick ]]; then
    log "    >>> A=fixed stand  B=2s zero handoff then LY vx+/-0.05m/s and RX yaw+/-0.05rad/s for max60s  Y=squat  X=emergency; LX ignored."
elif [[ $MODE == training-contract ]]; then
    if [[ $LOWPASS_MS -gt 0 ]]; then
        log "    >>> FILTERED CANDIDATE: 40ms leg targets; A=fixed stand, B=2s zero handoff then LY vx +/-0.2m/s, RX yaw +/-0.1rad/s for max30s; A brakes early, X=emergency."
    else
        log "    >>> A=fixed stand  B=2s zero handoff then LY vx and RX yaw within deploy.yaml envelope (default 0.2/0.2) for max60s (training-contract continuous/straight bias)  Y=squat  X=emergency; LX ignored."
    fi
elif [[ $MODE == forward ]]; then
    log "    >>> A=fixed stand  B=2s zero handoff then automatic vx=0.05m/s for 2s  Y=squat  X=emergency; sticks ignored."
else
    log "    >>> A=fixed stand  B=R1199 zero-command 2s only  Y=squat  X=emergency."
fi
LAUNCH_ARGS=()
[[ $DEBUG == 1 ]] && LAUNCH_ARGS+=(--debug)
[[ $LOWPASS_MS -gt 0 ]] && LAUNCH_ARGS+=(--lowpass-ms "$LOWPASS_MS")
[[ $LOWPASS_WHEELS == 1 ]] && LAUNCH_ARGS+=(--lowpass-wheels)
$LAUNCH "${LAUNCH_ARGS[@]}" 2>&1 | tee "$SESS/publisher.log"
RC=${PIPESTATUS[0]}
log "publisher exited rc=$RC"

# Archive the per-frame policy diagnostics (raw ONNX / wrapped action /
# final targets / wrapper internals at 50 Hz, local file) for inference-vs-
# hardware side diagnosis; the actual joints stay in low_capture_fast.log.
if [[ -f policy_diag.log ]]; then
    cp policy_diag.log "$SESS/policy_diag.log"
    rm -f policy_diag.log
    log "policy diagnostics archived: policy_diag.log ($(wc -l < "$SESS/policy_diag.log") lines)"
fi
if [[ $DEBUG == 1 ]]; then
    for name in debug_policy.csv debug_lowcmd.csv; do
        if [[ -s $name ]]; then
            mv -- "$name" "$SESS/$name"
            log "debug diagnostics archived: $name ($(wc -l < "$SESS/$name") lines)"
        else
            log "FATAL: debug diagnostics missing or empty: $name"
            RC=1
        fi
    done
    grep -q 'DEBUG_LOWCMD_RESULT .*dropped=0 .*file_ok=1' "$SESS/publisher.log" || {
        log 'FATAL: debug LowCmd capture dropped rows or writer failed'; RC=1;
    }
    grep -q 'DEBUG_POLICY_RESULT .*file_ok=1' "$SESS/publisher.log" || {
        log 'FATAL: debug policy capture writer failed'; RC=1;
    }
fi

# The operator's motion session is over. Keep five seconds of protection tail,
# then close read-only monitors rather than waiting out the full upper bound.
# Ctrl+C in Windows does not reliably reach the CPRO publisher through HDC;
# X/physical e-stop remain the motion-stop controls.
sleep 5
for monitor_pid in "$MON1" "$MON2"; do
    kill -TERM "$monitor_pid" 2>/dev/null || true
done
wait $MON1 2>/dev/null
wait $MON2 2>/dev/null
log "monitoring done; artifacts:"
ls -la "$SESS" | tee -a "$LOG"
log "session complete (mode=$MODE rc=$RC). Copy $SESS back to the workstation logs dir and append INDEX."
exit "$RC"
