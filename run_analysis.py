#!/usr/bin/env python
"""Run the complete analysis without installing the package."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ecommerce_analytics.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
