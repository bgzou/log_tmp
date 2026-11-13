#!/usr/bin/env bash
# R284 one-command field session: verify -> control-rights -> safe remote state.
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
# Usage: run_r284_field_session.sh [stand|zero-b|motion] [monitor_seconds]
#        run_r284_field_session.sh dry-run   (steps 1-3 only, no robot action)
# Requires per-session field consent before invoking, per AGENTS.md.
set -u

echo 'FATAL: R284 real-robot LowCmd blocked after 2026-11-10 violent oscillation incident. Offline diagnosis required.' >&2
exit 78

MONITOR_SECONDS=${1:-120}
[[ $# -le 1 ]] || { echo "usage: $0 [monitor_seconds]" >&2; exit 2; }
[[ $MONITOR_SECONDS =~ ^[0-9]+$ ]] || { echo "monitor_seconds must be integer" >&2; exit 2; }
(( MONITOR_SECONDS >= 60 && MONITOR_SECONDS <= 300 )) || {
    echo "monitor_seconds must be 60..300" >&2; exit 2;
}

cd /root/as2w_deploy || { echo "FATAL: /root/as2w_deploy missing" >&2; exit 4; }
STAMP=$(date +%Y%m%d-%H%M%S)
SESSION_LABEL=r284-zero-b
SESS=/root/field_sessions/${STAMP}_${SESSION_LABEL}
mkdir -p "$SESS"
LOG=$SESS/session.log
log() { echo "[field-session] $*" | tee -a "$LOG"; }

BUILD=build-r284-zero-b
LAUNCH="bash tools/run_r284_zero_b_trial.sh"
BIN=$BUILD/deploy/robots/as2w/r284/as2w_r284_publish
SDK="env LD_LIBRARY_PATH=/root/unitree_sdk2_install/lib ./build-sdk2/as2w_sdk2"
NIC=eth0

log "policy=r284 mode=zero-b monitor=${MONITOR_SECONDS}s dir=$SESS"

# ── 1. preflight: binary + audit + SHA (never skipped) ─────────────────────
if [[ ! -x $BIN ]]; then
    log "FATAL: publisher binary missing: $BIN (build it first)"
    exit 4
fi
log "step1 binary: $BIN"
sha256sum deploy/robots/as2w/common/as2w_publish.cpp \
    deploy/robots/as2w/r284/r284_controller.cpp \
    deploy/robots/as2w/r284/r284_observations.hpp "$BIN" 2>/dev/null | tee -a "$LOG"
if [[ ! -x build-sdk2/as2w_sdk2 ]]; then
    log "FATAL: build-sdk2/as2w_sdk2 missing (run sdk-build first)"
    exit 4
fi
AUDIT=$($BIN models/r284/deploy.yaml config/r152_measured.map --offline-audit 2>&1 | tail -1)
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
    [[ 0 == 1 ]] && { log "dry-run: factory mode ($NAME); would stand-down-if-standing + ReleaseMode here"; exit 0; }
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

# ── 5. local monitoring (background, CPRO-local files) ─────────────────────
log "step5 starting ${MONITOR_SECONDS}s monitoring (low-capture 10ms + low-protection)"
$SDK low-capture $NIC rt/lowstate $MONITOR_SECONDS 10 >"$SESS/low_capture_fast.log" 2>&1 &
MON1=$!
$SDK low-protection $NIC $MONITOR_SECONDS >"$SESS/low_protection.log" 2>&1 &
MON2=$!

# ── 6. launch publisher (its own verified wake sequence) ──────────────────
log "step6 launching: $LAUNCH"
log "    >>> Passive ready expected in ~3-5s; then hand the remote to the operator."
log "    >>> A=fixed stand  B=policy (mode dependent)  Y=squat  X=emergency."
$LAUNCH 2>&1 | tee "$SESS/publisher.log"
RC=${PIPESTATUS[0]}
log "publisher exited rc=$RC"

wait $MON1 2>/dev/null
wait $MON2 2>/dev/null
log "monitoring done; artifacts:"
ls -la "$SESS" | tee -a "$LOG"
log "session complete (policy=r284 mode=zero-b rc=$RC). Copy $SESS back to the workstation logs dir and append INDEX."
exit "$RC"




