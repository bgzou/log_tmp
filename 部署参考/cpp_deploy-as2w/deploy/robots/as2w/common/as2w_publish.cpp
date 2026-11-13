// AS2-W SHARED policy FSM publisher (all policies build from this file).
// Renamed from r214_publish.cpp 2026-11-12; event-driven state machine with remote control.
//
// States: Passive → FixStand → FixedStand → PolicyHandoff → PolicyWalk
//         PolicyWalk → Brake → ReturnStand → FixedStand
//         FixedStand/Brake → FixSquat → Passive
//         Any → EmergencyDamping (X key, watchdog, fault)
//
// Remote buttons (rising edge): A=fixed stand/return, B=policy, Y=squat,
// X=emergency passive. Remote axes drive only PolicyWalk.
//
// GATES (read before building/running):
//  * CMake option AS2W_R214_PUBLISH, default OFF. Never ship enabled.
//  * Requires ReleaseMode done (S1), NOT performed by this tool.
//  * Command direction assumption: sign mirrors state sign (unverified).
//  * FixStand/FixSquat gains are rehearsal-validated but hardware-unverified.
//  * EmergencyDamping may cause standing dog to sink (no active support).
//  * No SelectMode call: exit is EmergencyDamping/Passive only.
//  * Every real-robot run needs the field crew's explicit per-action consent.
//  * --zero-b-trial (AS2W_R214_ZERO_B_TRIAL build): one bounded B cycle.
//    A→fixed PD; B (gate-checked) → 2s handoff → forced-zero policy hold
//    10s (long window: the 2.5s window hid a slow collapse) → auto
//    Brake→ReturnStand→fixed PD → 15s → repaired FixSquat → stop. Sticks
//    never map to velocity; B accepted once; 60s cycle cap. PolicyWalk/
//    Brake print POLICY_TRACK cmd-actual per leg axis for sink diagnosis.

#if defined(AS2W_POLICY_R4000)
#include "../r4000/r4000_controller.hpp"
namespace active_policy = as2w_r4000_deploy;
#elif defined(AS2W_POLICY_GETUP1199)
#include "../getup1199/getup1199_controller.hpp"
namespace active_policy = as2w_getup1199_deploy;
#elif defined(AS2W_POLICY_R1199)
#include "../r1199/r1199_controller.hpp"
namespace active_policy = as2w_r1199_deploy;
#elif defined(AS2W_POLICY_R284)
#include "../r284/r284_controller.hpp"
namespace active_policy = as2w_r284_deploy;
#elif defined(AS2W_POLICY_R270)
#include "../r270/r270_controller.hpp"
namespace active_policy = as2w_r270;
#elif defined(AS2W_POLICY_R249)
#include "../r249/r249_controller.hpp"
namespace active_policy = as2w_r249;
#else
#include "../r214/r214_controller.hpp"
namespace active_policy = as2w_r214;
#endif

#include <unitree/idl/hg/LowState_.hpp>
#include <unitree/idl/hg/LowCmd_.hpp>
#include <unitree/robot/channel/channel_factory.hpp>
#include <unitree/robot/channel/channel_publisher.hpp>
#include <unitree/robot/channel/channel_subscriber.hpp>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <csignal>
#include <cstdlib>
#include <deque>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <cstring>
#include <mutex>
#include <memory>
#include <set>
#include <stdexcept>
#include <string>
#include <thread>

namespace {

using Clock = std::chrono::steady_clock;
using LowState = unitree_hg::msg::dds_::LowState_;
using LowCmd = unitree_hg::msg::dds_::LowCmd_;
using active_policy::MotorCount;
using active_policy::Controller;
using active_policy::Config;
using active_policy::SensorState;
using active_policy::Targets;
using active_policy::Vector3;

constexpr std::size_t LegCount = 12;
constexpr auto StartupObserve = std::chrono::milliseconds(500);
constexpr auto StartupNeutralMinimum = std::chrono::milliseconds(500);
constexpr auto StartupModeAck = std::chrono::milliseconds(200);
constexpr auto StartupModeTimeout = std::chrono::seconds(2);
constexpr auto StartupDampingRamp = std::chrono::seconds(1);
constexpr auto MaxStateAge = std::chrono::milliseconds(20);
constexpr auto RemoteCommandTimeout = std::chrono::milliseconds(200);

// Minimal field-development safety envelope. These are deliberately tighter
// than the URDF actuator maxima: they bound the first low-speed flat-ground
// tests, not the full trained capability. R214 recorded replay reaches about
// 37.9 Nm predicted leg PD effort; the R284 incident reached 73.4 Nm tau_est,
// 11.5 rad/s leg dq and 14.4 rad/s wheel dq. Warning values request a
// controlled Brake after 5 consecutive 50 Hz frames; hard values select
// EmergencyDamping after 3 consecutive frames.
struct FieldSafetyProfile {
    Vector3 command_accel{0.20f, 0.10f, 0.20f};
    Vector3 command_decel{0.40f, 0.20f, 0.40f};
    float leg_dq_warn = 5.f, leg_dq_hard = 8.f;
    float wheel_dq_warn = 8.f, wheel_dq_hard = 12.f;
    float leg_tau_warn = 35.f, leg_tau_hard = 50.f;
    float wheel_tau_warn = 8.f, wheel_tau_hard = 12.f;
    float leg_pd_warn = 35.f, leg_pd_hard = 50.f;
    float wheel_pd_warn = 8.f, wheel_pd_hard = 15.f;
    // getup1199 build: the staged-rise wrapper legitimately commands up to
    // 0.61 rad single-frame leg-target steps (16-trial 50 Hz trace, max
    // consecutive frames >0.2: 6; >0.35: 2; evidence
    // logs/20261113_getup1199_deploy_precheck experiment 4). dq/tau stay
    // within the walking thresholds (max 6.5 rad/s transient, 37.2 Nm), so
    // only the leg-target step band is widened for this build.
    float leg_target_step_warn
#if defined(AS2W_POLICY_GETUP1199)
        = 0.35f
#else
        = 0.20f
#endif
        ;
    float leg_target_step_hard
#if defined(AS2W_POLICY_GETUP1199)
        = 0.75f
#else
        = 0.35f
#endif
        ;
    float wheel_target_step_warn = 15.f, wheel_target_step_hard = 30.f;
    unsigned warn_frames = 5, hard_frames = 3;
};
constexpr FieldSafetyProfile kFieldSafety{};

// B gate thresholds. Pose error 0.35 rad: fixed-PD stand holds T2 against
// real-robot gravity with measured steady-state torque 14-15 Nm on rear legs
// (rear CoM), i.e. an unavoidable 0.26-0.30 rad static error = torque/kp;
// four observed stands ranged 0.2705-0.3033, so 0.30 sat on the edge and
// rejected healthy stands (INDEX 2026-11-10 12:04-12:15). 0.35 absorbs that
// spread while still rejecting real skew (prone >1.0). Stillness, wheel,
// stick-center, hold and upright gates all remain.
constexpr float kBGatePoseError = 0.35f;
constexpr float kBGateWheelDq = 0.5f;
constexpr float kBGateLegQuietDq = 0.15f;
constexpr float kBGateUpright = 0.9f;
constexpr auto kBGateQuietWindow = std::chrono::milliseconds(500);
constexpr auto kBGateMinHold = std::chrono::milliseconds(500);

// ── FSM ────────────────────────────────────────────────────────────────────
enum class State {
    Passive,
    FixStand,
    FixedStand,
    PolicyHandoff,
    PolicyWalk,
    Brake,
    ReturnStand,
    FixSquat,
    EmergencyDamping,
#if defined(AS2W_POLICY_GETUP1199)
    // getup1199 chain (plan: getup1199实机部署与测试方案_20261113.md §5):
    // B from Passive (prone entry checks) -> FixCrouchLite -> PolicyGetup ->
    // FixedStand -> FixSquat. Walking states are unreachable in this build.
    FixCrouchLite,
    PolicyGetup,
#endif
};
enum class BrakeGoal { FixedStand, FixSquat };
const char* state_name(State s) {
    switch (s) {
    case State::Passive: return "Passive";
    case State::FixStand: return "FixStand";
    case State::FixedStand: return "FixedStand";
    case State::PolicyHandoff: return "PolicyHandoff";
    case State::PolicyWalk: return "PolicyWalk";
    case State::Brake: return "Brake";
    case State::ReturnStand: return "ReturnStand";
    case State::FixSquat: return "FixSquat";
    case State::EmergencyDamping: return "EmergencyDamping";
#if defined(AS2W_POLICY_GETUP1199)
    case State::FixCrouchLite: return "FixCrouchLite";
    case State::PolicyGetup: return "PolicyGetup";
#endif
    }
    return "?";
}

Targets fixed_stand_targets(const std::array<float, MotorCount>& pose) {
    Targets t{};
    t.active = true;
    for (std::size_t i = 0; i < LegCount; ++i) {
        t.motors[i].q = pose[i];
        t.motors[i].kp = 55.f;
        t.motors[i].kd = 2.f;
    }
    for (std::size_t i = LegCount; i < MotorCount; ++i) {
        t.motors[i].dq = 0.f;
        t.motors[i].kd = 2.f;
    }
    return t;
}

Targets blend_targets(const Targets& from, const Targets& to, float alpha) {
    Targets out{};
    out.active = from.active && to.active;
    alpha = std::clamp(alpha, 0.f, 1.f);
    for (std::size_t i = 0; i < MotorCount; ++i) {
        out.motors[i].q = from.motors[i].q +
            alpha * (to.motors[i].q - from.motors[i].q);
        out.motors[i].dq = from.motors[i].dq +
            alpha * (to.motors[i].dq - from.motors[i].dq);
        out.motors[i].kp = from.motors[i].kp +
            alpha * (to.motors[i].kp - from.motors[i].kp);
        out.motors[i].kd = from.motors[i].kd +
            alpha * (to.motors[i].kd - from.motors[i].kd);
    }
    return out;
}

// Optional diagnostic candidate. Filter only the commanded leg position and
// wheel speed at the 50 Hz policy boundary. Gains, torque, Passive, X and
// fixed stand/squat are never filtered. A filtered run is a new actuation
// contract and cannot inherit an unfiltered policy's sim/field acceptance.
class PolicyTargetLowpass {
public:
    explicit PolicyTargetLowpass(float tau_seconds = 0.f) : tau_(tau_seconds) {}
    void reset(const Targets& start) { previous_ = start; primed_ = true; }
    Targets apply(const Targets& requested, float dt, bool filter_wheels) {
        if (tau_ <= 0.f || !requested.active) return requested;
        if (!primed_) { reset(requested); return requested; }
        const float alpha = -std::expm1(-dt / tau_);
        Targets applied = requested;
        for (std::size_t i = 0; i < LegCount; ++i)
            applied.motors[i].q = previous_.motors[i].q +
                alpha * (requested.motors[i].q - previous_.motors[i].q);
        for (std::size_t i = LegCount; i < MotorCount; ++i)
            applied.motors[i].dq = filter_wheels
                ? previous_.motors[i].dq +
                    alpha * (requested.motors[i].dq - previous_.motors[i].dq)
                : requested.motors[i].dq;
        previous_ = applied;
        return applied;
    }
private:
    float tau_ = 0.f;
    bool primed_ = false;
    Targets previous_{};
};

// ── Remote decode (P6 calibrated) ──────────────────────────────────────────
struct RemoteInput {
    // Buttons (u16 bitmask)
    static constexpr uint16_t BTN_A = 1u << 8;
    static constexpr uint16_t BTN_B = 1u << 9;
    static constexpr uint16_t BTN_X = 1u << 10;
    static constexpr uint16_t BTN_Y = 1u << 11;
    // Axes (float indices in 40-byte wireless_remote: head[2]+buttons[2]+5 floats)
    // layout: lx, rx, ry, L2, ly
    static constexpr std::size_t AXIS_LX = 0, AXIS_RX = 1, AXIS_RY = 2,
                                AXIS_L2 = 3, AXIS_LY = 4;

    uint16_t buttons = 0;
    float axes[5] = {};
    bool valid = false;

    float ly() const { return axes[AXIS_LY]; }  // forward +, back −
    float lx() const { return axes[AXIS_LX]; }
    float rx() const { return axes[AXIS_RX]; }
};

RemoteInput decode_remote(const LowState& frame) {
    RemoteInput r;
    const auto& raw = frame.wireless_remote();
    if (raw[0] != 0x55 || raw[1] != 0x51) return {};
    r.buttons = static_cast<uint16_t>(raw[2]) | (static_cast<uint16_t>(raw[3]) << 8);
    for (std::size_t i = 0; i < 5; ++i) {
        std::memcpy(&r.axes[i], &raw[4 + 4 * i], sizeof(float));
        if (!std::isfinite(r.axes[i]) || std::abs(r.axes[i]) > 1.5f)
            return {};
    }
    r.valid = true;
    return r;
}

Vector3 map_remote_command(const RemoteInput& r, float vx_limit) {
    Vector3 cmd{};
    // P6: ly forward +, lx/right +, rx/right +. Model +vy/+wz
    // are leftward/counterclockwise, hence the two minus signs.
    if (std::abs(r.ly()) > 0.05f)
        cmd[0] = std::clamp(r.ly() * vx_limit / 0.85f, -vx_limit, vx_limit);
    if (std::abs(r.lx()) > 0.05f)
        cmd[1] = std::clamp(-r.lx() * 0.05f / 0.85f, -0.05f, 0.05f);
    if (std::abs(r.rx()) > 0.05f)
        cmd[2] = std::clamp(-r.rx() * 0.10f / 0.85f, -0.10f, 0.10f);
    return cmd;
}

// Shared LY->vx / RX->wz stick mapping for the bounded joystick candidates
// (R1199 and R4000); the per-candidate envelope is passed by the caller.
#if defined(AS2W_R1199_JOYSTICK_CANDIDATE) || defined(AS2W_R4000_JOYSTICK_CANDIDATE)
Vector3 map_r1199_joystick_command(const RemoteInput& r, float vx_limit, float wz_limit) {
    // P6 measured signs: LY forward positive, RX right positive. R1199
    // accepts vx/wz only. Ignore LX/RY instead of inventing a vy action.
    // Speed limits come from deploy.yaml (config.vx_limit / config.wz_limit);
    // changing the yaml value requires offline re-verification before field.
    Vector3 cmd{};
    if (std::abs(r.ly()) > .05f)
        cmd[0] = std::clamp(r.ly() * vx_limit / .85f, -vx_limit, vx_limit);
    if (std::abs(r.rx()) > .05f)
        cmd[2] = std::clamp(-r.rx() * wz_limit / .85f, -wz_limit, wz_limit);
    return cmd;
}
#endif

Vector3 slew_command(const Vector3& current, const Vector3& desired, float dt) {
    Vector3 out{};
    for (std::size_t i = 0; i < out.size(); ++i) {
        const bool accelerating = current[i] * desired[i] >= 0.f &&
            std::abs(desired[i]) > std::abs(current[i]);
        const float rate = accelerating ? kFieldSafety.command_accel[i]
                                        : kFieldSafety.command_decel[i];
        const float delta = std::clamp(desired[i] - current[i], -rate * dt,
                                       rate * dt);
        out[i] = current[i] + delta;
        if (std::abs(out[i]) < 1e-6f) out[i] = 0.f;
    }
    return out;
}

// ── Mapping ────────────────────────────────────────────────────────────────
struct Axis {
    std::size_t index;
    float sign, zero;
};
using Mapping = std::array<Axis, MotorCount>;

// Single producer (500 Hz DDS writer), single consumer (file thread). The
// publisher only copies a fixed-size record; disk I/O never runs in its loop.
class DebugLowCmdLog {
    struct MotorRecord {
        unsigned slot = 0, mode = 0;
        float q = 0, dq = 0, kp = 0, kd = 0, tau = 0;
    };
    struct Record {
        int64_t mono_ns = 0;
        uint32_t tick = 0;
        unsigned state = 0, mode_machine = 0;
        std::array<MotorRecord, MotorCount> motors{};
    };
    static constexpr uint32_t Capacity = 4096;
public:
    void start() {
        rows_ = std::make_unique<Record[]>(Capacity);
        file_.open("debug_lowcmd.csv", std::ios::out | std::ios::trunc);
        if (!file_) throw std::runtime_error("Cannot open debug_lowcmd.csv");
        file_ << "DEBUG_LOWCMD_SCHEMA,mono_ns,lowstate_tick,state,mode_machine,"
                 "per_contract_axis(slot,mode,q,dq,kp,kd,tau)x16\n";
        file_ << std::setprecision(9);
        worker_ = std::thread([this] { drain(); });
    }
    void push(const LowCmd& cmd, const LowState& frame,
              const Mapping& map, State state) {
        const uint32_t write = written_.load(std::memory_order_relaxed);
        if (write - read_.load(std::memory_order_acquire) >= Capacity) {
            dropped_.fetch_add(1, std::memory_order_relaxed);
            return;
        }
        auto& row = rows_[write % Capacity];
        row.mono_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
            Clock::now().time_since_epoch()).count();
        row.tick = frame.tick();
        row.state = static_cast<unsigned>(state);
        row.mode_machine = cmd.mode_machine();
        for (std::size_t i = 0; i < MotorCount; ++i) {
            const auto slot = map[i].index;
            const auto& m = cmd.motor_cmd()[slot];
            row.motors[i] = {static_cast<unsigned>(slot),
                static_cast<unsigned>(m.mode()), m.q(), m.dq(),
                m.kp(), m.kd(), m.tau()};
        }
        written_.store(write + 1, std::memory_order_release);
    }
    void stop() {
        if (!worker_.joinable()) return;
        stopping_.store(true, std::memory_order_release);
        worker_.join();
        file_.flush();
        std::cout << "DEBUG_LOWCMD_RESULT rows=" << read_.load()
                  << " dropped=" << dropped_.load()
                  << " file_ok=" << static_cast<bool>(file_) << '\n';
        file_.close();
    }
    ~DebugLowCmdLog() { stop(); }
private:
    void drain() {
        while (!stopping_.load(std::memory_order_acquire) ||
               read_.load(std::memory_order_relaxed) !=
                   written_.load(std::memory_order_acquire)) {
            const uint32_t read = read_.load(std::memory_order_relaxed);
            if (read == written_.load(std::memory_order_acquire)) {
                std::this_thread::sleep_for(std::chrono::milliseconds(2));
                continue;
            }
            const auto& row = rows_[read % Capacity];
            file_ << "DEBUG_LOWCMD," << row.mono_ns << ',' << row.tick
                  << ',' << row.state << ',' << row.mode_machine;
            for (const auto& m : row.motors)
                file_ << ',' << m.slot << ',' << m.mode << ',' << m.q
                      << ',' << m.dq << ',' << m.kp << ',' << m.kd
                      << ',' << m.tau;
            file_ << '\n';
            read_.store(read + 1, std::memory_order_release);
        }
    }
    std::unique_ptr<Record[]> rows_;
    std::ofstream file_;
    std::thread worker_;
    std::atomic<uint32_t> written_{0}, read_{0}, dropped_{0};
    std::atomic<bool> stopping_{false};
};

