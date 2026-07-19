"""Read the pinned Binance Vision archive. The pipeline runs offline."""
from __future__ import annotations

import csv
import hashlib
import io
import math
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ARCHIVE = "BTCUSDT-1m-2024-06.zip"
SHA256 = "90f4fc3f55918787848c71f4cd0f2f1a5851bbffaf6392e76e9ab555b7479d2b"
START_MS = 1717200000000  # 2024-06-01 00:00:00 UTC


def normalize(archive: Path, output: Path) -> None:
    if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
        raise ValueError("Archive does not match the pinned SHA-256")
    count = 0
    with zipfile.ZipFile(archive) as zipped, zipped.open(ARCHIVE[:-4] + ".csv") as raw:
        with output.open("w", encoding="ascii", newline="\n") as target:
            for count, row in enumerate(csv.reader(io.TextIOWrapper(raw, encoding="ascii")), 1):
                timestamp = int(row[0])
                if timestamp != START_MS + (count - 1) * 60_000:
                    raise ValueError(f"Gap or duplicate at source row {count}")
                op, hi, lo, close, volume = map(float, row[1:6])
                quote = float(row[7])
                numbers = (op, hi, lo, close, volume, quote)
                if not all(map(math.isfinite, numbers)) or not 0 < lo <= min(op, close) <= max(op, close) <= hi:
                    raise ValueError(f"Invalid price at source row {count}")
                if volume < 0 or quote < 0 or (volume == 0) != (quote == 0):
                    raise ValueError(f"Invalid volume at source row {count}")
                vwap = quote / volume if volume else close
                if volume and not lo - 0.01 <= vwap <= hi + 0.01:
                    raise ValueError(f"VWAP outside bar range at source row {count}")
                dt = datetime.fromtimestamp(timestamp / 1000, timezone.utc)
                if dt.hour % 4 == 0:
                    print(dt.date(), dt.hour, dt.minute, op, close, volume, vwap, file=target)
    if count != 30 * 24 * 60:
        raise ValueError("Archive is missing minutes")

