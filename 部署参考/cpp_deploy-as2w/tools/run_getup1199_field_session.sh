#!/usr/bin/env bash
# getup1199 bounded field session: verify -> control-rights -> safe remote state.
#
# Same non-skippable sequence as the validated R1199/R4000 sessions:
#   1. preflight: publisher binary exists + offline-audit PASS + SHA record
#   2. DDS probe: LowState alive, mode_machine=2, no other LowCmd process
#   3. control rights: factory (name=ai) -> prone -> ReleaseMode; or already
#      released -> continue
#   4. LowState 2s quality check (~1 kHz, 16-axis mode=0) + prone calf gate
#   5. local monitoring (low-capture 2ms + low-protection, niced)
#   6. launch the gated getup1199 publisher (B chain: knee-open -> rise ->
#      stand hold -> auto/manual squat; 15s rise cap inside the binary)
#
# Usage: run_getup1199_field_session.sh getup [monitor_seconds]
#        run_getup1199_field_session.sh getup-dry-run [monitor_seconds]
# Motion mode always records the full debug chain (new policy, first field
# tier). Requires per-session field consent per AGENTS.md; Ctrl+C is not a
# motion e-stop (X / physical e-stop is).
set -u

MODE=getup
MONITOR_SECONDS=150
DRY_RUN=0
case "${1:-}" in
    getup) MODE=$1 ;;
    getup-dry-run) MODE=getup; DRY_RUN=1 ;;
    dry-run) MODE=getup; DRY_RUN=1 ;;
    *) echo "usage: $0 [getup|getup-dry-run|dry-run] [monitor_seconds]" >&2; exit 2 ;;
esac
[[ $# -ge 2 && $2 =~ ^[0-9]+$ ]] && { MONITOR_SECONDS=$2; shift; }
shift $(( $# > 0 ? 1 : 0 ))
while [[ $# -gt 0 ]]; do
    case "$1" in
        --debug) shift ;;  # accepted for launcher compatibility; always on
        *) echo "FATAL: unexpected session option: $1" >&2; exit 2 ;;
    esac
done
if ! [[ $MONITOR_SECONDS =~ ^[0-9]+$ ]] || (( MONITOR_SECONDS < 90 || MONITOR_SECONDS > 300 )); then
    [[ $DRY_RUN == 1 && $MONITOR_SECONDS =~ ^[0-9]+$ && $MONITOR_SECONDS -ge 10 && $MONITOR_SECONDS -le 300 ]] || {
        echo 'FATAL: monitor seconds must be 90..300 for motion (10..300 for dry-run)' >&2
        exit 2
    }
fi

cd /root/as2w_deploy || { echo "FATAL: /root/as2w_deploy missing" >&2; exit 4; }
STAMP=$(date +%Y%m%d-%H%M%S)
SESSION_LABEL=$MODE
[[ $DRY_RUN == 1 ]] && SESSION_LABEL=getup-dry-run
SESS=/root/field_sessions/${STAMP}_${SESSION_LABEL}
mkdir -p "$SESS"
LOG=$SESS/session.log
log() { echo "[field-session] $*" | tee -a "$LOG"; }

BUILD=build-getup1199
LAUNCH="bash tools/run_getup1199_trial.sh"
BIN=$BUILD/deploy/robots/as2w/getup1199/as2w_getup1199_publish
SDK="env LD_LIBRARY_PATH=/root/unitree_sdk2_install/lib ./build-sdk2/as2w_sdk2"
NIC=eth0

log "mode=$MODE monitor=${MONITOR_SECONDS}s dry_run=$DRY_RUN dir=$SESS"
AVAILABLE_MB=$(df -Pm /root/as2w_deploy | awk 'END{print $4}')
[[ $AVAILABLE_MB =~ ^[0-9]+$ && $AVAILABLE_MB -ge 1024 ]] || {
    log "FATAL: debug recording requires >=1024 MB free before control release (available=${AVAILABLE_MB:-?} MB)"; exit 5;
}

# ── 1. preflight: binary + audit + SHA (never skipped) ─────────────────────
if [[ ! -x $BIN ]]; then
    log "FATAL: publisher binary missing: $BIN (build it first)"
    exit 4
fi
log "step1 binary: $BIN"
sha256sum deploy/robots/as2w/common/as2w_publish.cpp \
  deploy/robots/as2w/getup1199/getup1199_controller.cpp \
  deploy/robots/as2w/getup1199/getup1199_controller.hpp \
  tools/run_getup1199_trial.sh \
  models/getup1199/policy.onnx "$BIN" 2>/dev/null | tee -a "$LOG"
if [[ ! -x build-sdk2/as2w_sdk2 ]]; then
    log "FATAL: build-sdk2/as2w_sdk2 missing (run sdk-build first)"
    exit 4
fi
AUDIT=$($BIN models/getup1199/deploy.yaml config/r152_measured.map --offline-audit 2>&1 | tail -1)
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
    echo "$MM2" | grep -qE 'name= *$' || { log "FATAL: service still active after release"; exit 5; }
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
PRONE_Q=$(echo "$CAP" | python3 -c '
import sys
f=sys.stdin.read().strip().split(",")
try:
  q=[float(f[14+i*6]) for i in (2,5,8,11)]
  print("yes" if all(-3.0 < x < -2.4 for x in q) else "no:"+",".join(f"{x:.3f}" for x in q))
except (ValueError,IndexError):
  print("invalid")' 2>/dev/null || echo invalid)
log "step4 prone calf gate=$PRONE_Q"
[[ $PRONE_Q == yes ]] || { log "FATAL: getup1199 trial requires the measured prone four-calf baseline"; exit 5; }

if [[ $DRY_RUN == 1 ]]; then
    log "dry-run: steps 1-4 PASS; would now start monitoring + getup launcher"
    exit 0
fi

# ── 5. local monitoring (background, CPRO-local files) ─────────────────────
log "step5 starting ${MONITOR_SECONDS}s monitoring (low-capture 2ms + low-protection)"
nice -n 10 $SDK low-capture $NIC rt/lowstate $MONITOR_SECONDS 2 >"$SESS/low_capture_fast.log" 2>&1 &
MON1=$!
nice -n 10 $SDK low-protection $NIC $MONITOR_SECONDS >"$SESS/low_protection.log" 2>&1 &
MON2=$!
rm -f debug_policy.csv debug_lowcmd.csv

# ── 6. launch publisher (its own verified wake sequence) ──────────────────
log "step6 launching: $LAUNCH"
log "    >>> Passive ready expected in ~3-5s; then hand the remote to the operator."
log "    >>> GETUP1199: B once = knee-open (~2.5s, body lifts ~3cm) -> staged rise (~3-5s) -> FixedStand hold (auto-squat after 30s or Y); A disabled; X=emergency; one B chain per session."
$LAUNCH 2>&1 | tee "$SESS/publisher.log"
RC=${PIPESTATUS[0]}
log "publisher exited rc=$RC"

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
