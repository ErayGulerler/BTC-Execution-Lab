import csv
import io
import math
import subprocess
import tempfile
import unittest
from pathlib import Path

from analysis.report import block_interval
from run import ROOT, build


def tape(change=None):
    """Seven training days, then one flat-price evaluation hour."""
    rows = []
    for day in range(1, 9):
        for hour in (range(0, 24, 4) if day < 8 else [0]):
            for minute in range(60):
                price, close, volume = 100., 100., 10.
                if change:
                    close, volume = change(day, minute, close, volume)
                rows.append(f"2024-06-{day:02} {hour} {minute} {price} {close} {volume} {price}")
    return "\n".join(rows) + "\n"


class ReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(dir=ROOT)
        cls.engine = build(Path(cls.folder.name))

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def replay(self, change=None):
        result = subprocess.run([self.engine], input=tape(change), capture_output=True, text=True, check=True)
        return list(csv.DictReader(io.StringIO(result.stdout)))

    def test_flat_market_cost_identity(self):
        rows = [r for r in self.replay() if (r["scenario"], r["policy"]) == ("base", "twap")]
        # Sell 0.2 BTC per minute into 10 BTC. Fee is charged on net proceeds.
        impact = 2 * math.sqrt(0.02 / 0.05)
        expected_bps = 0.5 + impact + 4 * (1 - (0.5 + impact) / 10000)
        costs = sum(float(r[k]) for r in rows for k in ("timing", "fee", "impact", "spread", "opportunity"))
        self.assertAlmostEqual(costs * 10000 / (12 * 100), expected_bps)
        self.assertAlmostEqual(sum(float(r["filled"]) for r in rows), 12)

    def test_zero_liquidity_residual_cost_and_side(self):
        def illiquid(day, minute, close, volume):
            return (98., 0.) if day == 8 else (close, volume)
        rows = self.replay(illiquid)
        last = next(r for r in rows if r["policy"] == "twap" and r["scenario"] == "base" and r["minute"] == "59")
        self.assertEqual(float(last["remaining"]), 12)
        self.assertEqual(int(last["side"]), -1)
        self.assertEqual(float(last["opportunity"]), 24)
        self.assertTrue(all(float(r["filled"]) == 0 for r in rows))

    def test_volume_forecast_uses_prior_days(self):
        def peaked(day, minute, close, volume):
            return close, (60. if minute == 0 else 0.) if day < 8 else volume
        rows = self.replay(peaked)
        first = next(r for r in rows if r["scenario"] == "base" and r["policy"] == "volume")
        self.assertAlmostEqual(float(first["requested"]), 12)
        self.assertAlmostEqual(float(first["filled"]), 0.5)

    def test_current_volume_only_changes_settlement(self):
        def future(day, minute, close, volume):
            return close, 0. if day == 8 and minute >= 30 else volume
        original, changed = self.replay(), self.replay(future)
        for a, b in zip(original, changed, strict=True):
            if int(a["minute"]) < 30:
                self.assertEqual(a, b)
            if int(a["minute"]) == 30:
                self.assertEqual(a["requested"], b["requested"])

    def test_buy_side_opportunity_and_direction(self):
        # Add a second evaluation hour. Day eight, hour four is a buy.
        data = tape()
        for m in range(60):
            data += f"2024-06-08 4 {m} 100 102 0 100\n"
        result = subprocess.run([self.engine], input=data, capture_output=True, text=True, check=True)
        rows = list(csv.DictReader(io.StringIO(result.stdout)))
        last = next(r for r in rows if (r["hour"], r["scenario"], r["policy"], r["minute"]) == ("4", "base", "twap", "59"))
        self.assertEqual(int(last["side"]), 1)
        self.assertEqual(float(last["opportunity"]), 24)

    def test_flat_forecast_with_no_history_volume(self):
        rows = self.replay(lambda d, m, c, v: (c, 0 if d < 8 else v))
        first = next(r for r in rows if r["scenario"] == "base" and r["policy"] == "volume")
        self.assertAlmostEqual(float(first["requested"]), 0.2)

    def test_no_overfill_or_excess_participation(self):
        for row in self.replay():
            cap = 0.02 if row["scenario"] == "tight_cap" else 0.05
            self.assertLessEqual(float(row["filled"]), cap * 10 + 1e-10)
            self.assertGreaterEqual(float(row["remaining"]), 0)
            self.assertLessEqual(float(row["filled"]), float(row["requested"]) + 1e-10)

    def test_rejects_incomplete_market(self):
        result = subprocess.run([self.engine], input="2024-06-01 0 1 100 100 10 100\n", capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Missing minute", result.stderr)

    def test_constant_paired_cost_has_point_interval(self):
        self.assertEqual(block_interval([2.] * 10, replicates=50), (2., 2.))

