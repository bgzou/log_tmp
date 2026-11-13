#include "r270_controller.hpp"

#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>
#include <vector>

#include <yaml-cpp/yaml.h>

namespace as2w_r270 {
namespace {
constexpr float Pi = 3.14159265358979323846f;
constexpr float GaitPeriodSeconds = 0.62f;

template <class Range>
bool finite(const Range& values) {
    return std::all_of(values.begin(), values.end(), [](float v) { return std::isfinite(v); });
}

template <class T, std::size_t N>
std::array<T, N> read_array(const YAML::Node& node) {
    if (!node.IsSequence() || node.size() != N)
        throw std::runtime_error("Unexpected deploy.yaml array length");
    std::array<T, N> result{};
    for (std::size_t i = 0; i < N; ++i) result[i] = node[i].as<T>();
    return result;
}

std::string checked_model(const std::filesystem::path& path) {
    Ort::Env env(ORT_LOGGING_LEVEL_WARNING, "as2w_r270_contract");
    Ort::SessionOptions options;
    options.SetIntraOpNumThreads(1);
    Ort::Session session(env, path.c_str(), options);
    Ort::AllocatorWithDefaultOptions allocator;
    if (session.GetInputCount() != 1 || session.GetOutputCount() != 1)
        throw std::runtime_error("AS2-W R270 ONNX must expose exactly obs -> actions");
    const auto input = session.GetInputNameAllocated(0, allocator);
    const auto output = session.GetOutputNameAllocated(0, allocator);
    // TensorTypeAndShapeInfo is an unowned view. Keep its owning TypeInfo
    // alive until all shape/type checks are complete.
    const auto input_type = session.GetInputTypeInfo(0);
    const auto output_type = session.GetOutputTypeInfo(0);
    const auto in = input_type.GetTensorTypeAndShapeInfo();
    const auto out = output_type.GetTensorTypeAndShapeInfo();
    if (std::string(input.get()) != "obs" || std::string(output.get()) != "actions"
        || in.GetShape() != std::vector<int64_t>{1, ObservationCount}
        || out.GetShape() != std::vector<int64_t>{1, MotorCount}
        || in.GetElementType() != ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT
        || out.GetElementType() != ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT)
        throw std::runtime_error("AS2-W R270 ONNX tensor contract mismatch");
    return path.string();
}
}  // namespace

Config load_config(const std::filesystem::path& path) {
    const auto root = YAML::LoadFile(path.string());
    Config config;
    config.onnx = std::filesystem::absolute(path.parent_path() / root["policy_file"].as<std::string>());
    config.model_version = root["model_version"].as<std::string>();
    config.joint_names = read_array<std::string, MotorCount>(root["joint_names"]);
    config.defaults = read_array<float, MotorCount>(root["default_joint_pos"]);
    config.lower = read_array<float, MotorCount>(root["position_lower"]);
    config.upper = read_array<float, MotorCount>(root["position_upper"]);
    config.velocity = read_array<float, MotorCount>(root["velocity_limit"]);
    config.stiffness = read_array<float, MotorCount>(root["stiffness"]);
    config.damping = read_array<float, MotorCount>(root["damping"]);
    config.command_limit = read_array<float, 3>(root["command_limit"]);
    config.dt = root["step_dt"].as<float>();
    config.leg_action_scale = root["actions"]["joint_position"]["scale"].as<float>();
    config.wheel_action_scale = root["actions"]["wheel_velocity"]["scale"].as<float>();
    const auto gate = root["low_speed_hind_posture"];
    config.low_speed_gate_enabled = gate["enabled"].as<bool>();
    config.low_speed_threshold = gate["planar_command_threshold_m_s"].as<float>();
    config.low_speed_action_scale = gate["action_scale"].as<float>();
    config.low_speed_action_indices = read_array<std::size_t, 6>(gate["action_indices"]);
    if (root["command_smoothing_seconds"])
        config.command_smoothing_seconds = root["command_smoothing_seconds"].as<float>();

    if (root["observation_size"].as<std::size_t>() != ObservationCount
        || root["action_size"].as<std::size_t>() != MotorCount
        || root["measured_base_linear_velocity"].as<bool>())
        throw std::runtime_error("AS2-W R270 observation/action contract mismatch");
    if (!std::isfinite(config.dt) || std::abs(config.dt - .02f) > 1e-6f
        || !finite(config.defaults) || !finite(config.lower) || !finite(config.upper)
        || !finite(config.velocity) || !finite(config.stiffness) || !finite(config.damping)
        || !finite(config.command_limit) || config.leg_action_scale <= 0.f
        || config.wheel_action_scale <= 0.f || config.low_speed_threshold < 0.f
        || config.low_speed_action_scale < 0.f || config.low_speed_action_scale > 1.f
        || config.command_smoothing_seconds < 0.f)
        throw std::runtime_error("Invalid AS2-W R270 control contract");
    for (std::size_t i = 0; i < MotorCount; ++i) {
        if (config.joint_names[i].empty() || config.lower[i] > config.upper[i]
            || config.velocity[i] <= 0.f || config.stiffness[i] < 0.f || config.damping[i] < 0.f)
            throw std::runtime_error("Invalid AS2-W R270 motor contract");
    }
    for (const auto i : config.low_speed_action_indices)
        if (i >= MotorCount) throw std::runtime_error("Invalid R270 low-speed action index");
    if (std::any_of(config.command_limit.begin(), config.command_limit.end(),
                    [](float limit) { return limit <= 0.f; }))
        throw std::runtime_error("Invalid R270 command limits");
    return config;
}

Controller::Controller(Config config)
    : config_(std::move(config)), runner_(checked_model(config_.onnx)) {}

void Controller::arm() {
    previous_action_.fill(0.f);
    smoothed_command_.fill(0.f);
    phase_seconds_ = 0.f;
    history_frames_.clear();
    armed_ = true;
}

void Controller::stop() {
    armed_ = false;
    previous_action_.fill(0.f);
    smoothed_command_.fill(0.f);
    phase_seconds_ = 0.f;
    history_frames_.clear();
}

Frame Controller::make_observation(const SensorState& state, const Vector3& command) const {
    const auto& quaternion = state.body_to_world_wxyz;
    if (!finite(quaternion) || !finite(state.gyro) || !finite(state.position)
        || !finite(state.velocity) || !finite(command))
        throw std::invalid_argument("Nonfinite R270 sensor or command");
    const float norm2 = std::inner_product(quaternion.begin(), quaternion.end(), quaternion.begin(), 0.f);
    if (norm2 < .81f || norm2 > 1.21f) throw std::invalid_argument("Invalid IMU quaternion");
    const float inv_norm = 1.f / std::sqrt(norm2);
    const float w = quaternion[0] * inv_norm, x = quaternion[1] * inv_norm;
    const float y = quaternion[2] * inv_norm, z = quaternion[3] * inv_norm;

    Frame observation{};
    observation[0] = command[0] - .4f;
    observation[1] = command[1];
    observation[2] = command[2];
    std::copy(state.gyro.begin(), state.gyro.end(), observation.begin() + 3);
    observation[6] = -2.f * (x*z - w*y);
    observation[7] = -2.f * (y*z + w*x);
    observation[8] = 2.f * (x*x + y*y) - 1.f;
    observation[9] = .4f;
    for (std::size_t i = 0; i < MotorCount; ++i) {
        observation[10 + i] = state.position[i] - config_.defaults[i];
        observation[26 + i] = state.velocity[i];
        observation[42 + i] = previous_action_[i];
    }
    const float phase = 2.f * Pi * phase_seconds_ / GaitPeriodSeconds;
    observation[58] = std::sin(phase);
    observation[59] = std::cos(phase);
    return observation;
}

Targets Controller::step(const SensorState& sensors, const Vector3& command, float age_seconds) {
    if (!armed_) return {};
    if (!std::isfinite(age_seconds) || age_seconds < 0.f || age_seconds > .05f) {
        stop();
        return {};
    }
    try {
        Vector3 limited{};
        for (std::size_t i = 0; i < limited.size(); ++i)
            limited[i] = std::clamp(command[i], -config_.command_limit[i], config_.command_limit[i]);
        const float alpha = config_.command_smoothing_seconds <= 0.f
            ? 1.f : std::min(1.f, config_.dt / config_.command_smoothing_seconds);
        for (std::size_t i = 0; i < limited.size(); ++i)
            smoothed_command_[i] += alpha * (limited[i] - smoothed_command_[i]);
        if (std::all_of(limited.begin(), limited.end(),
                        [](float value) { return std::abs(value) < 1e-8f; })
            && std::all_of(smoothed_command_.begin(), smoothed_command_.end(),
                           [](float value) { return std::abs(value) < .005f; }))
            smoothed_command_.fill(0.f);
        const auto frame = make_observation(sensors, smoothed_command_);
        if (history_frames_.size() == 25) history_frames_.pop_front();
        history_frames_.push_back(frame);
        Observation observation{};
        auto output = std::copy(frame.begin(), frame.end(), observation.begin());
        for (std::size_t offset = 2; offset <= 24; offset += 2) {
            const auto& past = history_frames_[
                history_frames_.size() - std::min(offset + 1, history_frames_.size())];
            output = std::copy(past.begin() + 3, past.begin() + 58, output);
        }
        auto targets = infer(observation, smoothed_command_);
        phase_seconds_ = std::fmod(phase_seconds_ + config_.dt, GaitPeriodSeconds);
        return targets;
    } catch (const std::invalid_argument&) {
        stop();
        return {};
    } catch (...) {
        stop();
        throw;
    }
}

Targets Controller::infer(const Observation& observation, const Vector3& command) {
    last_observation_ = observation;
    auto result = runner_.forward({{"obs", std::vector<float>(observation.begin(), observation.end())}});
    auto action = result.at("actions");
    if (action.size() != MotorCount || !finite(action))
        throw std::runtime_error("Invalid AS2-W R270 inference output");
    std::copy(action.begin(), action.end(), last_raw_action_.begin());
    if (config_.low_speed_gate_enabled
        && std::hypot(command[0], command[1]) <= config_.low_speed_threshold) {
        for (const auto i : config_.low_speed_action_indices)
            action[i] *= config_.low_speed_action_scale;
    }

    Targets targets;
    for (std::size_t i = 0; i < MotorCount; ++i) {
        targets.action[i] = action[i];
        if (i < 12) {
            const float q = std::clamp(config_.defaults[i] + config_.leg_action_scale * action[i],
                                       config_.lower[i], config_.upper[i]);
            targets.motors[i] = {q, 0.f, config_.stiffness[i], config_.damping[i]};
        } else {
            const float dq = std::clamp(config_.wheel_action_scale * action[i],
                                        -config_.velocity[i], config_.velocity[i]);
            targets.motors[i] = {0.f, dq, config_.stiffness[i], config_.damping[i]};
        }
    }
    std::copy(action.begin(), action.end(), previous_action_.begin());
    targets.active = true;
    return targets;
}
}  // namespace as2w_r270


