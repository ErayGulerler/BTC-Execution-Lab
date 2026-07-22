"""Build the C++ replay, run the pinned experiment and write the research report."""
import argparse
import csv
import os
import shutil
import sqlite3
import subprocess
import tempfile
from pathlib import Path

from analysis.market import ARCHIVE, normalize
from analysis.report import report

ROOT = Path(__file__).resolve().parent


def build(directory):
    compiler = os.environ.get("CXX") or next(
        (name for name in ("g++", "clang++", "cl") if shutil.which(name)), None)
    if not compiler:
        raise SystemExit("Install a C++17 compiler or set CXX to its executable path. See README.md.")
    exe = directory / ("replay.exe" if os.name == "nt" else "replay")
    source = str(ROOT / "engine/main.cpp")
    if Path(compiler).stem.lower() == "cl":
        args = [compiler, "/nologo", "/EHsc", "/std:c++17", "/O2", source, f"/Fe:{exe}"]
    else:
        args = [compiler]
        if Path(compiler).stem.lower() == "zig":
            args.append("c++")
        args.extend(["-std=c++17", "-O2", "-Wall", "-Wextra", source, "-o", str(exe)])
    subprocess.run(args, check=True, cwd=directory)
    return exe


def experiment(output, executable=None):
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as scratch:
        stage = Path(scratch)
        binary = executable or build(stage)
        market = stage / "market.txt"
        normalize(ROOT / "data" / ARCHIVE, market)
        with market.open("rb") as source, (stage / "fills.csv").open("wb") as dest:
            subprocess.run([binary], stdin=source, stdout=dest, check=True)
        db = sqlite3.connect(stage / "execution.sqlite")
        try:
            db.executescript((ROOT / "sql/orders.sql").read_text())
            with (stage / "fills.csv").open(newline="", encoding="ascii") as f:
                reader = csv.reader(f)
                header = next(reader)
                columns = [row[1] for row in db.execute("PRAGMA table_info(fills)")]
                if header != columns:
                    raise ValueError("Engine and SQL schema disagree on fill columns")
                db.executemany("INSERT INTO fills VALUES (" + ",".join("?" for _ in columns) + ")", reader)
            db.commit()
            report(db, stage, ROOT / "analysis/report.html")
        finally:
            db.close()
        for name in ("execution.sqlite", "orders.csv", "pairs.csv", "comparison.csv", "report.html"):
            (stage / name).replace(output / name)
    print(f"Report: {output / 'report.html'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "results")
    parser.add_argument("--engine", type=Path, help="Use an existing replay executable")
    args = parser.parse_args()
    experiment(args.out.resolve(), args.engine.resolve() if args.engine else None)

