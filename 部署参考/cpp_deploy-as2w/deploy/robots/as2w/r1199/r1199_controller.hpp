#pragma once

#include <array>
#include <filesystem>
#include <string>

#include "isaaclab/algorithms/algorithms.h"
#include "../r284/r284_observations.hpp"

namespace as2w_r1199_deploy {
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
    // Speed envelope for the joystick candidate, read from deploy.yaml
    // (vx_limit/wz_limit). Structural fallback keeps the historical 0.05
    // when the yaml omits the fields; the yaml is the only place to change
    // it. Any change requires offline re-verification before field use.
    float vx_limit = .05f;
    float wz_limit = .05f;
};

Config load_config(const std::filesystem::path& yaml);

// Bounded first gate: only zero physical velocity is accepted. The full
// motion adapter is intentionally absent until this path has parity and
// closed-loop exit validation. Never reuse it for free joystick motion.
class Controller {
public:
    explicit Controller(Config config);
    void arm();
    void stop();
    bool armed() const { return armed_; }
    Targets step(const SensorState& sensors, const Vector3& command, float age_seconds);
    const as2w_r284::Features& last_observation() const { return last_obs_; }
    // Diagnostics for splitting inference-side vs wrapper-side vs hardware
    // side: the raw ONNX output, the calibrated stand bias, its applied
    // scale and the wheel-hold latch counter of the last active step.
    const Motors& last_raw_action() const { return last_raw_; }
    const Motors& last_stand_bias() const { return bias_; }
    float last_bias_scale() const { return last_bias_scale_; }
    int hold_frames() const { return hold_frames_; }

private:
    Config config_;
    isaaclab::OrtRunner runner_;
    as2w_r284::Observations observations_;
    Motors bias_{};
    Motors last_raw_{};
    float last_bias_scale_ = 0.f;
    std::array<float, 4> park_reference_{};
    int hold_frames_ = 0;
    int age_frames_ = 0;
    bool armed_ = false;
    as2w_r284::Features last_obs_{};
};
}  // namespace as2w_r1199_deploy
