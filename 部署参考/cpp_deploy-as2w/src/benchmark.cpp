#include "policy.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

int main(int argc, char** argv) {
    try {
        if (argc != 4) {
            std::cerr << "Usage: as2w_bench MODEL FIXTURE ITERATIONS\n";
            return 2;
        }
        const std::string count_text = argv[3];
        std::size_t parsed = 0;
        const auto iterations = std::stoul(count_text, &parsed);
        if (parsed != count_text.size() || iterations < 100 || iterations > 1000000) {
            throw std::invalid_argument("Iterations must be 100..1000000");
        }
        as2w::Policy policy(argv[1]);
        std::ifstream fixture(argv[2]);
        float elapsed = 0.f;
        as2w::Observation obs{};
        if (!(fixture >> elapsed)) throw std::runtime_error("Cannot read fixture time");
        for (float& value : obs) {
            if (!(fixture >> value) || !std::isfinite(value)) {
                throw std::runtime_error("Cannot read finite fixture observation");
            }
        }
        for (int i = 0; i < 100; ++i) (void)policy.infer(obs, elapsed);
        std::vector<double> us;
        us.reserve(iterations);
        double action_sum = 0.0;
        for (std::size_t i = 0; i < iterations; ++i) {
            const auto begin = std::chrono::steady_clock::now();
            const auto output = policy.infer(obs, elapsed);
            const auto end = std::chrono::steady_clock::now();
            action_sum += output.action[i % output.action.size()];
            us.push_back(std::chrono::duration<double, std::micro>(end - begin).count());
        }
        if (!std::isfinite(action_sum)) throw std::runtime_error("Nonfinite benchmark action");
        std::sort(us.begin(), us.end());
        const auto percentile = [&](double q) { return us[std::size_t(q * double(us.size() - 1))]; };
        std::cout << std::fixed << std::setprecision(2)
                  << "iterations=" << iterations
                  << " p50_us=" << percentile(.50)
                  << " p99_us=" << percentile(.99)
                  << " max_us=" << us.back()
                  << " policy_period_us=20000"
                  << " action_sum=" << action_sum << '\n';
        if (percentile(.99) >= 20000.0) {
            std::cerr << "p99 policy computation exceeds 20 ms period\n";
            return 1;
        }
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
