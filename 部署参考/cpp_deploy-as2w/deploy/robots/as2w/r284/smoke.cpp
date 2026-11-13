#include "r284_controller.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>

int main(int argc, char** argv) {
    if (argc != 2) return 2;
    const auto config = as2w_r284_deploy::load_config(argv[1]);
    as2w_r284_deploy::SensorState sensors;
    sensors.body_to_world_wxyz = {1.f, 0.f, 0.f, 0.f};
    sensors.position = config.defaults;
    as2w_r284_deploy::Controller controller(config);
    controller.arm();
    for (int tick = 0; tick < 500; ++tick) {
        const auto targets = controller.step(sensors, {}, 0.f);
        if (!targets.active) throw std::runtime_error("R284 controller disarmed");
        for (std::size_t i = 0; i < targets.action.size(); ++i) {
            if (!std::isfinite(targets.action[i])
                || targets.motors[i].kp != config.stiffness[i]
                || targets.motors[i].kd != config.damping[i])
                throw std::runtime_error("R284 output contract mismatch");
        }
    }
    controller.stop();
    if (controller.armed()) throw std::runtime_error("R284 stop failed");
    std::cout << "R284 SMOKE PASS model=" << config.model_version
              << " obs=65 action=16 zero-wheel-memory=enabled\n";
}

