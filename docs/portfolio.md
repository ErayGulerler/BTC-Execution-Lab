# CV and interview notes

## CV project entry

**BTC Execution Lab | C++17, Python, SQL**  
Compared TWAP with a rolling volume-weighted schedule on 138 paired BTC execution simulations per scenario. Measured implementation shortfall, fill completion and tail costs under three order-size and participation settings using historical one-minute market data.

## A short walkthrough

1. Open the precomputed report. Explain the desk's decision and the sign convention before discussing the result.
2. Open the paired comparisons CSV. Pick one hour when the volume schedule performed worse. Use the order-level CSV to identify how much came from timing, impact and missed quantity.
3. In `engine/replay.hpp`, trace one request that exceeds the participation cap. Follow the backlog into the next minute.
4. Explain why the forecast only uses prior days. Point to the test that changes later volumes and checks that earlier requests stay identical.
5. Explain why the 138 observations cover only 23 days, and why that changes how you estimate uncertainty.

## A change to make your own

Choose an hour where both policies leave quantity unfilled. Before changing the code, predict what a more urgent schedule would do to completion and cost. Add a third policy with a simple front-loaded curve, keep the paired orders fixed, and record whether your prediction held. The order ledger lets you explain one specific trade-off in an interview.

