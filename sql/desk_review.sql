-- Run on results/execution.sqlite after python run.py.
-- Which windows drove the relative cost? Lower delta favors the volume policy.
SELECT hour, COUNT(*) AS orders, ROUND(AVG(delta_bps), 3) AS mean_delta_bps
FROM pairs WHERE scenario = 'base'
GROUP BY hour ORDER BY hour;

-- Break down the TWAP cost when the customer triples the parent quantity.
SELECT scenario,
       ROUND(100 * AVG(completion), 2) AS filled_pct,
       ROUND(AVG(timing_bps), 3) AS timing_bp,
       ROUND(AVG(spread_bps), 3) AS spread_bp,
       ROUND(AVG(impact_bps), 3) AS impact_bp,
       ROUND(AVG(fee_bps), 3) AS fee_bp,
       ROUND(AVG(residual_bps), 3) AS residual_bp
FROM orders WHERE policy = 'twap'
GROUP BY scenario ORDER BY scenario;

-- Inspect one parent order from forecast requests to final residual.
SELECT minute, ROUND(requested, 4) AS requested_btc, ROUND(filled, 4) AS filled_btc,
       ROUND(remaining, 4) AS outstanding_btc, ROUND(opportunity, 4) AS residual_usdt
FROM fills
WHERE day = '2024-06-08' AND hour = 8 AND scenario = 'base' AND policy = 'volume'
ORDER BY minute;

