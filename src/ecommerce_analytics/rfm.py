"""RFM scoring and actionable customer segmentation."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .config import SEGMENT_COLORS, SEGMENT_DESCRIPTIONS, SEGMENT_LABELS_ZH, SEGMENT_ORDER


def _quantile_score(values: pd.Series, higher_is_better: bool = True) -> pd.Series:
    """Rank-based 1–5 score, robust to tied values and small samples."""

    if values.empty:
        return pd.Series(dtype="int64", index=values.index)

    ranks = values.rank(method="first", ascending=True).to_numpy()
    scores = np.ceil(ranks / len(values) * 5).astype(int)
    scores = np.clip(scores, 1, 5)
    if not higher_is_better:
        scores = 6 - scores
    return pd.Series(scores, index=values.index, dtype="int64")


def score_rfm(customers: pd.DataFrame, snapshot: pd.Timestamp | None = None) -> pd.DataFrame:
    """Attach R/F/M scores and an exclusive lifecycle segment to each customer."""

    if customers.empty:
        return pd.DataFrame(
            columns=[
                "customer_id",
                "recency_days",
                "frequency",
                "monetary",
                "r_score",
                "f_score",
                "m_score",
                "rfm_score",
                "segment",
            ]
        )

    df = customers.copy()
    if snapshot is None:
        snapshot = pd.Timestamp(df["last_purchase"].max()).normalize() + pd.Timedelta(days=1)
    else:
        snapshot = pd.Timestamp(snapshot).normalize()

    df["recency_days"] = (snapshot - pd.to_datetime(df["last_purchase"])).dt.days.clip(lower=0)
    df["r_score"] = _quantile_score(df["recency_days"], higher_is_better=False)
    df["f_score"] = _quantile_score(df["frequency"], higher_is_better=True)
    df["m_score"] = _quantile_score(df["monetary"], higher_is_better=True)
    df["rfm_score"] = (
        df["r_score"].astype(str) + df["f_score"].astype(str) + df["m_score"].astype(str)
    )
    df["segment"] = assign_segments(df["r_score"], df["f_score"], df["m_score"])
    df["segment_label"] = df["segment"].map(SEGMENT_LABELS_ZH).fillna(df["segment"])
    df["snapshot_date"] = snapshot
    return df.sort_values(["monetary", "frequency"], ascending=False).reset_index(drop=True)


def assign_segments(r: pd.Series, f: pd.Series, m: pd.Series) -> pd.Series:
    """Exclusive rules, ordered so that high-value active customers win first."""

    conditions = [
        (r >= 4) & (f >= 4) & (m >= 4),
        (r >= 3) & (f >= 3),
        (r >= 4) & (f.isin([2, 3])),
        (r >= 4) & (f == 1),
        (r <= 2) & (f >= 3),
        (r <= 2) & (f == 2),
        (r <= 2) & (f == 1),
    ]
    choices = [
        "Champions",
        "Loyal",
        "Potential",
        "New",
        "At Risk",
        "Hibernating",
        "Lost",
    ]
    values = np.select(conditions, choices, default="Need Attention")
    return pd.Series(values, index=r.index, dtype="object")


def summarise_segments(scored: pd.DataFrame) -> pd.DataFrame:
    """One row per segment with customer and revenue contribution."""

    columns = [
        "segment",
        "segment_label",
        "customers",
        "customer_share",
        "revenue",
        "revenue_share",
        "avg_monetary",
        "avg_recency_days",
        "avg_frequency",
        "avg_order_value",
        "color",
        "description",
    ]
    if scored.empty:
        return pd.DataFrame(columns=columns)

    total_customers = len(scored)
    total_revenue = float(scored["monetary"].sum())
    grouped = (
        scored.groupby("segment", as_index=False)
        .agg(
            customers=("customer_id", "nunique"),
            revenue=("monetary", "sum"),
            avg_monetary=("monetary", "mean"),
            avg_recency_days=("recency_days", "mean"),
            avg_frequency=("frequency", "mean"),
            avg_order_value=("avg_order_value", "mean"),
        )
        .set_index("segment")
    )

    rows = []
    for segment in SEGMENT_ORDER:
        if segment in grouped.index:
            row = grouped.loc[segment]
            rows.append(
                {
                    "segment": segment,
                    "segment_label": SEGMENT_LABELS_ZH[segment],
                    "customers": int(row["customers"]),
                    "customer_share": float(row["customers"] / total_customers),
                    "revenue": float(row["revenue"]),
                    "revenue_share": float(row["revenue"] / total_revenue) if total_revenue else 0.0,
                    "avg_monetary": float(row["avg_monetary"]),
                    "avg_recency_days": float(row["avg_recency_days"]),
                    "avg_frequency": float(row["avg_frequency"]),
                    "avg_order_value": float(row["avg_order_value"]),
                    "color": SEGMENT_COLORS[segment],
                    "description": SEGMENT_DESCRIPTIONS[segment],
                }
            )
        else:
            rows.append(
                {
                    "segment": segment,
                    "segment_label": SEGMENT_LABELS_ZH[segment],
                    "customers": 0,
                    "customer_share": 0.0,
                    "revenue": 0.0,
                    "revenue_share": 0.0,
                    "avg_monetary": 0.0,
                    "avg_recency_days": 0.0,
                    "avg_frequency": 0.0,
                    "avg_order_value": 0.0,
                    "color": SEGMENT_COLORS[segment],
                    "description": SEGMENT_DESCRIPTIONS[segment],
                }
            )
    return pd.DataFrame(rows, columns=columns)


def high_value_at_risk(scored: pd.DataFrame) -> dict[str, Any]:
    """Customers who spend a lot but have not purchased recently."""

    if scored.empty:
        return {"customers": 0, "customer_share": 0.0, "revenue": 0.0, "revenue_share": 0.0}
    mask = (scored["r_score"] <= 2) & (scored["m_score"] >= 4)
    subset = scored.loc[mask]
    total_revenue = float(scored["monetary"].sum())
    return {
        "customers": int(subset["customer_id"].nunique()),
        "customer_share": float(len(subset) / len(scored)),
        "revenue": float(subset["monetary"].sum()),
        "revenue_share": float(subset["monetary"].sum() / total_revenue) if total_revenue else 0.0,
    }


def rfm_heatmap_data(scored: pd.DataFrame) -> pd.DataFrame:
    """Counts of R × F cells, useful for a compact diagnostic view."""

    if scored.empty:
        return pd.DataFrame(index=range(1, 6), columns=range(1, 6), data=0)
    table = pd.crosstab(scored["r_score"], scored["f_score"])
    return table.reindex(index=range(1, 6), columns=range(1, 6), fill_value=0)
