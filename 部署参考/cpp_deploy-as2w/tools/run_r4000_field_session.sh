#!/usr/bin/env bash
# R4000 bounded field session: verify -> control-rights -> safe remote state.
#
# Same non-skippable sequence as the validated R1199 sessions:
#   1. preflight: publisher binary exists + offline-audit PASS + SHA record
#   2. DDS probe: LowState alive, mode_machine=2, no other LowCmd process
#   3. control rights: factory (name=ai) -> prone -> ReleaseMode; or already
#      released -> continue
#   4. LowState 2s quality check (~1 kHz, 16-axis mode=0) + prone calf gate
#   5. local monitoring (low-capture 2ms + low-protection, niced)
#   6. launch the gated R4000 publisher (30s walk cap inside the binary)
#
# Usage: run_r4000_field_session.sh r4000 [monitor_seconds] [--vx-limit V] [--wz-limit W]
#        run_r4000_field_session.sh r4000-dry-run [monitor_seconds]
# The r4000 motion mode requires --debug-style full-chain recording by default
# (new policy, first field tiers). Requires per-session field consent per
# AGENTS.md; Ctrl+C is not a motion e-stop (X / physical e-stop is).
set -u

MODE=r4000
MONITOR_SECONDS=150
DRY_RUN=0
case "${1:-}" in
    r4000) MODE=$1 ;;
    r4000-dry-run) MODE=r4000; DRY_RUN=1 ;;
    dry-run) MODE=r4000; DRY_RUN=1 ;;
    *) echo "usage: $0 [r4000|r4000-dry-run|dry-run] [monitor_seconds] [--vx-limit 0.05..0.4] [--wz-limit 0.01..0.1]" >&2; exit 2 ;;
esac
[[ $# -ge 2 && $2 =~ ^[0-9]+$ ]] && { MONITOR_SECONDS=$2; shift; }
shift $(( $# > 0 ? 1 : 0 ))
VX_LIMIT=0.4
WZ_LIMIT=0.1
while [[ $# -gt 0 ]]; do
    case "$1" in
        --debug) shift ;;  # accepted for launcher compatibility; always on
        --vx-limit) [[ $# -ge 2 ]] && VX_LIMIT=$2; shift 2 ;;
        --wz-limit) [[ $# -ge 2 ]] && WZ_LIMIT=$2; shift 2 ;;
        *) echo "FATAL: unexpected session option: $1" >&2; exit 2 ;;
    esac
done
if ! [[ $MONITOR_SECONDS =~ ^[0-9]+$ ]] || (( MONITOR_SECONDS < 90 || MONITOR_SECONDS > 300 )); then
    [[ $DRY_RUN == 1 && $MONITOR_SECONDS =~ ^[0-9]+$ && $MONITOR_SECONDS -ge 10 && $MONITOR_SECONDS -le 300 ]] || {
        echo 'FATAL: monitor seconds must be 90..300 for motion (10..300 for dry-run)' >&2
        exit 2
    }
fi
if ! [[ $VX_LIMIT =~ ^[0-9.]+$ ]] || python3 -c "import sys; sys.exit(0 if 0.01 <= float('$VX_LIMIT') <= 0.4 else 1)" 2>/dev/null; then :; else
    echo 'FATAL: --vx-limit must be within 0.01..0.2 (deploy.yaml cap)' >&2; exit 2
fi
if ! [[ $WZ_LIMIT =~ ^[0-9.]+$ ]] || python3 -c "import sys; sys.exit(0 if 0.01 <= float('$WZ_LIMIT') <= 0.1 else 1)" 2>/dev/null; then :; else
    echo 'FATAL: --wz-limit must be within 0.01..0.1 (deploy.yaml cap)' >&2; exit 2
fi

cd /root/as2w_deploy || { echo "FATAL: /root/as2w_deploy missing" >&2; exit 4; }
STAMP=$(date +%Y%m%d-%H%M%S)
SESSION_LABEL=$MODE
[[ $DRY_RUN == 1 ]] && SESSION_LABEL=r4000-dry-run
SESS=/root/field_sessions/${STAMP}_${SESSION_LABEL}
mkdir -p "$SESS"
LOG=$SESS/session.log
log() { echo "[field-session] $*" | tee -a "$LOG"; }

BUILD=build-r4000-joystick
LAUNCH="bash tools/run_r4000_trial.sh"
BIN=$BUILD/deploy/robots/as2w/r4000/as2w_r4000_joystick_publish
SDK="env LD_LIBRARY_PATH=/root/unitree_sdk2_install/lib ./build-sdk2/as2w_sdk2"
NIC=eth0

log "mode=$MODE monitor=${MONITOR_SECONDS}s dry_run=$DRY_RUN vx_limit=$VX_LIMIT wz_limit=$WZ_LIMIT dir=$SESS"
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
  deploy/robots/as2w/r4000/r4000_controller.cpp \
  deploy/robots/as2w/r4000/r4000_controller.hpp \
  deploy/robots/as2w/r4000/r4000_observations.hpp \
  tools/run_r4000_trial.sh \
  models/r4000/policy.onnx "$BIN" 2>/dev/null | tee -a "$LOG"
if [[ ! -x build-sdk2/as2w_sdk2 ]]; then
    log "FATAL: build-sdk2/as2w_sdk2 missing (run sdk-build first)"
    exit 4
fi
AUDIT=$($BIN models/r4000/deploy.yaml config/r152_measured.map --offline-audit 2>&1 | tail -1)
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
PRONE_Q=$(echo "$CAP" | python3 -c '
import sys
f=sys.stdin.read().strip().split(",")
try:
 q=[float(f[14+i*6]) for i in (2,5,8,11)]
 print("yes" if all(-3.0 < x < -2.4 for x in q) else "no:"+",".join(f"{x:.3f}" for x in q))
except (ValueError,IndexError):
 print("invalid")' 2>/dev/null || echo invalid)
log "step4 prone calf gate=$PRONE_Q"
[[ $PRONE_Q == yes ]] || { log "FATAL: r4000 trial requires measured prone four-calf baseline"; exit 5; }

if [[ $DRY_RUN == 1 ]]; then
    log "dry-run: steps 1-4 PASS; would now start monitoring + r4000 launcher (vx=$VX_LIMIT wz=$WZ_LIMIT)"
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
log "step6 launching: $LAUNCH --vx-limit $VX_LIMIT --wz-limit $WZ_LIMIT"
log "    >>> Passive ready expected in ~3-5s; then hand the remote to the operator."
log "    >>> R4000 (training-contract 5Hz leg filter + 0.9rad/s slew): A=fixed stand, B=2s zero handoff then LY vx +/-${VX_LIMIT}m/s, RX yaw +/-${WZ_LIMIT}rad/s for max30s; center sticks to stop, A brakes early, Y squats, X=emergency; LX ignored."
$LAUNCH --vx-limit "$VX_LIMIT" --wz-limit "$WZ_LIMIT" 2>&1 | tee "$SESS/publisher.log"
RC=${PIPESTATUS[0]}
log "publisher exited rc=$RC"

if [[ -f policy_diag.log ]]; then
    cp policy_diag.log "$SESS/policy_diag.log"
    rm -f policy_diag.log
    log "policy diagnostics archived: policy_diag.log ($(wc -l < "$SESS/policy_diag.log") lines)"
fi
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
