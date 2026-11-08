"""Headline business metrics and customer concentration helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from .data import DataBundle


@dataclass(slots=True)
class KPIResult:
    values: dict[str, Any]
    lorenz: pd.DataFrame = field(default_factory=pd.DataFrame)


def _safe_div(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def _top_share(values: pd.Series, fraction: float) -> float:
    if values.empty or values.sum() <= 0:
        return 0.0
    n = max(1, int(np.ceil(len(values) * fraction)))
    ordered = values.sort_values(ascending=False)
    return float(ordered.head(n).sum() / values.sum())


def gini(values: pd.Series) -> float:
    """Gini coefficient for a non-negative distribution (0 = equal, 1 = maximal)."""

    arr = np.sort(values.dropna().to_numpy(dtype=float))
    arr = arr[arr >= 0]
    n = len(arr)
    total = arr.sum()
    if n == 0 or total <= 0:
        return 0.0
    index = np.arange(1, n + 1)
    return float((2 * np.sum(index * arr) / (n * total)) - (n + 1) / n)


def customer_lorenz(customers: pd.DataFrame, points: int = 240) -> pd.DataFrame:
    """Cumulative revenue share as customers are ordered from low to high value."""

    if customers.empty:
        return pd.DataFrame(columns=["customer_share", "revenue_share"])

    values = np.sort(customers["monetary"].to_numpy(dtype=float))
    total = values.sum()
    if total <= 0:
        return pd.DataFrame(columns=["customer_share", "revenue_share"])

    cum = np.cumsum(values) / total
    customer_share = np.arange(1, len(values) + 1) / len(values)
    idx = np.unique(np.linspace(0, len(values) - 1, min(points, len(values))).astype(int))
    curve = pd.DataFrame(
        {
            "customer_share": np.r_[0.0, customer_share[idx]],
            "revenue_share": np.r_[0.0, cum[idx]],
        }
    )
    return curve


def compute_kpis(bundle: DataBundle) -> KPIResult:
    sales = bundle.sales
    orders = bundle.orders
    customers = bundle.customers
    products = bundle.products
    monthly = bundle.monthly
    quality = bundle.quality

    total_revenue = float(sales["revenue"].sum()) if not sales.empty else 0.0
    total_orders = int(orders["invoice_no"].nunique()) if not orders.empty else 0
    total_customers = int(customers["customer_id"].nunique()) if not customers.empty else 0
    total_units = int(sales["quantity"].sum()) if not sales.empty else 0
    aov = _safe_div(total_revenue, total_orders)
    median_order = float(orders["revenue"].median()) if not orders.empty else 0.0
    p90_order = float(orders["revenue"].quantile(0.90)) if not orders.empty else 0.0
    median_order_units = float(orders["units"].median()) if not orders.empty else 0.0
    items_per_order = _safe_div(total_units, total_orders)

    repeat_customers = int((customers["frequency"] > 1).sum()) if not customers.empty else 0
    repeat_rate = _safe_div(repeat_customers, total_customers)
    identified_revenue = float(customers["monetary"].sum()) if not customers.empty else 0.0
    repeat_revenue = (
        float(customers.loc[customers["frequency"] > 1, "monetary"].sum())
        if not customers.empty
        else 0.0
    )
    repeat_revenue_share = _safe_div(repeat_revenue, identified_revenue)
    orders_per_customer = _safe_div(total_orders, total_customers)

    complete = monthly.loc[~monthly["is_partial"]] if not monthly.empty else monthly
    avg_monthly_revenue = float(complete["revenue"].mean()) if not complete.empty else 0.0
    peak_row = complete.loc[complete["revenue"].idxmax()] if not complete.empty else None
    peak_month = str(peak_row["invoice_month"]) if peak_row is not None else "—"
    peak_revenue = float(peak_row["revenue"]) if peak_row is not None else 0.0
    peak_multiple = _safe_div(peak_revenue, avg_monthly_revenue)

    top10_customer_share = _top_share(customers["monetary"], 0.10) if not customers.empty else 0.0
    top20_customer_share = _top_share(customers["monetary"], 0.20) if not customers.empty else 0.0

    if not products.empty:
        cutoff = max(1, int(np.ceil(len(products) * 0.20)))
        top20_sku_share = float(products.head(cutoff)["revenue"].sum() / products["revenue"].sum())
        sku_for_80 = int((products["cumulative_share"] < 0.80).sum() + 1)
        sku_for_80_share = _safe_div(sku_for_80, len(products))
        top10_product_share = float(products.head(10)["revenue"].sum() / products["revenue"].sum())
    else:
        top20_sku_share = 0.0
        sku_for_80 = 0
        sku_for_80_share = 0.0
        top10_product_share = 0.0

    uk = bundle.countries.loc[bundle.countries["country"] == "United Kingdom", "share"]
    uk_share = float(uk.iloc[0]) if not uk.empty else 0.0
    active_days = int(sales["invoice_date"].dt.date.nunique()) if not sales.empty else 0
    date_min = quality.get("date_min")
    date_max = quality.get("date_max")
    period_days = (date_max - date_min).days + 1 if pd.notna(date_min) and pd.notna(date_max) else 0

    values = {
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "total_customers": total_customers,
        "total_units": total_units,
        "aov": aov,
        "median_order_value": median_order,
        "p90_order_value": p90_order,
        "median_order_units": median_order_units,
        "items_per_order": items_per_order,
        "orders_per_customer": orders_per_customer,
        "repeat_customers": repeat_customers,
        "repeat_rate": repeat_rate,
        "repeat_revenue_share": repeat_revenue_share,
        "identified_revenue": identified_revenue,
        "guest_revenue_share": float(quality.get("guest_revenue_share", 0.0)),
        "guest_order_share": float(quality.get("guest_order_share", 0.0)),
        "cancellation_value": float(quality.get("cancellation_value", 0.0)),
        "cancellation_rate": float(quality.get("cancellation_rate", 0.0)),
        "cancellation_invoices": int(quality.get("cancellation_invoices", 0)),
        "avg_monthly_revenue": avg_monthly_revenue,
        "complete_months": int(len(complete)),
        "peak_month": peak_month,
        "peak_revenue": peak_revenue,
        "peak_multiple": peak_multiple,
        "top10_customer_share": top10_customer_share,
        "top20_customer_share": top20_customer_share,
        "customer_gini": gini(customers["monetary"]) if not customers.empty else 0.0,
        "top20_sku_share": top20_sku_share,
        "top10_product_share": top10_product_share,
        "sku_for_80": sku_for_80,
        "sku_for_80_share": sku_for_80_share,
        "sku_count": int(len(products)),
        "uk_share": uk_share,
        "active_days": active_days,
        "period_days": period_days,
        "revenue_per_active_day": _safe_div(total_revenue, active_days),
        "date_min": date_min,
        "date_max": date_max,
    }
    return KPIResult(values=values, lorenz=customer_lorenz(customers))