struct FieldSafetyMetrics {
    float leg_dq = 0.f, wheel_dq = 0.f;
    float leg_tau = 0.f, wheel_tau = 0.f;
    float leg_pd = 0.f, wheel_pd = 0.f;
    float leg_target_step = 0.f, wheel_target_step = 0.f;
    uint32_t motorstate_or = 0;
    bool invalid = false;

    bool warning() const {
        return invalid || motorstate_or != 0 ||
            leg_dq > kFieldSafety.leg_dq_warn ||
            wheel_dq > kFieldSafety.wheel_dq_warn ||
            leg_tau > kFieldSafety.leg_tau_warn ||
            wheel_tau > kFieldSafety.wheel_tau_warn ||
            leg_pd > kFieldSafety.leg_pd_warn ||
            wheel_pd > kFieldSafety.wheel_pd_warn ||
            leg_target_step > kFieldSafety.leg_target_step_warn ||
            wheel_target_step > kFieldSafety.wheel_target_step_warn;
    }
    bool hard() const {
        return invalid || motorstate_or != 0 ||
            leg_dq > kFieldSafety.leg_dq_hard ||
            wheel_dq > kFieldSafety.wheel_dq_hard ||
            leg_tau > kFieldSafety.leg_tau_hard ||
            wheel_tau > kFieldSafety.wheel_tau_hard ||
            leg_pd > kFieldSafety.leg_pd_hard ||
            wheel_pd > kFieldSafety.wheel_pd_hard ||
            leg_target_step > kFieldSafety.leg_target_step_hard ||
            wheel_target_step > kFieldSafety.wheel_target_step_hard;
    }
};

FieldSafetyMetrics measure_field_safety(const LowState& frame,
                                        const Mapping& map,
                                        const Targets& target,
                                        const Targets* previous) {
    FieldSafetyMetrics m{};
    if (!target.active) m.invalid = true;
    for (std::size_t i = 0; i < MotorCount; ++i) {
        const auto& feedback = frame.motor_state()[map[i].index];
        const auto& command = target.motors[i];
        const float q = map[i].sign * (feedback.q() - map[i].zero);
        const float dq = map[i].sign * feedback.dq();
        const float tau = std::abs(feedback.tau_est());
        const float pd = std::abs(command.kp * (command.q - q) +
                                  command.kd * (command.dq - dq));
        if (!std::isfinite(q) || !std::isfinite(dq) || !std::isfinite(tau) ||
            !std::isfinite(command.q) || !std::isfinite(command.dq) ||
            !std::isfinite(command.kp) || !std::isfinite(command.kd) ||
            command.kp < 0.f || command.kd < 0.f) {
            m.invalid = true;
        }
        m.motorstate_or |= feedback.motorstate();
        if (i < LegCount) {
            m.leg_dq = std::max(m.leg_dq, std::abs(dq));
            m.leg_tau = std::max(m.leg_tau, tau);
            m.leg_pd = std::max(m.leg_pd, pd);
            if (previous && previous->active)
                m.leg_target_step = std::max(m.leg_target_step,
                    std::abs(command.q - previous->motors[i].q));
        } else {
            m.wheel_dq = std::max(m.wheel_dq, std::abs(dq));
            m.wheel_tau = std::max(m.wheel_tau, tau);
            m.wheel_pd = std::max(m.wheel_pd, pd);
            if (previous && previous->active)
                m.wheel_target_step = std::max(m.wheel_target_step,
                    std::abs(command.dq - previous->motors[i].dq));
        }
    }
    return m;
}

void print_field_safety(const char* level, State state,
                        const FieldSafetyMetrics& m, unsigned count) {
    std::cout << "FIELD_SAFETY_" << level << " state=" << state_name(state)
              << " count=" << count
              << " leg_dq=" << m.leg_dq << " wheel_dq=" << m.wheel_dq
              << " leg_tau=" << m.leg_tau << " wheel_tau=" << m.wheel_tau
              << " leg_pd=" << m.leg_pd << " wheel_pd=" << m.wheel_pd
              << " leg_step=" << m.leg_target_step
              << " wheel_step=" << m.wheel_target_step
              << " motorstate_or=0x" << std::hex << m.motorstate_or << std::dec
              << " invalid=" << m.invalid << '\n';
}

// ── Field guard decision (shared by the 50 Hz FSM tick and offline audit) ──
// Pure evaluation of the consecutive-frame warn/hard counters. Counts are
// owned by one policy episode (Handoff/Walk/Brake) and reset by the caller
// when the FSM leaves that trio; `braking` mirrors st == Brake, where a
// warning must not request a second Brake (hard limits still fire).
struct FieldGuardCounts {
    unsigned warn = 0, hard = 0, log_tick = 0;
};
enum class FieldGuardAction { Continue, SoftBrake, HardStop };
struct FieldGuardOutcome {
    FieldGuardAction action = FieldGuardAction::Continue;
    bool log_metrics = false;
    const char* log_level = "WARN";
    unsigned log_count = 0;
};
FieldGuardOutcome evaluate_field_guard(const FieldSafetyMetrics& metrics,
                                       bool braking,
                                       FieldGuardCounts& counts) {
    FieldGuardOutcome out{};
    counts.warn = metrics.warning() ? counts.warn + 1 : 0;
    counts.hard = metrics.hard() ? counts.hard + 1 : 0;
    if (metrics.warning() && (++counts.log_tick == 1 ||
        counts.warn == kFieldSafety.warn_frames ||
        counts.hard == kFieldSafety.hard_frames ||
        counts.log_tick % 25 == 0)) {
        out.log_metrics = true;
        out.log_level = metrics.hard() ? "HARD" : "WARN";
        out.log_count = metrics.hard() ? counts.hard : counts.warn;
    }
    if (counts.hard >= kFieldSafety.hard_frames)
        out.action = FieldGuardAction::HardStop;
    else if (counts.warn >= kFieldSafety.warn_frames && !braking)
        out.action = FieldGuardAction::SoftBrake;
    return out;
}

// ── Remote timeout predicates (shared by FSM tick and offline audit) ──
// The HG embedded payload has no visible sequence/timestamp: only the
// absence of format-valid frames is detectable, not a frozen stale frame.
bool remote_payload_timed_out(Clock::time_point last_valid,
                              Clock::time_point now) {
    return last_valid == Clock::time_point{} ||
        now - last_valid > RemoteCommandTimeout;
}
// Only Handoff/Walk are stick-supervised. Brake ignores sticks, and there
// is no FSM path from Brake back into PolicyWalk: recovery after a timeout
// goes through ReturnStand/FixedStand and a fresh, gate-checked B press.
bool remote_timeout_requests_brake(State st, bool timed_out) {
    return timed_out &&
        (st == State::PolicyHandoff || st == State::PolicyWalk);
}

Mapping read_mapping(const Config& config, const char* path) {
    std::ifstream file(path);
    std::set<std::size_t> used;
    Mapping map{};
    const auto slots = LowState{}.motor_state().size();
    for (std::size_t i = 0; i < map.size(); ++i) {
        std::string name;
        auto& axis = map[i];
        if (!(file >> name >> axis.index >> axis.sign >> axis.zero)
            || name != config.joint_names[i] || axis.index >= slots
            || !used.insert(axis.index).second || std::abs(axis.sign) != 1.f
            || !std::isfinite(axis.zero)) {
            throw std::runtime_error("Invalid or incomplete motor mapping file");
        }
    }
    std::string extra;
    if (file >> extra) throw std::runtime_error("Trailing mapping data");
    return map;
}

// ── CRC32 (verified 5259/5259 against real LowState) ──────────────────────
uint32_t crc32Core(const uint32_t* ptr, uint32_t len) {
    unsigned int crc = 0xFFFFFFFF;
    const unsigned int poly = 0x04c11db7;
    for (unsigned int i = 0; i < len; ++i) {
        unsigned int data = ptr[i];
        for (int b = 0; b < 32; ++b) {
            crc = (crc & 0x80000000) ? ((crc << 1) ^ poly) : (crc << 1);
            if (data & (1u << (31 - b))) crc ^= poly;
        }
    }
    return crc;
}

// ── Frame builders ─────────────────────────────────────────────────────────
// This is a *candidate*, not a proven AS2-W wake protocol. Unlike the GO2W
// IDL, HG has no documented PosStopF/VelStopF semantics. With both gains and
// feed-forward torque zero, q/dq have no effect under the documented PD law;
// q tracks measured position to avoid out-of-range targets in firmware checks.
void fill_zero_torque(LowCmd& cmd, const LowState& st, const Mapping& map) {
    cmd = LowCmd{};
    cmd.mode_pr() = 0;
    cmd.mode_machine() = st.mode_machine();
    for (std::size_t i = 0; i < MotorCount; ++i) {
        const auto& axis = map[i];
        const auto& motor = st.motor_state()[axis.index];
        auto& out = cmd.motor_cmd()[axis.index];
        out.mode() = 0x01;
        out.q() = motor.q();
        out.dq() = 0.f;
        out.kp() = 0.f;
        out.kd() = 0.f;
        out.tau() = 0.f;
    }
}

void fill_passive(LowCmd& cmd, const LowState& st, const Mapping& map, float kd) {
    fill_zero_torque(cmd, st, map);
    for (std::size_t i = 0; i < MotorCount; ++i)
        cmd.motor_cmd()[map[i].index].kd() = kd;
}

// One bounded protocol probe. Contract index is deliberately explicit; no
// automatic multi-axis sequence is permitted here. Never call before the
// already-tested Passive wake sequence reaches Ready.
void fill_probe(LowCmd& cmd, const LowState& st, const Mapping& map,
                std::size_t index, float raw_anchor, float amplitude,
                float scale, float probe_kp, float passive_kd) {
    fill_passive(cmd, st, map, passive_kd);
    auto& out = cmd.motor_cmd()[map[index].index];
    if (index < LegCount) {
        out.q() = raw_anchor + map[index].sign * amplitude * scale;
        out.kp() = probe_kp;
    } else {
        out.q() = 0.f;
        out.dq() = map[index].sign * amplitude * scale;
        out.kp() = 0.f;
    }
}

void fill_targets(LowCmd& cmd, const LowState& st, const Mapping& map,
                  const Targets& targets) {
    cmd = LowCmd{};
    cmd.mode_pr() = 0;
    cmd.mode_machine() = st.mode_machine();
    for (std::size_t i = 0; i < MotorCount; ++i) {
        const auto& axis = map[i];
        auto& out = cmd.motor_cmd()[axis.index];
        out.mode() = 0x01;
        out.kp() = targets.motors[i].kp;
        out.kd() = targets.motors[i].kd;
        out.tau() = 0.f;
        if (i < LegCount || targets.motors[i].kp != 0.f) {
            // Legs are always position mode. Wheels are velocity mode in the
            // walking builds (kp==0); the getup1199 wheel position hold
            // (latched reference, kp=25) selects position mode here.
            out.q() = axis.sign * targets.motors[i].q + axis.zero;
            out.dq() = 0.f;
        } else {
            out.q() = 0.f;
            out.dq() = axis.sign * targets.motors[i].dq;
        }
    }
}

void finish(LowCmd& cmd) {
    cmd.crc() = crc32Core(reinterpret_cast<const uint32_t*>(&cmd),
                          (sizeof(LowCmd) >> 2) - 1);
}

bool valid_startup_state(const LowState& st, const Mapping& map) {
    if (st.mode_machine() == 0 ||
        st.crc() != crc32Core(reinterpret_cast<const uint32_t*>(&st),
                              (sizeof(LowState) >> 2) - 1)) return false;
    for (const auto& axis : map) {
        const auto& motor = st.motor_state()[axis.index];
        if (!std::isfinite(motor.q()) || !std::isfinite(motor.dq()) ||
            !std::isfinite(motor.tau_est())) return false;
    }
    return true;
}

enum class WakePhase { Neutral, Ramp, Ready, Fault };
struct WakeSequence {
    Clock::time_point started;
    Clock::time_point mode_one_since{};
    Clock::time_point ramp_started{};
    WakePhase phase = WakePhase::Neutral;

    explicit WakeSequence(Clock::time_point now) : started(now) {}

    void step(Clock::time_point now, bool all_foc) {
        if (phase == WakePhase::Neutral) {
            if (all_foc) {
                if (mode_one_since == Clock::time_point{}) mode_one_since = now;
            } else mode_one_since = Clock::time_point{};
            if (now - started > StartupModeTimeout) {
                phase = WakePhase::Fault;
            } else if (now - started >= StartupNeutralMinimum &&
                       mode_one_since != Clock::time_point{} &&
                       now - mode_one_since >= StartupModeAck) {
                phase = WakePhase::Ramp;
                ramp_started = now;
            }
        } else if (phase == WakePhase::Ramp) {
            if (!all_foc) phase = WakePhase::Fault;
            else if (now - ramp_started >= StartupDampingRamp)
                phase = WakePhase::Ready;
        }
    }

    float ramp_kd(Clock::time_point now, float target) const {
        return target * std::clamp(
            std::chrono::duration<float>(now-ramp_started).count() /
                std::chrono::duration<float>(StartupDampingRamp).count(),
            0.f, 1.f);
    }
};

void dump_frame(const char* label, LowCmd cmd) {
    finish(cmd);
    std::cout << "FRAME " << label << " sizeof=" << sizeof(LowCmd)
              << " mode_pr=" << unsigned(cmd.mode_pr())
              << " mode_machine=" << unsigned(cmd.mode_machine())
              << " crc=0x" << std::hex << std::setw(8) << std::setfill('0')
              << cmd.crc() << std::dec << std::setfill(' ') << '\n';
    for (std::size_t i = 0; i < cmd.motor_cmd().size(); ++i) {
        const auto& m = cmd.motor_cmd()[i];
        std::cout << "slot=" << i << " mode=" << unsigned(m.mode())
                  << " q=" << m.q() << " dq=" << m.dq()
                  << " kp=" << m.kp() << " kd=" << m.kd()
                  << " tau=" << m.tau() << " reserve=" << m.reserve() << '\n';
    }
    std::cout << "reserve=";
    for (auto word : cmd.reserve()) std::cout << word << ',';
    std::cout << "\nraw_hex=";
    const auto* bytes = reinterpret_cast<const unsigned char*>(&cmd);
    for (std::size_t i = 0; i < sizeof(cmd); ++i)
        std::cout << std::hex << std::setw(2) << std::setfill('0') << unsigned(bytes[i]);
    std::cout << std::dec << std::setfill(' ') << '\n';
}

// ── Stand/Squat poses (contract order, model coords) ─────────────────────
// Measured factory stand (P10 11:41 session)
std::array<float, MotorCount> make_stand_t1() {
    auto q = std::array<float, MotorCount>{};
    q[0] = 0.1298f; q[1] = -0.1213f; q[2] = 0.1215f; q[3] = -0.1308f;
    q[4] = q[5] = q[6] = q[7] = 0.60f;
    q[8] = q[9] = q[10] = q[11] = -1.23f;
    return q;
}

// R214 training default pose
std::array<float, MotorCount> make_stand_t2(const Config& config) {
    return config.defaults;
}

// Measured prone (G1 session, contract order FL,FR,RL,RR)
std::array<float, MotorCount> make_prone() {
    auto q = std::array<float, MotorCount>{};
    q[0] = -0.5676f; q[1] = 0.5725f; q[2] = -0.5930f; q[3] = 0.6040f;
    q[4] = q[5] = q[6] = q[7] = 1.0f;
    q[8] = q[9] = q[10] = q[11] = -2.75f;
    return q;
}

}  // namespace

std::atomic<bool> g_abort{false};

