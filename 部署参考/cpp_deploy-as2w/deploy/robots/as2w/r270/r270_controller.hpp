#pragma once

#include <array>
#include <deque>
#include <filesystem>
#include <string>

#include "isaaclab/algorithms/algorithms.h"

namespace as2w_r270 {
inline constexpr std::size_t MotorCount = 16;
inline constexpr std::size_t FrameCount = 60;
inline constexpr std::size_t ObservationCount = 720;
using Vector3 = std::array<float, 3>;
using Motors = std::array<float, MotorCount>;
using Frame = std::array<float, FrameCount>;
using Observation = std::array<float, ObservationCount>;

struct SensorState {
    Vector3 gyro{};
    std::array<float, 4> body_to_world_wxyz{};
    Motors position{};
    Motors velocity{};
};

struct MotorTarget {
    float q = 0, dq = 0, kp = 0, kd = 0;
};

struct Targets {
    std::array<MotorTarget, MotorCount> motors{};
    Motors action{};
    bool active = false;
};

struct Config {
    std::filesystem::path onnx;
    std::string model_version;
    std::array<std::string, MotorCount> joint_names;
    Motors defaults{}, lower{}, upper{}, velocity{};
    Motors stiffness{}, damping{};
    Vector3 command_limit{};
    float dt = 0;
    float leg_action_scale = 0;
    float wheel_action_scale = 0;
    bool low_speed_gate_enabled = false;
    float low_speed_threshold = 0;
    float low_speed_action_scale = 0;
    std::array<std::size_t, 6> low_speed_action_indices{};
    float command_smoothing_seconds = 0.25f;
};

Config load_config(const std::filesystem::path& yaml);

class Controller {
public:
    explicit Controller(Config config);
    void arm();
    void stop();
    bool armed() const { return armed_; }
    Targets step(const SensorState& sensors, const Vector3& command, float age_seconds);
    const Observation& last_observation() const { return last_observation_; }
    const Motors& last_raw_action() const { return last_raw_action_; }

private:
    Frame make_observation(const SensorState& sensors, const Vector3& command) const;
    Targets infer(const Observation& observation, const Vector3& smoothed_command);

    Config config_;
    isaaclab::OrtRunner runner_;
    Motors previous_action_{};
    Vector3 smoothed_command_{};
    float phase_seconds_ = 0;
    std::deque<Frame> history_frames_;
    bool armed_ = false;
    Observation last_observation_{};
    Motors last_raw_action_{};
};
}  // namespace as2w_r270


