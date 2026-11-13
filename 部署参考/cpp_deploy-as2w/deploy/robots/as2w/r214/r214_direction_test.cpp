// Minimal LowCmd direction verification: publishes a few frames with small
// single-joint/single-wheel commands while prone, reads back actual movement.
// Requires ReleaseMode done. Dog must be prone on ground.
//
// Usage: as2w_r214_direction_test <deploy.yaml> <map> <NIC>

#include "r214_controller.hpp"
#include <unitree/idl/hg/LowState_.hpp>
#include <unitree/idl/hg/LowCmd_.hpp>
#include <unitree/robot/channel/channel_factory.hpp>
#include <unitree/robot/channel/channel_publisher.hpp>
#include <unitree/robot/channel/channel_subscriber.hpp>
#include <chrono>
#include <cmath>
#include <cstring>
#include <fstream>
#include <iostream>
#include <mutex>
#include <set>
#include <thread>

using Clock = std::chrono::steady_clock;
using LowState = unitree_hg::msg::dds_::LowState_;
using LowCmd = unitree_hg::msg::dds_::LowCmd_;
using as2w_r214::MotorCount;

static uint32_t crc32(const uint32_t* ptr, uint32_t len) {
    uint32_t crc = 0xFFFFFFFF;
    for (uint32_t i = 0; i < len; i++)
        for (int b = 0; b < 32; b++) {
            crc = (crc & 0x80000000) ? ((crc << 1) ^ 0x04c11db7) : (crc << 1);
            if (ptr[i] & (1u << (31 - b))) crc ^= 0x04c11db7;
        }
    return crc;
}

struct Axis { std::size_t index; float sign, zero; };

