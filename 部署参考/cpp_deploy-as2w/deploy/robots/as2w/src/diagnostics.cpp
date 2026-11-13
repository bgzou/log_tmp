#include "policy.hpp"

#include <unitree/idl/go2/SportModeState_.hpp>
#include <unitree/idl/go2/WirelessController_.hpp>
#include <unitree/idl/hg/LowCmd_.hpp>
#include <unitree/idl/hg/LowState_.hpp>
#include <unitree/idl/hg/MainBoardState_.hpp>
#include <unitree/robot/as2/sport/sport_client.hpp>
#include <unitree/robot/b2/motion_switcher/motion_switcher_client.hpp>
#include <unitree/robot/b2/robot_state/robot_state_client.hpp>
#include <unitree/robot/channel/channel_subscriber.hpp>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <functional>
#include <iomanip>
#include <iostream>
#include <map>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

namespace {
using Clock = std::chrono::steady_clock;
using LowState = unitree_hg::msg::dds_::LowState_;
using MainBoardState = unitree_hg::msg::dds_::MainBoardState_;
using SportState = unitree_go::msg::dds_::SportModeState_;
using RemoteState = unitree_go::msg::dds_::WirelessController_;
using unitree::robot::ChannelSubscriber;

struct LatestLow {
    std::mutex mutex;
    LowState state{};
    Clock::time_point received{};
    unsigned count = 0;
};

int seconds(const char* text) {
    const int value = std::stoi(text);
    if (value < 1 || value > 300) throw std::invalid_argument("Seconds must be 1..300");
    return value;
}

void subscribeLow(LatestLow& latest, const std::string& topic,
                  const std::function<void()>& body) {
    ChannelSubscriber<LowState> subscriber(topic);
    subscriber.InitChannel([&](const void* message) {
        std::lock_guard<std::mutex> guard(latest.mutex);
        latest.state = *static_cast<const LowState*>(message);
        latest.received = Clock::now();
        ++latest.count;
    }, 1);
    body();
    subscriber.CloseChannel();
}

void sportState(int duration) {
    std::mutex mutex;
    SportState latest{};
    unsigned count = 0;
    ChannelSubscriber<SportState> subscriber("rt/lf/sportmodestate");
    subscriber.InitChannel([&](const void* message) {
        std::lock_guard<std::mutex> guard(mutex);
        latest = *static_cast<const SportState*>(message);
        ++count;
    }, 1);
    for (int i = 0; i < duration; ++i) {
        std::this_thread::sleep_for(std::chrono::seconds(1));
        std::lock_guard<std::mutex> guard(mutex);
        std::cout << "sport packets=" << count;
        if (count) std::cout << " mode=" << unsigned(latest.mode())
                             << " velocity=" << latest.velocity()[0] << ','
                             << latest.velocity()[1] << ',' << latest.velocity()[2];
        std::cout << std::endl;
    }
    if (!count) throw std::runtime_error("No SportModeState packets");
}

void remoteState(int duration) {
    std::mutex mutex;
    RemoteState latest{};
    Clock::time_point received{};
    unsigned count = 0;
    ChannelSubscriber<RemoteState> subscriber("rt/wirelesscontroller");
    subscriber.InitChannel([&](const void* message) {
        std::lock_guard<std::mutex> guard(mutex);
        latest = *static_cast<const RemoteState*>(message);
        received = Clock::now();
        ++count;
    }, 1);
    for (int i = 0; i < duration; ++i) {
        std::this_thread::sleep_for(std::chrono::seconds(1));
        std::lock_guard<std::mutex> guard(mutex);
        std::cout << "remote packets=" << count;
        if (count) {
            const auto age = std::chrono::duration<float>(Clock::now() - received).count();
            std::cout << " age_s=" << age << " lx=" << latest.lx()
                      << " ly=" << latest.ly() << " rx=" << latest.rx()
                      << " ry=" << latest.ry() << " keys=0x" << std::hex
                      << latest.keys() << std::dec;
        }
        std::cout << std::endl;
    }
    if (!count) throw std::runtime_error("No WirelessController packets");
}

void lowState(const std::string& topic, int duration) {
    LatestLow latest;
    subscribeLow(latest, topic, [&] {
        for (int i = 0; i < duration; ++i) {
            std::this_thread::sleep_for(std::chrono::seconds(1));
            std::lock_guard<std::mutex> guard(latest.mutex);
            std::cout << "low packets=" << latest.count;
            if (latest.count) {
                std::cout << " tick=" << latest.state.tick()
                          << " mode_pr=" << unsigned(latest.state.mode_pr())
                          << " mode_machine=" << unsigned(latest.state.mode_machine());
                const auto& imu = latest.state.imu_state();
                std::cout << " imu_wxyz=";
                for (const auto value : imu.quaternion()) std::cout << value << ',';
                std::cout << " gyro=";
                for (const auto value : imu.gyroscope()) std::cout << value << ',';
                for (std::size_t j = 0; j < latest.state.motor_state().size(); ++j) {
                    const auto& motor = latest.state.motor_state()[j];
                    std::cout << " m" << j << "=" << motor.q() << ',' << motor.dq();
                }
            }
            std::cout << std::endl;
        }
    });
    if (!latest.count) throw std::runtime_error("No compatible HG LowState packets");
}

// CRC32 per SDK2 G1/B2 low-level examples: polynomial 0x04c11db7, init 0xFFFFFFFF,
// over the first (sizeof(msg)>>2)-1 32-bit words (the trailing crc word excluded).
uint32_t crc32Core(const uint32_t* ptr, uint32_t len) {
    unsigned int xbit = 0;
    unsigned int data = 0;
    unsigned int CRC32 = 0xFFFFFFFF;
    const unsigned int dwPolynomial = 0x04c11db7;
    for (unsigned int i = 0; i < len; i++) {
        xbit = 1 << 31;
        data = ptr[i];
        for (unsigned int bits = 0; bits < 32; bits++) {
            if (CRC32 & 0x80000000) {
                CRC32 <<= 1;
                CRC32 ^= dwPolynomial;
            } else {
                CRC32 <<= 1;
            }
            if (data & xbit) CRC32 ^= dwPolynomial;
            xbit >>= 1;
        }
    }
    return CRC32;
}

void lowCrc(const std::string& topic, int duration) {
    std::atomic<unsigned> total{0}, matched{0};
    std::atomic<bool> first{true};
    std::mutex mutex;
    std::string sample;
    unitree::robot::ChannelSubscriber<LowState> subscriber(topic);
    subscriber.InitChannel([&](const void* message) {
        const auto& frame = *static_cast<const LowState*>(message);
        const auto computed = crc32Core(reinterpret_cast<const uint32_t*>(&frame),
                                        (sizeof(LowState) >> 2) - 1);
        ++total;
        if (computed == frame.crc()) ++matched;
        if (first.exchange(false)) {
            std::lock_guard<std::mutex> guard(mutex);
            std::ostringstream text;
            text << "first frame: received_crc=0x" << std::hex << frame.crc()
                 << " computed_crc=0x" << computed << std::dec
                 << " mode_pr=" << unsigned(frame.mode_pr())
                 << " mode_machine=" << unsigned(frame.mode_machine())
                 << " tick=" << frame.tick();
            sample = text.str();
        }
    }, 1);
    for (int i = 0; i < duration; ++i) std::this_thread::sleep_for(std::chrono::seconds(1));
    subscriber.CloseChannel();
    std::cout << "low-crc packets=" << total.load() << " crc_matched=" << matched.load() << std::endl;
    if (!sample.empty()) std::cout << sample << std::endl;
    if (!total) throw std::runtime_error("No compatible HG LowState packets");
    if (matched != total)
        std::cout << "WARNING: CRC mismatches present - algorithm or framing differs" << std::endl;
}

void lowRemote(const std::string& topic, int duration) {
    LatestLow latest;
    subscribeLow(latest, topic, [&] {
        for (int i = 0; i < duration; ++i) {
            std::this_thread::sleep_for(std::chrono::seconds(1));
            std::lock_guard<std::mutex> guard(latest.mutex);
            std::cout << "low remote packets=" << latest.count;
            if (latest.count) {
                const auto& raw = latest.state.wireless_remote();
                const unsigned buttons = unsigned(raw[2]) | (unsigned(raw[3]) << 8);
                std::cout << " tick=" << latest.state.tick() << " raw24=";
                for (std::size_t j = 0; j < 24; ++j) {
                    std::cout << std::hex << std::setw(2) << std::setfill('0')
                              << unsigned(raw[j]);
                }
                std::cout << std::dec << std::setfill(' ') << " candidate_buttons=0x"
                          << std::hex << buttons << std::dec << " candidate_axes=";
                for (std::size_t j = 0; j < 5; ++j) {
                    float axis = 0.f;
                    std::memcpy(&axis, raw.data() + 4 + 4 * j, sizeof(axis));
                    std::cout << axis << (j == 4 ? "" : ",");
                }
            }
            std::cout << std::endl;
        }
    });
    if (!latest.count) throw std::runtime_error("No compatible HG LowState packets");
}

void lowCapture(const std::string& topic, int duration, int period_ms) {
    LatestLow latest;
    const auto started = Clock::now();
    std::cout << "LOW_SAMPLE_SCHEMA,elapsed_ms,packet_count,age_ms,tick,mode_pr,mode_machine,"
                 "quat_w,quat_x,quat_y,quat_z,gyro_x,gyro_y,gyro_z,"
                 "m0_q,m0_dq,m0_ddq,m0_tau,m0_mode,m0_temp,"
                 "m1_q,m1_dq,m1_ddq,m1_tau,m1_mode,m1_temp,"
                 "...,m34_q,m34_dq,m34_ddq,m34_tau,m34_mode,m34_temp" << std::endl;
    subscribeLow(latest, topic, [&] {
        for (int i = 0; i < duration * 1000 / period_ms; ++i) {
            std::this_thread::sleep_until(started + std::chrono::milliseconds(std::int64_t{period_ms} * (i + 1)));
            LowState frame{};
            Clock::time_point received{};
            unsigned count = 0;
            {
                std::lock_guard<std::mutex> guard(latest.mutex);
                frame = latest.state;
                received = latest.received;
                count = latest.count;
            }
            const auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(Clock::now() - started).count();
            const auto age = count ? std::chrono::duration_cast<std::chrono::milliseconds>(Clock::now() - received).count() : -1;
            std::cout << "LOW_SAMPLE," << elapsed << ',' << count << ',' << age;
            if (count) {
                std::cout << ',' << frame.tick() << ',' << unsigned(frame.mode_pr())
                          << ',' << unsigned(frame.mode_machine());
                const auto& imu = frame.imu_state();
                for (const auto value : imu.quaternion()) std::cout << ',' << value;
                for (const auto value : imu.gyroscope()) std::cout << ',' << value;
                for (const auto& motor : frame.motor_state()) {
                    std::cout << ',' << motor.q() << ',' << motor.dq()
                              << ',' << motor.ddq() << ',' << motor.tau_est()
                              << ',' << unsigned(motor.mode())
                              << ',' << motor.temperature()[0];
                }
            }
            std::cout << std::endl;
        }
    });
    if (!latest.count) throw std::runtime_error("No compatible HG LowState packets");
}

void shadow(const std::string& topic, const std::string& model,
            const std::string& map, int duration) {
    as2w::Policy policy(model);
    if (!policy.stairs()) {
        throw std::runtime_error("Recovery needs a verified body-frame velocity source; shadow is stairs only");
    }
    const auto mapping = as2w::loadMapping(map, LowState{}.motor_state().size());
    LatestLow latest;
    as2w::Controller controller(policy);
    subscribeLow(latest, topic, [&] {
        const auto end = Clock::now() + std::chrono::seconds(duration);
        auto next = Clock::now();
        unsigned printed = 0;
        unsigned ticks = 0, stale_skips = 0, episodes = 0, episode_ticks = 0;
        bool locked = false;
        std::vector<float> age_ms, compute_ms;
        while (Clock::now() < end) {
            next += std::chrono::milliseconds(20);
            std::this_thread::sleep_until(next);
            LowState frame{};
            Clock::time_point stamp{};
            {
                std::lock_guard<std::mutex> guard(latest.mutex);
                if (!latest.count) { ++stale_skips; continue; }
                frame = latest.state;
                stamp = latest.received;
            }
            as2w::State state{};
            const auto& imu = frame.imu_state();
            std::copy(imu.gyroscope().begin(), imu.gyroscope().end(), state.gyro.begin());
            std::copy(imu.quaternion().begin(), imu.quaternion().end(),
                      state.body_to_world_wxyz.begin());
            std::vector<float> q, dq;
            q.reserve(frame.motor_state().size());
            dq.reserve(frame.motor_state().size());
            for (const auto& motor : frame.motor_state()) {
                q.push_back(motor.q());
                dq.push_back(motor.dq());
            }
            state = as2w::decodeEncoders(state, mapping, q, dq);
            if (!controller.armed()) controller.arm();
            const float age = std::chrono::duration<float>(Clock::now() - stamp).count();
            const auto compute_start = Clock::now();
            const auto commands = controller.step(state, age);
            const auto motors = as2w::encodeCommands(commands, mapping, q.size());
            const float compute = std::chrono::duration<float, std::milli>(Clock::now() - compute_start).count();
            age_ms.push_back(age * 1000.f);
            compute_ms.push_back(compute);
            ++ticks;
            ++episode_ticks;
            // Populate the HG wire layout in memory only. Motor mode and CRC are
            // deliberately absent until the AS2-W firmware contract is known.
            unitree_hg::msg::dds_::LowCmd_ preview{};
            preview.mode_pr(frame.mode_pr());
            preview.mode_machine(frame.mode_machine());
            for (std::size_t i = 0; i < motors.size(); ++i) {
                auto& dst = preview.motor_cmd()[i];
                const auto& src = motors[i];
                dst.q(src.q);
                dst.dq(src.dq);
                dst.kp(src.kp);
                dst.kd(src.kd);
                dst.tau(src.tau);
            }
            if (!controller.armed()) {
                if (episode_ticks >= controller.horizon()) {
                    ++episodes;
                    std::cout << "shadow episode " << episodes << " ended at horizon, re-arming" << std::endl;
                    episode_ticks = 0;
                    continue;
                }
                std::cout << "shadow locked: stale/invalid state at tick " << frame.tick() << std::endl;
                locked = true;
                break;
            }
            if (++printed % 25 == 1) {
                const auto& wheel = preview.motor_cmd()[mapping[15].index];
                std::cout << "SHADOW_ONLY tick=" << frame.tick() << " age_ms=" << age * 1000.f
                          << " RR_foot_slot=" << mapping[15].index
                          << " RR_foot_sdk_dq=" << wheel.dq() << std::endl;
            }
        }
        const auto percentile = [](std::vector<float> values, float p) {
            if (values.empty()) return -1.f;
            std::sort(values.begin(), values.end());
            const auto idx = std::min(values.size() - 1,
                static_cast<std::size_t>(p * (values.size() - 1)));
            return values[idx];
        };
        std::cout << "SHADOW_SUMMARY ticks=" << ticks << " episodes=" << episodes + 1
                  << " stale_skips=" << stale_skips
                  << " locked=" << (locked ? 1 : 0)
                  << " age_ms_p50=" << percentile(age_ms, .5f)
                  << " age_ms_p99=" << percentile(age_ms, .99f)
                  << " age_ms_max=" << percentile(age_ms, 1.f)
                  << " compute_ms_p50=" << percentile(compute_ms, .5f)
                  << " compute_ms_p99=" << percentile(compute_ms, .99f)
                  << " compute_ms_max=" << percentile(compute_ms, 1.f) << std::endl;
    });
    if (!latest.count) throw std::runtime_error("No compatible HG LowState packets");
}

void sportCommand(const std::string& action) {
    unitree::robot::as2::SportClient client;
    client.SetTimeout(5.f);
    client.Init();
    int32_t rc = -1;
    if (action == "get-state") {
        std::map<std::string, std::string> state;
        rc = client.GetState(state);
        for (const auto& kv : state) std::cout << kv.first << '=' << kv.second << '\n';
    } else if (action == "stop-move") rc = client.StopMove();
    else if (action == "balance-stand") rc = client.BalanceStand();
    else if (action == "stand-up") rc = client.StandUp();
    else if (action == "stand-down") rc = client.StandDown();
    else if (action == "damp") rc = client.Damp();
    else throw std::invalid_argument("Unknown Sport action");
    std::cout << "Sport API rc=" << rc << std::endl;
    if (rc != 0) throw std::runtime_error("Sport API failed");
}

void motionMode() {
    // The As2 documentation names this RPC, while SDK2 currently exposes its
    // client in the b2 namespace. This command only queries the service.
    unitree::robot::b2::MotionSwitcherClient client;
    client.SetTimeout(5.f);
    client.Init();
    std::string form, name;
    const int32_t rc = client.CheckMode(form, name);
    std::cout << "MotionSwitcher CheckMode rc=" << rc
              << " form=" << form << " name=" << name << std::endl;
    if (rc != 0) throw std::runtime_error("MotionSwitcher CheckMode failed");
}

void lowProtection(int duration) {
    // Read-only evidence stream for LowCmd startup incidents. No publisher.
    std::mutex mutex;
    LowState low{};
    MainBoardState board{};
    Clock::time_point low_at{}, board_at{};
    unsigned low_count = 0, board_count = 0;
    ChannelSubscriber<LowState> low_sub("rt/lowstate");
    low_sub.InitChannel([&](const void* message) {
        std::lock_guard<std::mutex> lock(mutex);
        low = *static_cast<const LowState*>(message);
        low_at = Clock::now();
        ++low_count;
    }, 1);
    ChannelSubscriber<MainBoardState> board_sub("rt/lf/mainboardstate");
    board_sub.InitChannel([&](const void* message) {
        std::lock_guard<std::mutex> lock(mutex);
        board = *static_cast<const MainBoardState*>(message);
        board_at = Clock::now();
        ++board_count;
    }, 1);
    const auto started = Clock::now();
    while (Clock::now() - started < std::chrono::seconds(duration)) {
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
        std::lock_guard<std::mutex> lock(mutex);
        const auto now = Clock::now();
        const auto age = [&](Clock::time_point at) -> long long {
            return at == Clock::time_point{} ? -1 :
                std::chrono::duration_cast<std::chrono::milliseconds>(now-at).count();
        };
        uint32_t motorstate_or = 0, warning_or = 0;
        std::string modes;
        for (std::size_t i = 0; i < 16; ++i) {
            const auto& m = low.motor_state()[i];
            modes += char('0' + std::min<unsigned>(m.mode(), 9));
            motorstate_or |= m.motorstate();
            warning_or |= m.reserve()[3];
        }
        std::cout << "PROTECT," << std::chrono::duration_cast<std::chrono::milliseconds>(now-started).count()
                  << ",low_count=" << low_count << ",low_age_ms=" << age(low_at)
                  << ",tick=" << low.tick() << ",machine=" << unsigned(low.mode_machine())
                  << ",modes=" << modes << ",motorstate_or=0x" << std::hex
                  << motorstate_or << ",warning_or=0x" << warning_or
                  << ",board_count=" << std::dec << board_count
                  << ",board_age_ms=" << age(board_at)
                  << ",board_state0=0x" << std::hex << board.state()[0] << std::dec
                  << ",battery_v=" << board.value()[0]
                  << ",motor_v=" << board.value()[1]
                  << ",motor_a=" << board.value()[2] << '\n';
    }
    board_sub.CloseChannel();
    low_sub.CloseChannel();
    if (!low_count) throw std::runtime_error("No LowState packets during protection capture");
    if (!board_count) std::cerr << "WARNING: no MainBoardState packets on rt/lf/mainboardstate\n";
}

// P4 gated actions: one ReleaseMode / SelectMode RPC each, then a read-back.
// These change robot control ownership; run only with the field crew's
// explicit per-action consent, dog prone, power switch within reach.
void motionRelease() {
    unitree::robot::b2::MotionSwitcherClient client;
    client.SetTimeout(5.f);
    client.Init();
    const int32_t rc = client.ReleaseMode();
    std::cout << "MotionSwitcher ReleaseMode rc=" << rc << std::endl;
    std::this_thread::sleep_for(std::chrono::seconds(1));
    std::string form, name;
    const int32_t check = client.CheckMode(form, name);
    std::cout << "MotionSwitcher CheckMode rc=" << check
              << " form=" << form << " name=" << name << std::endl;
    if (rc != 0) throw std::runtime_error("MotionSwitcher ReleaseMode failed");
}

void motionSelect(const std::string& target) {
    unitree::robot::b2::MotionSwitcherClient client;
    client.SetTimeout(5.f);
    client.Init();
    const int32_t rc = client.SelectMode(target);
    std::cout << "MotionSwitcher SelectMode(\"" << target << "\") rc=" << rc << std::endl;
    std::this_thread::sleep_for(std::chrono::seconds(1));
    std::string form, name;
    const int32_t check = client.CheckMode(form, name);
    std::cout << "MotionSwitcher CheckMode rc=" << check
              << " form=" << form << " name=" << name << std::endl;
    if (rc != 0) throw std::runtime_error("MotionSwitcher SelectMode failed");
}

void serviceList() {
    // Query only. ServiceSwitch is deliberately not exposed by this tool.
    unitree::robot::b2::RobotStateClient client;
    client.SetTimeout(5.f);
    client.Init();
    std::vector<unitree::robot::b2::ServiceState> services;
    const int32_t rc = client.ServiceList(services);
    std::cout << "RobotState ServiceList rc=" << rc
              << " count=" << services.size() << std::endl;
    for (const auto& service : services) {
        std::cout << "service name=" << service.name
                  << " status=" << service.status
                  << " protect=" << service.protect << std::endl;
    }
    if (rc != 0) throw std::runtime_error("RobotState ServiceList failed");
}

void packageVersion() {
    unitree::robot::b2::RobotStateClient client;
    client.SetTimeout(5.f);
    client.Init();
    std::string package;
    std::map<std::string, std::string> modules;
    const int32_t rc = client.GetPkgVersion(package, modules);
    std::cout << "RobotState GetPkgVersion rc=" << rc
              << " package=" << package << " modules=" << modules.size() << std::endl;
    for (const auto& module : modules) {
        std::cout << "module=" << module.first << " version=" << module.second << std::endl;
    }
    if (rc != 0) throw std::runtime_error("RobotState GetPkgVersion failed");
}

void usage() {
    std::cerr << "as2w_sdk2 sport-state NIC [SECONDS]\n"
                 "as2w_sdk2 remote-state NIC [SECONDS]\n"
                 "as2w_sdk2 low-state NIC HG_LOWSTATE_TOPIC [SECONDS]\n"
                 "as2w_sdk2 low-remote NIC HG_LOWSTATE_TOPIC [SECONDS] (candidate raw layout)\n"
                 "as2w_sdk2 low-crc NIC [SECONDS] [TOPIC] (verify LowState CRC32 algorithm, read-only)\n"
                 "as2w_sdk2 low-capture NIC HG_LOWSTATE_TOPIC [SECONDS] [PERIOD_MS] (read-only samples, default 50 ms)\n"
                 "as2w_sdk2 low-protection NIC [SECONDS] (read-only board/motor warning capture)\n"
                 "as2w_sdk2 shadow NIC HG_LOWSTATE_TOPIC STAIRS_MODEL MAP SECONDS --imu-wxyz-body-to-world\n"
                 "as2w_sdk2 sport-command NIC get-state|stop-move|balance-stand|stand-up|stand-down|damp\n"
                 "as2w_sdk2 motion-mode NIC\n"
                 "as2w_sdk2 motion-release NIC   (GATED: one ReleaseMode RPC, control ownership changes)\n"
                 "as2w_sdk2 motion-select NIC NAME (GATED: one SelectMode RPC to restore a motion mode)\n"
                 "as2w_sdk2 service-list NIC (read-only RobotState query)\n"
                 "as2w_sdk2 package-version NIC (read-only firmware version query)\n"
                 "Read-only modes never publish motor commands. Sport commands use official high-level API.\n";
}
} // namespace

