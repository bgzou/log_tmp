// Gated AS2-W LowCmd publisher. This program is NOT approved for robot use.
// LowCmd direction, wheel command semantics, loss-of-writer behavior and the
// emergency remote path still require device-specific tests and consent.
// CMake AS2W_R152_PUBLISH defaults OFF. Do not add this binary to field.sh.
#include "r152_controller.hpp"

#include <unitree/idl/hg/LowCmd_.hpp>
#include <unitree/idl/hg/LowState_.hpp>
#include <unitree/robot/channel/channel_factory.hpp>
#include <unitree/robot/channel/channel_publisher.hpp>
#include <unitree/robot/channel/channel_subscriber.hpp>

#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cmath>
#include <csignal>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <thread>

namespace {
using Clock = std::chrono::steady_clock;
using LowState = unitree_hg::msg::dds_::LowState_;
using LowCmd = unitree_hg::msg::dds_::LowCmd_;
using as2w_r152::Config;
using as2w_r152::Controller;
using as2w_r152::MotorCount;
using as2w_r152::SensorState;
using as2w_r152::Targets;
using as2w_r152::Vector3;

struct Axis { std::size_t index; float sign, zero; };
using Mapping = std::array<Axis, MotorCount>;
using Pose = std::array<float, MotorCount>;

Mapping read_mapping(const Config& config, const std::string& path) {
    std::ifstream file(path);
    if (!file) throw std::runtime_error("Cannot open motor mapping: " + path);
    std::set<std::size_t> used;
    Mapping map{};
    const auto slots = LowState{}.motor_state().size();
    for (std::size_t i = 0; i < map.size(); ++i) {
        std::string name;
        auto& a = map[i];
        if (!(file >> name >> a.index >> a.sign >> a.zero) ||
            name != config.joint_names[i] || a.index >= slots ||
            !used.insert(a.index).second || std::abs(a.sign) != 1.f ||
            !std::isfinite(a.zero))
            throw std::runtime_error("Invalid or incomplete motor mapping");
    }
    std::string extra;
    if (file >> extra) throw std::runtime_error("Unexpected mapping data");
    return map;
}

uint32_t crc32Core(const uint32_t* ptr, uint32_t len) {
    uint32_t crc = 0xFFFFFFFFu;
    for (uint32_t i = 0; i < len; ++i) {
        uint32_t mask = 0x80000000u;
        const uint32_t data = ptr[i];
        for (unsigned bit = 0; bit < 32; ++bit) {
            crc = (crc & 0x80000000u) ? (crc << 1) ^ 0x04c11db7u : crc << 1;
            if (data & mask) crc ^= 0x04c11db7u;
            mask >>= 1;
        }
    }
    return crc;
}

Pose stand_pose(const Config& config, const std::string& variant) {
    if (variant == "t2") return config.defaults;
    if (variant != "t1") throw std::runtime_error("--stand must be t1 or t2");
    Pose p{};
    p[0] = 0.1298f; p[1] = -0.1213f; p[2] = 0.1215f; p[3] = -0.1308f;
    for (int i = 4; i < 8; ++i) p[i] = 0.60f;
    for (int i = 8; i < 12; ++i) p[i] = -1.23f;
    return p;
}

struct Snapshot {
    LowState frame{};
    Clock::time_point received{};
    bool valid = false;
    float age_ms = 1e6f;
    float upright = -1.f;
};
struct SharedState {
    std::mutex mutex;
    LowState frame{};
    Clock::time_point received{};
    unsigned count = 0, crc_bad = 0;
    Snapshot get() {
        std::lock_guard<std::mutex> lock(mutex);
        Snapshot s;
        if (count) {
            s.frame = frame;
            s.received = received;
            s.valid = true;
            s.age_ms = std::chrono::duration<float, std::milli>(
                Clock::now() - received).count();
            const auto& q = s.frame.imu_state().quaternion();
            s.upright = 1.f - 2.f * (q[1]*q[1] + q[2]*q[2]);
        }
        return s;
    }
};

struct Remote {
    bool valid = false;
    uint16_t buttons = 0, pressed = 0;
    float lx = 0, ly = 0, rx = 0;
};
template<class Bytes>
float read_float(const Bytes& bytes, int offset) {
    float value = 0;
    std::memcpy(&value, &bytes[offset], sizeof(value));
    return std::isfinite(value) ? value : 0.f;
}
Remote decode_remote(const Snapshot& s, uint16_t prior) {
    Remote r;
    if (!s.valid || s.age_ms > 50.f) return r;
    const auto& b = s.frame.wireless_remote();
    if (b.size() != 40 || uint8_t(b[0]) != 0x55 || uint8_t(b[1]) != 0x51)
        return r;
    r.valid = true;
    r.buttons = uint16_t(uint8_t(b[2])) | (uint16_t(uint8_t(b[3])) << 8);
    r.pressed = r.buttons & ~prior;
    r.lx = read_float(b, 4);
    r.rx = read_float(b, 8);
    r.ly = read_float(b, 20);
    return r;
}

Pose measured_pose(const Snapshot& s, const Mapping& map) {
    Pose q{};
    for (std::size_t i = 0; i < MotorCount; ++i)
        q[i] = map[i].sign * (s.frame.motor_state()[map[i].index].q() - map[i].zero);
    return q;
}
Targets pose_targets(const Pose& q, float kp) {
    Targets t{};
    for (std::size_t i = 0; i < MotorCount; ++i) {
        t.motors[i].q = q[i];
        t.motors[i].dq = 0.f;
        t.motors[i].kp = i < 12 ? kp : 0.f;
        t.motors[i].kd = 2.f;
    }
    t.active = true;
    return t;
}
void fill_passive(LowCmd& cmd, const LowState& s, const Mapping& map, float kd) {
    cmd.mode_pr() = 0;
    cmd.mode_machine() = s.mode_machine();
    for (const auto& a : map) {
        auto& m = cmd.motor_cmd()[a.index];
        m.mode() = 0x01;
        m.q() = s.motor_state()[a.index].q();
        m.dq() = 0.f; m.kp() = 0.f; m.kd() = kd; m.tau() = 0.f;
    }
}
void fill_targets(LowCmd& cmd, const LowState& s, const Mapping& map,
                  const Targets& target) {
    cmd.mode_pr() = 0;
    cmd.mode_machine() = s.mode_machine();
    for (std::size_t i = 0; i < MotorCount; ++i) {
        const auto& a = map[i];
        auto& m = cmd.motor_cmd()[a.index];
        m.mode() = 0x01;
        m.kp() = target.motors[i].kp; m.kd() = target.motors[i].kd;
        m.tau() = 0.f;
        if (i < 12) {
            // Device command direction is still UNVERIFIED. Never run until tested.
            m.q() = a.sign * target.motors[i].q + a.zero;
            m.dq() = 0.f;
        } else {
            m.q() = 0.f;
            m.dq() = a.sign * target.motors[i].dq;
        }
    }
}
void finish(LowCmd& cmd) {
    cmd.crc() = crc32Core(reinterpret_cast<const uint32_t*>(&cmd),
                          (sizeof(LowCmd) >> 2) - 1);
}

enum class Kind { Passive, FixStand, Stand, R152, ReturnStand, FixSquat };
const char* name(Kind k) {
    switch (k) {
    case Kind::Passive: return "Passive";
    case Kind::FixStand: return "FixStand";
    case Kind::Stand: return "Stand";
    case Kind::R152: return "R152";
    case Kind::ReturnStand: return "ReturnStand";
    case Kind::FixSquat: return "FixSquat";
    }
    return "?";
}
struct Transition { Kind to; const char* why; };
struct Context {
    const Config& config;
    const Mapping& mapping;
    Controller& controller;
    Pose stand;
    float interp_sec;
    std::mutex target_mutex;
    Targets target{};
    bool active = false;
    bool latched = false;
    void publish_target(const Targets& t) {
        std::lock_guard<std::mutex> lock(target_mutex);
        target = t;
        active = true;
    }
    void passive() {
        std::lock_guard<std::mutex> lock(target_mutex);
        active = false;
    }
};
class State {
public:
    virtual ~State() = default;
    virtual Kind kind() const = 0;
    virtual void enter(Context&, const Snapshot&) = 0;
    virtual std::optional<Transition> run(Context&, const Snapshot&, const Remote&) = 0;
    virtual void exit(Context&) {}
};
class Passive final : public State {
public:
    Kind kind() const override { return Kind::Passive; }
    void enter(Context& c, const Snapshot&) override { c.controller.stop(); c.passive(); }
    std::optional<Transition> run(Context& c, const Snapshot& s, const Remote& r) override {
        c.passive();
        if (!c.latched && s.valid && r.valid && (r.pressed & (1u << 8)))
            return Transition{Kind::FixStand, "remote A"};
        return {};
    }
};
class FixStand final : public State {
    Clock::time_point t0_{};
    Pose start_{}, preload_{}, after_pre_{};
    bool second_ = false;
public:
    Kind kind() const override { return Kind::FixStand; }
    void enter(Context& c, const Snapshot& s) override {
        start_ = measured_pose(s, c.mapping);
        preload_ = start_;
        for (int i = 4; i < 8; ++i) preload_[i] += 0.25f;
        second_ = false;
        t0_ = Clock::now();
        c.publish_target(pose_targets(start_, 20.f));
    }
    std::optional<Transition> run(Context& c, const Snapshot& s, const Remote&) override {
        const float elapsed = std::chrono::duration<float>(Clock::now()-t0_).count();
        const float pre_sec = c.interp_sec * 0.6f;
        if (!second_ && elapsed >= pre_sec) {
            after_pre_ = measured_pose(s, c.mapping);
            second_ = true;
        }
        if (elapsed >= c.interp_sec) return Transition{Kind::Stand, "FixStand complete"};
        Pose q{};
        if (!second_) {
            const float alpha = std::clamp(elapsed/pre_sec, 0.f, 1.f);
            for (int i = 0; i < 12; ++i)
                q[i] = start_[i] + alpha*(preload_[i]-start_[i]);
            c.publish_target(pose_targets(q, 20.f));
        } else {
            const float alpha = std::clamp((elapsed-pre_sec) /
                                           (c.interp_sec-pre_sec), 0.f, 1.f);
            for (int i = 0; i < 12; ++i)
                q[i] = after_pre_[i] + alpha*(c.stand[i]-after_pre_[i]);
            c.publish_target(pose_targets(q, 55.f));
        }
        return {};
    }
};
std::optional<Transition> policy_tick(Context& c, const Snapshot& s,
                                       const Vector3& command) {
    SensorState sensors{};
    const auto& imu = s.frame.imu_state();
    std::copy(imu.gyroscope().begin(), imu.gyroscope().end(), sensors.gyro.begin());
    std::copy(imu.quaternion().begin(), imu.quaternion().end(),
              sensors.body_to_world_wxyz.begin());
    for (std::size_t i = 0; i < MotorCount; ++i) {
        const auto& a = c.mapping[i];
        sensors.position[i] = a.sign*(s.frame.motor_state()[a.index].q()-a.zero);
        sensors.velocity[i] = a.sign*s.frame.motor_state()[a.index].dq();
    }
    auto t = c.controller.step(sensors, command, s.age_ms*0.001f);
    if (!t.active) return Transition{Kind::Passive, "controller inactive"};
    c.publish_target(t);
    return {};
}
class Stand final : public State {
public:
    Kind kind() const override { return Kind::Stand; }
    void enter(Context& c, const Snapshot&) override {
        c.controller.stop();
        c.publish_target(pose_targets(c.stand, 55.f));
    }
    std::optional<Transition> run(Context& c, const Snapshot& s, const Remote& r) override {
        c.publish_target(pose_targets(c.stand, 55.f));
        if (r.valid && (r.pressed & (1u << 9)))
            return Transition{Kind::R152, "remote B enable walking"};
        if (r.valid && (r.pressed & (1u << 11)))
            return Transition{Kind::FixSquat, "remote Y controlled squat"};
        return {};
    }
};
class R152 final : public State {
public:
    Kind kind() const override { return Kind::R152; }
    void enter(Context& c, const Snapshot&) override {
        if (!c.controller.armed()) c.controller.arm();
    }
    std::optional<Transition> run(Context& c, const Snapshot& s, const Remote& r) override {
        // First-robot domain: forward only, 0..0.2 m/s. vy/wz are locked to 0.
        // No undocumented controller-axis behavior is assumed.
        const float ly = r.valid && std::abs(r.ly) > 0.05f ? r.ly : 0.f;
        const Vector3 command{std::clamp(ly*0.2f, 0.f, 0.2f), 0.f, 0.f};
        if (auto fault = policy_tick(c, s, command)) return fault;
        if (r.valid && (r.pressed & (1u << 8)))
            return Transition{Kind::ReturnStand, "remote A brake then fixed stand"};
        return {};
    }
};
class ReturnStand final : public State {
    enum class Phase { Brake, Interpolate };
    Phase phase_ = Phase::Brake;
    Clock::time_point started_{}, stable_since_{}, interp_started_{};
    Pose start_{};
public:
    Kind kind() const override { return Kind::ReturnStand; }
    void enter(Context&, const Snapshot&) override {
        phase_ = Phase::Brake;
        started_ = Clock::now();
        stable_since_ = Clock::time_point{};
    }
    std::optional<Transition> run(Context& c, const Snapshot& s, const Remote&) override {
        const auto now = Clock::now();
        if (phase_ == Phase::Brake) {
            // Keep policy balance while commanding zero speed. Do not switch
            // to fixed PD until the four measured wheel speeds have settled.
            if (auto fault = policy_tick(c, s, Vector3{})) return fault;
            float wheel_max = 0.f;
            for (std::size_t i = 12; i < MotorCount; ++i)
                wheel_max = std::max(wheel_max,
                    std::abs(s.frame.motor_state()[c.mapping[i].index].dq()));
            if (wheel_max < 0.5f) {
                if (stable_since_ == Clock::time_point{}) stable_since_ = now;
            } else stable_since_ = Clock::time_point{};
            if (stable_since_ != Clock::time_point{} &&
                now - stable_since_ >= std::chrono::milliseconds(300)) {
                start_ = measured_pose(s, c.mapping);
                c.controller.stop();
                c.publish_target(pose_targets(start_, 35.f));
                phase_ = Phase::Interpolate;
                interp_started_ = now;
                return {};
            }
            if (now - started_ > std::chrono::seconds(3))
                return Transition{Kind::Passive, "ReturnStand brake timeout"};
            return {};
        }
        constexpr float duration = 1.5f;
        const float elapsed = std::chrono::duration<float>(now-interp_started_).count();
        if (elapsed >= duration) return Transition{Kind::Stand, "ReturnStand complete"};
        const float alpha = std::clamp(elapsed/duration, 0.f, 1.f);
        Pose q{};
        for (int i = 0; i < 12; ++i)
            q[i] = start_[i] + alpha*(c.stand[i]-start_[i]);
        c.publish_target(pose_targets(q, 35.f + 20.f*alpha));
        return {};
    }
};
class FixSquat final : public State {
    Clock::time_point t0_{};
    Pose start_{}, fold_{}, after_fold_{}, prone_{};
    bool second_ = false;
    static constexpr float duration_ = 2.5f;
public:
    Kind kind() const override { return Kind::FixSquat; }
    void enter(Context& c, const Snapshot& s) override {
        c.controller.stop();
        start_ = measured_pose(s, c.mapping);
        fold_ = start_;
        for (int i = 4; i < 8; ++i) fold_[i] += 0.6f;
        for (int i = 8; i < 12; ++i) fold_[i] *= 0.5f;
        prone_ = Pose{-0.5676f, 0.5725f, -0.5930f, 0.6040f,
                      1.f,1.f,1.f,1.f,-2.75f,-2.75f,-2.75f,-2.75f,
                      0.f,0.f,0.f,0.f};
        second_ = false;
        t0_ = Clock::now();
        c.publish_target(pose_targets(start_, 35.f));
    }
    std::optional<Transition> run(Context& c, const Snapshot& s, const Remote&) override {
        const float elapsed = std::chrono::duration<float>(Clock::now()-t0_).count();
        if (!second_ && elapsed >= duration_*0.5f) {
            after_fold_ = measured_pose(s, c.mapping);
            second_ = true;
        }
        if (elapsed >= duration_+1.f) return Transition{Kind::Passive, "FixSquat complete"};
        Pose q{};
        float kp = 0.f;
        if (!second_) {
            const float alpha = std::clamp(elapsed/(duration_*0.5f), 0.f, 1.f);
            for (int i = 0; i < 12; ++i)
                q[i] = start_[i] + alpha*(fold_[i]-start_[i]);
            kp = 35.f;
        } else {
            const float alpha = std::clamp((elapsed-duration_*0.5f) /
                                           (duration_*0.5f), 0.f, 1.f);
            for (int i = 0; i < 12; ++i)
                q[i] = after_fold_[i] + alpha*(prone_[i]-after_fold_[i]);
            kp = elapsed < duration_ ? 20.f : 10.f;
        }
        c.publish_target(pose_targets(q, kp));
        return {};
    }
};

std::atomic<bool> g_terminal_safe{false};
void log_transition(Kind from, Kind to, const char* reason) {
    const auto now = std::chrono::system_clock::now();
    const auto seconds = std::chrono::duration<double>(now.time_since_epoch()).count();
    std::cout << std::fixed << std::setprecision(3) << "FSM " << seconds << " "
              << name(from) << " -> " << name(to) << " reason=" << reason << std::endl;
}
} // namespace

