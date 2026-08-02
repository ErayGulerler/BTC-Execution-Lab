# How the replay works

## The question

An execution desk receives a parent order with a one-hour deadline. Should it target the same quantity every minute, or wait for the minutes that were busiest in recent sessions? The costs a trader cares about are the price paid relative to arrival and the quantity still open at the deadline. A cheaper average fill on a half-finished order can be misleading.

## A day in the experiment

At 08:00 UTC on June 8, for example, the volume policy can see the 08:00–08:59 bars from June 1 through June 7. It divides each of those historical hours into 60 minute-volume shares and averages the seven curves. Each day has equal weight. A zero-volume training hour is skipped. An all-zero history gives equal weights.

The forecast is frozen for the full hour. TWAP targets 1/60 of the parent order each minute. If either schedule falls behind, the next request includes the backlog. A request is set before the minute starts. When the minute closes, the simulator fills up to the smaller of the request and the allowed share of actual market volume. This ordering prevents the schedule from seeing liquidity that has yet to trade.

Six non-overlapping sessions start at 00, 04, 08, 12, 16 and 20 UTC each day. Buy and sell sides alternate across hours and reverse the next day. Positive cost means a worse outcome on either side. The 23 evaluation days therefore give 138 paired parent orders per scenario. Each order is a separate counterfactual decision.

## Fill prices and shortfall

The arrival reference is the first bar's open. It approximates the price at order receipt. A child's reference price is quote volume in USDT divided by base volume in BTC. Simulated fills pay a half-spread of 0.5 bp and impact of `2 × sqrt(participation / 0.05)` bp. Participation is filled BTC divided by that minute's historical BTC volume. Costs move the fill price up for buys and down for sells. A fee of 4 bp is charged on the resulting fill notional. These parameters are assumptions, with no fee tier or measured impact calibration implied.

For side +1 on buys and −1 on sells, let Q be ordered BTC, A the arrival price, F the sum of filled BTC and C the deadline close. The model records five cost components in USDT.

| Component | Calculation |
| --- | --- |
| Timing | Sum of side × child BTC × (minute VWAP − A) |
| Spread | Sum of child VWAP notional × assumed half-spread |
| Impact | Sum of child VWAP notional × modeled impact |
| Fees | Sum of executed notional × fee rate |
| Residual opportunity cost | side × (Q − F) × (C − A) |

Divide the sum by Q × A and multiply by 10,000 to get implementation shortfall in basis points. The residual mark can be positive or negative. It measures the price move on the outstanding quantity. It excludes the additional spread and impact that a later completion would incur. The report presents completion alongside shortfall for this reason.

A simple check is to buy two BTC at an arrival price of 100. Fill one at 101 before costs and leave one unfilled when the market closes at 102. Timing costs 1 and residual opportunity costs 2. Shortfall before fees and friction is 3 / 200 × 10,000 = 150 bp.

## Evaluation

Each day advances the training window by one. The two policies share each market path, and the cost difference is volume minus TWAP. The primary statistic is the mean of those paired differences in the base case. Each hour and each day carry equal weight. The secondary scenarios change one assumption at a time. They serve as sensitivity checks.

The interval resamples whole days in circular, consecutive three-day blocks with replacement. Each draw contains 23 days after truncation. Keeping six sessions together respects within-day dependence, and short blocks preserve some day-to-day dependence. The endpoints are the 2.5th and 97.5th percentiles of 2,000 bootstrap means with seed 216. Block length is a modeling choice. With only 23 days, treat the interval as exploratory.

## What would change the decision?

Minute bars cannot say where the best quote stood, how much liquidity was displayed or how the market would react to our order. This fill model assumes access to a fraction of all traded volume, values fills at minute VWAP and treats impact as temporary. A large customer order could move subsequent prices.

A next experiment would freeze the schedule and costs, replay an untouched second month, and compare both cost and completion. With historical bid/ask and trade messages, replace the constant half-spread and test whether assumed fill quantities were available at the time.

