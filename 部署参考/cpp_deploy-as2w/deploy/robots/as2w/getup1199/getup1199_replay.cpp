#include "getup1199_controller.hpp"

#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "usage: as2w_getup1199_replay deploy.yaml sensor_fixture.txt\n";
        return 2;
    }
    try {
        as2w_getup1199_deploy::Controller c(as2w_getup1199_deploy::load_config(argv[1]));
        std::ifstream input(argv[2]);
        if (!input) throw std::runtime_error("Cannot open fixture");
        c.arm();
        int n = 0;
        float elapsed;
        while (input >> elapsed) {
            as2w_getup1199_deploy::SensorState s;
            for (auto& v : s.body_to_world_wxyz) if (!(input >> v)) throw std::runtime_error("quat");
            for (auto& v : s.gyro) if (!(input >> v)) throw std::runtime_error("gyro");
            for (auto& v : s.position) if (!(input >> v)) throw std::runtime_error("position");
            for (auto& v : s.velocity) if (!(input >> v)) throw std::runtime_error("velocity");
            const auto target = c.step(s, .02f);
            if (!target.active) throw std::runtime_error("Controller disarmed");
            std::cout << std::setprecision(9) << "GETUP1199_OBS," << elapsed;
            for (auto v : c.last_observation()) std::cout << ',' << v;
            std::cout << '\n';
            std::cout << std::setprecision(9) << "GETUP1199_TARGET," << elapsed;
            for (auto v : target.action) std::cout << ',' << v;
            for (std::size_t i = 0; i < 12; ++i) std::cout << ',' << c.last_command()[i];
            std::cout << ',' << c.blend() << ',' << c.last_height_estimate() << ',' << c.last_up();
            std::cout << '\n';
            ++n;
        }
        if (!n) throw std::runtime_error("Empty fixture");
        std::cerr << "GETUP1199_REPLAY_FRAMES=" << n << '\n';
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "getup1199 replay failed: " << e.what() << '\n';
        return 1;
    }
}