// ── Main ────────────────────────────────────────────────────────────────────
int main(int argc, char** argv) {
    using namespace active_policy;
    // Preserve phase evidence even if the SDK's DDS teardown aborts.
    std::cout << std::unitbuf;
    try {
        std::string yaml, map_path, nic, stand_variant = "t1";
        float passive_kd = 3.f, interp_sec = 3.0f, squat_sec = 4.0f;
        float passive_seconds = 3.f;
        float vx_limit = 0.2f, stand_hold_seconds = 15.f;
        float wz_limit = 0.2f;
        float policy_lowpass_ms = 0.f;
        bool vx_limit_given = false, wz_limit_given = false;
        bool confirmed = false, offline_audit = false, enable_fsm_motion = false;
        bool stand_trial = false, zero_b_trial = false;
        bool getup_trial = false;
        bool debug_capture = false;
        bool policy_lowpass_wheels = false;
        int probe_index = -1;
        float probe_amplitude = 0.f, probe_kp = 5.f;
        for (int i = 1; i < argc; ++i) {
            const std::string arg = argv[i];
            auto next = [&]() {
                if (i + 1 >= argc) throw std::runtime_error("Missing value for " + arg);
                return std::string(argv[++i]);
            };
            if (arg == "--i-confirm-lowcmd-publish") confirmed = true;
            else if (arg == "--offline-audit") offline_audit = true;
            else if (arg == "--debug") debug_capture = true;
            else if (arg == "--policy-lowpass-ms") policy_lowpass_ms = std::stof(next());
            else if (arg == "--policy-lowpass-wheels") policy_lowpass_wheels = true;
            else if (arg == "--enable-fsm-motion") enable_fsm_motion = true;
            else if (arg == "--stand-trial") stand_trial = true;
            else if (arg == "--zero-b-trial") zero_b_trial = true;
            else if (arg == "--getup-trial") getup_trial = true;
            else if (arg == "--stand-hold-seconds") stand_hold_seconds = std::stof(next());
            else if (arg == "--passive-kd") passive_kd = std::stof(next());
            else if (arg == "--passive-seconds") passive_seconds = std::stof(next());
            else if (arg == "--interp-sec") interp_sec = std::stof(next());
            else if (arg == "--squat-sec") squat_sec = std::stof(next());
            else if (arg == "--vx-limit") { vx_limit = std::stof(next()); vx_limit_given = true; }
            else if (arg == "--wz-limit") { wz_limit = std::stof(next()); wz_limit_given = true; }
            else if (arg == "--probe-index") probe_index = std::stoi(next());
            else if (arg == "--probe-amplitude") probe_amplitude = std::stof(next());
            else if (arg == "--probe-kp") probe_kp = std::stof(next());
            else if (arg == "--stand") stand_variant = next();
            else if (yaml.empty()) yaml = arg;
            else if (map_path.empty()) map_path = arg;
            else if (nic.empty()) nic = arg;
            else throw std::runtime_error("Unexpected arg: " + arg);
        }
        if (yaml.empty() || map_path.empty() ||
            (!offline_audit && (!confirmed || nic.empty())) ||
            !std::isfinite(passive_kd) || passive_kd < 0.f || passive_kd > 3.f ||
            !std::isfinite(passive_seconds) || passive_seconds <= 0.f || passive_seconds > 10.f ||
            probe_index < -1 || probe_index >= static_cast<int>(MotorCount) ||
            (probe_index >= 0 && (enable_fsm_motion || stand_trial || zero_b_trial ||
                !std::isfinite(probe_amplitude) ||
                probe_amplitude <= 0.f || probe_amplitude >
                    (probe_index < static_cast<int>(LegCount) ? 0.03f : 0.5f))) ||
            !std::isfinite(probe_kp) || probe_kp < 0.f || probe_kp > 20.f ||
            (probe_index < 0 && probe_amplitude != 0.f) ||
            (stand_trial && (enable_fsm_motion || zero_b_trial ||
                stand_variant != "t2" || interp_sec != 3.f || squat_sec != 4.f)) ||
            (zero_b_trial && (enable_fsm_motion || stand_trial ||
                stand_variant != "t2" || interp_sec != 3.f || squat_sec != 4.f)) ||
            (getup_trial && (enable_fsm_motion || stand_trial ||
                zero_b_trial || probe_index >= 0)) ||
#if defined(AS2W_POLICY_GETUP1199)
            // The getup build has no walking path; it exists only for the
            // bounded one-shot B chain.
            (!getup_trial && !offline_audit) ||
#endif
            !std::isfinite(stand_hold_seconds) || stand_hold_seconds < 0.5f ||
            stand_hold_seconds > 30.f || !std::isfinite(vx_limit) ||
            vx_limit <= 0.f || (enable_fsm_motion && vx_limit > 0.1f) ||
            !std::isfinite(wz_limit) || wz_limit < 0.f ||
            (wz_limit == 0.f && policy_lowpass_ms == 0.f) ||
            !std::isfinite(policy_lowpass_ms) || policy_lowpass_ms < 0.f ||
            policy_lowpass_ms > 200.f ||
            (policy_lowpass_wheels && policy_lowpass_ms == 0.f)) {
            std::cerr << "Usage: as2w_r214_publish <deploy.yaml> <map> <NIC>"
                         " --i-confirm-lowcmd-publish [--stand t1|t2]"
                         " [--interp-sec 3] [--squat-sec 4] [--passive-kd 3]"
                         " [--passive-seconds 3]"
                         " [--enable-fsm-motion | --stand-trial | --zero-b-trial]"
                         " [--getup-trial]"
                         " [--stand-hold-seconds 15] [--offline-audit]"
                         " [--vx-limit 0.2] [--wz-limit 0.2]"
                         " [--debug] [--policy-lowpass-ms 0..200]"
                         " [--policy-lowpass-wheels]"
                         " [--probe-index 0..15 --probe-amplitude <=0.03rad|0.5rad/s]"
                         " [--probe-kp <=20]\n";
            return 2;
        }
#ifndef AS2W_ENABLE_POLICY_LOWPASS
        if (policy_lowpass_ms > 0.f)
            throw std::runtime_error("Policy low-pass requires an isolated candidate build");
#endif
#if defined(AS2W_R1199_FORWARD_CANDIDATE)
        // This binary has no free-running path: exactly one 2 s B cycle,
        // no lateral/yaw command, and a fixed 0.05 m/s forward ceiling.
        if (!offline_audit && (!zero_b_trial || enable_fsm_motion ||
            stand_trial || std::abs(vx_limit - .05f) > 1e-6f))
            throw std::runtime_error("R1199 forward candidate requires one bounded B trial at vx-limit=0.05");
#elif defined(AS2W_R1199_JOYSTICK_CANDIDATE)
        if (!offline_audit && (!zero_b_trial || enable_fsm_motion ||
            stand_trial))
            throw std::runtime_error("R1199 joystick candidate requires one bounded B trial");
#elif defined(AS2W_R4000_JOYSTICK_CANDIDATE)
        if (!offline_audit && (!zero_b_trial || enable_fsm_motion ||
            stand_trial))
            throw std::runtime_error("R4000 joystick candidate requires one bounded B trial");
#endif

        const auto config = load_config(yaml);
#if defined(AS2W_R1199_JOYSTICK_CANDIDATE)
        // Joystick candidate: deploy.yaml (config.vx_limit/wz_limit) is the
        // authoritative envelope. CLI --vx-limit/--wz-limit may only restrict
        // the session further, never exceed the yaml cap.
        const float r1199_vx_limit = vx_limit_given
            ? std::min(vx_limit, config.vx_limit) : config.vx_limit;
        const float r1199_wz_limit = wz_limit_given
            ? std::min(wz_limit, config.wz_limit) : config.wz_limit;
#endif
#if defined(AS2W_R4000_JOYSTICK_CANDIDATE)
        // Same rule for the R4000 candidate: deploy.yaml is authoritative,
        // the CLI may only restrict.
        const float r4000_vx_limit = vx_limit_given
            ? std::min(vx_limit, config.vx_limit) : config.vx_limit;
        const float r4000_wz_limit = wz_limit_given
            ? std::min(wz_limit, config.wz_limit) : config.wz_limit;
#endif
        const auto mapping = read_mapping(config, map_path.c_str());
#ifndef AS2W_ENABLE_POLICY_MOTION
        if (enable_fsm_motion)
            throw std::runtime_error("FSM motion is compile-time locked pending separate review");
#endif
#ifndef AS2W_ENABLE_POLICY_STAND_TRIAL
        if (stand_trial)
            throw std::runtime_error("Stand trial requires the separate gated build");
#endif
#ifndef AS2W_ENABLE_POLICY_ZERO_B_TRIAL
        if (zero_b_trial)
            throw std::runtime_error("Zero-B trial requires the separate gated build");
#endif
#ifndef AS2W_ENABLE_GETUP_TRIAL
        if (getup_trial)
            throw std::runtime_error("Getup trial requires the separate getup build");
#endif
        Controller controller(config);
        const auto stand_pose = (stand_variant == "t2")
            ? make_stand_t2(config) : make_stand_t1();
        const auto prone_pose = make_prone();

        if (offline_audit) {
            if (debug_capture) {
                DebugLowCmdLog capture;
                capture.start();
                const auto begun = Clock::now();
                for (unsigned i = 0; i < 500; ++i) {
                    capture.push(LowCmd{}, LowState{}, mapping, State::Passive);
                    std::this_thread::sleep_until(
                        begun + std::chrono::milliseconds(2 * (i + 1)));
                }
                capture.stop();
                std::ifstream rows("debug_lowcmd.csv");
                std::string line;
                unsigned lines = 0;
                while (std::getline(rows, line)) ++lines;
                if (lines != 501)
                    throw std::runtime_error("Debug LowCmd offline capture audit failed");
                std::cout << "DEBUG_CAPTURE_AUDIT PASS rows=500 at 500Hz\n";
            }
            const auto fixed = fixed_stand_targets(stand_pose);
            {
                PolicyTargetLowpass filter(0.08f);
                filter.reset(fixed);
                auto request = fixed;
                request.motors[0].q += .20f;
                request.motors[12].dq = 1.f;
                request.motors[0].kp = 17.f;
                const auto first = filter.apply(request, .02f, true);
                const float alpha = -std::expm1(-.02f / .08f);
                if (std::abs(first.motors[0].q -
                    (fixed.motors[0].q + .20f * alpha)) > 1e-6f ||
                    std::abs(first.motors[12].dq - alpha) > 1e-6f ||
                    first.motors[0].kp != 17.f)
                    throw std::runtime_error("Policy low-pass audit failed");
                const auto brake = filter.apply(fixed, .02f, false);
                if (brake.motors[12].dq != 0.f ||
                    brake.motors[0].q >= first.motors[0].q)
                    throw std::runtime_error("Policy brake-bypass audit failed");
                PolicyTargetLowpass off;
                if (off.apply(request, .02f, true).motors[0].q != request.motors[0].q)
                    throw std::runtime_error("Policy low-pass OFF audit failed");
            }
            if (!fixed.active || fixed.motors[0].kp != 55.f ||
                fixed.motors[0].q != stand_pose[0] ||
                fixed.motors[LegCount].dq != 0.f)
                throw std::runtime_error("FixedStand target audit failed");
            auto policy_example = fixed;
            policy_example.motors[0].q += 0.2f;
            policy_example.motors[0].kp = 35.f;
            policy_example.motors[LegCount].dq = 0.4f;
            const auto entry = blend_targets(fixed, policy_example, 0.f);
            const auto exit = blend_targets(fixed, policy_example, 1.f);
            if (entry.motors[0].q != fixed.motors[0].q ||
                entry.motors[0].kp != fixed.motors[0].kp ||
                entry.motors[LegCount].dq != 0.f ||
                exit.motors[0].q != policy_example.motors[0].q ||
                exit.motors[0].kp != policy_example.motors[0].kp ||
                exit.motors[LegCount].dq != 0.4f)
                throw std::runtime_error("FSM handoff endpoint audit failed");
            std::cout << "FSM CONTRACT A=FixedStand B=PolicyHandoff"
                         " Y=FixSquat X=EmergencyDamping\n";
            RemoteInput remote_audit{};
            remote_audit.axes[RemoteInput::AXIS_LY] = 0.85f;
            remote_audit.axes[RemoteInput::AXIS_LX] = 0.85f;
            remote_audit.axes[RemoteInput::AXIS_RX] = 0.85f;
            const auto mapped = map_remote_command(remote_audit, 0.1f);
            if (std::abs(mapped[0]-0.1f)>1e-6f ||
                std::abs(mapped[1]+0.05f)>1e-6f ||
                std::abs(mapped[2]+0.10f)>1e-6f)
                throw std::runtime_error("Remote direction mapping audit failed");
            remote_audit.axes[RemoteInput::AXIS_LY] = -0.85f;
            remote_audit.axes[RemoteInput::AXIS_LX] = -0.85f;
            remote_audit.axes[RemoteInput::AXIS_RX] = -0.85f;
            const auto reverse = map_remote_command(remote_audit, 0.1f);
            if (std::abs(reverse[0]+0.1f)>1e-6f ||
                std::abs(reverse[1]-0.05f)>1e-6f ||
                std::abs(reverse[2]-0.10f)>1e-6f)
                throw std::runtime_error("Reverse remote direction audit failed");
            const Vector3 zero_command{};
            const Vector3 full_command{0.1f, 0.05f, 0.1f};
            const auto ramp_up = slew_command(zero_command, full_command, .02f);
            const auto ramp_down = slew_command(full_command, zero_command, .02f);
            if (std::abs(ramp_up[0]-.004f)>1e-6f ||
                std::abs(ramp_up[1]-.002f)>1e-6f ||
                std::abs(ramp_up[2]-.004f)>1e-6f ||
                std::abs(ramp_down[0]-.092f)>1e-6f ||
                std::abs(ramp_down[1]-.046f)>1e-6f ||
                std::abs(ramp_down[2]-.092f)>1e-6f)
                throw std::runtime_error("Command slew audit failed");
            // No ChannelFactory, publisher, ReleaseMode or network access here.
            LowState synthetic{};
            synthetic.mode_machine(2);
            for (std::size_t i = 0; i < MotorCount; ++i) {
                auto& m = synthetic.motor_state()[mapping[i].index];
                m.mode(0);
                m.q(i < LegCount ? (i < 4 ? 0.56f : i < 8 ? 1.f : -2.75f) : 0.f);
                m.dq(0.f);
            }
            synthetic.crc() = crc32Core(reinterpret_cast<const uint32_t*>(&synthetic),
                                         (sizeof(LowState) >> 2) - 1);
            if (!valid_startup_state(synthetic, mapping))
                throw std::runtime_error("Synthetic LowState preflight rejected");
            auto bad = synthetic;
            bad.mode_machine(0);
            if (valid_startup_state(bad, mapping))
                throw std::runtime_error("Invalid LowState preflight accepted");

            Targets safe_guard{};
            safe_guard.active = true;
            for (std::size_t i = 0; i < MotorCount; ++i) {
                const auto& feedback = synthetic.motor_state()[mapping[i].index];
                safe_guard.motors[i].q = mapping[i].sign *
                    (feedback.q() - mapping[i].zero);
                safe_guard.motors[i].dq = 0.f;
                safe_guard.motors[i].kp = i < LegCount ? 55.f : 0.f;
                safe_guard.motors[i].kd = 2.f;
            }
            const auto safe_metrics = measure_field_safety(
                synthetic, mapping, safe_guard, nullptr);
            if (safe_metrics.warning() || safe_metrics.hard())
                throw std::runtime_error("Safe field-guard audit frame rejected");
            auto unsafe_guard = safe_guard;
            unsafe_guard.motors[0].q += 1.f;
            const auto unsafe_metrics = measure_field_safety(
                synthetic, mapping, unsafe_guard, &safe_guard);
            if (!unsafe_metrics.warning() || !unsafe_metrics.hard())
                throw std::runtime_error("Unsafe field-guard audit frame accepted");

            // ── Offline fault injection ──────────────────────────────────
            // Drives the same pure helpers the 50 Hz FSM tick uses
            // (evaluate_field_guard / remote predicates / slew_command),
            // so the audit cannot drift from the runtime thresholds.
            // No robot action: synthetic frames only, no DDS here.
            // (1) Safe envelope: 200 consecutive frames never trip or log.
            {
                FieldGuardCounts counts{};
                for (unsigned f = 0; f < 200; ++f) {
                    const auto m = measure_field_safety(
                        synthetic, mapping, safe_guard, &safe_guard);
                    const auto o = evaluate_field_guard(m, false, counts);
                    if (o.action != FieldGuardAction::Continue || o.log_metrics)
                        throw std::runtime_error(
                            "Safe field-guard injection tripped or logged");
                }
            }
            // (2) Warning via leg dq (5 < 6 < 8): frames 1-4 continue,
            // frame 5 requests one controlled Brake; while already braking
            // the same warning continues instead of re-requesting Brake.
            {
                auto warn_frame = synthetic;
                for (std::size_t i = 0; i < LegCount; ++i)
                    warn_frame.motor_state()[mapping[i].index].dq(
                        6.f * mapping[i].sign);
                FieldGuardCounts counts{};
                for (unsigned f = 1; f <= 5; ++f) {
                    const auto m = measure_field_safety(
                        warn_frame, mapping, safe_guard, &safe_guard);
                    const auto o = evaluate_field_guard(m, false, counts);
                    if (f < 5 && o.action != FieldGuardAction::Continue)
                        throw std::runtime_error(
                            "Warning injection tripped before 5 frames");
                    if (f == 5 && o.action != FieldGuardAction::SoftBrake)
                        throw std::runtime_error(
                            "Warning injection missed SoftBrake at frame 5");
                }
                const auto m = measure_field_safety(
                    warn_frame, mapping, safe_guard, &safe_guard);
                const auto o = evaluate_field_guard(m, true, counts);
                if (o.action != FieldGuardAction::Continue)
                    throw std::runtime_error(
                        "Braking-state warning re-requested Brake");
            }
            // (2b) Warning via predicted leg PD torque only
            // (kp 55 * 0.7 rad = 38.5 Nm, 35 < 38.5 < 50): same 5-frame trip.
            {
                auto pd_guard = safe_guard;
                pd_guard.motors[0].q += 0.7f;
                FieldGuardCounts counts{};
                for (unsigned f = 1; f <= 5; ++f) {
                    const auto m = measure_field_safety(
                        synthetic, mapping, pd_guard, &pd_guard);
                    const auto o = evaluate_field_guard(m, false, counts);
                    if (f < 5 && o.action != FieldGuardAction::Continue)
                        throw std::runtime_error(
                            "Predicted-PD warning injection tripped early");
                    if (f == 5 && o.action != FieldGuardAction::SoftBrake)
                        throw std::runtime_error(
                            "Predicted-PD warning injection missed frame 5");
                }
            }
            // (3) Hard via leg dq (9 > 8): frames 1-2 continue, frame 3
            // selects EmergencyDamping.
            {
                auto hard_frame = synthetic;
                for (std::size_t i = 0; i < LegCount; ++i)
                    hard_frame.motor_state()[mapping[i].index].dq(
                        9.f * mapping[i].sign);
                FieldGuardCounts counts{};
                for (unsigned f = 1; f <= 3; ++f) {
                    const auto m = measure_field_safety(
                        hard_frame, mapping, safe_guard, &safe_guard);
                    const auto o = evaluate_field_guard(m, false, counts);
                    if (f < 3 && o.action != FieldGuardAction::Continue)
                        throw std::runtime_error(
                            "Hard injection tripped before 3 frames");
                    if (f == 3 && o.action != FieldGuardAction::HardStop)
                        throw std::runtime_error(
                            "Hard injection missed EmergencyDamping at frame 3");
                }
            }
            // (3b) Hard via single-frame wheel target step only
            // (|16 - (-16)| = 32 > 30 rad/s per 20 ms, kd 0 removes the PD term).
            {
                auto step_guard = safe_guard;
                step_guard.motors[LegCount].dq = 16.f;
                step_guard.motors[LegCount].kd = 0.f;
                auto step_prev = step_guard;
                step_prev.motors[LegCount].dq = -16.f;
                FieldGuardCounts counts{};
                for (unsigned f = 1; f <= 3; ++f) {
                    const auto m = measure_field_safety(
                        synthetic, mapping, step_guard, &step_prev);
                    const auto o = evaluate_field_guard(m, false, counts);
                    if (f < 3 && o.action != FieldGuardAction::Continue)
                        throw std::runtime_error(
                            "Wheel-step hard injection tripped early");
                    if (f == 3 && o.action != FieldGuardAction::HardStop)
                        throw std::runtime_error(
                            "Wheel-step hard injection missed frame 3");
                }
            }
            // (4) Nonzero motorstate on one active axis follows the hard
            // counter (frame 3), and single-frame blips reset: 40
            // alternating fault/clean frames never trip.
            {
                auto fault_frame = synthetic;
                fault_frame.motor_state()[mapping[0].index].motorstate(1u);
                FieldGuardCounts counts{};
                for (unsigned f = 1; f <= 3; ++f) {
                    const auto m = measure_field_safety(
                        fault_frame, mapping, safe_guard, &safe_guard);
                    const auto o = evaluate_field_guard(m, false, counts);
                    if (f < 3 && o.action != FieldGuardAction::Continue)
                        throw std::runtime_error(
                            "Motorstate injection tripped before 3 frames");
                    if (f == 3 && o.action != FieldGuardAction::HardStop)
                        throw std::runtime_error(
                            "Motorstate injection missed frame 3");
                }
                FieldGuardCounts flicker{};
                for (unsigned f = 0; f < 40; ++f) {
                    const bool fault = f % 2 == 0;
                    const auto m = measure_field_safety(
                        fault ? fault_frame : synthetic, mapping, safe_guard,
                        &safe_guard);
                    const auto o = evaluate_field_guard(m, false, flicker);
                    if (o.action != FieldGuardAction::Continue)
                        throw std::runtime_error(
                            "Motorstate flicker injection tripped");
                }
            }
            // (5) Remote timeout: 200 ms of invalid embedded payload requests
            // a controlled Brake only in Handoff/Walk; recovery after the
            // Brake does not re-enter PolicyWalk (no FSM path exists from
            // Brake back to PolicyWalk; return is via ReturnStand/FixedStand
            // and a fresh gate-checked B).
            {
                const auto now = Clock::now();
                if (!remote_payload_timed_out(Clock::time_point{}, now))
                    throw std::runtime_error(
                        "Remote injection missed never-valid timeout");
                if (remote_payload_timed_out(
                        now - std::chrono::milliseconds(199), now))
                    throw std::runtime_error(
                        "Remote injection tripped before 200 ms");
                if (!remote_payload_timed_out(
                        now - std::chrono::milliseconds(201), now))
                    throw std::runtime_error(
                        "Remote injection missed 200 ms timeout");
                for (State s : {State::Passive, State::FixStand,
                                State::FixedStand, State::PolicyHandoff,
                                State::PolicyWalk, State::Brake,
                                State::ReturnStand, State::FixSquat,
                                State::EmergencyDamping
#if defined(AS2W_POLICY_GETUP1199)
                                , State::FixCrouchLite, State::PolicyGetup
#endif
                                }) {
                    const bool expected =
                        s == State::PolicyHandoff || s == State::PolicyWalk;
                    if (remote_timeout_requests_brake(s, true) != expected)
                        throw std::runtime_error(
                            "Remote timeout Brake request matrix wrong");
                    if (remote_timeout_requests_brake(s, false))
                        throw std::runtime_error(
                            "Fresh remote payload requested Brake");
                }
            }
            // (6) Full command ramp 0 -> motion endpoints -> 0: per-frame
            // slew bound, monotone approach, ~0.5 s in / ~0.25 s out.
            {
                const Vector3 endpoint{0.1f, 0.05f, 0.1f};
                Vector3 c{};
                unsigned frames = 0;
                while (c != endpoint && ++frames < 200) {
                    const auto prev = c;
                    c = slew_command(c, endpoint, 0.02f);
                    for (std::size_t i = 0; i < c.size(); ++i) {
                        const float bound =
                            kFieldSafety.command_accel[i] * 0.02f + 1e-9f;
                        if (std::abs(c[i] - prev[i]) > bound)
                            throw std::runtime_error(
                                "Slew injection exceeded accel bound");
                        if (std::abs(c[i]) < std::abs(prev[i]) - 1e-9f)
                            throw std::runtime_error(
                                "Slew injection not monotone toward endpoint");
                    }
                }
                if (c != endpoint || frames < 24 || frames > 26)
                    throw std::runtime_error(
                        "Slew injection accel ramp timing wrong");
                const float up_seconds = frames * 0.02f;
                if (up_seconds < 0.48f || up_seconds > 0.54f)
                    throw std::runtime_error("Slew accel duration wrong");
                unsigned down_frames = 0;
                while (c != Vector3{} && ++down_frames < 200) {
                    const auto prev = c;
                    c = slew_command(c, Vector3{}, 0.02f);
                    for (std::size_t i = 0; i < c.size(); ++i) {
                        const float bound =
                            kFieldSafety.command_decel[i] * 0.02f + 1e-9f;
                        if (std::abs(c[i] - prev[i]) > bound)
                            throw std::runtime_error(
                                "Slew injection exceeded decel bound");
                        if (std::abs(c[i]) > std::abs(prev[i]) + 1e-9f)
                            throw std::runtime_error(
                                "Slew injection not monotone toward zero");
                    }
                }
                if (c != Vector3{} || down_frames < 12 || down_frames > 14)
                    throw std::runtime_error(
                        "Slew injection decel ramp timing wrong");
                const float down_seconds = down_frames * 0.02f;
                if (down_seconds < 0.22f || down_seconds > 0.30f)
                    throw std::runtime_error("Slew decel duration wrong");
            }
            // (7) requested/applied consistency: the applied (slewed) command
            // is exactly what the policy consumes; a centered stick maps to
            // zero and the slew snaps to exact zero.
            {
                RemoteInput stick{};
                stick.axes[RemoteInput::AXIS_LY] = 0.85f;
                stick.axes[RemoteInput::AXIS_LX] = 0.85f;
                stick.axes[RemoteInput::AXIS_RX] = 0.85f;
                const auto requested = map_remote_command(stick, 0.1f);
                // P6 signs: vy=-lx*…, wz=-rx*… (leftward/CCW positive in
                // model coords), so full-forward/right stick maps to
                // {+0.1, -0.05, -0.1}.
                const Vector3 endpoint{0.1f, -0.05f, -0.1f};
                for (std::size_t i = 0; i < endpoint.size(); ++i)
                    if (std::abs(requested[i] - endpoint[i]) > 1e-6f)
                        throw std::runtime_error(
                            "Requested command endpoint mapping wrong");
                Vector3 applied{};
                unsigned frames = 0;
                while (applied != requested && ++frames < 200)
                    applied = slew_command(applied, requested, 0.02f);
                if (applied != requested)
                    throw std::runtime_error(
                        "Applied command never converged to requested");
                RemoteInput neutral{};
                const auto zero_desired = map_remote_command(neutral, 0.1f);
                if (zero_desired != Vector3{})
                    throw std::runtime_error(
                        "Centered stick did not map to zero command");
                unsigned release = 0;
                while (applied != Vector3{} && ++release < 200)
                    applied = slew_command(applied, zero_desired, 0.02f);
                if (applied != Vector3{})
                    throw std::runtime_error(
                        "Released stick never slews to exact zero");
#if defined(AS2W_R4000_JOYSTICK_CANDIDATE)
                RemoteInput r4000_stick{};
                r4000_stick.axes[RemoteInput::AXIS_LY] = .85f;
                r4000_stick.axes[RemoteInput::AXIS_LX] = .85f;
                r4000_stick.axes[RemoteInput::AXIS_RX] = .85f;
                const auto r4000_forward_right =
                    map_r1199_joystick_command(r4000_stick, r4000_vx_limit, r4000_wz_limit);
                if (r4000_forward_right != Vector3{r4000_vx_limit, 0.f, -r4000_wz_limit})
                    throw std::runtime_error("R4000 joystick forward/right mapping wrong");
                r4000_stick.axes[RemoteInput::AXIS_LY] = -.85f;
                r4000_stick.axes[RemoteInput::AXIS_RX] = -.85f;
                if (map_r1199_joystick_command(r4000_stick, r4000_vx_limit, r4000_wz_limit) !=
                    Vector3{-r4000_vx_limit, 0.f, r4000_wz_limit})
                    throw std::runtime_error("R4000 joystick back/left mapping wrong");
                if (map_r1199_joystick_command(RemoteInput{}, r4000_vx_limit, r4000_wz_limit) != Vector3{})
                    throw std::runtime_error("R4000 joystick neutral mapping wrong");
                std::cout << "R4000 JOYSTICK MAPPING PASS: LY +/-" << r4000_vx_limit
                          << " RX -/+" << r4000_wz_limit << " LX ignored\n";
#endif
#if defined(AS2W_R1199_JOYSTICK_CANDIDATE)
                RemoteInput r1199_stick{};
                r1199_stick.axes[RemoteInput::AXIS_LY] = .85f;
                r1199_stick.axes[RemoteInput::AXIS_LX] = .85f;
                r1199_stick.axes[RemoteInput::AXIS_RX] = .85f;
                const auto r1199_forward_right =
                    map_r1199_joystick_command(r1199_stick, r1199_vx_limit, r1199_wz_limit);
                if (r1199_forward_right != Vector3{r1199_vx_limit, 0.f, -r1199_wz_limit})
                    throw std::runtime_error("R1199 joystick forward/right mapping wrong");
                r1199_stick.axes[RemoteInput::AXIS_LY] = -.85f;
                r1199_stick.axes[RemoteInput::AXIS_RX] = -.85f;
                if (map_r1199_joystick_command(r1199_stick, r1199_vx_limit, r1199_wz_limit) !=
                    Vector3{-r1199_vx_limit, 0.f, r1199_wz_limit})
                    throw std::runtime_error("R1199 joystick back/left mapping wrong");
                if (map_r1199_joystick_command(RemoteInput{}, r1199_vx_limit, r1199_wz_limit) != Vector3{})
                    throw std::runtime_error("R1199 joystick neutral mapping wrong");
                std::cout << "R1199 JOYSTICK MAPPING PASS: LY +/-" << r1199_vx_limit
                          << " RX -/+" << r1199_wz_limit << " LX ignored\n";
#endif
                std::cout << "GUARD INJECTION PASS:"
                             " safe-envelope-200f warn@5->Brake hard@3->Emergency"
                             " motorstate=hard flicker-reset remote-timeout@200ms"
                             " no-auto-rewalk slew-0.5s-in/0.25s-out"
                             " applied==policy-command\n";
            }

            const auto t0 = Clock::time_point{} + std::chrono::seconds(10);
            WakeSequence wake(t0);
            wake.step(t0 + std::chrono::milliseconds(499), false);
            if (wake.phase != WakePhase::Neutral)
                throw std::runtime_error("Wake advanced before FOC feedback");
            wake.step(t0 + std::chrono::milliseconds(500), true);
            wake.step(t0 + std::chrono::milliseconds(699), true);
            if (wake.phase != WakePhase::Neutral)
                throw std::runtime_error("Wake advanced before 200ms FOC ack");
            wake.step(t0 + std::chrono::milliseconds(700), true);
            if (wake.phase != WakePhase::Ramp || wake.ramp_kd(t0 +
                    std::chrono::milliseconds(700), 3.f) != 0.f)
                throw std::runtime_error("Wake ramp start is wrong");
            wake.step(t0 + std::chrono::milliseconds(1200), true);
            if (wake.phase != WakePhase::Ramp ||
                std::abs(wake.ramp_kd(t0 + std::chrono::milliseconds(1200), 3.f)-1.5f)>1e-5f)
                throw std::runtime_error("Wake ramp midpoint is wrong");
            wake.step(t0 + std::chrono::milliseconds(1700), true);
            if (wake.phase != WakePhase::Ready)
                throw std::runtime_error("Wake did not reach ready");
            WakeSequence no_ack(t0);
            no_ack.step(t0 + std::chrono::milliseconds(2001), false);
            if (no_ack.phase != WakePhase::Fault)
                throw std::runtime_error("Wake missing FOC timeout fault");
            WakeSequence lost_mode(t0);
            lost_mode.step(t0 + std::chrono::milliseconds(500), true);
            lost_mode.step(t0 + std::chrono::milliseconds(700), true);
            lost_mode.step(t0 + std::chrono::milliseconds(701), false);
            if (lost_mode.phase != WakePhase::Fault)
                throw std::runtime_error("Wake missing FOC loss fault");

            LowCmd neutral{}, passive{};
            fill_zero_torque(neutral, synthetic, mapping);
            fill_passive(passive, synthetic, mapping, passive_kd);
            for (std::size_t slot = 0; slot < neutral.motor_cmd().size(); ++slot) {
                const auto& n = neutral.motor_cmd()[slot];
                const auto& p = passive.motor_cmd()[slot];
                if (slot < MotorCount) {
                    if (n.mode() != 1 || n.kp() != 0 || n.kd() != 0 ||
                        n.dq() != 0 || n.tau() != 0 ||
                        p.mode() != 1 || p.kp() != 0 || p.kd() != passive_kd ||
                        p.dq() != 0 || p.tau() != 0 || p.q() != n.q())
                        throw std::runtime_error("Startup frame audit failed at active slot");
                } else if (n.mode() != 0 || n.kp() != 0 || n.kd() != 0 ||
                           p.mode() != 0 || p.kp() != 0 || p.kd() != 0)
                    throw std::runtime_error("Startup frame audit failed at inactive slot");
            }
            dump_frame("neutral_zero_torque", neutral);
            dump_frame("passive_kd3", passive);
            if (probe_index >= 0) {
                LowCmd probe{};
                const float q0 = synthetic.motor_state()[mapping[probe_index].index].q();
                fill_probe(probe, synthetic, mapping, probe_index, q0,
                           probe_amplitude, 1.f, probe_kp, passive_kd);
                const auto& m = probe.motor_cmd()[mapping[probe_index].index];
                if (probe_index < static_cast<int>(LegCount)) {
                    if (m.kp() != probe_kp ||
                        std::abs(m.q() - q0 - mapping[probe_index].sign *
                            probe_amplitude) > 1e-5f)
                        throw std::runtime_error("Leg probe frame audit failed");
                } else if (m.kp() != 0.f ||
                           std::abs(m.dq() - mapping[probe_index].sign *
                               probe_amplitude) > 1e-5f)
                    throw std::runtime_error("Wheel probe frame audit failed");
                std::cout << "PROBE_AUDIT contract_index=" << probe_index
                          << " dds_slot=" << mapping[probe_index].index
                          << " sign=" << mapping[probe_index].sign << '\n';
                dump_frame("single_axis_probe_peak", probe);
            }
            std::cout << "AUDIT PASS: synthetic HG frames and wake timing;"
                         " command slew and field safety guards;"
                         " offline fault injection (warn/hard/motorstate/"
                         "remote-timeout/slew); firmware acceptance unknown\n";
            return 0;
        }

        std::cout << "WARNING: publishes LowCmd. ReleaseMode must already be done."
                     " X selects EmergencyDamping; SIGINT/SIGTERM stop the publisher.\n"
#if defined(AS2W_POLICY_GETUP1199)
                  << (getup_trial ?
                      "GETUP1199 TRIAL: from prone press B once = knee-open (~2.5s, body lifts ~3cm) -> "
                      "rise to stand (~3-5s) -> FixedStand hold (auto-squat by --stand-hold-seconds) "
                      "-> Y squat. A is disabled in this build. One B chain per session. X emergency.\n"
                      : "PASSIVE ONLY: B ignored (run with --getup-trial for the bounded chain).\n");
#else
                  << (enable_fsm_motion ? "FSM motion ENABLED.\n"
                      : stand_trial ? "STAND TRIAL: A reaches fixed PD stand, B locked, Y squats (15s timeout).\n"
#if defined(AS2W_R1199_FORWARD_CANDIDATE)
                      : zero_b_trial ? "R1199 FORWARD TRIAL: A fixed stand; B automatically requests forward 0.05m/s for 2s, then auto Brake/ReturnStand/Y squat; sticks ignored.\n"
#elif defined(AS2W_R4000_JOYSTICK_CANDIDATE)
                      : zero_b_trial ? "R4000 JOYSTICK TRIAL (training-contract 5 Hz leg filter + 0.9 rad/s slew): B accepts LY vx and RX yaw within the deploy.yaml speed envelope for max 120s; LX ignored; center sticks to stop, A brakes, Y squats, X emergency.\n"
#elif defined(AS2W_R1199_JOYSTICK_CANDIDATE)
                      : zero_b_trial ? (policy_lowpass_ms > 0.f
                          ? "R1199 FILTERED TRIAL: B accepts LY vx and RX yaw within the deploy.yaml speed envelope for max 120s; LX ignored; center sticks to stop, A brakes, Y squats, X emergency.\n"
                          : "R1199 JOYSTICK TRIAL: B accepts LY vx and RX yaw within the deploy.yaml speed envelope for max 60s; LX ignored; center sticks to stop, A brakes, Y squats, X emergency.\n")
#elif defined(AS2W_POLICY_R1199)
                      : zero_b_trial ? "R1199 ZERO-B TRIAL: A fixed stand; B enters forced zero speed for 2s, then auto Brake/ReturnStand/Y squat.\n"
#else
                      : zero_b_trial ? "ZERO-B TRIAL: A fixed stand; B enters forced zero speed, then auto Brake/ReturnStand/Y squat.\n"
#endif
                       : probe_index >= 0 ? "BOUNDED SINGLE-AXIS PROBE: A/B/Y ignored.\n"
                                           : "PASSIVE ONLY: A/B/Y ignored.\n");
#endif

#if defined(AS2W_R1199_JOYSTICK_CANDIDATE)
        if (zero_b_trial)
            std::cout << "R1199 joystick envelope: vx +/-" << r1199_vx_limit
                      << " m/s, wz +/-" << r1199_wz_limit
                      << " rad/s (deploy.yaml; CLI may only restrict)\n";
#endif
#if defined(AS2W_R4000_JOYSTICK_CANDIDATE)
        if (zero_b_trial)
            std::cout << "R4000 joystick envelope: vx +/-" << r4000_vx_limit
                      << " m/s, wz +/-" << r4000_wz_limit
                      << " rad/s (deploy.yaml; CLI may only restrict)\n";
#endif
#if defined(AS2W_POLICY_GETUP1199)
        if (getup_trial)
            std::cout << "GETUP1199 contract: obs 42 / act 12 legs; wheels position-"
                         "hold at the latched angle; staged rise 0.22/0.50 0.22/1.1 "
                         "1.45/1.2 authority 0.42; low-support latch 0.45s blend 0.85s; "
                         "integral stand; predictive guard; entry gate: prone, legs in "
                         "90% envelope, wheels quiet; success gate 2s; 15s cap; "
                         "one B chain per session\n";
#endif

        std::cout << "Type 'GO' and press Enter to start (nothing else proceeds).\n";
        std::cout << "FIELD_SAFETY_PROFILE command_accel="
                  << kFieldSafety.command_accel[0] << ','
                  << kFieldSafety.command_accel[1] << ','
                  << kFieldSafety.command_accel[2]
                  << " command_decel=" << kFieldSafety.command_decel[0] << ','
                  << kFieldSafety.command_decel[1] << ','
                  << kFieldSafety.command_decel[2]
                  << " remote_timeout_ms=" << RemoteCommandTimeout.count()
                  << " leg_dq=" << kFieldSafety.leg_dq_warn << '/'
                  << kFieldSafety.leg_dq_hard
                  << " wheel_dq=" << kFieldSafety.wheel_dq_warn << '/'
                  << kFieldSafety.wheel_dq_hard
                  << " leg_tau=" << kFieldSafety.leg_tau_warn << '/'
                  << kFieldSafety.leg_tau_hard
                  << " wheel_tau=" << kFieldSafety.wheel_tau_warn << '/'
                  << kFieldSafety.wheel_tau_hard
                  << " leg_pd=" << kFieldSafety.leg_pd_warn << '/'
                  << kFieldSafety.leg_pd_hard
                  << " wheel_pd=" << kFieldSafety.wheel_pd_warn << '/'
                  << kFieldSafety.wheel_pd_hard
                  << " leg_step=" << kFieldSafety.leg_target_step_warn << '/'
                  << kFieldSafety.leg_target_step_hard
                  << " wheel_step=" << kFieldSafety.wheel_target_step_warn << '/'
                  << kFieldSafety.wheel_target_step_hard
                  << " warn_frames=" << kFieldSafety.warn_frames
                  << " hard_frames=" << kFieldSafety.hard_frames
                  << " (units: dq rad/s, tau/pd Nm, step per 20 ms)\n";
        std::string dummy;
        if (!std::getline(std::cin, dummy) || dummy != "GO") {
            std::cerr << "Aborted: confirmation not given (stdin EOF or wrong input).\n";
            return 1;
        }

        std::signal(SIGINT, [](int) { g_abort.store(true); });
        std::signal(SIGTERM, [](int) { g_abort.store(true); });

        DebugLowCmdLog debug_lowcmd;
        std::ofstream debug_policy;
        unsigned debug_policy_lines = 0;
        if (debug_capture) {
            debug_lowcmd.start();
            debug_policy.open("debug_policy.csv", std::ios::out | std::ios::trunc);
            if (!debug_policy) throw std::runtime_error("Cannot open debug_policy.csv");
            debug_policy << std::setprecision(9)
                << "DEBUG_POLICY_SCHEMA,mono_ns,phase,tick,age_s,cmd_xyz,"
                   "remote_valid,remote_buttons,remote_axes_5,gyro_xyz,quat_wxyz,"
                   "imu_accel_xyz,"
                   "sensor_q_16,sensor_dq_16,obs_count,obs_values,state_count,"
                   "state_values,raw_action_16,wrapped_action_16,"
                   "requested_targets(q,dq,kp,kd)x16,applied_targets(q,dq,kp,kd)x16\n";
            std::cout << "DEBUG_CAPTURE enabled: 50Hz policy inputs/targets +"
                         " 500Hz final LowCmd; independent LowState monitor required\n";
        }
        std::cout << "POLICY_LOWPASS tau_ms=" << policy_lowpass_ms
                  << " wheels=" << policy_lowpass_wheels
                  << " (0=OFF; enabled only for isolated candidate builds)\n";

        // ── Shared state (g_abort is global for signal handler) ──
        std::atomic<State> g_state{State::Passive};
        std::mutex state_mutex;
        LowState latest_frame{};
        Clock::time_point latest_received{};
        unsigned latest_count = 0;
        RemoteInput latest_remote{};
        RemoteInput remote_snapshot{};
        Clock::time_point latest_remote_received{};
        Clock::time_point remote_snapshot_received{};
        std::atomic<bool> startup_ready{false};
        std::atomic<bool> startup_fault{false};
        std::atomic<bool> stand_trial_completed{false};
        std::atomic<bool> motion_cycle_completed{false};
        // zero-b-trial session bookkeeping (single B cycle, bounded chain)
        bool zero_b_cycle_used = false;
        Clock::time_point zero_b_cycle_started{};
        std::deque<std::pair<Clock::time_point, float>> leg_dq_history;

        // ── DDS ──
        unitree::robot::ChannelFactory::Instance()->Init(0, nic.c_str());
        unitree::robot::ChannelSubscriber<LowState> subscriber("rt/lowstate");
        subscriber.InitChannel([&](const void* message) {
            const auto* frame = static_cast<const LowState*>(message);
            if (!valid_startup_state(*frame, mapping)) return;
            std::lock_guard<std::mutex> lock(state_mutex);
            latest_frame = *frame;
            latest_received = Clock::now();
            ++latest_count;
            latest_remote = decode_remote(*frame);
            if (latest_remote.valid)
                latest_remote_received = latest_received;
        }, 1);
        unitree::robot::ChannelPublisher<LowCmd> publisher("rt/lowcmd");
        publisher.InitChannel();

        // Observe at least 500 ms of fresh, CRC-valid feedback after discovery.
        // No LowCmd is published during this phase. Require released motor
        // feedback (mode=0) before attempting the candidate wake sequence.
        {
            std::cout << "Observing released LowState on " << nic
                      << " for 500 ms (no LowCmd)...\n";
            auto t0 = Clock::now();
            Clock::time_point stable_since{};
            uint8_t stable_machine = 0;
            while (true) {
                bool ready = false;
                {
                    std::lock_guard<std::mutex> lock(state_mutex);
                    const auto now = Clock::now();
                    const bool fresh = latest_count > 0 &&
                        now - latest_received <= MaxStateAge;
                    bool released = fresh;
                    for (std::size_t i = 0; i < MotorCount && released; ++i)
                        released = latest_frame.motor_state()[mapping[i].index].mode() == 0;
                    if (released && latest_frame.mode_machine() == stable_machine) {
                        if (stable_since == Clock::time_point{}) stable_since = now;
                    } else {
                        stable_machine = latest_frame.mode_machine();
                        stable_since = released ? now : Clock::time_point{};
                    }
                    ready = released && latest_count >= 100 &&
                        now - stable_since >= StartupObserve;
                }
                if (ready) break;
                if (Clock::now() - t0 > std::chrono::seconds(5)) {
                    std::cerr << "ERROR: no stable released LowState within 5s. "
                              << "Aborting; no LowCmd published.\n";
                    return 1;
                }
                std::this_thread::sleep_for(std::chrono::milliseconds(10));
            }
            {
                std::lock_guard<std::mutex> lock(state_mutex);
                std::cout << "Released feedback stable. mode_machine="
                          << static_cast<int>(latest_frame.mode_machine())
                          << " tick=" << latest_frame.tick()
                          << " packets=" << latest_count << "\n";
            }
        }

        // ── Button edge detection ──
        uint16_t prev_buttons = 0;
        auto button_pressed = [&](uint16_t mask) {
            return (remote_snapshot.buttons & mask) && !(prev_buttons & mask);
        };
        auto update_buttons = [&]() { prev_buttons = remote_snapshot.buttons; };

        // ── Target buffer (writer thread reads, FSM thread writes) ──
        Targets current_targets{};
        PolicyTargetLowpass policy_lowpass(policy_lowpass_ms / 1000.f);
        std::mutex targets_mutex;

        // ── FixStand / FixSquat interpolation state ──
        struct InterpState {
            std::array<float, MotorCount> start{};
            std::array<float, MotorCount> target{};
            std::array<float, LegCount> start_kp{};
            int total_ticks = 0;
            int current_tick = 0;
            // Two-segment: seg1_frac of ticks at kp1, rest at kp2
            float seg1_frac = 0.6f;
            float kp1 = 20.f, kp2 = 55.f;
        } interp;
        auto fixed_pose = stand_pose;
        Clock::time_point fixed_stand_entered{};
        Clock::time_point policy_handoff_started{};
        Clock::time_point policy_walk_entered{};
        Clock::time_point brake_started{};
        Clock::time_point brake_stable_since{};
        Clock::time_point return_stand_started{};
        BrakeGoal brake_goal = BrakeGoal::FixedStand;
        Targets policy_handoff_start{};
        Targets brake_entry_targets{};
        Targets return_stand_start{};
        unsigned walk_command_log_tick = 0;
        unsigned policy_track_log_tick = 0;
        Vector3 slewed_command{};
        Targets safety_previous_targets{};
        State safety_previous_state = State::Passive;
        FieldGuardCounts guard_counts{};
#if defined(AS2W_POLICY_GETUP1199)
        // getup1199 chain state (getup1199实机部署与测试方案_20261113.md §5):
        // one B chain per session; FixCrouchLite latch; PolicyGetup gates.
        bool getup_cycle_used = false;
        bool getup_chain_started = false;
        Clock::time_point getup_wait_since{};
        Clock::time_point getup_prone_since{};
        Clock::time_point getup_started{};
        unsigned getup_success_frames = 0;
        struct {
            std::array<float, MotorCount> start{};
            std::array<float, 4> wheel_ref{};
            std::array<float, MotorCount> lite{};
            int total_ticks = 0, current_tick = 0;
        } getup_crouch;
        // Shared entry/success-gate helpers over the live frame.
        auto policy_order_state = [&]() {
            std::array<float, MotorCount> q{};
            std::lock_guard<std::mutex> lock(state_mutex);
            for (std::size_t i = 0; i < MotorCount; ++i)
                q[i] = mapping[i].sign *
                    (latest_frame.motor_state()[mapping[i].index].q() - mapping[i].zero);
            return q;
        };
        auto legs_in_envelope = [&](const std::array<float, MotorCount>& q) {
            for (std::size_t i = 0; i < LegCount; ++i) {
                const float lower = config.defaults[i] +
                    .90f * (config.angle_lower[i] - config.defaults[i]);
                const float upper = config.defaults[i] +
                    .90f * (config.angle_upper[i] - config.defaults[i]);
                if (q[i] < lower || q[i] > upper) return false;
            }
            return true;
        };
        auto live_wheel_dq_max = [&]() {
            float worst = 0.f;
            std::lock_guard<std::mutex> lock(state_mutex);
            for (std::size_t i = LegCount; i < MotorCount; ++i)
                worst = std::max(worst, std::abs(
                    latest_frame.motor_state()[mapping[i].index].dq()));
            return worst;
        };
#endif
#if defined(AS2W_POLICY_R1199) || defined(AS2W_POLICY_R4000)
        // Per-policy-frame diagnostics (50 Hz) to a LOCAL file so the hdc
        // stdout pipe can never block the publish loop. Captures the full
        // chain raw ONNX -> wrapped action -> final targets -> wrapper
        // internals for splitting inference/wrapper/hardware issues; the
        // actual joint side stays in the 10 ms low_capture_fast.log and is
        // aligned via the LowState tick.
        std::ofstream policy_diag{"policy_diag.log"};
        unsigned policy_diag_lines = 0;
        if (policy_diag.is_open())
            policy_diag << "POLICY_DIAG_SCHEMA,phase,t_since_walk_s,cmd_vx,cmd_vy,cmd_wz,tick,"
                           "raw_0..15,wrapped_0..15,target_q_0..11,target_dq_12..15,"
                           "stand_bias_0..11,bias_scale,hold_frames\n";
        auto log_policy_diag = [&](const char* phase, const Vector3& cmd,
                                   const Targets& targets) {
            if (!policy_diag.is_open() || !targets.active) return;
            uint32_t diag_tick = 0;
            { std::lock_guard<std::mutex> lock(state_mutex);
              diag_tick = latest_frame.tick(); }
            const float since_walk = policy_walk_entered != Clock::time_point{}
                ? std::chrono::duration<float>(Clock::now() -
                    policy_walk_entered).count() : 0.f;
            policy_diag << "POLICY_DIAG," << phase << ',' << since_walk
                        << ',' << cmd[0] << ',' << cmd[1] << ',' << cmd[2]
                        << ',' << diag_tick;
            for (auto v : controller.last_raw_action()) policy_diag << ',' << v;
            for (auto v : targets.action) policy_diag << ',' << v;
            for (std::size_t i = 0; i < LegCount; ++i)
                policy_diag << ',' << targets.motors[i].q;
            for (std::size_t i = LegCount; i < MotorCount; ++i)
                policy_diag << ',' << targets.motors[i].dq;
            for (std::size_t i = 0; i < LegCount; ++i)
                policy_diag << ',' << controller.last_stand_bias()[i];
            policy_diag << ',' << controller.last_bias_scale()
                        << ',' << controller.hold_frames() << '\n';
            if (++policy_diag_lines % 250 == 0) policy_diag.flush();
        };
#endif
        auto log_debug_policy = [&](const char* phase, const SensorState& sensors,
                                    uint32_t sensor_tick,
                                    const std::array<float, 3>& imu_accel,
                                    float age, const Vector3& cmd,
                                    const Targets& requested,
                                    const Targets& applied) {
            if (!debug_capture || !requested.active) return;
            const auto mono_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
                Clock::now().time_since_epoch()).count();
            debug_policy << "DEBUG_POLICY," << mono_ns << ',' << phase
                         << ',' << sensor_tick << ',' << age;
            for (auto v : cmd) debug_policy << ',' << v;
            debug_policy << ',' << remote_snapshot.valid
                         << ',' << remote_snapshot.buttons;
            for (auto v : remote_snapshot.axes) debug_policy << ',' << v;
            for (auto v : sensors.gyro) debug_policy << ',' << v;
            for (auto v : sensors.body_to_world_wxyz) debug_policy << ',' << v;
            for (auto v : imu_accel) debug_policy << ',' << v;
            for (auto v : sensors.position) debug_policy << ',' << v;
            for (auto v : sensors.velocity) debug_policy << ',' << v;
            const auto& obs = controller.last_observation();
            debug_policy << ',' << obs.size();
            for (auto v : obs) debug_policy << ',' << v;
#if !defined(AS2W_POLICY_R1199) && !defined(AS2W_POLICY_R4000) && \
    !defined(AS2W_POLICY_GETUP1199) && \
    !defined(AS2W_POLICY_R249) && !defined(AS2W_POLICY_R270) && \
    !defined(AS2W_POLICY_R284)
            const auto& state_input = controller.last_state_input();
            debug_policy << ',' << state_input.size();
            for (auto v : state_input) debug_policy << ',' << v;
#else
            debug_policy << ",0";
#endif
            for (auto v : controller.last_raw_action()) debug_policy << ',' << v;
            for (auto v : requested.action) debug_policy << ',' << v;
            for (const auto& m : requested.motors)
                debug_policy << ',' << m.q << ',' << m.dq << ',' << m.kp << ',' << m.kd;
            for (const auto& m : applied.motors)
                debug_policy << ',' << m.q << ',' << m.dq << ',' << m.kp << ',' << m.kd;
            debug_policy << '\n';
            if (++debug_policy_lines % 250 == 0) debug_policy.flush();
        };

        auto start_squat = [&](const char* source) {
            // The first squat target is derived from the last published target.
            // This keeps q and kp continuous at the state boundary.
            {
                std::lock_guard<std::mutex> tlock(targets_mutex);
                for (std::size_t i = 0; i < MotorCount; ++i) {
                    interp.start[i] = current_targets.motors[i].q;
                    if (i < LegCount)
                        interp.start_kp[i] = current_targets.motors[i].kp;
                }
            }
            interp.target = prone_pose;
            interp.total_ticks = int(squat_sec / 0.02f);
            interp.current_tick = 0;
            interp.seg1_frac = 1.5f / 4.f;
            interp.kp1 = 35.f;
            interp.kp2 = 20.f;
            std::cout << '[' << source << "] → FixSquat\n";
            g_state.store(State::FixSquat);
        };

        auto start_brake = [&](const char* source, BrakeGoal goal) {
            brake_goal = goal;
            {
                std::lock_guard<std::mutex> tlock(targets_mutex);
                brake_entry_targets = current_targets;
            }
            if (policy_lowpass_ms > 0.f)
                policy_lowpass.reset(brake_entry_targets);
            brake_started = Clock::now();
            brake_stable_since = Clock::time_point{};
            slewed_command = {};
            std::cout << '[' << source << "] → Brake\n";
            g_state.store(State::Brake);
        };

        // ── Safety checks ──
        auto check_safety = [&]() -> bool {
            // Returns true if safe to continue, false if emergency
            std::lock_guard<std::mutex> lock(state_mutex);
            const auto age = std::chrono::duration<float, std::milli>(
                Clock::now() - latest_received).count();
            if (latest_count == 0 || age > 50.f) {
                std::cout << "SAFETY: LowState age " << age << "ms\n";
                return false;
            }
            const auto& q = latest_frame.imu_state().quaternion();
            const float up = 1.f - 2.f * (q[1]*q[1] + q[2]*q[2]);
            if (up < -0.2f) {
                std::cout << "SAFETY: upright " << up << "\n";
                return false;
            }
            return true;
        };

        // ── 500 Hz writer thread ──
        // Candidate HG startup: zero-torque FOC request, wait for mode feedback,
        // then ramp kd. This has NOT been validated on AS2-W firmware.
        std::thread writer([&] {
            LowCmd cmd{};
            Clock::time_point next = Clock::now();
            WakeSequence wake(next);
            unsigned publish_count = 0;
            Clock::time_point probe_ready_at{};
            float probe_raw_anchor = 0.f;
            unsigned probe_report_tick = 0;
            while (!g_abort.load()) {
                next += std::chrono::milliseconds(2);
                std::this_thread::sleep_until(next);
                LowState frame{};
                Clock::time_point received{};
                {
                    std::lock_guard<std::mutex> lock(state_mutex);
                    frame = latest_frame;
                    received = latest_received;
                }
                const auto now = Clock::now();
                if (received == Clock::time_point{} ||
                    now - received > MaxStateAge ||
                    !valid_startup_state(frame, mapping)) {
                    std::cerr << "STARTUP FAULT: stale/invalid LowState; stop publisher"
                              << " after " << publish_count << " frames\n";
                    startup_fault.store(true);
                    g_abort.store(true);
                    break;
                }
                bool all_foc = true;
                for (std::size_t i = 0; i < MotorCount; ++i)
                    all_foc &= frame.motor_state()[mapping[i].index].mode() == 1;
                const auto old_phase = wake.phase;
                wake.step(now, all_foc);
                if (wake.phase == WakePhase::Fault ||
                    (wake.phase == WakePhase::Ready && !all_foc)) {
                    std::cerr << "STARTUP FAULT: FOC acknowledgement timeout/loss; "
                              << publish_count << " frames sent\n";
                    startup_fault.store(true);
                    g_abort.store(true);
                    break;
                }
                if (old_phase == WakePhase::Neutral && wake.phase == WakePhase::Ramp)
                    std::cout << "STARTUP: 16-axis FOC feedback stable;"
                                 " begin passive kd 0->" << passive_kd << " ramp\n";
                if (wake.phase == WakePhase::Neutral) {
                    fill_zero_torque(cmd, frame, mapping);
                } else if (wake.phase == WakePhase::Ramp) {
                    fill_passive(cmd, frame, mapping, wake.ramp_kd(now, passive_kd));
                } else if (probe_index >= 0) {
                    // Timed 0.5s Passive → 0.5s ramp → 0.5s hold →
                    // 0.5s return → 1s Passive. One axis, one invocation.
                    if (probe_ready_at == Clock::time_point{}) {
                        probe_ready_at = now;
                        probe_raw_anchor = frame.motor_state()[
                            mapping[probe_index].index].q();
                        std::cout << "PROBE ready contract_index=" << probe_index
                                  << " dds_slot=" << mapping[probe_index].index
                                  << " raw_q0=" << probe_raw_anchor
                                  << " model_amplitude=" << probe_amplitude
                                  << " kp=" << probe_kp << '\n';
                    }
                    const float elapsed = std::chrono::duration<float>(
                        now - probe_ready_at).count();
                    float scale = 0.f;
                    if (elapsed >= 0.5f && elapsed < 1.f)
                        scale = 2.f * (elapsed - 0.5f);
                    else if (elapsed >= 1.f && elapsed < 1.5f)
                        scale = 1.f;
                    else if (elapsed >= 1.5f && elapsed < 2.f)
                        scale = 2.f * (2.f - elapsed);
                    if (g_state.load() == State::EmergencyDamping) {
                        fill_passive(cmd, frame, mapping, passive_kd);
                        std::cout << "PROBE abort: X/safety -> Passive\n";
                        g_abort.store(true);
                    } else if (scale > 0.f) {
                        fill_probe(cmd, frame, mapping, probe_index,
                                   probe_raw_anchor, probe_amplitude,
                                   scale, probe_kp, passive_kd);
                    } else {
                        fill_passive(cmd, frame, mapping, passive_kd);
                    }
                    const auto& feedback = frame.motor_state()[
                        mapping[probe_index].index];
                    if (probe_index < static_cast<int>(LegCount) &&
                        std::abs(feedback.q() - probe_raw_anchor) > 0.08f) {
                        std::cerr << "PROBE FAULT: leg displacement >0.08 rad\n";
                        startup_fault.store(true);
                        g_abort.store(true);
                        break;
                    }
                    if (probe_index >= static_cast<int>(LegCount) &&
                        std::abs(feedback.dq()) > 2.f) {
                        std::cerr << "PROBE FAULT: wheel speed >2 rad/s\n";
                        startup_fault.store(true);
                        g_abort.store(true);
                        break;
                    }
                    if (++probe_report_tick % 100 == 0)
                        std::cout << "PROBE sample t=" << elapsed
                                  << " scale=" << scale
                                  << " cmd_q=" << cmd.motor_cmd()[mapping[probe_index].index].q()
                                  << " cmd_dq=" << cmd.motor_cmd()[mapping[probe_index].index].dq()
                                  << " feedback_q=" << feedback.q()
                                  << " feedback_dq=" << feedback.dq() << '\n';
                    if (elapsed >= 3.f) {
                        std::cout << "PROBE bounded duration complete\n";
                        g_abort.store(true);
                    }
                } else {
                    const auto st = g_state.load();
                    std::lock_guard<std::mutex> tlock(targets_mutex);
                    if (st == State::FixedStand || st == State::PolicyHandoff ||
                        st == State::PolicyWalk || st == State::Brake ||
                        st == State::ReturnStand || st == State::FixStand ||
                        st == State::FixSquat
#if defined(AS2W_POLICY_GETUP1199)
                        || st == State::FixCrouchLite || st == State::PolicyGetup
#endif
                        ) {
                        fill_targets(cmd, frame, mapping, current_targets);
                    } else {
                        fill_passive(cmd, frame, mapping, passive_kd);
                    }
                }
                finish(cmd);
                if (!publisher.Write(cmd)) {
                    std::cerr << "STARTUP FAULT: DDS Write returned false\n";
                    startup_fault.store(true);
                    g_abort.store(true);
                    break;
                }
                if (debug_capture)
                    debug_lowcmd.push(cmd, frame, mapping, g_state.load());
                ++publish_count;
                if (wake.phase == WakePhase::Ready && !startup_ready.exchange(true))
                    std::cout << "STARTUP: Passive ready after " << publish_count
                              << " frames\n";
                // A delayed scheduler tick must not cause a burst of catch-up
                // LowCmd writes at sub-2ms spacing.
                if (Clock::now() > next + std::chrono::milliseconds(2))
                    next = Clock::now();
            }
        });

        // ── 50 Hz FSM thread ──
        auto fsm_tick = [&]() {
            {
                std::lock_guard<std::mutex> lock(state_mutex);
                remote_snapshot = latest_remote;
                remote_snapshot_received = latest_remote_received;
            }
            if (!startup_ready.load() &&
                button_pressed(RemoteInput::BTN_X)) {
                std::cout << "[Startup] X → EmergencyDamping; stop publisher\n";
                g_state.store(State::EmergencyDamping);
                g_abort.store(true);
                update_buttons();
                return;
            }
            if (!startup_ready.load()) {
                update_buttons();
                return;
            }
            const auto st = g_state.load();

            // Safety check (all states)
            if (!check_safety()) {
                if (st != State::EmergencyDamping) {
                    std::cout << "[" << state_name(st) << "] → EmergencyDamping (safety)\n";
                    g_state.store(State::EmergencyDamping);
                }
                update_buttons();
                return;
            }

            // X button: any state → EmergencyDamping
            if (button_pressed(RemoteInput::BTN_X)) {
                std::cout << "[" << state_name(st) << "] → EmergencyDamping (X key)\n";
                g_state.store(State::EmergencyDamping);
                update_buttons();
                return;
            }

            // Best-effort remote timeout. The HG LowState payload has no
            // exposed controller sequence/timestamp, so this detects invalid
            // or absent embedded frames; it cannot distinguish a firmware-
            // repeated valid payload from a deliberately held constant stick.
            const auto now = Clock::now();
            const bool remote_timed_out =
                remote_payload_timed_out(remote_snapshot_received, now);
            if (remote_timeout_requests_brake(st, remote_timed_out)) {
                std::cout << "REMOTE_TIMEOUT age_ms="
                          << (remote_snapshot_received == Clock::time_point{}
                              ? -1.f : std::chrono::duration<float, std::milli>(
                                    now - remote_snapshot_received).count())
                          << " → controlled Brake\n";
                start_brake("RemoteTimeout", BrakeGoal::FixedStand);
                update_buttons();
                return;
            }

            // Policy-only dynamic envelope. Known FixStand/FixSquat
            // trajectories keep their separately validated timing; the new
            // guards supervise the learned controller and its braking phase.
            const bool policy_safety_state = st == State::PolicyHandoff ||
                st == State::PolicyWalk || st == State::Brake
#if defined(AS2W_POLICY_GETUP1199)
                || st == State::FixCrouchLite || st == State::PolicyGetup
#endif
                ;
            if (policy_safety_state) {
                LowState safety_frame{};
                Targets safety_targets{};
                {
                    std::lock_guard<std::mutex> lock(state_mutex);
                    safety_frame = latest_frame;
                }
                {
                    std::lock_guard<std::mutex> lock(targets_mutex);
                    safety_targets = current_targets;
                }
                const Targets* previous = safety_previous_state == st &&
                    safety_previous_targets.active ? &safety_previous_targets : nullptr;
                const auto metrics = measure_field_safety(
                    safety_frame, mapping, safety_targets, previous);
                safety_previous_targets = safety_targets;
                safety_previous_state = st;
                const auto outcome = evaluate_field_guard(
                    metrics, st == State::Brake, guard_counts);
                if (outcome.log_metrics)
                    print_field_safety(outcome.log_level, st, metrics,
                                       outcome.log_count);
                if (outcome.action == FieldGuardAction::HardStop) {
                    std::cout << '[' << state_name(st)
                              << "] → EmergencyDamping (field hard limit)\n";
                    g_state.store(State::EmergencyDamping);
                    update_buttons();
                    return;
                }
                if (outcome.action == FieldGuardAction::SoftBrake) {
                    print_field_safety("SOFT_TRIP", st, metrics,
                                       guard_counts.warn);
                    start_brake("FieldSafety", BrakeGoal::FixedStand);
                    update_buttons();
                    return;
                }
            } else {
                safety_previous_targets = {};
                safety_previous_state = st;
                guard_counts = {};
            }

            // First reviewed robot test is Passive only. A/B/Y require an
            // explicit separately reviewed motion-enabled build and CLI flag.
            if (!enable_fsm_motion && !stand_trial && !zero_b_trial
#if defined(AS2W_POLICY_GETUP1199)
                && !getup_trial
#endif
            ) {
                update_buttons();
                return;
            }

            switch (st) {
            case State::Passive:
                if (stand_trial_completed.load()) break;
#if defined(AS2W_POLICY_GETUP1199)
                // getup1199 build: A (FixStand) is a stand-state button and
                // is disabled here; B from prone starts the bounded chain.
                if (button_pressed(RemoteInput::BTN_A)) {
                    std::cout << "[Passive] A ignored: getup build has no "
                                 "FixStand entry\n";
                } else if (button_pressed(RemoteInput::BTN_B)) {
                    if (!getup_trial) {
                        std::cout << "[Passive] B rejected: no --getup-trial\n";
                        break;
                    }
                    if (getup_cycle_used) {
                        std::cout << "[Passive] B rejected: one getup chain "
                                     "per session\n";
                        break;
                    }
                    const auto q = policy_order_state();
                    float up = 1.f;
                    {
                        std::lock_guard<std::mutex> lock(state_mutex);
                        const auto& quat = latest_frame.imu_state().quaternion();
                        up = 1.f - 2.f * (quat[1]*quat[1] + quat[2]*quat[2]);
                    }
                    active_policy::Legs legs{};
                    for (std::size_t i = 0; i < LegCount; ++i) legs[i] = q[i];
                    const float h_est =
                        active_policy::Controller::height_estimate(legs);
                    const float wheel_dq = live_wheel_dq_max();
                    // Prone entry: low FK height (not standing) AND level
                    // belly-down (not side/inverted) AND quiet wheels.
                    const bool prone_ok =
                        h_est < config.entry_max_height_est &&
                        up > config.entry_min_up_z &&
                        wheel_dq < config.entry_wheel_quiet_dq;
                    if (!prone_ok) {
                        std::cout << "[Passive] B rejected: entry gate "
                                     "h_est=" << h_est << " (max "
                                  << config.entry_max_height_est << ") up="
                                  << up << " (min " << config.entry_min_up_z
                                  << ") wheel_dq=" << wheel_dq << " (max "
                                  << config.entry_wheel_quiet_dq << ")\n";
                        break;
                    }
                    getup_cycle_used = true;
                    if (legs_in_envelope(q)) {
                        controller.arm();
                        getup_started = Clock::now();
                        getup_success_frames = 0;
                        std::cout << "[Passive] → PolicyGetup (B; already in "
                                     "envelope, knee-open skipped)\n";
                        g_state.store(State::PolicyGetup);
                    } else {
                        getup_crouch.start = q;
                        for (std::size_t i = 0; i < 4; ++i)
                            getup_crouch.wheel_ref[i] = q[LegCount + i];
                        // FixCrouch-lite targets (sim-validated 3 seeds,
                        // logs/20261113_getup1199_deploy_precheck exp 6):
                        // open calves to -2.43, pull hips to +-0.50, keep
                        // thighs; all inside the 90% command envelope.
                        for (std::size_t i = 0; i < LegCount; ++i) {
                            float target = q[i];
                            if (i < 4)
                                target = std::clamp(q[i], -.50f, .50f);
                            else if (i >= 8)
                                target = -2.43f;
                            const float lower = config.defaults[i] +
                                .90f * (config.angle_lower[i] - config.defaults[i]);
                            const float upper = config.defaults[i] +
                                .90f * (config.angle_upper[i] - config.defaults[i]);
                            getup_crouch.lite[i] =
                                std::clamp(target, lower + .06f, upper - .06f);
                        }
                        getup_crouch.total_ticks = int(2.5f / 0.02f);
                        getup_crouch.current_tick = 0;
                        std::cout << "[Passive] → FixCrouchLite (B; "
                                     "knee-open 2.5s)\n";
                        g_state.store(State::FixCrouchLite);
                    }
                }
#else
                if (button_pressed(RemoteInput::BTN_A)) {
                    fixed_pose = stand_pose;
                    // Snapshot current pose for FixStand interpolation
                    Targets passive_start{};
                    passive_start.active = true;
                    {
                        std::lock_guard<std::mutex> lock(state_mutex);
                        for (std::size_t i = 0; i < MotorCount; ++i) {
                            interp.start[i] = mapping[i].sign *
                                (latest_frame.motor_state()[mapping[i].index].q() - mapping[i].zero);
                            if (i < LegCount) {
                                passive_start.motors[i].q = interp.start[i];
                                passive_start.motors[i].kd = passive_kd;
                            } else {
                                passive_start.motors[i].dq = 0.f;
                                passive_start.motors[i].kd = passive_kd;
                            }
                        }
                    }
                    { std::lock_guard<std::mutex> tlock(targets_mutex);
                      current_targets = passive_start; }
                    interp.target = stand_pose;
                    interp.total_ticks = int(interp_sec / 0.02f);
                    interp.current_tick = 0;
                    interp.seg1_frac = 0.6f;
                    interp.kp1 = 20.f; interp.kp2 = 55.f;
                    std::cout << "[Passive] → FixStand (A)\n";
                    g_state.store(State::FixStand);
                }
#endif
                break;

#if defined(AS2W_POLICY_GETUP1199)
            case State::FixCrouchLite: {
                getup_chain_started = true;
                getup_crouch.current_tick++;
                const int n = getup_crouch.total_ticks;
                float a = std::min(1.f, float(getup_crouch.current_tick) / n);
                a = a * a * (3.f - 2.f * a);  // smoothstep (probe profile)
                Targets t{};
                t.active = true;
                for (std::size_t j = 0; j < LegCount; ++j) {
                    t.motors[j].q = getup_crouch.start[j] +
                        a * (getup_crouch.lite[j] - getup_crouch.start[j]);
                    t.motors[j].kp = 55.f;
                    t.motors[j].kd = 2.f;
                }
                for (std::size_t j = 0; j < 4; ++j) {
                    t.motors[LegCount + j].q = getup_crouch.wheel_ref[j];
                    t.motors[LegCount + j].kp = 25.f;
                    t.motors[LegCount + j].kd = 4.f;
                }
                { std::lock_guard<std::mutex> tlock(targets_mutex);
                  current_targets = t; }
                if (getup_crouch.current_tick >= n) {
                    const auto q = policy_order_state();
                    if (legs_in_envelope(q)) {
                        controller.arm();
                        getup_started = Clock::now();
                        getup_success_frames = 0;
                        std::cout << "[FixCrouchLite] envelope reached → "
                                     "PolicyGetup\n";
                        g_state.store(State::PolicyGetup);
                    } else {
                        std::cout << "[FixCrouchLite] envelope NOT reached → "
                                     "Passive (no rise attempt)\n";
                        g_state.store(State::Passive);
                    }
                }
                break;
            }

            case State::PolicyGetup: {
                getup_chain_started = true;
                SensorState sensors;
                Clock::time_point received{};
                uint32_t sensor_tick = 0;
                std::array<float, 3> imu_accel{};
                {
                    std::lock_guard<std::mutex> lock(state_mutex);
                    received = latest_received;
                    sensor_tick = latest_frame.tick();
                    const auto& imu = latest_frame.imu_state();
                    imu_accel = imu.accelerometer();
                    std::copy(imu.gyroscope().begin(), imu.gyroscope().end(),
                              sensors.gyro.begin());
                    std::copy(imu.quaternion().begin(), imu.quaternion().end(),
                              sensors.body_to_world_wxyz.begin());
                    for (std::size_t i = 0; i < MotorCount; ++i) {
                        sensors.position[i] = mapping[i].sign *
                            (latest_frame.motor_state()[mapping[i].index].q() - mapping[i].zero);
                        sensors.velocity[i] = mapping[i].sign *
                            (latest_frame.motor_state()[mapping[i].index].dq());
                    }
                }
                const float age = std::chrono::duration<float>(
                    Clock::now() - received).count();
                const Vector3 zero_cmd{};
                auto targets = controller.step(sensors, zero_cmd, age);
                if (!targets.active) {
                    std::cout << "[PolicyGetup] controller disarmed → "
                                 "EmergencyDamping\n";
                    g_state.store(State::EmergencyDamping);
                    break;
                }
                { std::lock_guard<std::mutex> tlock(targets_mutex);
                  current_targets = targets; }
                log_debug_policy("GETUP", sensors, sensor_tick, imu_accel,
                                 age, zero_cmd, targets, targets);
                // Success gate on the deployment estimators (validated
                // against the training evaluator; the same thresholds the
                // wrapper's latch uses, plus the joint-error bound).
                active_policy::Legs legs{};
                for (std::size_t i = 0; i < LegCount; ++i)
                    legs[i] = sensors.position[i];
                const float h_est =
                    active_policy::Controller::height_estimate(legs);
                const float up = controller.last_up();
                float joint_error = 0.f;
                for (std::size_t i = 0; i < LegCount; ++i)
                    joint_error = std::max(joint_error,
                        std::abs(sensors.position[i] - config.defaults[i]));
                const float spin = std::sqrt(
                    sensors.gyro[0]*sensors.gyro[0] +
                    sensors.gyro[1]*sensors.gyro[1] +
                    sensors.gyro[2]*sensors.gyro[2]);
                float wheel_dq = 0.f;
                for (std::size_t i = LegCount; i < MotorCount; ++i)
                    wheel_dq = std::max(wheel_dq, std::abs(sensors.velocity[i]));
                const bool gate = h_est >= config.success_height &&
                    up >= config.success_up &&
                    joint_error <= config.success_joint_error &&
                    spin <= config.success_spin &&
                    wheel_dq < config.entry_wheel_quiet_dq;
                getup_success_frames = gate ? getup_success_frames + 1 : 0;
                if (++policy_track_log_tick % 10 == 0)
                    std::cout << "GETUP_GATE h_est=" << h_est << " up=" << up
                              << " jerr=" << joint_error << " spin=" << spin
                              << " wheel_dq=" << wheel_dq
                              << " hold=" << getup_success_frames << " blend="
                              << controller.blend() << '\n';
                const auto elapsed = std::chrono::duration<float>(
                    Clock::now() - getup_started).count();
                if (getup_success_frames >=
                        unsigned(config.success_hold_s / 0.02f + 0.5f)) {
                    // Hold the posture the policy just supported (Brake
                    // precedent) instead of snapping to the default stand.
                    for (std::size_t i = 0; i < LegCount; ++i)
                        fixed_pose[i] = targets.motors[i].q;
                    controller.stop();
                    fixed_stand_entered = Clock::now();
                    leg_dq_history.clear();
                    std::cout << "[PolicyGetup] → FixedStand (success; "
                                 "hold=" << getup_success_frames
                              << " frames h_est=" << h_est << ")\n";
                    g_state.store(State::FixedStand);
                } else if (elapsed >= config.getup_cap_s) {
                    controller.stop();
                    std::cout << "FIELD_GETUP_TIMEOUT elapsed=" << elapsed
                              << " h_est=" << h_est << " up=" << up
                              << " → Passive\n";
                    g_state.store(State::Passive);
                }
                break;
            }
#endif

            case State::FixStand: {
                const int n_a = int(interp.total_ticks * interp.seg1_frac);
                const int n_b = interp.total_ticks - n_a;
                interp.current_tick++;
                Targets t{};
                t.active = true;
                if (interp.current_tick <= n_a) {
                    // B1: pre-load (slow, kp1)
                    float a = float(interp.current_tick) / n_a;
                    // Pre-load pose: thighs +0.25 from start
                    auto preload = interp.start;
                    for (std::size_t j = 4; j < 8; ++j)
                        preload[j] = interp.start[j] + 0.25f;
                    for (std::size_t j = 0; j < LegCount; ++j) {
                        t.motors[j].q = interp.start[j] + a * (preload[j] - interp.start[j]);
                        t.motors[j].kp = interp.kp1;
                        t.motors[j].kd = 3.f;
                    }
                } else if (interp.current_tick <= interp.total_ticks) {
                    // B2: explosive lift (fast, kp2)
                    // Snapshot actual position at B2 start
                    if (interp.current_tick == n_a + 1) {
                        std::lock_guard<std::mutex> lock(state_mutex);
                        for (std::size_t i = 0; i < MotorCount; ++i) {
                            interp.start[i] = mapping[i].sign *
                                (latest_frame.motor_state()[mapping[i].index].q() - mapping[i].zero);
                        }
                    }
                    float a = float(interp.current_tick - n_a) / n_b;
                    for (std::size_t j = 0; j < LegCount; ++j) {
                        t.motors[j].q = interp.start[j] + a * (interp.target[j] - interp.start[j]);
                        t.motors[j].kp = interp.kp2;
                        t.motors[j].kd = 2.f;
                    }
                }
                for (std::size_t j = LegCount; j < MotorCount; ++j) {
                    t.motors[j].dq = 0.f;
                    t.motors[j].kp = 0.f;
                    t.motors[j].kd = 2.f;
                }
                { std::lock_guard<std::mutex> tlock(targets_mutex); current_targets = t; }

                if (button_pressed(RemoteInput::BTN_Y)) {
                    start_squat("FixStand");
                } else if (interp.current_tick >= interp.total_ticks) {
                    // A ends at fixed PD. B alone may arm R214 later.
                    fixed_stand_entered = Clock::now();
                    leg_dq_history.clear();
                    std::cout << "[FixStand] → FixedStand (PD hold; B required for R214)\n";
                    g_state.store(State::FixedStand);
                }
                break;
            }

            case State::FixedStand: {
                const auto fixed = fixed_stand_targets(fixed_pose);
                { std::lock_guard<std::mutex> tlock(targets_mutex); current_targets = fixed; }
                {
                    std::lock_guard<std::mutex> lock(state_mutex);
                    float max_leg_dq = 0.f;
                    for (std::size_t i = 0; i < LegCount; ++i)
                        max_leg_dq = std::max(max_leg_dq, std::abs(
                            latest_frame.motor_state()[mapping[i].index].dq()));
                    leg_dq_history.emplace_back(Clock::now(), max_leg_dq);
                    while (!leg_dq_history.empty() &&
                           leg_dq_history.front().first <
                               Clock::now() - std::chrono::seconds(2))
                        leg_dq_history.pop_front();
                }
                const bool squat_by_y = button_pressed(RemoteInput::BTN_Y);
                const bool squat_by_timeout =
                    (stand_trial || zero_b_trial
#if defined(AS2W_POLICY_GETUP1199)
                     || getup_trial
#endif
                    ) &&
                    fixed_stand_entered != Clock::time_point{} &&
                    std::chrono::duration<float>(Clock::now() -
                        fixed_stand_entered).count() >= stand_hold_seconds;
                if (squat_by_y || squat_by_timeout) {
                    std::cout << "FixedStand squat trigger="
                              << (squat_by_y ? "Y" : "timeout") << '\n';
                    start_squat("FixedStand");
#if defined(AS2W_POLICY_GETUP1199)
                } else if (button_pressed(RemoteInput::BTN_B)) {
                    // The getup chain ended here; B (walking handoff) has no
                    // meaning in this build. Y or the hold timeout squats.
                    std::cout << "[FixedStand] B ignored: no walking handoff "
                                 "in the getup build\n";
                }
#else
                } else if (!stand_trial && button_pressed(RemoteInput::BTN_B) &&
                           (!zero_b_trial || !zero_b_cycle_used)) {
                    float max_pose_error = 0.f, max_wheel_speed = 0.f, upright = 1.f;
                    std::array<float, LegCount> axis_errors{};
                    {
                        std::lock_guard<std::mutex> lock(state_mutex);
                        for (std::size_t i = 0; i < LegCount; ++i) {
                            const auto& m = latest_frame.motor_state()[mapping[i].index];
                            const float measured = mapping[i].sign *
                                (m.q() - mapping[i].zero);
                            axis_errors[i] = std::abs(measured - fixed_pose[i]);
                            max_pose_error = std::max(max_pose_error, axis_errors[i]);
                        }
                        for (std::size_t i = LegCount; i < MotorCount; ++i)
                            max_wheel_speed = std::max(max_wheel_speed,
                                std::abs(latest_frame.motor_state()[mapping[i].index].dq()));
                        const auto& quat = latest_frame.imu_state().quaternion();
                        upright = 1.f - 2.f * (quat[1]*quat[1] + quat[2]*quat[2]);
                    }
                    float quiet_window_max_dq = 0.f;
                    bool quiet_window_long_enough = false;
                    {
                        const auto now = Clock::now();
                        const auto horizon = now - kBGateQuietWindow;
                        std::size_t counted = 0;
                        Clock::time_point oldest = Clock::time_point{};
                        for (const auto& entry : leg_dq_history) {
                            if (entry.first < horizon) continue;
                            quiet_window_max_dq = std::max(quiet_window_max_dq,
                                entry.second);
                            if (counted == 0 || entry.first < oldest)
                                oldest = entry.first;
                            ++counted;
                        }
                        quiet_window_long_enough = counted > 0 && now - oldest >=
                            kBGateQuietWindow - std::chrono::milliseconds(50);
                    }
                    const bool stick_centered =
                        std::abs(remote_snapshot.ly()) < 0.05f &&
                        std::abs(remote_snapshot.lx()) < 0.05f &&
                        std::abs(remote_snapshot.rx()) < 0.05f;
                    const bool hold_ok = fixed_stand_entered != Clock::time_point{} &&
                        Clock::now() - fixed_stand_entered >= kBGateMinHold;
                    const bool gate_ok = max_pose_error <= kBGatePoseError &&
                        max_wheel_speed <= kBGateWheelDq && stick_centered &&
                        hold_ok && upright >= kBGateUpright &&
                        quiet_window_max_dq <= kBGateLegQuietDq &&
                        quiet_window_long_enough;
                    if (!gate_ok) {
                        std::cout << "[FixedStand] B rejected: pose_error="
                                  << max_pose_error << " (gate " << kBGatePoseError
                                  << ") wheel_dq=" << max_wheel_speed
                                  << " (gate " << kBGateWheelDq << ")"
                                  << " stick_centered=" << stick_centered
                                  << " hold_ok=" << hold_ok
                                  << " upright=" << upright << " (gate "
                                  << kBGateUpright << ") quiet_max_dq="
                                  << quiet_window_max_dq << " (gate "
                                  << kBGateLegQuietDq << ") quiet_window="
                                  << quiet_window_long_enough << '\n';
                        std::cout << "[FixedStand] per-axis |err|:";
                        for (std::size_t i = 0; i < LegCount; ++i)
                            std::cout << ' ' << config.joint_names[i]
                                      << '=' << axis_errors[i];
                        std::cout << '\n';
                    } else {
                        controller.arm();
                        slewed_command = {};
                        policy_handoff_start = fixed;
                        policy_handoff_started = Clock::now();
                        if (zero_b_trial) {
                            zero_b_cycle_used = true;
                            zero_b_cycle_started = Clock::now();
                        }
                        std::cout << "[FixedStand] → PolicyHandoff (B accepted:"
                                  << " pose_error=" << max_pose_error
                                  << " wheel_dq=" << max_wheel_speed
                                  << " upright=" << upright
                                  << " quiet_dq=" << quiet_window_max_dq << ")\n";
                        g_state.store(State::PolicyHandoff);
                    }
                }
#endif
                break;
            }

            case State::PolicyHandoff: {
                // Run R214 at zero speed while q, dq and gains blend from the
                // fixed PD command. This is the only B transition boundary.
                SensorState sensors;
                Clock::time_point received{};
                uint32_t sensor_tick = 0;
                std::array<float, 3> imu_accel{};
                {
                    std::lock_guard<std::mutex> lock(state_mutex);
                    received = latest_received;
                    sensor_tick = latest_frame.tick();
                    const auto& imu = latest_frame.imu_state();
                    imu_accel = imu.accelerometer();
                    std::copy(imu.gyroscope().begin(), imu.gyroscope().end(), sensors.gyro.begin());
                    std::copy(imu.quaternion().begin(), imu.quaternion().end(),
                              sensors.body_to_world_wxyz.begin());
                    for (std::size_t i = 0; i < MotorCount; ++i) {
                        sensors.position[i] = mapping[i].sign *
                            (latest_frame.motor_state()[mapping[i].index].q() - mapping[i].zero);
                        sensors.velocity[i] = mapping[i].sign *
                            latest_frame.motor_state()[mapping[i].index].dq();
                    }
                }
                const float age = std::chrono::duration<float>(
                    Clock::now() - received).count();
                const Vector3 zero_cmd{};
                auto policy_targets = controller.step(sensors, zero_cmd, age);
                if (!policy_targets.active) {
                    std::cout << "[PolicyHandoff] controller disarmed → EmergencyDamping\n";
                    g_state.store(State::EmergencyDamping);
                    break;
                }
#if defined(AS2W_POLICY_R1199) || defined(AS2W_POLICY_R4000)
                log_policy_diag("HANDOFF", zero_cmd, policy_targets);
#endif
                const float elapsed = std::chrono::duration<float>(
                    Clock::now() - policy_handoff_started).count();
                const auto blended = blend_targets(policy_handoff_start,
                    policy_targets, elapsed / 2.f);
                { std::lock_guard<std::mutex> tlock(targets_mutex); current_targets = blended; }
                log_debug_policy("HANDOFF", sensors, sensor_tick, imu_accel,
                                 age, zero_cmd,
                                 policy_targets, blended);

                const bool request_a = button_pressed(RemoteInput::BTN_A);
                const bool request_y = button_pressed(RemoteInput::BTN_Y);
                if (request_a || request_y) {
                    start_brake("PolicyHandoff",
                        request_y ? BrakeGoal::FixSquat : BrakeGoal::FixedStand);
                } else if (elapsed >= 2.f) {
                    if (policy_lowpass_ms > 0.f)
                        policy_lowpass.reset(blended);
                    std::cout << "[PolicyHandoff] → PolicyWalk (zero-speed handoff complete)\n";
                    policy_walk_entered = Clock::now();
                    g_state.store(State::PolicyWalk);
                }
                break;
            }

            case State::PolicyWalk: {
                SensorState sensors;
                Clock::time_point received{};
                uint32_t sensor_tick = 0;
                std::array<float, 3> imu_accel{};
                {
                    std::lock_guard<std::mutex> lock(state_mutex);
                    received = latest_received;
                    sensor_tick = latest_frame.tick();
                    const auto& imu = latest_frame.imu_state();
                    imu_accel = imu.accelerometer();
                    std::copy(imu.gyroscope().begin(), imu.gyroscope().end(), sensors.gyro.begin());
                    std::copy(imu.quaternion().begin(), imu.quaternion().end(),
                              sensors.body_to_world_wxyz.begin());
                    for (std::size_t i = 0; i < MotorCount; ++i) {
                        sensors.position[i] = mapping[i].sign *
                            (latest_frame.motor_state()[mapping[i].index].q() - mapping[i].zero);
                        sensors.velocity[i] = mapping[i].sign *
                            latest_frame.motor_state()[mapping[i].index].dq();
                    }
                }
                const float age = std::chrono::duration<float>(
                    Clock::now() - received).count();
                const bool request_a = button_pressed(RemoteInput::BTN_A);
                const bool request_y = button_pressed(RemoteInput::BTN_Y);
#if defined(AS2W_R4000_JOYSTICK_CANDIDATE)
                // Bounded trial cap for the R4000 candidate; A remains the
                // operator's early brake, this cap is the backstop.
                const auto walk_cap = std::chrono::seconds(120);
#elif defined(AS2W_R1199_JOYSTICK_CANDIDATE)
                // A filtered field trial is deliberately shorter than the
                // established unfiltered joystick cycle. A is still an early
                // operator brake; this cap is the independent backstop.
                const auto walk_cap = policy_lowpass_ms > 0.f
                    ? std::chrono::seconds(30) : std::chrono::seconds(60);
#elif defined(AS2W_POLICY_R1199)
                const auto walk_cap = std::chrono::milliseconds(2000);
#elif defined(AS2W_POLICY_R284)
                const auto walk_cap = zero_b_trial
                    ? std::chrono::milliseconds(2000) : std::chrono::seconds(30);
#elif defined(AS2W_POLICY_R270)
                const auto walk_cap = zero_b_trial
                    ? std::chrono::milliseconds(2000) : std::chrono::seconds(30);
#elif defined(AS2W_POLICY_R249)
                const auto walk_cap = zero_b_trial
                    ? std::chrono::milliseconds(3000) : std::chrono::seconds(30);
#else
                const auto walk_cap = zero_b_trial
                    ? std::chrono::milliseconds(10000) : std::chrono::seconds(30);
#endif
                const bool time_cap = policy_walk_entered != Clock::time_point{} &&
                    Clock::now() - policy_walk_entered >= walk_cap;
                // Bounded candidates do not permit a free-running PolicyWalk.
                Vector3 desired_cmd{};
                if (!request_a && !request_y && !time_cap) {
#if defined(AS2W_R1199_FORWARD_CANDIDATE)
                    // Deterministic first nonzero trial. Sticks are ignored;
                    // later hand-control testing needs a separate build.
                    if (zero_b_trial)
                        desired_cmd[0] = vx_limit;
                    else
                        desired_cmd = map_remote_command(remote_snapshot, vx_limit);
#elif defined(AS2W_R4000_JOYSTICK_CANDIDATE)
                    if (zero_b_trial)
                        desired_cmd = map_r1199_joystick_command(
                            remote_snapshot, r4000_vx_limit, r4000_wz_limit);
                    else
                        desired_cmd = map_remote_command(remote_snapshot, vx_limit);
#elif defined(AS2W_R1199_JOYSTICK_CANDIDATE)
                    if (zero_b_trial)
                        desired_cmd = map_r1199_joystick_command(
                            remote_snapshot, r1199_vx_limit, r1199_wz_limit);
                    else
                        desired_cmd = map_remote_command(remote_snapshot, vx_limit);
#else
                    desired_cmd = zero_b_trial ? Vector3{}
                        : map_remote_command(remote_snapshot, vx_limit);
#endif
                }
                if (request_a || request_y || time_cap)
                    slewed_command = {};
                else
                    slewed_command = slew_command(
                        slewed_command, desired_cmd, config.dt);
                const auto cmd = slewed_command;
                if (++walk_command_log_tick % 10 == 0)
                    std::cout << "WALK_CMD vx=" << cmd[0] << " vy=" << cmd[1]
                              << " wz=" << cmd[2]
                              << " requested=" << desired_cmd[0] << ','
                              << desired_cmd[1] << ',' << desired_cmd[2]
                              << " ly=" << remote_snapshot.ly()
                              << " lx=" << remote_snapshot.lx()
                              << " rx=" << remote_snapshot.rx() << '\n';
                auto targets = controller.step(sensors, cmd, age);
                if (!targets.active) {
                    std::cout << "[PolicyWalk] controller disarmed → EmergencyDamping\n";
                    g_state.store(State::EmergencyDamping);
                    break;
                }
                const auto requested_targets = targets;
                if (policy_lowpass_ms > 0.f)
                    targets = policy_lowpass.apply(targets, config.dt,
                                                   policy_lowpass_wheels);
                { std::lock_guard<std::mutex> tlock(targets_mutex); current_targets = targets; }
                log_debug_policy("WALK", sensors, sensor_tick, imu_accel,
                                 age, cmd,
                                 requested_targets, targets);
#if defined(AS2W_POLICY_R1199) || defined(AS2W_POLICY_R4000)
                log_policy_diag("WALK", cmd, targets);
#endif

                // Policy command tracking: cmd - actual per contract leg axis,
                // CSV order fl_h,fr_h,rl_h,rr_h,fl_t,fr_t,rl_t,rr_t,fl_c,fr_c,rl_c,rr_c.
                // Sign of rear-leg entries distinguishes sink mechanisms:
                // negative/near-zero => policy drives the collapse (A);
                // steadily positive ~0.3rad => target holds but PD cannot (B).
                if (++policy_track_log_tick % 10 == 0) {
                    const float hold = policy_walk_entered != Clock::time_point{}
                        ? std::chrono::duration<float>(Clock::now() -
                            policy_walk_entered).count() : 0.f;
                    std::cout << "POLICY_TRACK," << hold;
                    for (std::size_t i = 0; i < LegCount; ++i)
                        std::cout << ',' << (targets.motors[i].q - sensors.position[i]);
                    std::cout << '\n';
                }

                if (request_a || request_y || time_cap) {
                    std::cout << "[PolicyWalk] brake trigger="
                              << (request_y ? "Y" : request_a ? "A"
#if defined(AS2W_R1199_FORWARD_CANDIDATE)
                              : zero_b_trial ? "bounded forward 2s cap" : "30s cap")
#elif defined(AS2W_R4000_JOYSTICK_CANDIDATE)
                              : zero_b_trial ? "bounded R4000 joystick 120s cap" : "30s cap")
#elif defined(AS2W_R1199_JOYSTICK_CANDIDATE)
                              : zero_b_trial ? (policy_lowpass_ms > 0.f
                                  ? "bounded filtered joystick 30s cap"
                                  : "bounded joystick 60s cap") : "30s cap")
#else
                              : zero_b_trial ? "bounded zero hold cap" : "30s cap")
#endif
                              << '\n';
                    start_brake("PolicyWalk",
                        request_y ? BrakeGoal::FixSquat : BrakeGoal::FixedStand);
                }
                break;
            }

            case State::Brake: {
                // R214 with zero commands until wheel speed stabilizes
                SensorState sensors;
                Clock::time_point received{};
                uint32_t sensor_tick = 0;
                std::array<float, 3> imu_accel{};
                {
                    std::lock_guard<std::mutex> lock(state_mutex);
                    received = latest_received;
                    sensor_tick = latest_frame.tick();
                    const auto& imu = latest_frame.imu_state();
                    imu_accel = imu.accelerometer();
                    std::copy(imu.gyroscope().begin(), imu.gyroscope().end(), sensors.gyro.begin());
                    std::copy(imu.quaternion().begin(), imu.quaternion().end(),
                              sensors.body_to_world_wxyz.begin());
                    for (std::size_t i = 0; i < MotorCount; ++i) {
                        sensors.position[i] = mapping[i].sign *
                            (latest_frame.motor_state()[mapping[i].index].q() - mapping[i].zero);
                        sensors.velocity[i] = mapping[i].sign *
                            latest_frame.motor_state()[mapping[i].index].dq();
                    }
                }
                const float age = std::chrono::duration<float>(
                    Clock::now() - received).count();
                const Vector3 zero_cmd{};
                auto targets = controller.step(sensors, zero_cmd, age);
                if (!targets.active) {
                    g_state.store(State::EmergencyDamping);
                    break;
                }
                const auto requested_targets = targets;
#if defined(AS2W_POLICY_R1199) || defined(AS2W_POLICY_R4000)
                log_policy_diag("BRAKE", zero_cmd, targets);
#endif
#if defined(AS2W_POLICY_R249) || defined(AS2W_POLICY_R270)
                // These preview policies retain nonzero wheel targets for a
                // zero physical-velocity request. Ramp those targets explicitly
                // to zero before the measured wheel-stability gate.
                const float brake_elapsed = std::chrono::duration<float>(
                    Clock::now() - brake_started).count();
                const float wheel_alpha = std::clamp(brake_elapsed / 2.f, 0.f, 1.f);
                for (std::size_t j = LegCount; j < MotorCount; ++j)
                    targets.motors[j].dq =
                        (1.f - wheel_alpha) * brake_entry_targets.motors[j].dq;
#endif
                if (policy_lowpass_ms > 0.f)
                    targets = policy_lowpass.apply(targets, config.dt, false);
                { std::lock_guard<std::mutex> tlock(targets_mutex); current_targets = targets; }
                log_debug_policy("BRAKE", sensors, sensor_tick, imu_accel,
                                 age, zero_cmd,
                                 requested_targets, targets);
                if (++policy_track_log_tick % 10 == 0) {
                    const float hold = policy_walk_entered != Clock::time_point{}
                        ? std::chrono::duration<float>(Clock::now() -
                            policy_walk_entered).count() : 0.f;
                    std::cout << "POLICY_TRACK," << hold;
                    for (std::size_t i = 0; i < LegCount; ++i)
                        std::cout << ',' << (targets.motors[i].q - sensors.position[i]);
                    std::cout << '\n';
                }

                // Check wheel speed
                float max_wheel_dq = 0.f;
                {
                    std::lock_guard<std::mutex> lock(state_mutex);
                    for (std::size_t j = LegCount; j < MotorCount; ++j) {
                        max_wheel_dq = std::max(max_wheel_dq,
                            std::abs(latest_frame.motor_state()[mapping[j].index].dq()));
                    }
                }
                if (button_pressed(RemoteInput::BTN_Y))
                    brake_goal = BrakeGoal::FixSquat;
                else if (button_pressed(RemoteInput::BTN_A))
                    brake_goal = BrakeGoal::FixedStand;
                if (max_wheel_dq < 0.5f) {
                    if (brake_stable_since == Clock::time_point{})
                        brake_stable_since = Clock::now();
                } else {
                    brake_stable_since = Clock::time_point{};
                }
                if (brake_stable_since != Clock::time_point{} &&
                    Clock::now() - brake_stable_since >= std::chrono::milliseconds(300)) {
                    if (brake_goal == BrakeGoal::FixSquat) {
                        start_squat("Brake");
                    } else {
                        {
                            std::lock_guard<std::mutex> tlock(targets_mutex);
                            return_stand_start = current_targets;
                        }
                        // The last zero-command R214 target is a posture the
                        // policy just supported. Hold it with fixed PD after
                        // braking instead of forcing the training default.
                        for (std::size_t i = 0; i < LegCount; ++i)
                            fixed_pose[i] = return_stand_start.motors[i].q;
                        return_stand_started = Clock::now();
                        std::cout << "[Brake] → ReturnStand (A/timeout, wheels stable)\n";
                        g_state.store(State::ReturnStand);
                    }
                } else if (brake_started != Clock::time_point{} &&
                           Clock::now() - brake_started >= std::chrono::seconds(3) &&
                           (Clock::now() - brake_started) <
                               std::chrono::seconds(3) + std::chrono::milliseconds(20)) {
                    std::cout << "[Brake] wheel-stability timeout; holding zero policy"
                              << " until stable or X\n";
                }
                break;
            }

            case State::ReturnStand: {
                const auto fixed = fixed_stand_targets(fixed_pose);
                const float elapsed = std::chrono::duration<float>(
                    Clock::now() - return_stand_started).count();
                const auto target = blend_targets(return_stand_start,
                    fixed, elapsed / 2.5f);
                { std::lock_guard<std::mutex> tlock(targets_mutex); current_targets = target; }
                if (button_pressed(RemoteInput::BTN_Y)) {
                    start_squat("ReturnStand");
                } else if (elapsed >= 2.5f) {
                    controller.stop();
                    fixed_stand_entered = Clock::now();
                    leg_dq_history.clear();
                    std::cout << "[ReturnStand] → FixedStand (A complete)\n";
                    g_state.store(State::FixedStand);
                }
                break;
            }

            case State::FixSquat: {
                const int n_f1 = int(interp.total_ticks * interp.seg1_frac);
                const int n_f2 = interp.total_ticks - n_f1;
                interp.current_tick++;
                Targets t{};
                t.active = true;
                if (interp.current_tick <= n_f1) {
                    // F1: fold with each motor's actual policy gain as the start.
                    float a = float(interp.current_tick) / n_f1;
                    auto fold = interp.start;
                    for (std::size_t j = 4; j < 8; ++j)
                        fold[j] = interp.start[j] + 0.2f;
                    for (std::size_t j = 8; j < LegCount; ++j)
                        fold[j] = interp.start[j] - 0.3f;
                    for (std::size_t j = 0; j < LegCount; ++j) {
                        t.motors[j].q = interp.start[j] + a * (fold[j] - interp.start[j]);
                        t.motors[j].kp = interp.start_kp[j] +
                            a * (interp.kp1 - interp.start_kp[j]);
                        t.motors[j].kd = 3.f;
                    }
                } else if (interp.current_tick <= interp.total_ticks) {
                    // F2 starts from the last F1 commanded target. Snapping q to
                    // measured position here removes support torque; this
                    // boundary coincided with a sudden drop in the A/Y field trial.
                    if (interp.current_tick == n_f1 + 1) {
                        for (std::size_t j = 4; j < 8; ++j)
                            interp.start[j] += 0.2f;
                        for (std::size_t j = 8; j < LegCount; ++j)
                            interp.start[j] -= 0.3f;
                    }
                    float a = float(interp.current_tick - n_f1) / n_f2;
                    for (std::size_t j = 0; j < LegCount; ++j) {
                        t.motors[j].q = interp.start[j] + a * (interp.target[j] - interp.start[j]);
                        t.motors[j].kp = interp.kp1 + a * (interp.kp2 - interp.kp1);
                        t.motors[j].kd = 3.f;
                    }
                } else if (interp.current_tick <= interp.total_ticks + 50) {
                    // One-second continuous gain release after reaching prone.
                    const float a = float(interp.current_tick - interp.total_ticks) / 50.f;
                    for (std::size_t j = 0; j < LegCount; ++j) {
                        t.motors[j].q = prone_pose[j];
                        t.motors[j].kp = interp.kp2 + a * (10.f - interp.kp2);
                        t.motors[j].kd = 3.f;
                    }
                } else if (interp.current_tick <= interp.total_ticks + 150) {
                    // Two-second gradual release, preemptible by X/fault.
                    const float a = float(interp.current_tick - interp.total_ticks - 50) / 100.f;
                    for (std::size_t j = 0; j < LegCount; ++j) {
                        t.motors[j].q = prone_pose[j];
                        t.motors[j].kp = 10.f * (1.f - a);
                        t.motors[j].kd = 3.f;
                    }
                }
                for (std::size_t j = LegCount; j < MotorCount; ++j) {
                    t.motors[j].dq = 0.f;
                    t.motors[j].kp = 0.f;
                    t.motors[j].kd = 2.f;
                }
                { std::lock_guard<std::mutex> tlock(targets_mutex); current_targets = t; }

                if (interp.current_tick >= interp.total_ticks + 150) {
                    std::cout << "[FixSquat] → Passive (auto, squat done + kp decay)\n";
                    g_state.store(State::Passive);
                    motion_cycle_completed.store(true);
                    if (stand_trial) stand_trial_completed.store(true);
                }
                break;
            }

            case State::EmergencyDamping:
                // Terminal state; writer thread publishes passive frames
                break;
            }

            update_buttons();
        };

        // ── Main FSM loop (50 Hz) ──
        Clock::time_point next_fsm = Clock::now();
        Clock::time_point passive_ready_since{};
        Clock::time_point stand_trial_wait_since{};
        Clock::time_point stand_trial_prone_since{};
        Clock::time_point motion_prone_since{};
        Clock::time_point motion_wait_since{};
        Clock::time_point emergency_since{};
        std::cout << "FSM started in Passive startup. "
                  << (enable_fsm_motion ? "A/B/Y enabled."
                      : stand_trial ? "A/Y enabled, B locked."
#if defined(AS2W_R1199_FORWARD_CANDIDATE)
                      : zero_b_trial ? "A/Y enabled; B once (automatic forward 0.05m/s for 2s, then auto return+squat)."
#elif defined(AS2W_R4000_JOYSTICK_CANDIDATE)
                      : zero_b_trial ? "A/Y enabled; B once (LY/RX capped, 120s maximum, then auto return+squat)."
#elif defined(AS2W_R1199_JOYSTICK_CANDIDATE)
                      : zero_b_trial ? (policy_lowpass_ms > 0.f
                          ? "A/Y enabled; B once (LY/RX capped, 120s maximum, then auto return+squat)."
                          : "A/Y enabled; B once (LY/RX capped, 60s maximum, then auto return+squat).")
#else
                      : zero_b_trial ? "A/Y enabled; B once (forced zero speed, auto return+squat)."
#endif
                                      : "A/B/Y locked out.")
                  << " X=emergency.\n";
        while (!g_abort.load()) {
            next_fsm += std::chrono::milliseconds(20);
            std::this_thread::sleep_until(next_fsm);
            fsm_tick();
            if (enable_fsm_motion && startup_ready.load()) {
                const auto state = g_state.load();
                const auto now = Clock::now();
                if (state == State::EmergencyDamping) {
                    if (emergency_since == Clock::time_point{}) emergency_since = now;
                    if (now - emergency_since >= std::chrono::seconds(3)) {
                        std::cout << "MOTION SESSION: emergency passive hold complete, stop\n";
                        g_abort.store(true);
                    }
                } else if (state == State::Passive && !motion_cycle_completed.load()) {
                    if (motion_wait_since == Clock::time_point{}) motion_wait_since = now;
                    if (now - motion_wait_since >= std::chrono::seconds(120)) {
                        std::cout << "MOTION SESSION: A not pressed in 120s, stop\n";
                        g_abort.store(true);
                    }
                }
            }
            if (enable_fsm_motion && motion_cycle_completed.load() &&
                g_state.load() == State::Passive) {
                if (motion_prone_since == Clock::time_point{})
                    motion_prone_since = Clock::now();
                if (Clock::now() - motion_prone_since >= std::chrono::seconds(1)) {
                    std::cout << "MOTION SESSION: prone hold complete, stop\n";
                    g_abort.store(true);
                }
            }
            if (!enable_fsm_motion && probe_index < 0 && startup_ready.load()) {
#if defined(AS2W_POLICY_GETUP1199)
                // Getup trial lifecycle: wait in Passive up to 120 s for the
                // operator's single B; after the chain returns to Passive
                // (success -> squat, or the 15 s rise cap) stop after a 1 s
                // prone hold. Without this branch the generic 3 s
                // passive_seconds abort would kill the session before the
                // operator can press B.
                if (getup_trial) {
                    const auto state = g_state.load();
                    const auto now = Clock::now();
                    if (state == State::EmergencyDamping) {
                        if (emergency_since == Clock::time_point{})
                            emergency_since = now;
                        if (now - emergency_since >= std::chrono::seconds(3)) {
                            std::cout << "GETUP TRIAL: emergency passive hold complete, stop\n";
                            g_abort.store(true);
                        }
                    } else if (getup_chain_started && state == State::Passive) {
                        if (getup_prone_since == Clock::time_point{})
                            getup_prone_since = now;
                        if (now - getup_prone_since >= std::chrono::seconds(1)) {
                            std::cout << "GETUP TRIAL: prone hold complete, stop\n";
                            g_abort.store(true);
                        }
                    } else if (!getup_cycle_used && state == State::Passive) {
                        if (getup_wait_since == Clock::time_point{})
                            getup_wait_since = now;
                        if (now - getup_wait_since >= std::chrono::seconds(120)) {
                            std::cout << "GETUP TRIAL: B not pressed in 120s, stop\n";
                            g_abort.store(true);
                        }
                    }
                    continue;
                }
#else
                if (zero_b_trial) {
                    const auto state = g_state.load();
                    const auto now = Clock::now();
                    if (state == State::EmergencyDamping) {
                        if (emergency_since == Clock::time_point{})
                            emergency_since = now;
                        if (now - emergency_since >= std::chrono::seconds(3)) {
                            std::cout << "ZERO-B TRIAL: emergency passive hold complete, stop\n";
                            g_abort.store(true);
                        }
                    } else if (zero_b_cycle_used &&
                               zero_b_cycle_started != Clock::time_point{} &&
                               now - zero_b_cycle_started >=
#if defined(AS2W_R4000_JOYSTICK_CANDIDATE)
                                   std::chrono::seconds(160)) {
                        // 120s walk cap + handoff/brake/return/squat margin.
                        std::cout << "R4000 JOYSTICK: absolute 65s cycle cap"
                                  << " → controlled Brake or FixSquat\n";
                        zero_b_cycle_started = {};
                        if (state == State::PolicyHandoff || state == State::PolicyWalk)
                            start_brake("absolute joystick cap", BrakeGoal::FixSquat);
                        else if (state == State::FixedStand)
                            start_squat("absolute joystick cap");
#elif defined(AS2W_R1199_JOYSTICK_CANDIDATE)
                                   std::chrono::seconds(95)) {
                        // The normal path is B+2s handoff+60s joystick,
                        // Brake, ReturnStand, then Y/15s squat. Do not let
                        // the legacy 60s absolute cap cut that path short.
                        std::cout << "R1199 JOYSTICK: absolute 95s cycle cap"
                                  << " → controlled Brake or FixSquat\n";
                        zero_b_cycle_started = {};
                        if (state == State::PolicyHandoff || state == State::PolicyWalk)
                            start_brake("absolute joystick cap", BrakeGoal::FixSquat);
                        else if (state == State::FixedStand)
                            start_squat("absolute joystick cap");
#else
                                   std::chrono::seconds(60)) {
                        std::cout << "ZERO-B TRIAL: absolute 60s policy-cycle cap"
                                  << " → FixSquat from current targets\n";
                        start_squat("ZERO-B cap");
#endif
                    } else if (state == State::Passive &&
                               motion_cycle_completed.load()) {
                        if (stand_trial_prone_since == Clock::time_point{})
                            stand_trial_prone_since = now;
                        if (now - stand_trial_prone_since >= std::chrono::seconds(1)) {
                            std::cout << "ZERO-B TRIAL: prone hold complete, stop\n";
                            g_abort.store(true);
                        }
                    } else if (state == State::Passive) {
                        if (stand_trial_wait_since == Clock::time_point{})
                            stand_trial_wait_since = now;
                        if (now - stand_trial_wait_since >= std::chrono::seconds(120)) {
                            std::cout << "ZERO-B TRIAL: A not pressed in 120s, stop\n";
                            g_abort.store(true);
                        }
                    }
                    continue;
                }
                if (stand_trial) {
                    const auto state = g_state.load();
                    const auto now = Clock::now();
                    if (state == State::EmergencyDamping) {
                        std::cout << "STAND TRIAL: emergency, stop publisher\n";
                        g_abort.store(true);
                    } else if (state == State::Passive && stand_trial_completed.load()) {
                        if (stand_trial_prone_since == Clock::time_point{})
                            stand_trial_prone_since = now;
                        if (now - stand_trial_prone_since >= std::chrono::seconds(1)) {
                            std::cout << "STAND TRIAL: prone hold complete, stop\n";
                            g_abort.store(true);
                        }
                    } else if (state == State::Passive) {
                        if (stand_trial_wait_since == Clock::time_point{})
                            stand_trial_wait_since = now;
                        if (now - stand_trial_wait_since >= std::chrono::seconds(120)) {
                            std::cout << "STAND TRIAL: A not pressed in 120s, stop\n";
                            g_abort.store(true);
                        }
                    }
                    continue;
                }
#endif
                if (passive_ready_since == Clock::time_point{})
                    passive_ready_since = Clock::now();
                if (std::chrono::duration<float>(Clock::now()-passive_ready_since).count()
                    >= passive_seconds) {
                    std::cout << "PASSIVE ONLY: bounded duration complete\n";
                    g_abort.store(true);
                }
            }
        }

        // On a feedback/write fault, never continue sending stale commands.
        // Exit behavior under motor power remains an unverified hardware item.
        std::cout << (startup_fault.load() ? "Publisher fault; stop.\n"
                                           : "Operator exit; stop.\n");
        g_state.store(State::EmergencyDamping);
        g_abort.store(true);
        writer.join();
#if defined(AS2W_POLICY_R1199) || defined(AS2W_POLICY_R4000)
        policy_diag.flush();
#endif
        if (debug_capture) {
            debug_lowcmd.stop();
            debug_policy.flush();
            std::cout << "DEBUG_POLICY_RESULT rows=" << debug_policy_lines
                      << " file_ok=" << static_cast<bool>(debug_policy) << '\n';
            debug_policy.close();
        }
        // This CPRO build intermittently asserts in DDS C++ cleanup even for
        // read-only tools. After the writer is joined, end this short field
        // process without invoking the affected SDK destructors.
        const int result = startup_fault.load() ? 1 : 0;
        std::cout << "Publisher stopped, exit=" << result << '\n';
        std::cout.flush();
        std::cerr.flush();
        std::_Exit(result);
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
