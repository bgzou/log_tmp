#pragma once

#include <array>
#include <filesystem>
#include <string>

#include "isaaclab/algorithms/algorithms.h"
#include "r4000_observations.hpp"

namespace as2w_r4000_deploy {

inline constexpr std::size_t MotorCount = 16;
using Vector3 = std::array<float, 3>;
using Motors = std::array<float, MotorCount>;

struct SensorState {
    Vector3 gyro{};
    std::array<float, 4> body_to_world_wxyz{};
    Motors position{};
    Motors velocity{};
};
struct MotorTarget { float q = 0, dq = 0, kp = 0, kd = 0; };
struct Targets {
    std::array<MotorTarget, MotorCount> motors{};
    Motors action{};
    bool active = false;
};
struct Config {
    std::filesystem::path onnx;
    std::string model_version;
    std::array<std::string, MotorCount> joint_names;
    Motors defaults{}, stiffness{}, damping{};
    float dt = .02f;
    // Speed envelope from deploy.yaml (vx_limit/wz_limit); the observation
    // goal planar clamp follows vx_limit because the rolling-4000 training
    // run sampled straight commands up to 0.20 m/s.
    float vx_limit = .05f;
    float wz_limit = .05f;
    // Training runtime contract (run filtered-4000-env4096-stage020.ovvRL3):
    // leg residual one-pole cutoff and wrapped leg-target slew.
    float leg_filter_hz = 5.f;
    float leg_slew_rad_s = .9f;
};

Config load_config(const std::filesystem::path& yaml);

// Bounded joystick candidate mirroring the validated R1199 training-contract
// adapter: the 65-D observation contract is shared, the action wrapping adds
// the 5 Hz leg-residual filter, pure-turn common suppression
// (pure_turn_common_scale=0) and the 0.9 rad/s leg-target slew that the
// rolling-4000 training run used.
class Controller {
public:
    explicit Controller(Config config);
    void arm();
    void stop();
    bool armed() const { return armed_; }
    Targets step(const SensorState& sensors, const Vector3& command, float age_seconds);
    const Features& last_observation() const { return last_obs_; }
    const Motors& last_raw_action() const { return last_raw_; }
    const Motors& last_stand_bias() const { return bias_; }
    float last_bias_scale() const { return last_bias_scale_; }
    int hold_frames() const { return hold_frames_; }

private:
    Config config_;
    isaaclab::OrtRunner runner_;
    Observations observations_;
    Motors bias_{};
    Motors last_raw_{};
    Motors filtered_legs_{};   // 5 Hz one-pole state on raw leg residuals
    Motors slew_legs_{};       // 0.9 rad/s target slew state (normalized)
    float last_bias_scale_ = 0.f;
    std::array<float, 4> park_reference_{};
    int hold_frames_ = 0;
    int age_frames_ = 0;
    bool armed_ = false;
    Features last_obs_{};
};
}  // namespace as2w_r4000_deploy
