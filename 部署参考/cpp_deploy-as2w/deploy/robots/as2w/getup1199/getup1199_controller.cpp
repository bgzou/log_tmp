#include "getup1199_controller.hpp"

#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>
#include <vector>

#include <yaml-cpp/yaml.h>

namespace as2w_getup1199_deploy {
namespace {
constexpr float StepDt = .02f;
constexpr float PiF = 3.14159265358979323846f;
constexpr float WheelRadius = .086f;
// Leg geometry (locked official AS2-W URDF/XML snapshot):
// hip bodies at (+-0.2119, +-0.06, 0) (policy order FL,FR,RL,RR), thigh offset
// y +0.1054 left / -0.1054 right, both links 0.212 m, hip joint axis x,
// thigh/calf joints axis y. Wheel radius .086.
constexpr std::array<float, 4> ThighOffsetY{.1054f, -.1054f, .1054f, -.1054f};
constexpr float LinkLength = .212f;

template <class Range> bool finite(const Range& xs) {
    return std::all_of(xs.begin(), xs.end(), [](float x) { return std::isfinite(x); });
}
bool finite(float x) { return std::isfinite(x); }
template <class T, std::size_t N> std::array<T, N> read_array(const YAML::Node& n) {
    if (!n.IsSequence() || n.size() != N) throw std::runtime_error("getup1199 YAML array length");
    std::array<T, N> out{};
    for (std::size_t i = 0; i < N; ++i) out[i] = n[i].as<T>();
    return out;
}
float clamp(float x, float lo, float hi) { return std::clamp(x, lo, hi); }

std::string checked_model(const std::filesystem::path& path) {
    Ort::Env env(ORT_LOGGING_LEVEL_WARNING, "as2w_getup1199_contract");
    Ort::SessionOptions options;
    options.SetIntraOpNumThreads(1);
    Ort::Session session(env, path.c_str(), options);
    Ort::AllocatorWithDefaultOptions allocator;
    if (session.GetInputCount() != 1 || session.GetOutputCount() != 1)
        throw std::runtime_error("getup1199 expects one ONNX input and output");
    const auto input = session.GetInputNameAllocated(0, allocator);
    const auto output = session.GetOutputNameAllocated(0, allocator);
    const auto input_type = session.GetInputTypeInfo(0);
    const auto output_type = session.GetOutputTypeInfo(0);
    const auto in = input_type.GetTensorTypeAndShapeInfo();
    const auto out = output_type.GetTensorTypeAndShapeInfo();
    if (std::string(input.get()) != "obs" || std::string(output.get()) != "actions" ||
        in.GetShape() != std::vector<int64_t>{1, 42} ||
        out.GetShape() != std::vector<int64_t>{1, 12} ||
        in.GetElementType() != ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT ||
        out.GetElementType() != ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT)
        throw std::runtime_error("getup1199 ONNX tensor contract mismatch");
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
    c.effort_limit = read_array<float, MotorCount>(root["effort_limit_nm"]);
    c.angle_lower = read_array<float, LegAxisCount>(root["angle_lower_rad"]);
    c.angle_upper = read_array<float, LegAxisCount>(root["angle_upper_rad"]);
    c.staged_crouch = read_array<float, LegAxisCount>(root["staged_crouch"]);
    if (root["effort_fraction"]) c.effort_fraction = root["effort_fraction"].as<float>();
    if (root["action_scale"]) c.action_scale = root["action_scale"].as<float>();
    if (root["command_margin"]) c.command_margin = root["command_margin"].as<float>();
    if (root["guard_lookahead_s"]) c.guard_lookahead = root["guard_lookahead_s"].as<float>();
    if (root["guard_band"]) c.guard_band = root["guard_band"].as<float>();
    if (root["guard_gain"]) c.guard_gain = root["guard_gain"].as<float>();
    if (root["guard_margin"]) c.guard_margin = root["guard_margin"].as<float>();
    if (root["wheel_hold_kp"]) c.wheel_hold_kp = root["wheel_hold_kp"].as<float>();
    if (root["wheel_hold_kd"]) c.wheel_hold_kd = root["wheel_hold_kd"].as<float>();
    if (root["entry_min_up_z"]) c.entry_min_up_z = root["entry_min_up_z"].as<float>();
    if (root["entry_max_height_est"]) c.entry_max_height_est = root["entry_max_height_est"].as<float>();
    if (root["entry_wheel_quiet_dq"]) c.entry_wheel_quiet_dq = root["entry_wheel_quiet_dq"].as<float>();
    if (root["success_height"]) c.success_height = root["success_height"].as<float>();
    if (root["success_up"]) c.success_up = root["success_up"].as<float>();
    if (root["success_joint_error"]) c.success_joint_error = root["success_joint_error"].as<float>();
    if (root["success_spin"]) c.success_spin = root["success_spin"].as<float>();
    if (root["success_hold_s"]) c.success_hold_s = root["success_hold_s"].as<float>();
    if (root["getup_cap_s"]) c.getup_cap_s = root["getup_cap_s"].as<float>();
    const auto ramp = [&](float& a, float& b, const char* k) {
        if (root[k]) {
            const auto n = root[k];
            if (!n.IsSequence() || n.size() != 2) throw std::runtime_error("getup1199 ramp length");
            a = n[0].as<float>();
            b = n[1].as<float>();
        }
    };
    ramp(c.entry_ramp0, c.entry_ramp1, "staged_entry_ramp_s");
    ramp(c.plant_ramp0, c.plant_ramp1, "staged_plant_ramp_s");
    ramp(c.extend_ramp0, c.extend_ramp1, "staged_extend_ramp_s");
    if (root["staged_authority"]) c.staged_authority = root["staged_authority"].as<float>();
    if (root["stable_height"]) c.stable_height = root["stable_height"].as<float>();
    if (root["latch_quiet_s"]) c.latch_quiet_s = root["latch_quiet_s"].as<float>();
    if (root["latch_min_height"]) c.latch_min_height = root["latch_min_height"].as<float>();
    if (root["blend_tau_s"]) c.blend_tau_s = root["blend_tau_s"].as<float>();
    if (root["integral_min_height"]) c.integral_min_height = root["integral_min_height"].as<float>();
    if (root["integral_decay"]) c.integral_decay = root["integral_decay"].as<float>();
    if (root["integral_gain"]) c.integral_gain = root["integral_gain"].as<float>();
    if (root["integral_clip"]) c.integral_clip = root["integral_clip"].as<float>();
    if (c.model_version != "getup1199-deep-side-research" ||
        root["observation_size"].as<int>() != 42 || root["action_size"].as<int>() != 12 ||
        root["step_dt"].as<float>() != StepDt || !finite(c.defaults) || !finite(c.stiffness) ||
        !finite(c.damping) || !finite(c.effort_limit) || !finite(c.angle_lower) ||
        !finite(c.angle_upper) || !finite(c.staged_crouch) || !finite(c.action_scale) ||
        c.effort_fraction <= .5f || c.effort_fraction > .95f ||
        c.action_scale <= 0.f || c.action_scale > 1.f ||
        c.latch_quiet_s <= 0.f || c.blend_tau_s <= 0.f || c.integral_gain <= 0.f ||
        c.guard_band <= 0.f || c.guard_gain <= 0.f)
        throw std::runtime_error("getup1199 deploy contract mismatch");
    for (std::size_t i = 0; i < MotorCount; ++i) {
        if (c.joint_names[i].empty() ||
            std::abs(c.defaults[i] - Defaults[i]) > 1e-5f ||
            std::abs(c.stiffness[i] - (i < 12 ? 85.f : 25.f)) > 1e-5f ||
            std::abs(c.damping[i] - (i < 12 ? 3.2f : 4.f)) > 1e-5f)
            throw std::runtime_error("getup1199 q/default/gain contract mismatch");
    }
    return c;
}

float Controller::height_estimate(const Legs& q) {
    // Wheel axle z in base frame per leg, then min over legs of
    // (wheel radius - z_axle). Assumes the wheel touches the ground.
    float zmin = 1e9f;
    for (std::size_t k = 0; k < 4; ++k) {
        const float h = q[k], t = q[4 + k], c = q[8 + k];
        const float z = ThighOffsetY[k] * std::sin(h) +
                        (-LinkLength * std::cos(t) - LinkLength * std::cos(t + c)) * std::cos(h);
        zmin = std::min(zmin, WheelRadius - z);
    }
    return zmin;
}

Controller::Controller(Config config)
    : config_(std::move(config)), runner_(checked_model(config_.onnx)) {}

void Controller::arm() {
    previous_action_.fill(0.f);
    initial_norm_.fill(0.f);
    bias_.fill(0.f);
    last_raw_.fill(0.f);
    last_command_.fill(0.f);
    wheel_reference_.fill(0.f);
    last_obs_.fill(0.f);
    policy_frames_ = steady_frames_ = latch_frames_ = 0;
    blend_ = last_height_ = last_up_ = 0.f;
    armed_ = true;
    initialized_ = false;
}
void Controller::stop() { armed_ = false; }

Targets Controller::step(const SensorState& s, float age_seconds) {
    if (!armed_) return {};
    if (!finite(age_seconds) || age_seconds < 0.f || age_seconds > .05f ||
        !finite(s.gyro) || !finite(s.body_to_world_wxyz) ||
        !finite(s.position) || !finite(s.velocity)) { stop(); return {}; }
    const auto& qw = s.body_to_world_wxyz;
    const float norm2 = std::inner_product(qw.begin(), qw.end(), qw.begin(), 0.f);
    if (norm2 < .81f || norm2 > 1.21f) { stop(); return {}; }
    const float inv = 1.f / std::sqrt(norm2);
    const float w = qw[0] * inv, x = qw[1] * inv, y = qw[2] * inv, z = qw[3] * inv;

    Legs q{}, dq{};
    for (std::size_t i = 0; i < 12; ++i) { q[i] = s.position[i]; dq[i] = s.velocity[i]; }
    if (!initialized_) {
        for (std::size_t i = 0; i < 12; ++i)
            initial_norm_[i] = (q[i] - Defaults[i]) / config_.action_scale;
        for (std::size_t i = 0; i < 4; ++i) wheel_reference_[i] = s.position[12 + i];
        initialized_ = true;
    }

    // obs: gravity convention = -third row of the body-to-world rotation
    // (upright z = -1; the same numeric formula as the r4000 observations).
    Features obs{};
    for (std::size_t i = 0; i < 3; ++i) obs[i] = s.gyro[i];
    obs[3] = -2.f * (x * z - w * y);
    obs[4] = -2.f * (y * z + w * x);
    obs[5] = 2.f * (x * x + y * y) - 1.f;
    const float up = -obs[5];
    for (std::size_t i = 0; i < 12; ++i) {
        obs[6 + i] = q[i] - Defaults[i];
        obs[18 + i] = dq[i];
        obs[30 + i] = previous_action_[i];
    }
    last_obs_ = obs;
    last_up_ = up;
    last_height_ = height_estimate(q);

    auto output = runner_.forward({{"obs", std::vector<float>(obs.begin(), obs.end())}}).at("actions");
    if (output.size() != LegAxisCount || !finite(output)) { stop(); return {}; }
    for (std::size_t i = 0; i < LegAxisCount; ++i) last_raw_[i] = output[i];

    // as2w_recovery_control.staged_target: hold the latched pose, blend to
    // the crouch anchor, fade out after 1.45 s while the policy ramps in.
    ++policy_frames_;
    const float age = (policy_frames_ - 1) * StepDt;
    // Ramp keys are [start, duration] (as2w_recovery_control:
    // ((age - start) / duration).clamp(0, 1)).
    const float entry = clamp((age - config_.entry_ramp0) / config_.entry_ramp1, 0.f, 1.f);
    const float plant = clamp((age - config_.plant_ramp0) / config_.plant_ramp1, 0.f, 1.f);
    const float extend = clamp((age - config_.extend_ramp0) / config_.extend_ramp1, 0.f, 1.f);
    Legs target{};
    for (std::size_t i = 0; i < LegAxisCount; ++i) {
        const float prior = (initial_norm_[i] +
                             plant * (config_.staged_crouch[i] / config_.action_scale - initial_norm_[i])) *
                            (1.f - extend);
        target[i] = prior + config_.staged_authority * entry * last_raw_[i];
    }

    // Deployment estimators (validated against the training evaluator,
    // logs/20261113_getup1199_deploy_precheck): leg-FK height, wheel
    // quietness proxy for contact, wheel-odometry speed proxy.
    float max_wheel_dq = 0.f;
    for (std::size_t i = 12; i < MotorCount; ++i)
        max_wheel_dq = std::max(max_wheel_dq, std::abs(s.velocity[i]));
    const float speed_est = WheelRadius * max_wheel_dq;
    const bool wheel_quiet = max_wheel_dq < .35f;
    const float gyro_norm = std::sqrt(s.gyro[0] * s.gyro[0] + s.gyro[1] * s.gyro[1] + s.gyro[2] * s.gyro[2]);

    const bool stable = last_height_ > config_.stable_height && up > .95f &&
                        wheel_quiet && speed_est < .08f && gyro_norm < .18f;
    steady_frames_ = stable ? steady_frames_ + 1 : 0;
    const bool begin = steady_frames_ * StepDt >= config_.latch_quiet_s;
    const bool viable = last_height_ > config_.latch_min_height && up > .90f;
    latch_frames_ = (viable && (begin || latch_frames_ > 0)) ? latch_frames_ + 1 : 0;
    blend_ = clamp(latch_frames_ * StepDt / config_.blend_tau_s, 0.f, 1.f);

    // as2w_recovery_control.stand_integral with fixed_stand_integral=true.
    const bool enabled = blend_ >= .80f && up > .93f && last_height_ > config_.integral_min_height;
    Legs wrapped{};
    for (std::size_t i = 0; i < LegAxisCount; ++i) {
        if (enabled) {
            const float error = obs[6 + i];  // measured q - defaults
            bias_[i] = clamp((1.f - config_.integral_decay * StepDt) * bias_[i] -
                                 config_.integral_gain * StepDt * error,
                             -config_.integral_clip, config_.integral_clip);
        } else {
            bias_[i] = 0.f;
        }
        wrapped[i] = target[i] * (1.f - blend_) + blend_ * bias_[i] / config_.action_scale;
    }
    previous_action_ = wrapped;

    // 90% envelope command clip (training `command` variable, pre guard).
    for (std::size_t i = 0; i < LegAxisCount; ++i) {
        const float lower = Defaults[i] + .90f * (config_.angle_lower[i] - Defaults[i]);
        const float upper = Defaults[i] + .90f * (config_.angle_upper[i] - Defaults[i]);
        last_command_[i] = clamp(Defaults[i] + config_.action_scale * wrapped[i],
                                 lower + config_.command_margin, upper - config_.command_margin);
    }

    const Legs guarded = guard(s.position, s.velocity);
    Targets result;
    result.active = true;
    result.action = wrapped;
    for (std::size_t i = 0; i < LegAxisCount; ++i) {
        result.motors[i] = {guarded[i], 0.f, config_.stiffness[i], config_.damping[i]};
    }
    for (std::size_t i = 12; i < MotorCount; ++i) {
        result.motors[i] = {wheel_reference_[i - 12], 0.f, config_.wheel_hold_kp, config_.wheel_hold_kd};
    }
    return result;
}

Targets Controller::step(const SensorState& sensors, const Vector3& command,
                         float age_seconds) {
    if (command[0] != 0.f || command[1] != 0.f || command[2] != 0.f) {
        stop();
        return {};
    }
    return step(sensors, age_seconds);
}

Legs Controller::guard(const Motors& position, const Motors& velocity) const {
    // as2w_predictive_joint_guard.guarded_target on the 90% envelope.
    Legs out = last_command_;
    for (std::size_t i = 0; i < LegAxisCount; ++i) {
        const float lower = Defaults[i] + .90f * (config_.angle_lower[i] - Defaults[i]);
        const float upper = Defaults[i] + .90f * (config_.angle_upper[i] - Defaults[i]);
        const float predicted = position[i] + config_.guard_lookahead * velocity[i];
        const float lower_risk = clamp(lower + config_.guard_band - predicted, 0.f, config_.guard_band * 1.2f);
        const float upper_risk = clamp(predicted - (upper - config_.guard_band), 0.f, config_.guard_band * 1.2f);
        out[i] = clamp(last_command_[i] + config_.guard_gain * (lower_risk - upper_risk),
                       lower + config_.guard_margin, upper - config_.guard_margin);
    }
    return out;
}
}  // namespace as2w_getup1199_deploy
