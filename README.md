# BTC Execution Lab

A one-hour BTC order is too large to assume it all trades at the opening price. This project compares two ways of splitting it across the hour. TWAP targets equal slices. A second schedule uses the last seven days of volume to decide when to trade more heavily.

**Start with [the execution report](sample/report.html).** It opens offline and includes the decision, the order-size stress test and downloadable order-level results. [CV wording and an interview walkthrough](docs/portfolio.md) are included.

## Result

Across 138 paired orders in the base case, the volume schedule averaged **0.27 basis points less modeled shortfall** than TWAP. The 95% interval for volume minus TWAP ran from **−0.69 to +0.11 bp**. That leaves too little evidence to switch the default schedule on cost alone. One basis point is 0.01% of order value.

Order size mattered more to completion. At 12 BTC, the volume schedule filled **97.4%** on average. At 36 BTC, that fell to **77.2%**, compared with **75.9%** for TWAP. A desk with a firm deadline would need to revisit the participation limit or allow more time. All fills are simulated on historical BTCUSDT bars from June 2024.

## Run it

Extract the ZIP first. Open a terminal in the folder containing this README. Use Python 3.10 or later and a C++17 compiler. The Python code uses the standard library. The data is bundled, and the experiment runs offline.

```sh
python run.py
python -m unittest discover -s tests -v
python tests/check_results.py results
```

Open `results/report.html`. The run also writes an SQLite database with the complete minute-by-minute fill ledger.

On Windows, use a Visual Studio Developer PowerShell with the C++ tools installed, or put MinGW g++ on your PATH. If Python is installed through the Windows launcher, replace `python` with `py -3`. On Linux use g++, and on macOS use clang++ from the Xcode command line tools. The runner also accepts `CXX` set to the path of a g++, clang++, cl or Zig executable.

## Read the code in order

| File | Responsibility |
| --- | --- |
| `analysis/market.py` | Verify the source hash, minute sequence and prices. Select six one-hour windows per day. |
| `engine/replay.hpp` | Forecast a volume curve, schedule child orders, cap fills and charge execution costs. |
| `engine/main.cpp` | Roll the seven-day training window and replay both policies on the same parent orders. |
| `sql/orders.sql` | Aggregate fills into orders and pair both outcomes using the same day, hour, side and scenario. |
| `analysis/report.py` | Estimate day-block intervals and write the report and CSVs. |
| `sql/desk_review.sql` | Query costs by time of day and inspect one order minute by minute. |

The base case targets 12 BTC at up to 5% of minute volume. Two stress cases tighten participation to 2% or triple the parent order to 36 BTC. For the shortfall formula, a worked example and the model's limitations, read [the method](docs/method.md). [Data provenance and terms](data/README.md) cover the historical archive and derived results.

## Why this stack

C++ handles the repeatable execution loop, Python handles validation and statistical analysis, and SQL makes each reported cost traceable to individual fills. The language choice follows examples of quant roles that ask for model implementation, simulation and execution analysis. The sources are examples of hiring requirements, not a market-wide ranking. [Citadel quantitative research internship](https://www.citadel.com/careers/details/quantitative-research-analyst-intern-bs-ms-europe/) · [IMC quantitative trading role](https://www.imc.com/us/careers/jobs/4787640101)

