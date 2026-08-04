"""Run after a complete replay to audit the persisted outputs."""
import csv
import math
import sqlite3
import sys
from pathlib import Path


def check(out):
    with sqlite3.connect((out / "execution.sqlite").resolve().as_uri() + "?mode=ro", uri=True) as db:
        assert db.execute("SELECT COUNT(*) FROM fills").fetchone()[0] == 49_680
        assert db.execute("SELECT COUNT(*) FROM pairs").fetchone()[0] == 414
        count, start, end = db.execute("SELECT COUNT(*), MIN(day), MAX(day) FROM orders").fetchone()
        assert (count, start, end) == (828, "2024-06-08", "2024-06-30")
        for cost, parts, completion in db.execute("""
            SELECT shortfall_bps, timing_bps+fee_bps+spread_bps+impact_bps+residual_bps, completion
            FROM orders
        """):
            assert math.isclose(cost, parts, abs_tol=1e-9)
            assert -1e-12 <= completion <= 1 + 1e-12
        with (out / "orders.csv").open() as f:
            assert len(list(csv.DictReader(f))) == count
        with (out / "comparison.csv").open() as f:
            for r in csv.DictReader(f):
                expected, = db.execute("SELECT AVG(delta_bps) FROM pairs WHERE scenario=?", (r["scenario"],)).fetchone()
                assert math.isclose(float(r["mean_delta_bps"]), expected, abs_tol=1e-9)
    print("Verified fill count, pair count, dates, component accounting, completion and CSV aggregates.")


if __name__ == "__main__":
    check(Path(sys.argv[1]))

