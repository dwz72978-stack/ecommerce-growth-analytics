"""Command-line entry point for the analysis pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import DEFAULT_RAW_PATH, DEFAULT_SAMPLE_PATH
from .data import DataValidationError
from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ecommerce-analytics",
        description="Run the end-to-end e-commerce analytics pipeline and build the static report.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help=f"Transaction CSV/CSV.GZ (default: {DEFAULT_RAW_PATH})",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help=f"Use the bundled sample instead of the full dataset ({DEFAULT_SAMPLE_PATH})",
    )
    parser.add_argument("--outdir", type=Path, default=Path("reports"), help="CSV/JSON output directory")
    parser.add_argument("--site-dir", type=Path, default=Path("docs"), help="Static report output directory")
    parser.add_argument("--quiet", action="store_true", help="Only print errors")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_path = args.input
    if input_path is None:
        input_path = Path(DEFAULT_SAMPLE_PATH) if args.sample else Path(DEFAULT_RAW_PATH)

    try:
        context = run_pipeline(input_path, outdir=args.outdir, site_dir=args.site_dir)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except DataValidationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if not args.quiet:
        k = context.kpis.values
        print("Analysis complete")
        print(f"  input      : {input_path}")
        print(f"  sales      : £{k['total_revenue']:,.0f}")
        print(f"  orders     : {k['total_orders']:,}")
        print(f"  customers  : {k['total_customers']:,}")
        print(f"  report     : {args.site_dir / 'index.html'}")
        print(f"  metrics    : {args.outdir / 'metrics.json'}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
