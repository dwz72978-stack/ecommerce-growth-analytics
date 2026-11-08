"""End-to-end analysis pipeline."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .basket import BasketResult, mine_basket_rules
from .charts import (
    basket_rules_chart,
    cancellation_chart,
    cohort_heatmap,
    country_mix_chart,
    lorenz_chart,
    monthly_revenue_chart,
    pareto_chart,
    rfm_segment_chart,
    rhythm_heatmap,
)
from .cohort import CohortResult, build_cohorts
from .data import DataBundle, load_transactions, prepare_data
from .metrics import KPIResult, compute_kpis
from .rfm import high_value_at_risk, score_rfm, summarise_segments


@dataclass(slots=True)
class AnalysisContext:
    bundle: DataBundle
    kpis: KPIResult
    scored: pd.DataFrame
    segments: pd.DataFrame
    high_value: dict[str, Any]
    cohorts: CohortResult
    basket: BasketResult
    figures: dict[str, str]
    generated_at: str
    input_path: Path


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, pd.Period):
        return str(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if np.isnan(value) else float(value)
    if isinstance(value, float) and np.isnan(value):
        return None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def _frame_records(df: pd.DataFrame, columns: list[str] | None = None) -> list[dict[str, Any]]:
    if df.empty:
        return []
    subset = df[columns] if columns else df
    records = subset.to_dict(orient="records")
    return _json_safe(records)


def run_pipeline(
    input_path: str | Path,
    *,
    outdir: str | Path = "reports",
    site_dir: str | Path = "docs",
) -> AnalysisContext:
    input_path = Path(input_path)
    outdir = Path(outdir)
    site_dir = Path(site_dir)
    figures_dir = site_dir / "figures"
    outdir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    raw = load_transactions(input_path)
    bundle = prepare_data(raw)
    kpis = compute_kpis(bundle)
    scored = score_rfm(bundle.customers, bundle.snapshot)
    segments = summarise_segments(scored)
    hvar = high_value_at_risk(scored)
    cohorts = build_cohorts(bundle.sales, bundle.last_complete_month)
    basket = mine_basket_rules(bundle.sales, bundle.products)

    figures = {
        "monthly": monthly_revenue_chart(bundle.monthly, figures_dir / "monthly_revenue.svg"),
        "country": country_mix_chart(bundle.countries, figures_dir / "country_mix.svg"),
        "pareto": pareto_chart(bundle.products, figures_dir / "pareto.svg"),
        "rfm": rfm_segment_chart(segments, figures_dir / "rfm_segments.svg"),
        "lorenz": lorenz_chart(
            kpis.lorenz,
            kpis.values["top10_customer_share"],
            kpis.values["customer_gini"],
            figures_dir / "lorenz.svg",
        ),
        "cohort": cohort_heatmap(
            cohorts.rates,
            cohorts.sizes,
            cohorts.summary,
            figures_dir / "cohort_retention.svg",
        ),
        "rhythm": rhythm_heatmap(bundle.rhythm, figures_dir / "rhythm.svg"),
        "basket": basket_rules_chart(basket.rules, figures_dir / "basket_rules.svg"),
        "cancellation": cancellation_chart(
            bundle.monthly,
            kpis.values["cancellation_rate"],
            figures_dir / "cancellation.svg",
        ),
    }

    generated_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    context = AnalysisContext(
        bundle=bundle,
        kpis=kpis,
        scored=scored,
        segments=segments,
        high_value=hvar,
        cohorts=cohorts,
        basket=basket,
        figures=figures,
        generated_at=generated_at,
        input_path=input_path,
    )
    write_artifacts(context, outdir=outdir, site_dir=site_dir)
    return context


def write_artifacts(context: AnalysisContext, *, outdir: Path, site_dir: Path) -> None:
    from .reporting import render_report

    bundle = context.bundle
    kpis = context.kpis
    outdir.mkdir(parents=True, exist_ok=True)

    bundle.monthly.to_csv(outdir / "monthly_summary.csv", index=False, float_format="%.4f")
    bundle.countries.to_csv(outdir / "country_summary.csv", index=False, float_format="%.4f")
    bundle.products.head(100).to_csv(outdir / "top_products.csv", index=False, float_format="%.4f")
    context.segments.to_csv(outdir / "rfm_segments.csv", index=False, float_format="%.4f")
    if not context.cohorts.long.empty:
        context.cohorts.long.to_csv(outdir / "cohort_retention.csv", index=False, float_format="%.4f")
    if not context.basket.rules.empty:
        context.basket.rules.to_csv(outdir / "basket_rules.csv", index=False, float_format="%.4f")

    top_products = bundle.products.head(10)[
        ["rank", "stock_code", "description", "revenue", "orders", "units", "avg_unit_price"]
    ]
    top_countries = bundle.countries.head(8)[["country", "revenue", "orders", "customers", "share"]]
    cohort_summary = {
        "cohorts": context.cohorts.summary.get("cohorts", 0),
        "customers": context.cohorts.summary.get("customers", 0),
        "first_cohort": context.cohorts.summary.get("first_cohort"),
        "last_cohort": context.cohorts.summary.get("last_cohort"),
        "m1": context.cohorts.summary.get("m1"),
        "m3": context.cohorts.summary.get("m3"),
        "m6": context.cohorts.summary.get("m6"),
        "m10": context.cohorts.summary.get("m10"),
        "m12": context.cohorts.summary.get("m12"),
    }
    metrics = {
        "meta": {
            "project": "E-commerce Growth Analytics",
            "version": "1.0.0",
            "generated_at": context.generated_at,
            "input": str(context.input_path),
            "snapshot": context.bundle.snapshot.date().isoformat(),
            "last_complete_month": str(context.bundle.last_complete_month),
        },
        "kpis": kpis.values,
        "quality": bundle.quality,
        "segments": _frame_records(context.segments),
        "high_value_at_risk": context.high_value,
        "cohort": cohort_summary,
        "basket": {
            "orders_considered": context.basket.orders_considered,
            "products_considered": context.basket.products_considered,
            "rules": _frame_records(context.basket.rules),
        },
        "monthly": _frame_records(bundle.monthly),
        "countries": _frame_records(top_countries),
        "top_products": _frame_records(top_products),
    }
    text = json.dumps(_json_safe(metrics), ensure_ascii=False, indent=2)
    (outdir / "metrics.json").write_text(text, encoding="utf-8")

    render_report(context, site_dir / "index.html")
