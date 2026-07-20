"""Paired, day-block uncertainty estimates and a standalone research report."""
from __future__ import annotations

import csv
import math
import random
import sqlite3
from pathlib import Path
from statistics import mean
from string import Template

SCENARIOS = {"base": "12 BTC · 5% cap", "tight_cap": "12 BTC · 2% cap", "large_order": "36 BTC · 5% cap"}


def percentile(values, fraction):
    ordered = sorted(values)
    pos = (len(ordered) - 1) * fraction
    i = int(pos)
    return ordered[i] + (ordered[math.ceil(pos)] - ordered[i]) * (pos - i)


def block_interval(daily, replicates=2000, length=3):
    # Resample consecutive day means so orders from the same day stay together.
    rng = random.Random(216)
    samples = []
    for _ in range(replicates):
        draw = []
        while len(draw) < len(daily):
            first = rng.randrange(len(daily))
            draw.extend(daily[(first + j) % len(daily)] for j in range(length))
        samples.append(mean(draw[:len(daily)]))
    return percentile(samples, 0.025), percentile(samples, 0.975)


def write_csv(path, cursor):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([col[0] for col in cursor.description])
        writer.writerows(cursor)


def report(db: sqlite3.Connection, out: Path, template: Path):
    write_csv(out / "orders.csv", db.execute("SELECT * FROM orders ORDER BY day,hour,scenario,policy"))
    write_csv(out / "pairs.csv", db.execute("SELECT * FROM pairs ORDER BY day,hour,scenario"))
    summaries, details = [], []
    daily_base = []
    for key, label in SCENARIOS.items():
        data = db.execute("SELECT day, AVG(delta_bps) FROM pairs WHERE scenario=? GROUP BY day ORDER BY day", (key,)).fetchall()
        day_means = [value for _, value in data]
        interval = block_interval(day_means)
        summaries.append((key, label, mean(day_means), *interval))
        if key == "base":
            daily_base = data
        for policy in ("twap", "volume"):
            rows = db.execute("SELECT shortfall_bps,completion FROM orders WHERE scenario=? AND policy=?", (key, policy)).fetchall()
            costs, completion = zip(*rows)
            details.append((label, policy, len(costs), mean(costs), percentile(costs, 0.95), mean(completion)))

    with (out / "comparison.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["scenario", "order_and_cap", "mean_delta_bps", "lower95_bps", "upper95_bps"])
        writer.writerows(summaries)

    _, _, delta, low, high = summaries[0]
    if low <= 0 <= high:
        conclusion = "Keep TWAP as the default for this sample. The estimated difference is too small to distinguish from day-to-day variation."
    elif high < 0:
        conclusion = "The volume schedule reduced modeled cost in the base case. Check a second month and the cost assumptions before changing the default."
    else:
        conclusion = "TWAP had lower modeled cost in the base case. Check whether the advantage holds in a different month."
    rows_html = "".join(
        f"<tr><th>{label}</th><td>{p.upper() if p == 'twap' else 'Volume'}</td>"
        f"<td>{n}</td><td>{avg:.2f}</td><td>{tail:.2f}</td><td>{completion:.1%}</td></tr>"
        for label, p, n, avg, tail, completion in details
    )
    pairs_html = "".join(
        f"<tr><th>{label}</th><td>{avg:+.2f}</td><td>{a:+.2f} to {b:+.2f}</td></tr>"
        for _, label, avg, a, b in summaries
    )
    max_abs = max(abs(v) for _, v in daily_base) or 1
    bars = []
    for day, val in daily_base:
        width = 48 * abs(val) / max_abs
        left = 50 - width if val < 0 else 50
        bars.append(f'<div class="row"><time>{day[5:]}</time><div class="track"><i style="left:{left:.2f}%;width:{width:.2f}%;background:{"#13786d" if val < 0 else "#bb6437"}"></i></div><span>{val:+.2f}</span></div>')
    content = Template(template.read_text(encoding="utf-8")).substitute(
        conclusion=conclusion, delta=f"{delta:+.2f}", interval=f"{low:+.2f} to {high:+.2f}",
        orders=len(daily_base) * 6, rows=rows_html, paired=pairs_html, bars="".join(bars)
    )
    (out / "report.html").write_text(content, encoding="utf-8")

