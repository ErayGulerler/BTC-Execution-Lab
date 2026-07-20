CREATE TABLE fills (
    day TEXT NOT NULL, hour INTEGER NOT NULL, side INTEGER NOT NULL,
    scenario TEXT NOT NULL, policy TEXT NOT NULL, minute INTEGER NOT NULL,
    quantity REAL NOT NULL, arrival REAL NOT NULL, requested REAL NOT NULL,
    filled REAL NOT NULL, remaining REAL NOT NULL, timing REAL NOT NULL,
    spread REAL NOT NULL, impact REAL NOT NULL, fee REAL NOT NULL,
    opportunity REAL NOT NULL,
    PRIMARY KEY(day, hour, scenario, policy, minute)
);

CREATE VIEW orders AS
SELECT day, hour, side, scenario, policy, quantity, arrival,
       SUM(filled) / quantity AS completion,
       SUM(timing) * 1e4 / (quantity * arrival) AS timing_bps,
       SUM(spread) * 1e4 / (quantity * arrival) AS spread_bps,
       SUM(impact) * 1e4 / (quantity * arrival) AS impact_bps,
       SUM(fee) * 1e4 / (quantity * arrival) AS fee_bps,
       SUM(opportunity) * 1e4 / (quantity * arrival) AS residual_bps,
       SUM(timing + spread + impact + fee + opportunity)
           * 1e4 / (quantity * arrival) AS shortfall_bps
FROM fills
GROUP BY day, hour, side, scenario, policy, quantity, arrival;

CREATE VIEW pairs AS
SELECT v.day, v.hour, v.side, v.scenario,
       v.shortfall_bps - t.shortfall_bps AS delta_bps,
       v.completion - t.completion AS delta_completion
FROM orders AS v JOIN orders AS t USING (day, hour, side, scenario)
WHERE v.policy = 'volume' AND t.policy = 'twap';

