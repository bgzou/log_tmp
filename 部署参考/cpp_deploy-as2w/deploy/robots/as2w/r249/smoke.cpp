#include "r249_controller.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "Usage: as2w_r249_smoke <deploy.yaml>\n";
        return 2;
    }
    const auto config = as2w_r249::load_config(argv[1]);
    as2w_r249::SensorState sensors;
    sensors.body_to_world_wxyz = {1.f, 0.f, 0.f, 0.f};
    sensors.position = config.defaults;
    as2w_r249::Controller controller(config);
    controller.arm();
    as2w_r249::Targets targets;
    for (int i = 0; i < 100; ++i) {
        targets = controller.step(sensors, {0.f, 0.f, 0.f}, 0.f);
        if (!targets.active) throw std::runtime_error("R249 smoke controller disarmed");
        for (const auto v : targets.action)
            if (!std::isfinite(v)) throw std::runtime_error("R249 smoke nonfinite action");
        for (const auto index : config.low_speed_action_indices)
            if (std::abs(targets.action[index]) > 1e-6f)
                throw std::runtime_error("R249 low-speed hind gate not applied");
    }
    for (std::size_t i = 0; i < as2w_r249::MotorCount; ++i) {
        if (targets.motors[i].kp != config.stiffness[i]
            || targets.motors[i].kd != config.damping[i])
            throw std::runtime_error("R249 gains do not match strategy config");
    }
    controller.stop();
    if (controller.armed()) throw std::runtime_error("R249 stop failed");
    std::cout << "R249 SMOKE PASS model=" << config.model_version
              << " obs=60 action=16 final-action-history=enabled\n";
}