int main(int argc, char** argv) {
    if (argc != 4) {
        std::cerr << "Usage: " << argv[0] << " <deploy.yaml> <map> <NIC>\n";
        return 2;
    }
    const auto config = as2w_r214::load_config(argv[1]);

    // Read mapping
    std::array<Axis, MotorCount> map{};
    {
        std::ifstream file(argv[2]);
        std::set<std::size_t> used;
        for (std::size_t i = 0; i < MotorCount; ++i) {
            std::string name;
            if (!(file >> name >> map[i].index >> map[i].sign >> map[i].zero)
                || name != config.joint_names[i]) {
                std::cerr << "Bad mapping\n"; return 1;
            }
        }
    }

    unitree::robot::ChannelFactory::Instance()->Init(0, argv[3]);
    std::mutex mtx;
    LowState latest{};
    Clock::time_point recv{};
    unsigned count = 0;
    unitree::robot::ChannelSubscriber<LowState> sub("rt/lowstate");
    sub.InitChannel([&](const void* msg) {
        std::lock_guard<std::mutex> l(mtx);
        latest = *static_cast<const LowState*>(msg);
        recv = Clock::now(); ++count;
    }, 1);
    unitree::robot::ChannelPublisher<LowCmd> pub("rt/lowcmd");
    pub.InitChannel();

    // Wait for LowState
    for (int i = 0; i < 50 && !count; ++i)
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    if (!count) { std::cerr << "No LowState\n"; return 1; }
    std::cout << "LowState flowing (" << count << " packets)\n";

    auto get_q = [&](std::size_t contract_idx) {
        std::lock_guard<std::mutex> l(mtx);
        return latest.motor_state()[map[contract_idx].index].q();
    };
    auto get_dq = [&](std::size_t contract_idx) {
        std::lock_guard<std::mutex> l(mtx);
        return latest.motor_state()[map[contract_idx].index].dq();
    };

    auto publish_passive = [&](float secs) {
        LowCmd cmd{};
        auto end = Clock::now() + std::chrono::duration<float>(secs);
        auto next = Clock::now();
        while (Clock::now() < end) {
            next += std::chrono::milliseconds(2);
            std::this_thread::sleep_until(next);
            LowState st{};
            { std::lock_guard<std::mutex> l(mtx); st = latest; }
            cmd.mode_pr() = 0;
            cmd.mode_machine() = st.mode_machine();
            for (std::size_t i = 0; i < MotorCount; ++i) {
                auto& out = cmd.motor_cmd()[map[i].index];
                out.mode() = 0x01;
                out.q() = st.motor_state()[map[i].index].q();
                out.dq() = 0; out.kp() = 0; out.kd() = 5; out.tau() = 0;
            }
            cmd.crc() = crc32(reinterpret_cast<const uint32_t*>(&cmd), (sizeof(LowCmd)>>2)-1);
            pub.Write(cmd);
        }
    };

    auto publish_joint_test = [&](std::size_t contract_idx, float delta_rad, float secs) {
        LowCmd cmd{};
        const float q0 = get_q(contract_idx);
        const float target = q0 + delta_rad * map[contract_idx].sign; // sign encode
        std::cout << "  joint " << config.joint_names[contract_idx]
                  << " (slot " << map[contract_idx].index << ")"
                  << " q0=" << q0 << " target=" << target << "\n";
        auto end = Clock::now() + std::chrono::duration<float>(secs);
        auto next = Clock::now();
        while (Clock::now() < end) {
            next += std::chrono::milliseconds(2);
            std::this_thread::sleep_until(next);
            LowState st{};
            { std::lock_guard<std::mutex> l(mtx); st = latest; }
            cmd.mode_pr() = 0;
            cmd.mode_machine() = st.mode_machine();
            for (std::size_t i = 0; i < MotorCount; ++i) {
                auto& out = cmd.motor_cmd()[map[i].index];
                out.mode() = 0x01;
                if (i == contract_idx) {
                    out.q() = target; out.kp() = 10; out.kd() = 2; out.dq() = 0;
                } else {
                    out.q() = st.motor_state()[map[i].index].q();
                    out.kp() = 0; out.kd() = 5; out.dq() = 0;
                }
                out.tau() = 0;
            }
            cmd.crc() = crc32(reinterpret_cast<const uint32_t*>(&cmd), (sizeof(LowCmd)>>2)-1);
            pub.Write(cmd);
        }
        const float q1 = get_q(contract_idx);
        std::cout << "  result: q went " << q0 << " -> " << q1
                  << " (delta=" << (q1-q0) << ")\n";
        return q1 - q0;
    };

    auto publish_wheel_test = [&](std::size_t contract_idx, float dq_cmd, float secs) {
        LowCmd cmd{};
        std::cout << "  wheel " << config.joint_names[contract_idx]
                  << " (slot " << map[contract_idx].index << ")"
                  << " dq_cmd=" << dq_cmd << "\n";
        const float q0 = get_q(contract_idx);
        auto end = Clock::now() + std::chrono::duration<float>(secs);
        auto next = Clock::now();
        while (Clock::now() < end) {
            next += std::chrono::milliseconds(2);
            std::this_thread::sleep_until(next);
            LowState st{};
            { std::lock_guard<std::mutex> l(mtx); st = latest; }
            cmd.mode_pr() = 0;
            cmd.mode_machine() = st.mode_machine();
            for (std::size_t i = 0; i < MotorCount; ++i) {
                auto& out = cmd.motor_cmd()[map[i].index];
                out.mode() = 0x01;
                if (i == contract_idx) {
                    out.q() = 0; out.kp() = 0; out.kd() = 2;
                    out.dq() = dq_cmd * map[contract_idx].sign;
                } else {
                    out.q() = st.motor_state()[map[i].index].q();
                    out.kp() = 0; out.kd() = 5; out.dq() = 0;
                }
                out.tau() = 0;
            }
            cmd.crc() = crc32(reinterpret_cast<const uint32_t*>(&cmd), (sizeof(LowCmd)>>2)-1);
            pub.Write(cmd);
        }
        const float q1 = get_q(contract_idx);
        const float dq_avg = get_dq(contract_idx);
        std::cout << "  result: q " << q0 << " -> " << q1
                  << " (delta=" << (q1-q0) << ", dq_avg=" << dq_avg << ")\n";
        return q1 - q0;
    };

    std::cout << "\n=== T1: Passive 5s (baseline) ===\n";
    publish_passive(5.0);
    std::cout << "  done (dog should be still)\n";

    std::cout << "\n=== T2: FL_hip +0.05 rad, 2s ===\n";
    float d_hip = publish_joint_test(0, 0.05f, 2.0f); // contract idx 0 = FL_hip
    publish_passive(2.0);

    std::cout << "\n=== T2b: FR_thigh +0.05 rad, 2s ===\n";
    float d_thigh = publish_joint_test(5, 0.05f, 2.0f); // contract idx 5 = FR_thigh
    publish_passive(2.0);

    std::cout << "\n=== T3: FL_foot (wheel) dq=+1.0, 2s ===\n";
    float d_wheel = publish_wheel_test(12, 1.0f, 2.0f); // contract idx 12 = FL_foot
    publish_passive(3.0);

    std::cout << "\n=== Summary ===\n";
    std::cout << "FL_hip:  commanded +0.05, actual " << (d_hip >= 0 ? "+" : "") << d_hip
              << " -> " << (d_hip > 0.01 ? "CORRECT" : d_hip < -0.01 ? "REVERSED!" : "NO MOVEMENT") << "\n";
    std::cout << "FR_thigh: commanded +0.05, actual " << (d_thigh >= 0 ? "+" : "") << d_thigh
              << " -> " << (d_thigh > 0.01 ? "CORRECT" : d_thigh < -0.01 ? "REVERSED!" : "NO MOVEMENT") << "\n";
    std::cout << "FL_foot: commanded dq=+1.0, q delta " << (d_wheel >= 0 ? "+" : "") << d_wheel
              << " -> " << (d_wheel > 0.1 ? "FORWARD (CORRECT)" : d_wheel < -0.1 ? "BACKWARD (REVERSED!)" : "NO MOVEMENT") << "\n";

    std::cout << "\nDone. Returning to passive...\n";
    publish_passive(3.0);
    sub.CloseChannel();
    return 0;
}
