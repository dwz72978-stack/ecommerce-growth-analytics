#!/usr/bin/env python
"""Download the UCI Online Retail CSV and store it as a gzip file.

The UCI page distributes an Excel workbook. This helper uses a public CSV
mirror of the same UCI table (the Databricks Spark example repository) so the
project can be reproduced without Excel. You can also download the original
workbook yourself and convert it to CSV.

Usage:
    python scripts/fetch_data.py
    python scripts/fetch_data.py --force
"""

from __future__ import annotations

import argparse
import gzip
import sys
import urllib.request
from pathlib import Path

URL = (
    "https://raw.githubusercontent.com/databricks/Spark-The-Definitive-Guide/"
    "master/data/retail-data/all/online-retail-dataset.csv"
)
DEFAULT_OUT = Path("data/raw/online_retail.csv.gz")


def download(url: str, out: Path, *, force: bool = False) -> None:
    if out.exists() and not force:
        print(f"{out} already exists; use --force to overwrite.")
        return

    out.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "ecommerce-growth-analytics/1.0"})
    print(f"Downloading {url}")
    with urllib.request.urlopen(request, timeout=120) as response:
        total = int(response.headers.get("Content-Length") or 0)
        written = 0
        with gzip.open(out, "wt", encoding="utf-8", newline="") as target:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                target.write(chunk.decode("utf-8"))
                written += len(chunk)
                if total:
                    print(f"\r  {written / 1e6:6.1f} / {total / 1e6:6.1f} MB", end="", flush=True)
        print()
    print(f"Saved {out} ({out.stat().st_size / 1e6:.1f} MB compressed)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=URL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        download(args.url, args.out, force=args.force)
    except Exception as exc:  # pragma: no cover - network path
        print(f"Download failed: {exc}", file=sys.stderr)
        print("You can download the UCI workbook manually and save it as data/raw/online_retail.csv.gz.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
