#pragma once

// getup1199 (recovery deep-side-curriculum formal model_1199) deploy controller.
//
// Training runtime contract (eval_as2w_mujoco_recovery.py +
// as2w_recovery_control.py, --low-support-handoff --predictive-guard):
//   obs 42 = [gyro(3), -R_row2 gravity(3), q-defaults(12), dq(12),
//             previous wrapped action(12)]  (no commands, no clock)
//   action 12 = leg targets (normalized, ONNX Hardtanh +-2), wheels are NOT
//   policy outputs: they position-hold the angle latched at policy start.
//   wrapper: staged_target ramp -> latch handoff -> integral stand bias ->
//   0.35 scale + 90% envelope clip -> per-publish predictive guard.
// Deployment estimators replace sim-privileged signals (validated
// 2026-11-13, logs/20261113_getup1199_deploy_precheck):
//   height = min over legs of leg-FK wheel axle height (wheel radius .086)
//   stable wheel support ~ wheel quietness (max |wheel dq| < .35)
//   body speed ~ .086 * max |wheel dq|

#include <array>
#include <filesystem>
#include <string>

#include "isaaclab/algorithms/algorithms.h"

namespace as2w_getup1199_deploy {

inline constexpr std::size_t MotorCount = 16;
inline constexpr std::size_t LegAxisCount = 12;
inline constexpr std::size_t ObsCount = 42;
using Vector3 = std::array<float, 3>;
using Motors = std::array<float, MotorCount>;
using Legs = std::array<float, LegAxisCount>;
using Features = std::array<float, ObsCount>;
inline constexpr Motors Defaults{0, 0, 0, 0, .8f, .8f, .8f, .8f,
                                 -1.6f, -1.6f, -1.6f, -1.6f, 0, 0, 0, 0};

struct SensorState {
    Vector3 gyro{};
    std::array<float, 4> body_to_world_wxyz{};
    Motors position{};
    Motors velocity{};
};

struct MotorTarget { float q = 0, dq = 0, kp = 0, kd = 0; };
struct Targets {
    std::array<MotorTarget, MotorCount> motors{};
    Legs action{};      // wrapped normalized action (pre 0.35 scale, pre guard)
    bool active = false;
};

struct Config {
    std::filesystem::path onnx;
    std::string model_version;
    std::array<std::string, MotorCount> joint_names;
    Motors defaults{}, stiffness{}, damping{}, effort_limit{};
    float effort_fraction = .9f;
    Legs angle_lower{}, angle_upper{};
    float dt = .02f;
    // staged rise (training contract)
    Legs staged_crouch{};
    float staged_authority = .42f;
    float entry_ramp0 = .22f, entry_ramp1 = .50f;
    float plant_ramp0 = .22f, plant_ramp1 = 1.10f;
    float extend_ramp0 = 1.45f, extend_ramp1 = 1.20f;
    // latch / integral stand (low_support_handoff=true)
    float stable_height = .27f;
    float latch_quiet_s = .45f;
    float latch_min_height = .25f;
    float blend_tau_s = .85f;
    float integral_min_height = .25f;
    float integral_decay = .04f;
    float integral_gain = 1.10f;
    float integral_clip = .34f;
    // envelope clip + predictive guard
    float action_scale = .35f;
    float command_margin = .06f;
    float guard_lookahead = .04f;
    float guard_band = .10f;
    float guard_gain = 2.f;
    float guard_margin = .06f;
    // wheels
    float wheel_hold_kp = 25.f, wheel_hold_kd = 4.f;
    // Entry / success gates (deployment estimators; deploy.yaml).
    float entry_min_up_z = .60f;
    float entry_max_height_est = .26f;
    float entry_wheel_quiet_dq = .35f;
    float success_height = .31f;
    float success_up = .95f;
    float success_joint_error = .18f;
    float success_spin = .18f;
    float success_hold_s = 2.f;
    float getup_cap_s = 15.f;
};

Config load_config(const std::filesystem::path& yaml);

class Controller {
public:
    explicit Controller(Config config);
    void arm();
    void stop();
    bool armed() const { return armed_; }
    bool initialized() const { return initialized_; }

    // One 50 Hz policy step. age_seconds is the caller's measured gap since
    // the previous step (cadence watchdog, not policy age).
    Targets step(const SensorState& sensors, float age_seconds);

    // Shared-publisher signature. The getup contract has no velocity
    // commands; any nonzero command disarms (defensive only).
    Targets step(const SensorState& sensors, const Vector3& command, float age_seconds);

    // Re-apply the predictive guard on the last command with fresh feedback.
    // The training evaluator re-guards every physics substep; the publisher
    // calls this on every ~2 ms publish frame for the same semantics.
    Legs guard(const Motors& position, const Motors& velocity) const;

    // Wheel position-hold reference (latched at policy start).
    const std::array<float, 4>& wheel_reference() const { return wheel_reference_; }

    // Deployment estimators / diagnostics.
    static float height_estimate(const Legs& q);
    float last_height_estimate() const { return last_height_; }
    float last_up() const { return last_up_; }
    int latch_frames() const { return latch_frames_; }
    float blend() const { return blend_; }
    const Legs& last_bias() const { return bias_; }
    const Features& last_observation() const { return last_obs_; }
    const Legs& last_raw_action() const { return last_raw_; }
    const Legs& last_command() const { return last_command_; }
    int policy_frames() const { return policy_frames_; }

private:
    Config config_;
    isaaclab::OrtRunner runner_;
    Legs previous_action_{};   // wrapped normalized (obs[30:42])
    Legs initial_norm_{};      // latched (q-defaults)/0.35 at policy start
    Legs bias_{};
    Legs last_raw_{};
    Legs last_command_{};      // defaults + .35*action, envelope clipped
    std::array<float, 4> wheel_reference_{};
    Features last_obs_{};
    int policy_frames_ = 0;
    int steady_frames_ = 0;
    int latch_frames_ = 0;
    float blend_ = 0.f;
    float last_height_ = 0.f;
    float last_up_ = 0.f;
    bool armed_ = false;
    bool initialized_ = false;
};
}  // namespace as2w_getup1199_deploy
