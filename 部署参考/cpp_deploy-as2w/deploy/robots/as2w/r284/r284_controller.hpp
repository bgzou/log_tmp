#pragma once

#include <array>
#include <filesystem>
#include <string>

#include "isaaclab/algorithms/algorithms.h"
#include "r284_observations.hpp"

namespace as2w_r284_deploy {
inline constexpr std::size_t MotorCount = 16;
using Vector3 = std::array<float, 3>;
using Motors = std::array<float, MotorCount>;

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
    Motors defaults{}, stiffness{}, damping{};
    float dt = .02f;  // deploy.yaml step_dt is checked to be exactly 0.02
};

Config load_config(const std::filesystem::path& yaml);

class Controller {
public:
    explicit Controller(Config config);
    void arm();
    void stop();
    bool armed() const { return armed_; }
    Targets step(const SensorState& sensors, const Vector3& command, float age_seconds);
    const as2w_r284::Features& last_observation() const { return last_observation_; }
    const Motors& last_raw_action() const { return last_raw_action_; }

private:
    Config config_;
    isaaclab::OrtRunner runner_;
    as2w_r284::Observations observations_;
    bool armed_ = false;
    as2w_r284::Features last_observation_{};
    Motors last_raw_action_{};
};
}  // namespace as2w_r284_deploy