int main(int argc, char** argv) {
    try {
        std::string yaml, map_path, nic, stand_variant = "t1";
        float passive_kd = 5.f, interp_sec = 2.5f;
        bool confirmed = false;
        for (int i = 1; i < argc; ++i) {
            const std::string arg = argv[i];
            auto next = [&]() -> std::string {
                if (i+1 >= argc) throw std::runtime_error("Missing value after " + arg);
                return argv[++i];
            };
            if (arg == "--i-confirm-lowcmd-publish") confirmed = true;
            else if (arg == "--passive-kd") passive_kd = std::stof(next());
            else if (arg == "--interp-sec") interp_sec = std::stof(next());
            else if (arg == "--stand") stand_variant = next();
            else if (yaml.empty()) yaml = arg;
            else if (map_path.empty()) map_path = arg;
            else if (nic.empty()) nic = arg;
            else throw std::runtime_error("Unexpected argument: " + arg);
        }
        if (!confirmed || yaml.empty() || map_path.empty() || nic.empty()) {
            std::cerr << "Usage: as2w_r152_publish DEPLOY_YAML MEASURED_MAP NIC "
                         "--i-confirm-lowcmd-publish [--passive-kd 5] "
                         "[--interp-sec 2.5] [--stand t1|t2]\n";
            return 2;
        }
        if (!(passive_kd > 0.f && passive_kd <= 10.f && interp_sec >= 2.f &&
              interp_sec <= 4.f))
            throw std::runtime_error("Passive kd or interpolation duration out of range");
        const auto config = as2w_r152::load_config(yaml);
        const auto map = read_mapping(config, map_path);
        Controller controller(config);
        Context ctx{config, map, controller, stand_pose(config, stand_variant),
                    interp_sec};

        std::cout << "WARNING: publishes 500 Hz LowCmd. Device contract gates and "
                     "specific field consent are mandatory. X is emergency damping. "
                     "A: prone->stand or walking->brake->fixed stand, B: walk enable, "
                     "Y: controlled squat from Stand. Press Enter to start Passive.\n";
        std::string line;
        if (!std::getline(std::cin, line))
            throw std::runtime_error("No interactive confirmation");
        std::signal(SIGINT, [](int) { g_terminal_safe = true; });
        std::thread([] {
            std::string key;
            while (std::getline(std::cin, key))
                if (key == "q") g_terminal_safe = true;
        }).detach();

        unitree::robot::ChannelFactory::Instance()->Init(0, nic.c_str());
        SharedState shared;
        unitree::robot::ChannelSubscriber<LowState> subscriber("rt/lowstate");
        subscriber.InitChannel([&](const void* message) {
            const auto* f = static_cast<const LowState*>(message);
            if (crc32Core(reinterpret_cast<const uint32_t*>(f),
                          (sizeof(LowState) >> 2)-1) != f->crc()) {
                std::lock_guard<std::mutex> lock(shared.mutex);
                ++shared.crc_bad;
                return;
            }
            std::lock_guard<std::mutex> lock(shared.mutex);
            shared.frame = *f; shared.received = Clock::now(); ++shared.count;
        }, 1);
        unitree::robot::ChannelPublisher<LowCmd> publisher("rt/lowcmd");
        publisher.InitChannel();

        // Do not send a single frame before a current CRC-validated state exists.
        // If state goes stale after arming, keep sending damping frames based on
        // the last known mode_machine; firmware loss-of-writer semantics unknown.
        std::thread writer([&] {
            auto next = Clock::now();
            for (;;) {
                next += std::chrono::milliseconds(2);
                std::this_thread::sleep_until(next);
                const auto s = shared.get();
                if (!s.valid) continue;
                LowCmd cmd{};
                {
                    std::lock_guard<std::mutex> lock(ctx.target_mutex);
                    if (ctx.active && s.age_ms <= 50.f && !g_terminal_safe)
                        fill_targets(cmd, s.frame, map, ctx.target);
                    else fill_passive(cmd, s.frame, map, passive_kd);
                }
                finish(cmd);
                publisher.Write(cmd);
            }
        });

        Passive passive; FixStand fixstand; Stand stand; R152 r152;
        ReturnStand returnstand; FixSquat fixsquat;
        auto resolve = [&](Kind k) -> State* {
            switch (k) {
            case Kind::Passive: return &passive;
            case Kind::FixStand: return &fixstand;
            case Kind::Stand: return &stand;
            case Kind::R152: return &r152;
            case Kind::ReturnStand: return &returnstand;
            case Kind::FixSquat: return &fixsquat;
            }
            return &passive;
        };
        State* current = &passive;
        current->enter(ctx, shared.get());
        uint16_t old_buttons = 0;
        auto next = Clock::now();
        for (;;) {
            next += std::chrono::milliseconds(20);
            std::this_thread::sleep_until(next);
            const auto s = shared.get();
            const auto r = decode_remote(s, old_buttons);
            old_buttons = r.valid ? r.buttons : 0;
            std::optional<Transition> change;
            // Global rules have priority over all state-local transitions.
            if (g_terminal_safe) {
                ctx.latched = true;
                if (current->kind() != Kind::Passive)
                    change = Transition{Kind::Passive, "terminal q/SIGINT"};
            } else if (!s.valid || s.age_ms > 50.f || s.upright < -0.2f) {
                if (current->kind() != Kind::Passive) {
                    ctx.latched = true;
                    change = Transition{Kind::Passive, "LowState/attitude watchdog"};
                }
            } else if (r.valid && (r.pressed & (1u << 10))) {
                ctx.latched = true;
                if (current->kind() != Kind::Passive)
                    change = Transition{Kind::Passive, "remote X emergency damping"};
            } else {
                change = current->run(ctx, s, r);
            }
            if (change && change->to != current->kind()) {
                const auto from = current->kind();
                current->exit(ctx);
                if (change->to == Kind::Passive) ctx.passive();
                current = resolve(change->to);
                current->enter(ctx, s);
                log_transition(from, current->kind(), change->why);
            }
        }
        writer.join();
        subscriber.CloseChannel();
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
