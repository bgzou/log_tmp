#include <unitree/robot/as2/sport/sport_client.hpp>
#include <unitree/robot/channel/channel_factory.hpp>

#include <linux/joystick.h>
#include <fcntl.h>
#include <poll.h>
#include <unistd.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <cerrno>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <csignal>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>

namespace {
using Clock = std::chrono::steady_clock;
std::atomic<bool> running{true};
void stopSignal(int) { running = false; }

int index(const char* text) {
    const int value = std::stoi(text);
    if (value < 0 || value > 63) throw std::invalid_argument("Joystick index must be 0..63");
    return value;
}

float axis(std::int16_t value) {
    const float x = std::clamp(float(value) / 32767.f, -1.f, 1.f);
    return std::abs(x) < .15f ? 0.f : x;
}
}

int main(int argc, char** argv) {
    try {
        if (argc != 8 || (std::string(argv[7]) != "--dry-run" &&
                          std::string(argv[7]) != "--enable-sport")) {
            std::cerr << "Usage: as2w_sport_gamepad NIC /dev/input/js0 VX_AXIS VY_AXIS YAW_AXIS DEADMAN_BUTTON --dry-run|--enable-sport\n";
            return 2;
        }
        const int vx_axis = index(argv[3]), vy_axis = index(argv[4]);
        const int yaw_axis = index(argv[5]), deadman_button = index(argv[6]);
        const bool enabled = std::string(argv[7]) == "--enable-sport";
        const int fd = open(argv[2], O_RDONLY | O_NONBLOCK);
        if (fd < 0) throw std::runtime_error("Cannot open joystick device");
        std::signal(SIGINT, stopSignal);
        std::signal(SIGTERM, stopSignal);
        std::array<std::int16_t, 64> axes{};
        std::array<bool, 64> buttons{};
        unitree::robot::as2::SportClient client;
        if (enabled) {
            unitree::robot::ChannelFactory::Instance()->Init(0, argv[1]);
            client.SetTimeout(3.f);
            client.Init();
        }
        bool moving = false;
        auto last_event = Clock::now() - std::chrono::seconds(2);
        const auto deadline = Clock::now() + std::chrono::seconds(120);
        auto next = Clock::now();
        while (running && Clock::now() < deadline) {
            next += std::chrono::milliseconds(50);
            pollfd watch{fd, POLLIN, 0};
            const int poll_rc = poll(&watch, 1, 0);
            if (poll_rc < 0 || (watch.revents & (POLLHUP | POLLERR | POLLNVAL))) break;
            js_event event{};
            while (read(fd, &event, sizeof(event)) == sizeof(event)) {
                const auto type = event.type & ~JS_EVENT_INIT;
                if (type == JS_EVENT_AXIS && event.number < axes.size()) axes[event.number] = event.value;
                if (type == JS_EVENT_BUTTON && event.number < buttons.size()) buttons[event.number] = event.value != 0;
                last_event = Clock::now();
            }
            const bool fresh = Clock::now() - last_event < std::chrono::milliseconds(350);
            const bool deadman = buttons[deadman_button] && fresh;
            if (deadman) {
                const float vx = -.15f * axis(axes[vx_axis]);
                const float vy = -.10f * axis(axes[vy_axis]);
                const float yaw = -.20f * axis(axes[yaw_axis]);
                if (enabled) {
                    const auto rc = client.Move(vx, vy, yaw);
                    if (rc != 0) { std::cerr << "Move failed: " << rc << '\n'; break; }
                } else {
                    std::cout << "DRY_RUN vx=" << vx << " vy=" << vy << " yaw=" << yaw << '\n';
                }
                moving = true;
            } else if (moving) {
                if (enabled) client.StopMove();
                std::cout << "STOP (deadman released or input stale)\n";
                moving = false;
            }
            std::this_thread::sleep_until(next);
        }
        if (enabled) client.StopMove();
        close(fd);
        std::cout << "Gamepad session ended; StopMove sent if enabled.\n";
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
