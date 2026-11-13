#include "r4000_controller.hpp"

#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "usage: as2w_r4000_replay deploy.yaml sensor_fixture.txt\n";
        return 2;
    }
    try {
        as2w_r4000_deploy::Controller c(as2w_r4000_deploy::load_config(argv[1]));
        std::ifstream input(argv[2]);
        if (!input) throw std::runtime_error("Cannot open fixture");
        c.arm();
        int n = 0;
        float elapsed;
        while (input >> elapsed) {
            as2w_r4000_deploy::SensorState s;
            for (auto& v : s.body_to_world_wxyz) if (!(input >> v)) throw std::runtime_error("quat");
            for (auto& v : s.gyro) if (!(input >> v)) throw std::runtime_error("gyro");
            for (auto& v : s.position) if (!(input >> v)) throw std::runtime_error("position");
            for (auto& v : s.velocity) if (!(input >> v)) throw std::runtime_error("velocity");
            as2w_r4000_deploy::Vector3 command{};
            for (auto& v : command) if (!(input >> v)) throw std::runtime_error("command");
            const auto target = c.step(s, command, .02f);
            if (!target.active) throw std::runtime_error("Controller disarmed");
            std::cout << std::setprecision(9) << "R4000_OBS," << elapsed;
            for (auto v : c.last_observation()) std::cout << ',' << v;
            std::cout << '\n';
            std::cout << std::setprecision(9) << "R4000_TARGET," << elapsed;
            for (auto v : target.action) std::cout << ',' << v;
            for (int i = 0; i < 12; ++i) std::cout << ',' << target.motors[i].q;
            for (int i = 12; i < 16; ++i) std::cout << ',' << target.motors[i].dq;
            std::cout << '\n';
            ++n;
        }
        if (!n) throw std::runtime_error("Empty fixture");
        std::cerr << "R4000_REPLAY_FRAMES=" << n << '\n';
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "R4000 replay failed: " << e.what() << '\n';
        return 1;
    }
}
