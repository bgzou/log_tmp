#include "r270_controller.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "Usage: as2w_r270_smoke <deploy.yaml>\n";
        return 2;
    }
    const auto config = as2w_r270::load_config(argv[1]);
    as2w_r270::SensorState sensors;
    sensors.body_to_world_wxyz = {1.f, 0.f, 0.f, 0.f};
    sensors.position = config.defaults;
    as2w_r270::Controller controller(config);
    controller.arm();
    as2w_r270::Targets targets;
    for (int i = 0; i < 100; ++i) {
        targets = controller.step(sensors, {0.f, 0.f, 0.f}, 0.f);
        if (!targets.active) throw std::runtime_error("R270 smoke controller disarmed");
        for (const auto v : targets.action)
            if (!std::isfinite(v)) throw std::runtime_error("R270 smoke nonfinite action");
        if (config.low_speed_gate_enabled) {
            for (const auto index : config.low_speed_action_indices)
                if (std::abs(targets.action[index]) > 1e-6f)
                    throw std::runtime_error("R270 low-speed hind gate not applied");
        }
    }
    for (std::size_t i = 0; i < as2w_r270::MotorCount; ++i) {
        if (targets.motors[i].kp != config.stiffness[i]
            || targets.motors[i].kd != config.damping[i])
            throw std::runtime_error("R270 gains do not match strategy config");
    }
    controller.stop();
    if (controller.armed()) throw std::runtime_error("R270 stop failed");
    std::cout << "R270 SMOKE PASS model=" << config.model_version
              << " obs=720 action=16 history=480ms\n";
}