int main(int argc, char** argv) {
    try {
        if (argc < 3) { usage(); return 2; }
        const std::string command = argv[1];
        if (command == "sport-state" && (argc == 3 || argc == 4)) {
            unitree::robot::ChannelFactory::Instance()->Init(0, argv[2]);
            sportState(argc == 4 ? seconds(argv[3]) : 10);
        } else if (command == "remote-state" && (argc == 3 || argc == 4)) {
            unitree::robot::ChannelFactory::Instance()->Init(0, argv[2]);
            remoteState(argc == 4 ? seconds(argv[3]) : 10);
        } else if (command == "low-state" && (argc == 4 || argc == 5)) {
            unitree::robot::ChannelFactory::Instance()->Init(0, argv[2]);
            lowState(argv[3], argc == 5 ? seconds(argv[4]) : 10);
        } else if (command == "low-remote" && (argc == 4 || argc == 5)) {
            unitree::robot::ChannelFactory::Instance()->Init(0, argv[2]);
            lowRemote(argv[3], argc == 5 ? seconds(argv[4]) : 10);
        } else if (command == "low-capture" && (argc == 4 || argc == 5 || argc == 6)) {
            unitree::robot::ChannelFactory::Instance()->Init(0, argv[2]);
            lowCapture(argv[3], argc >= 5 ? seconds(argv[4]) : 10, argc == 6 ? seconds(argv[5]) : 50);
        } else if (command == "low-crc" && (argc == 3 || argc == 4 || argc == 5)) {
            unitree::robot::ChannelFactory::Instance()->Init(0, argv[2]);
            lowCrc(argc >= 4 ? argv[3] : "rt/lowstate", argc == 5 ? seconds(argv[4]) : 5);
        } else if (command == "low-protection" && (argc == 3 || argc == 4)) {
            unitree::robot::ChannelFactory::Instance()->Init(0, argv[2]);
            lowProtection(argc == 4 ? seconds(argv[3]) : 10);
        } else if (command == "shadow" && argc == 8 &&
                   std::string(argv[7]) == "--imu-wxyz-body-to-world") {
            unitree::robot::ChannelFactory::Instance()->Init(0, argv[2]);
            shadow(argv[3], argv[4], argv[5], seconds(argv[6]));
        } else if (command == "sport-command" && argc == 4) {
            unitree::robot::ChannelFactory::Instance()->Init(0, argv[2]);
            sportCommand(argv[3]);
        } else if (command == "motion-mode" && argc == 3) {
            unitree::robot::ChannelFactory::Instance()->Init(0, argv[2]);
            motionMode();
        } else if (command == "motion-release" && argc == 3) {
            unitree::robot::ChannelFactory::Instance()->Init(0, argv[2]);
            motionRelease();
        } else if (command == "motion-select" && argc == 4) {
            unitree::robot::ChannelFactory::Instance()->Init(0, argv[2]);
            motionSelect(argv[3]);
        } else if (command == "service-list" && argc == 3) {
            unitree::robot::ChannelFactory::Instance()->Init(0, argv[2]);
            serviceList();
        } else if (command == "package-version" && argc == 3) {
            unitree::robot::ChannelFactory::Instance()->Init(0, argv[2]);
            packageVersion();
        } else { usage(); return 2; }
    } catch (const std::exception& error) {
        std::cerr << error.what() << std::endl;
        return 1;
    }
}
