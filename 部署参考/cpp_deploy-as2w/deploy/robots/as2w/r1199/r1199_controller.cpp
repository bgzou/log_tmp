#include "r1199_controller.hpp"

#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>
#include <vector>

#include <yaml-cpp/yaml.h>

namespace as2w_r1199_deploy {
namespace {
constexpr float Dt = .02f;
constexpr float Pi = 3.14159265358979323846f;
constexpr std::array<float, 4> Side{1.f, -1.f, 1.f, -1.f};

template <class Range> bool finite(const Range& xs) {
    return std::all_of(xs.begin(), xs.end(), [](float x) { return std::isfinite(x); });
}
template <class T, std::size_t N> std::array<T, N> read_array(const YAML::Node& n) {
    if (!n.IsSequence() || n.size() != N) throw std::runtime_error("R1199 YAML array length");
    std::array<T, N> out{};
    for (std::size_t i = 0; i < N; ++i) out[i] = n[i].as<T>();
    return out;
}
float wrap(float angle) {
    float shifted = std::fmod(angle + 2.f * Pi, 4.f * Pi);
    if (shifted < 0.f) shifted += 4.f * Pi;
    return shifted - 2.f * Pi;
}
float clamp(float x, float lo, float hi) { return std::clamp(x, lo, hi); }

std::string checked_model(const std::filesystem::path& path) {
    Ort::Env env(ORT_LOGGING_LEVEL_WARNING, "as2w_r1199_contract");
    Ort::SessionOptions options;
    options.SetIntraOpNumThreads(1);
    Ort::Session session(env, path.c_str(), options);
    Ort::AllocatorWithDefaultOptions allocator;
    if (session.GetInputCount() != 1 || session.GetOutputCount() != 1)
        throw std::runtime_error("R1199 expects one ONNX input and output");
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
        throw std::runtime_error("R1199 ONNX tensor contract mismatch");
    return path.string();
}
}  // namespace

Config load_config(const std::filesystem::path& path) {
    const auto root = YAML::LoadFile(path.string());
    Config c;
    c.onnx = std::filesystem::absolute(path.parent_path() / root["policy_file"].as<std::string>());
    c.model_version = root["model_version"].as<std::string>();
    c.joint_names = read_array<std::string, MotorCount>(root["joint_names"]);
    c.defaults = read_array<float, MotorCount>(root["default_joint_pos"]);
    c.stiffness = read_array<float, MotorCount>(root["stiffness"]);
    c.damping = read_array<float, MotorCount>(root["damping"]);
    if (root["vx_limit"]) c.vx_limit = root["vx_limit"].as<float>();
    if (root["wz_limit"]) c.wz_limit = root["wz_limit"].as<float>();
    if (c.model_version != "r1199-zero-b-candidate" ||
        root["observation_size"].as<int>() != 65 || root["action_size"].as<int>() != 16 ||
        root["step_dt"].as<float>() != Dt || !finite(c.defaults) ||
        !finite(c.stiffness) || !finite(c.damping) ||
        !std::isfinite(c.vx_limit) || c.vx_limit < .01f || c.vx_limit > .30f ||
        !std::isfinite(c.wz_limit) || c.wz_limit < .01f || c.wz_limit > .30f)
        throw std::runtime_error("R1199 deploy contract mismatch");
    for (std::size_t i = 0; i < MotorCount; ++i) {
        if (c.joint_names[i].empty() ||
            std::abs(c.defaults[i] - as2w_r284::Defaults[i]) > 1e-5f ||
            std::abs(c.stiffness[i] - (i < 12 ? 55.f : 0.f)) > 1e-5f ||
            std::abs(c.damping[i] - 2.f) > 1e-5f)
            throw std::runtime_error("R1199 q/default/gain contract mismatch");
    }
    return c;
}

Controller::Controller(Config config)
    : config_(std::move(config)), runner_(checked_model(config_.onnx)) {}

void Controller::arm() {
    observations_.reset(); bias_.fill(0.f); park_reference_.fill(0.f);
    last_obs_.fill(0.f); last_raw_.fill(0.f); last_bias_scale_ = 0.f;
    hold_frames_ = age_frames_ = 0; armed_ = true;
}
void Controller::stop() { arm(); armed_ = false; }

Targets Controller::step(const SensorState& s, const Vector3& command, float age_seconds) {
    if (!armed_) return {};
    // The previously validated zero-B library remains zero-only. A separate
    // CMake target defines this macro for the bounded forward candidate.
#if defined(AS2W_R1199_JOYSTICK_CANDIDATE)
    const bool invalid_command = std::abs(command[0]) > config_.vx_limit * 1.00002f ||
        command[1] != 0.f || std::abs(command[2]) > config_.wz_limit * 1.00002f;
#elif defined(AS2W_R1199_FORWARD_CANDIDATE)
    const bool invalid_command = command[0] < 0.f || command[0] > .050001f ||
        command[1] != 0.f || command[2] != 0.f;
#else
    const bool invalid_command = command != Vector3{};
#endif
    if (!finite(command) || invalid_command ||
        !std::isfinite(age_seconds) || age_seconds < 0.f || age_seconds > .05f ||
        !finite(s.gyro) || !finite(s.body_to_world_wxyz) ||
        !finite(s.position) || !finite(s.velocity)) { stop(); return {}; }
    const auto& q = s.body_to_world_wxyz;
    const float norm2 = std::inner_product(q.begin(), q.end(), q.begin(), 0.f);
    if (norm2 < .81f || norm2 > 1.21f) { stop(); return {}; }
    const float inv = 1.f / std::sqrt(norm2);
    const float w = q[0] * inv, x = q[1] * inv, y = q[2] * inv, z = q[3] * inv;
    as2w_r284::SensorFrame sample;
    sample.gyro_body = s.gyro;
    sample.gravity_body = {-2.f * (x*z - w*y), -2.f * (y*z + w*x),
                           2.f * (x*x + y*y) - 1.f};
    sample.joint_q = s.position;
    sample.joint_dq = s.velocity;
    const auto obs = observations_.push(sample, command);
    last_obs_ = obs;
    auto output = runner_.forward({{"obs", std::vector<float>(obs.begin(), obs.end())}}).at("actions");
    if (output.size() != MotorCount || !finite(output)) { stop(); return {}; }
    for (std::size_t i = 0; i < MotorCount; ++i) last_raw_[i] = output[i];

    // The policy observes vx-0.4, while the training action wrapper receives
    // physical vx. Use the *filtered observation command* so its history and
    // action conversion agree frame for frame with the training evaluator.
    const Vector3 physical_cmd{obs[0] + .4f, obs[1], obs[2]};
    const float activity = std::max(std::abs(physical_cmd[0]) / .08f,
                                    std::abs(physical_cmd[2]) / .15f);
#if defined(AS2W_R1199_JOYSTICK_CANDIDATE)
    if (std::abs(physical_cmd[0]) > config_.vx_limit * 1.00002f ||
        std::abs(physical_cmd[1]) > 1e-6f ||
        std::abs(physical_cmd[2]) > config_.wz_limit * 1.00002f) {
        stop(); return {};
    }
#elif defined(AS2W_R1199_FORWARD_CANDIDATE)
    if (physical_cmd[0] < -1e-6f || physical_cmd[0] > .050001f ||
        std::abs(physical_cmd[1]) > 1e-6f || std::abs(physical_cmd[2]) > 1e-6f) {
        stop(); return {};
    }
#endif

    // The old joystick binary used the diagnostic parking path. The isolated
    // TRAINING_CONTRACT candidate matches the R1199 model_1199 training run:
    // no parking odometry, no leg-speed settle check, no common wheel feedback,
    // and continuous/straight precalibrated stand bias.
    const std::array<float, 3> up{-obs[6], -obs[7], -obs[8]};
    std::array<float, 4> odometry{};
#if defined(AS2W_R1199_TRAINING_CONTRACT)
    for (std::size_t i = 0; i < 4; ++i)
        odometry[i] = obs[22 + i];  // training park_odometry=false
#else
    const float pitch = std::atan2(-up[0], std::hypot(up[1], up[2]));
    for (std::size_t i = 0; i < 4; ++i) {
        const float thigh_error = obs[14 + i], calf_error = obs[18 + i];
        const float thigh = .8f + thigh_error, calf = -1.6f + calf_error;
        const float hub_x = .2119f * (i < 2 ? 1.f : -1.f)
            - .212f * (std::sin(thigh) + std::sin(thigh + calf));
        const float hub_z = -.212f * (std::cos(thigh) + std::cos(thigh + calf));
        odometry[i] = obs[22 + i] + thigh_error + calf_error + pitch
            - (std::cos(pitch) * hub_x + std::sin(pitch) * hub_z) / .086f;
    }
#endif
    const float gyro_norm = std::sqrt(s.gyro[0]*s.gyro[0] + s.gyro[1]*s.gyro[1] + s.gyro[2]*s.gyro[2]);
    float max_wheel_dq = 0.f;
    for (int i = 12; i < 16; ++i) max_wheel_dq = std::max(max_wheel_dq, std::abs(s.velocity[i]));
#if defined(AS2W_R1199_TRAINING_CONTRACT)
    const bool quiet_hold = max_wheel_dq < .5f && gyro_norm < .15f;
    constexpr float LatchTime = .12f;
#else
    float max_leg_dq = 0.f;
    for (int i = 0; i < 12; ++i) max_leg_dq = std::max(max_leg_dq, std::abs(s.velocity[i]));
    const bool quiet_hold = max_wheel_dq < .5f && gyro_norm < .15f && max_leg_dq < .5f;
    constexpr float LatchTime = .35f;
#endif
    // Match the training Torch float32 comparisons exactly. In particular,
    // 15 * 0.02f compares below 0.30f on this runtime; integer thresholds
    // would start stand calibration one frame early.
    const bool was_latched = hold_frames_ * Dt >= LatchTime;
    const bool centered = std::max({std::abs(physical_cmd[0]),
                                    std::abs(physical_cmd[1]),
                                    std::abs(physical_cmd[2])}) < .005f;
    hold_frames_ = (centered && (was_latched || quiet_hold)) ? hold_frames_ + 1 : 0;
    const bool latched = hold_frames_ * Dt >= LatchTime;
    if (latched && !was_latched) park_reference_ = odometry;
    std::array<float, 4> error{};
#if !defined(AS2W_R1199_TRAINING_CONTRACT)
    float longitudinal = 0.f, heading = 0.f;
#endif
    for (std::size_t i = 0; i < 4; ++i) {
        error[i] = wrap(odometry[i] - park_reference_[i]);
#if !defined(AS2W_R1199_TRAINING_CONTRACT)
        longitudinal += error[i] * .25f;
        heading += error[i] * Side[i] * .25f;
#endif
    }
    Motors wrapped{};
#if defined(AS2W_R1199_FORWARD_CANDIDATE) || defined(AS2W_R1199_JOYSTICK_CANDIDATE)
    // as2w_rolling_fixed_exit.py: rolling_fixed_exit, default
    // pure_turn_common_scale=1. Both candidates still suppress vy; the
    // joystick candidate alone admits signed vx and yaw up to 0.05.
    const float turning = clamp(std::abs(physical_cmd[2]) / .20f, 0.f, 1.f);
    const float motion = clamp(std::max(std::abs(physical_cmd[0]) / .10f,
                                        turning), 0.f, 1.f);
    float wheel_common = 0.f, wheel_steering = 0.f;
    for (int i = 12; i < 16; ++i) {
        const float wheel = clamp(output[i], -1.f, 1.f);
        wheel_common += wheel * .25f;
        wheel_steering += wheel * Side[i - 12] * .25f;
    }
    for (int i = 0; i < 12; ++i)
        wrapped[i] = .18f * motion * clamp(output[i], -1.f, 1.f);
    for (int i = 12; i < 16; ++i) {
        const float wheel = clamp(output[i], -1.f, 1.f);
        const float linear = physical_cmd[0] + .10f * turning * wheel_common -
            .66f * (1.f + .25f * wheel_steering) * physical_cmd[2] * Side[i - 12];
        wrapped[i] = clamp(linear / (.086f * 16.f) +
            .035f * motion * (1.f - turning) * (wheel - wheel_common), -6.f, 6.f);
    }
#endif
    if (latched) for (std::size_t i = 0; i < 4; ++i) {
#if defined(AS2W_R1199_TRAINING_CONTRACT)
        // Training runtime composes wheels + hold (rolling_fixed_exit output is
        // zero only for exactly centered commands); keep the residual instead of
        // replacing it so the action matches frame for frame.
        wrapped[12 + i] += clamp(-6.f * error[i], -1.5f, 1.5f) / 16.f;
#else
        wrapped[12 + i] = clamp(.5f * (-2.5f * longitudinal - 1.4f * heading * Side[i]),
                                 -.75f, .75f) / 16.f;
#endif
    }
    ++age_frames_;
    const float age = age_frames_ * Dt;
    const bool quiet_bias = gyro_norm < .20f && up[2] > .92f && max_wheel_dq < .55f;
    if (age < 4.f && quiet_bias && hold_frames_ * Dt >= .30f && activity < .05f) {
        for (std::size_t i = 0; i < 12; ++i) {
            const float correction = clamp(-1.4f * Dt * obs[10 + i], -.004f, .004f);
            bias_[i] = clamp((1.f - .03f * Dt) * bias_[i] + correction, -.38f, .38f);
        }
    }
    const float release_blend = clamp((hold_frames_ * Dt - .45f) / 1.05f, 0.f, 1.f);
    const float stand_blend = age < 4.f ? 1.f : release_blend;
    const float stand_scale = clamp(1.f - activity, 0.f, 1.f);
#if defined(AS2W_R1199_TRAINING_CONTRACT)
    // The formal R1199 Isaac/MuJoCo contracts enable both continuous and
    // straight-only stand bias. For pure longitudinal commands, retain the
    // calibrated support correction instead of dropping it on the first
    // nonzero command after a wheel-hold latch. This is the exact upstream
    // scale.lerp(upright_scale, straight) branch; no additional smoothing.
    const float upright_scale = clamp((up[2] - .82f) / .10f, 0.f, 1.f);
    const float straight = clamp(1.f - std::abs(physical_cmd[2]) / .12f,
                                 0.f, 1.f);
    const float bias_scale = (1.f - straight) * stand_blend * stand_scale +
                             straight * upright_scale;
#else
    const float bias_scale = stand_blend * stand_scale;
#endif
    for (std::size_t i = 0; i < 12; ++i)
        wrapped[i] += bias_scale * bias_[i] / .35f;
    last_bias_scale_ = bias_scale;
    observations_.remember(wrapped); // previous *wrapped* action, not raw ONNX
    const auto mapped = as2w_r284::targets(wrapped);
    Targets result;
    result.active = true;
    result.action = wrapped;
    for (std::size_t i = 0; i < MotorCount; ++i)
        result.motors[i] = {mapped.q[i], mapped.dq[i], mapped.kp[i], mapped.kd[i]};
    return result;
}
}  // namespace as2w_r1199_deploy
