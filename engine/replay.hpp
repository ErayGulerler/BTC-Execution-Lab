#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>

namespace execution {
constexpr int minutes = 60;
constexpr int history_days = 7;

struct Bar {
    double open, close, volume, vwap;
};
using Hour = std::array<Bar, minutes>;
using Profile = std::array<double, minutes>;

struct Scenario {
    std::string name;
    double quantity, cap, fee_bps, half_spread_bps, impact_at_five_percent_bps;
};

struct Slice {
    double requested, filled, remaining;
    double timing, spread, impact, fee; // Signed costs in USDT. Positive is worse.
};

inline Profile equal_weights() {
    Profile weights{};
    weights.fill(1.0 / minutes);
    return weights;
}

// Each historical hour casts one vote, including unusually quiet days.
// Normalising each day first prevents a single high-volume day dominating.
inline Profile volume_weights(const std::vector<Hour>& history) {
    Profile weights{};
    int usable = 0;
    for (const Hour& hour : history) {
        double total = 0;
        for (const Bar& bar : hour) total += bar.volume;
        if (total == 0) continue;
        ++usable;
        for (int m = 0; m < minutes; ++m) weights[m] += hour[m].volume / total;
    }
    if (usable == 0) return equal_weights();
    for (double& weight : weights) weight /= usable;
    return weights;
}

inline std::array<Slice, minutes> simulate(const Hour& market, const Profile& weights,
                                           const Scenario& cfg, int side) {
    std::array<Slice, minutes> slices{};
    double executed = 0, cumulative_weight = 0;
    const double arrival = market.front().open;
    for (int m = 0; m < minutes; ++m) {
        cumulative_weight += weights[m];
        double target = cfg.quantity * std::min(1.0, cumulative_weight);
        if (m == minutes - 1) target = cfg.quantity;
        const double requested = std::max(0.0, target - executed);

        // Request is set before this minute. Only settlement reads its volume and VWAP.
        const Bar& bar = market[m];
        const double fill = std::min(requested, cfg.cap * bar.volume);
        const double participation = bar.volume > 0 ? fill / bar.volume : 0;
        const double impact_bps = cfg.impact_at_five_percent_bps * std::sqrt(participation / 0.05);
        const double notional = fill * bar.vwap;
        const double spread = notional * cfg.half_spread_bps / 10000;
        const double impact = notional * impact_bps / 10000;
        const double fee = (notional + side * (spread + impact)) * cfg.fee_bps / 10000;
        executed += fill;
        slices[m] = {requested, fill, std::max(0.0, cfg.quantity - executed),
                     side * fill * (bar.vwap - arrival), spread, impact, fee};
    }
    return slices;
}
} // namespace execution

