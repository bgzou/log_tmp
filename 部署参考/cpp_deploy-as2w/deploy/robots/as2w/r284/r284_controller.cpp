#include "r284_controller.hpp"

#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>
#include <vector>

#include <yaml-cpp/yaml.h>

namespace as2w_r284_deploy {
namespace {
template <class Range>
bool finite(const Range& values) {
    return std::all_of(values.begin(), values.end(), [](float v) { return std::isfinite(v); });
}

template <class T, std::size_t N>
std::array<T, N> read_array(const YAML::Node& node) {
    if (!node.IsSequence() || node.size() != N)
        throw std::runtime_error("Unexpected R284 deploy.yaml array length");
    std::array<T, N> result{};
    for (std::size_t i = 0; i < N; ++i) result[i] = node[i].as<T>();
    return result;
}

std::string checked_model(const std::filesystem::path& path) {
    Ort::Env env(ORT_LOGGING_LEVEL_WARNING, "as2w_r284_contract");
    Ort::SessionOptions options;
    options.SetIntraOpNumThreads(1);
    Ort::Session session(env, path.c_str(), options);
    Ort::AllocatorWithDefaultOptions allocator;
    if (session.GetInputCount() != 1 || session.GetOutputCount() != 1)
        throw std::runtime_error("AS2-W R284 ONNX must expose exactly obs -> actions");
    const auto input = session.GetInputNameAllocated(0, allocator);
    const auto output = session.GetOutputNameAllocated(0, allocator);
    const auto input_type = session.GetInputTypeInfo(0);
    const auto output_type = session.GetOutputTypeInfo(0);
    const auto in = input_type.GetTensorTypeAndShapeInfo();
    const auto out = output_type.GetTensorTypeAndShapeInfo();
    if (std::string(input.get()) != "obs" || std::string(output.get()) != "actions"
        || in.GetShape() != std::vector<int64_t>{1, 65}
        || out.GetShape() != std::vector<int64_t>{1, 16}
        || in.GetElementType() != ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT
        || out.GetElementType() != ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT)
        throw std::runtime_error("AS2-W R284 ONNX tensor contract mismatch");
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
    config.stiffness = read_array<float, MotorCount>(root["stiffness"]);
    config.damping = read_array<float, MotorCount>(root["damping"]);
    if (root["observation_size"].as<std::size_t>() != 65
        || root["action_size"].as<std::size_t>() != MotorCount
        || root["step_dt"].as<float>() != .02f
        || !finite(config.defaults) || !finite(config.stiffness) || !finite(config.damping))
        throw std::runtime_error("Invalid AS2-W R284 control contract");
    for (std::size_t i = 0; i < MotorCount; ++i) {
        if (config.joint_names[i].empty()
            || std::abs(config.defaults[i] - as2w_r284::Defaults[i]) > 1e-5f
            || std::abs(config.stiffness[i] - (i < 12 ? 55.f : 0.f)) > 1e-5f
            || std::abs(config.damping[i] - 2.f) > 1e-5f)
            throw std::runtime_error("R284 motor contract differs from official adapter");
    }
    return config;
}

Controller::Controller(Config config)
    : config_(std::move(config)), runner_(checked_model(config_.onnx)) {}

void Controller::arm() {
    observations_.reset();
    armed_ = true;
}

void Controller::stop() {
    armed_ = false;
    observations_.reset();
}

Targets Controller::step(const SensorState& state, const Vector3& command, float age_seconds) {
    if (!armed_) return {};
    if (!std::isfinite(age_seconds) || age_seconds < 0.f || age_seconds > .05f
        || !finite(state.gyro) || !finite(state.body_to_world_wxyz)
        || !finite(state.position) || !finite(state.velocity) || !finite(command)) {
        stop();
        return {};
    }
    try {
        const auto& quaternion = state.body_to_world_wxyz;
        const float norm2 = std::inner_product(
            quaternion.begin(), quaternion.end(), quaternion.begin(), 0.f);
        if (norm2 < .81f || norm2 > 1.21f) throw std::invalid_argument("Invalid IMU quaternion");
        const float inv_norm = 1.f / std::sqrt(norm2);
        const float w = quaternion[0] * inv_norm, x = quaternion[1] * inv_norm;
        const float y = quaternion[2] * inv_norm, z = quaternion[3] * inv_norm;

        as2w_r284::SensorFrame sensors;
        sensors.gyro_body = state.gyro;
        sensors.gravity_body[0] = -2.f * (x*z - w*y);
        sensors.gravity_body[1] = -2.f * (y*z + w*x);
        sensors.gravity_body[2] = 2.f * (x*x + y*y) - 1.f;
        sensors.joint_q = state.position;
        sensors.joint_dq = state.velocity;
        const auto features = observations_.push(sensors, command);
        last_observation_ = features;
        auto result = runner_.forward({{"obs", std::vector<float>(features.begin(), features.end())}});
        auto action = result.at("actions");
        if (action.size() != MotorCount || !finite(action))
            throw std::runtime_error("Invalid AS2-W R284 inference output");
        std::copy(action.begin(), action.end(), last_raw_action_.begin());

        as2w_r284::Motors clipped{};
        for (std::size_t i = 0; i < MotorCount; ++i)
            clipped[i] = std::clamp(action[i], -6.f, 6.f);
        observations_.remember(clipped);
        const auto mapped = as2w_r284::targets(clipped);

        Targets targets;
        targets.active = true;
        for (std::size_t i = 0; i < MotorCount; ++i) {
            targets.action[i] = clipped[i];
            targets.motors[i] = {mapped.q[i], mapped.dq[i], mapped.kp[i], mapped.kd[i]};
        }
        return targets;
    } catch (const std::invalid_argument&) {
        stop();
        return {};
    } catch (...) {
        stop();
        throw;
    }
}
}  // namespace as2w_r284_deploy

