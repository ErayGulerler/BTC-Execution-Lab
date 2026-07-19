#include "replay.hpp"
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>

// Input comes from the validated archive reader. One row represents one minute.
struct Session {
    std::string date;
    int hour;
    execution::Hour bars;
};

std::vector<Session> read_sessions(std::istream& input) {
    std::vector<Session> sessions;
    std::string line;
    int count = 0;
    while (std::getline(input, line)) {
        std::istringstream row(line);
        std::string day;
        int hour, minute;
        execution::Bar bar;
        if (!(row >> day >> hour >> minute >> bar.open >> bar.close >> bar.volume >> bar.vwap))
            throw std::runtime_error("Invalid normalised market row");
        if (minute != count % execution::minutes) throw std::runtime_error("Missing minute");
        if (minute == 0) sessions.push_back({day, hour, {}});
        auto& session = sessions.back();
        if (session.date != day || session.hour != hour) throw std::runtime_error("Mixed sessions");
        session.bars[minute] = bar;
        ++count;
    }
    if (count % execution::minutes || sessions.size() <= 6 * execution::history_days)
        throw std::runtime_error("Incomplete input or insufficient history");
    return sessions;
}

int main() {
    using namespace execution;
    try {
        auto sessions = read_sessions(std::cin);
        const std::array<Scenario, 3> scenarios = {{
            {"base", 12, 0.05, 4, 0.5, 2},
            {"tight_cap", 12, 0.02, 4, 0.5, 2},
            {"large_order", 36, 0.05, 4, 0.5, 2}
        }};
        std::cout << std::setprecision(15)
                  << "day,hour,side,scenario,policy,minute,quantity,arrival,requested,filled,"
                     "remaining,timing,spread,impact,fee,opportunity\n";
        constexpr int sessions_per_day = 6;
        for (size_t i = history_days * sessions_per_day; i < sessions.size(); ++i) {
            const auto& current = sessions[i];
            std::vector<Hour> prior;
            for (int lag = 1; lag <= history_days; ++lag)
                prior.push_back(sessions[i - lag * sessions_per_day].bars);
            const auto forecast = volume_weights(prior);
            // Reverse side every day at each hour. Both policies get the same parent order.
            const int side = (i / sessions_per_day + i % sessions_per_day) % 2 ? -1 : 1;
            for (const auto& cfg : scenarios) {
                for (std::string policy : {"twap", "volume"}) {
                    const auto weights = policy == "twap" ? equal_weights() : forecast;
                    const auto slices = simulate(current.bars, weights, cfg, side);
                    for (int m = 0; m < minutes; ++m) {
                        const auto& s = slices[m];
                        const double arrival = current.bars.front().open;
                        double opportunity = 0;
                        if (m == minutes - 1)
                            opportunity = side * s.remaining * (current.bars.back().close - arrival);
                        std::cout << current.date << ',' << current.hour << ',' << side << ','
                                  << cfg.name << ',' << policy << ',' << m << ',' << cfg.quantity
                                  << ',' << arrival << ',' << s.requested << ',' << s.filled << ','
                                  << s.remaining << ',' << s.timing << ',' << s.spread << ','
                                  << s.impact << ',' << s.fee << ',' << opportunity << '\n';
                    }
                }
            }
        }
        if (!std::cout) throw std::runtime_error("Could not write fills");
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}

