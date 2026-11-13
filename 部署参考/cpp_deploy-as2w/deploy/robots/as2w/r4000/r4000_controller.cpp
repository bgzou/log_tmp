#include "r4000_controller.hpp"

#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>
#include <vector>

#include <yaml-cpp/yaml.h>

namespace as2w_r4000_deploy {
namespace {
constexpr float StepDt = .02f;
constexpr float PiF = 3.14159265358979323846f;
constexpr std::array<float, 4> Side{1.f, -1.f, 1.f, -1.f};

template <class Range> bool finite(const Range& xs) {
    return std::all_of(xs.begin(), xs.end(), [](float x) { return std::isfinite(x); });
}
template <class T, std::size_t N> std::array<T, N> read_array(const YAML::Node& n) {
    if (!n.IsSequence() || n.size() != N) throw std::runtime_error("R4000 YAML array length");
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
    Ort::Env env(ORT_LOGGING_LEVEL_WARNING, "as2w_r4000_contract");
    Ort::SessionOptions options;
    options.SetIntraOpNumThreads(1);
    Ort::Session session(env, path.c_str(), options);
    Ort::AllocatorWithDefaultOptions allocator;
    if (session.GetInputCount() != 1 || session.GetOutputCount() != 1)
        throw std::runtime_error("R4000 expects one ONNX input and output");
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
        throw std::runtime_error("R4000 ONNX tensor contract mismatch");
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
    if (root["leg_filter_hz"]) c.leg_filter_hz = root["leg_filter_hz"].as<float>();
    if (root["leg_slew_rad_s"]) c.leg_slew_rad_s = root["leg_slew_rad_s"].as<float>();
    if (c.model_version != "r4000-stage020-research" ||
        root["observation_size"].as<int>() != 65 || root["action_size"].as<int>() != 16 ||
        root["step_dt"].as<float>() != StepDt || !finite(c.defaults) ||
        !finite(c.stiffness) || !finite(c.damping) ||
        !std::isfinite(c.vx_limit) || c.vx_limit < .01f || c.vx_limit > .50f ||
        !std::isfinite(c.wz_limit) || c.wz_limit < .01f || c.wz_limit > .30f ||
        !std::isfinite(c.leg_filter_hz) || c.leg_filter_hz <= 0.f || c.leg_filter_hz > 20.f ||
        !std::isfinite(c.leg_slew_rad_s) || c.leg_slew_rad_s <= 0.f || c.leg_slew_rad_s > 5.f)
        throw std::runtime_error("R4000 deploy contract mismatch");
    for (std::size_t i = 0; i < MotorCount; ++i) {
        if (c.joint_names[i].empty() ||
            std::abs(c.defaults[i] - Defaults[i]) > 1e-5f ||
            std::abs(c.stiffness[i] - (i < 12 ? 55.f : 0.f)) > 1e-5f ||
            std::abs(c.damping[i] - 2.f) > 1e-5f)
            throw std::runtime_error("R4000 q/default/gain contract mismatch");
    }
    return c;
}

Controller::Controller(Config config)
    : config_(std::move(config)), runner_(checked_model(config_.onnx)),
      observations_(config_.vx_limit) {}

void Controller::arm() {
    observations_.reset(); bias_.fill(0.f); park_reference_.fill(0.f);
    last_obs_.fill(0.f); last_raw_.fill(0.f); last_bias_scale_ = 0.f;
    filtered_legs_.fill(0.f); slew_legs_.fill(0.f);
    hold_frames_ = age_frames_ = 0; armed_ = true;
}
void Controller::stop() { arm(); armed_ = false; }

Targets Controller::step(const SensorState& s, const Vector3& command, float age_seconds) {
    if (!armed_) return {};
    // Bounded joystick candidate: deploy.yaml envelope is the ceiling; the
    // publisher additionally restricts through CLI and the stick mapping.
    const bool invalid_command = std::abs(command[0]) > config_.vx_limit * 1.00002f ||
        command[1] != 0.f || std::abs(command[2]) > config_.wz_limit * 1.00002f;
    if (!finite(command) || invalid_command ||
        !std::isfinite(age_seconds) || age_seconds < 0.f || age_seconds > .05f ||
        !finite(s.gyro) || !finite(s.body_to_world_wxyz) ||
        !finite(s.position) || !finite(s.velocity)) { stop(); return {}; }
    const auto& q = s.body_to_world_wxyz;
    const float norm2 = std::inner_product(q.begin(), q.end(), q.begin(), 0.f);
    if (norm2 < .81f || norm2 > 1.21f) { stop(); return {}; }
    const float inv = 1.f / std::sqrt(norm2);
    const float w = q[0] * inv, x = q[1] * inv, y = q[2] * inv, z = q[3] * inv;
    SensorFrame sample;
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

    // The policy observes vx-0.4; the wrapper receives the filtered physical
    // command (same channel the training env's command manager produced).
    const Vector3 physical_cmd{obs[0] + .4f, obs[1], obs[2]};
    const float activity = std::max(std::abs(physical_cmd[0]) / .08f,
                                    std::abs(physical_cmd[2]) / .15f);
    if (std::abs(physical_cmd[0]) > config_.vx_limit * 1.00002f ||
        std::abs(physical_cmd[1]) > 1e-6f ||
        std::abs(physical_cmd[2]) > config_.wz_limit * 1.00002f) {
        stop(); return {};
    }

    // as2w_rolling_fixed_exit with pure_turn_common_scale=0: the wheel
    // common injection is blended out for pure turns
    // (forward_blend = clamp(|vx|/0.04, 0, 1)).
    const float turning = clamp(std::abs(physical_cmd[2]) / .20f, 0.f, 1.f);
    const float motion = clamp(std::max(std::abs(physical_cmd[0]) / .10f, turning), 0.f, 1.f);
    float wheel_common = 0.f, wheel_steering = 0.f;
    for (int i = 12; i < 16; ++i) {
        const float wheel = clamp(last_raw_[i], -1.f, 1.f);
        wheel_common += wheel * .25f;
        wheel_steering += wheel * Side[i - 12] * .25f;
    }
    const float turn_common = wheel_common *
        clamp(std::abs(physical_cmd[0]) / .04f, 0.f, 1.f);
    Motors wrapped{};
    // as2w_rolling_filtered.filter_leg_residual: one-pole 5 Hz filter on the
    // ±6-clipped raw leg residuals; state is zeroed at arm().
    const float alpha = -std::expm1(-2.f * PiF * config_.leg_filter_hz * StepDt);
    for (int i = 0; i < 12; ++i) {
        const float action = clamp(last_raw_[i], -6.f, 6.f);
        filtered_legs_[i] += alpha * (action - filtered_legs_[i]);
        wrapped[i] = .18f * motion * clamp(filtered_legs_[i], -1.f, 1.f);
    }
    for (int i = 12; i < 16; ++i) {
        const float wheel = clamp(last_raw_[i], -1.f, 1.f);
        const float linear = physical_cmd[0] + .10f * turning * turn_common -
            .66f * (1.f + .25f * wheel_steering) * physical_cmd[2] * Side[i - 12];
        wrapped[i] = clamp(linear / (.086f * 16.f) +
            .035f * motion * (1.f - turning) * (wheel - wheel_common), -6.f, 6.f);
    }

    // Training park runtime (park_odometry=false, park_settle_joints=false):
    // wheel hold latches the observed wheel angle after 0.12 s of centered
    // quiet commands and adds a per-wheel wrapped-position feedback term.
    const std::array<float, 3> up{-obs[6], -obs[7], -obs[8]};
    const float gyro_norm = std::sqrt(s.gyro[0]*s.gyro[0] + s.gyro[1]*s.gyro[1] + s.gyro[2]*s.gyro[2]);
    float max_wheel_dq = 0.f;
    for (int i = 12; i < 16; ++i) max_wheel_dq = std::max(max_wheel_dq, std::abs(s.velocity[i]));
    const bool quiet_hold = max_wheel_dq < .5f && gyro_norm < .15f;
    constexpr float LatchTime = .12f;
    // Match the training Torch float32 comparisons exactly (integer
    // thresholds could latch one frame early).
    const bool was_latched = hold_frames_ * StepDt >= LatchTime;
    const bool centered = std::max({std::abs(physical_cmd[0]),
                                    std::abs(physical_cmd[1]),
                                    std::abs(physical_cmd[2])}) < .005f;
    hold_frames_ = (centered && (was_latched || quiet_hold)) ? hold_frames_ + 1 : 0;
    const bool latched = hold_frames_ * StepDt >= LatchTime;
    if (latched && !was_latched)
        for (std::size_t i = 0; i < 4; ++i) park_reference_[i] = obs[22 + i];
    if (latched) for (std::size_t i = 0; i < 4; ++i) {
        const float error = wrap(obs[22 + i] - park_reference_[i]);
        wrapped[12 + i] += clamp(-6.f * error, -1.5f, 1.5f) / 16.f;
    }

    // as2w_rolling_fixed_exit.rolling_precalibrated_stand with
    // continuous=true, straight_only=true: calibrate the static deflection
    // during the first 4 s of quiet centered support, then keep the frozen
    // offset with the upright blend.
    ++age_frames_;
    const float age = age_frames_ * StepDt;
    const bool quiet_bias = gyro_norm < .20f && up[2] > .92f && max_wheel_dq < .55f;
    if (age < 4.f && quiet_bias && hold_frames_ * StepDt >= .30f && activity < .05f) {
        for (std::size_t i = 0; i < 12; ++i) {
            const float correction = clamp(-1.4f * StepDt * obs[10 + i], -.004f, .004f);
            bias_[i] = clamp((1.f - .03f * StepDt) * bias_[i] + correction, -.38f, .38f);
        }
    }
    const float release_blend = clamp((hold_frames_ * StepDt - .45f) / 1.05f, 0.f, 1.f);
    const float stand_blend = age < 4.f ? 1.f : release_blend;
    const float stand_scale = clamp(1.f - activity, 0.f, 1.f);
    const float upright_scale = clamp((up[2] - .82f) / .10f, 0.f, 1.f);
    const float straight = clamp(1.f - std::abs(physical_cmd[2]) / .12f, 0.f, 1.f);
    const float bias_scale = (1.f - straight) * stand_blend * stand_scale +
                             straight * upright_scale;
    for (std::size_t i = 0; i < 12; ++i)
        wrapped[i] += bias_scale * bias_[i] / .35f;
    last_bias_scale_ = bias_scale;

    // as2w_rolling_low_speed_smooth: wrapped leg-target slew after the
    // stance addition (0.9 rad/s joint-space = 0.9*dt/0.35 normalized per
    // step); state zeroed at arm().
    const float step_limit = config_.leg_slew_rad_s * StepDt / .35f;
    for (std::size_t i = 0; i < 12; ++i) {
        slew_legs_[i] += clamp(wrapped[i] - slew_legs_[i], -step_limit, step_limit);
        wrapped[i] = slew_legs_[i];
    }
    observations_.remember(wrapped); // previous *wrapped* action, post filter/slew/hold
    const auto mapped = targets(wrapped);
    Targets result;
    result.active = true;
    result.action = wrapped;
    for (std::size_t i = 0; i < MotorCount; ++i)
        result.motors[i] = {mapped.q[i], mapped.dq[i], mapped.kp[i], mapped.kd[i]};
    return result;
}
}  // namespace as2w_r4000_deploy
