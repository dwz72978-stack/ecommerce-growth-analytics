"""Monthly acquisition cohorts and retention curves."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


@dataclass(slots=True)
class CohortResult:
    sizes: pd.DataFrame = field(default_factory=pd.DataFrame)
    rates: pd.DataFrame = field(default_factory=pd.DataFrame)
    counts: pd.DataFrame = field(default_factory=pd.DataFrame)
    long: pd.DataFrame = field(default_factory=pd.DataFrame)
    summary: dict[str, Any] = field(default_factory=dict)


def build_cohorts(sales: pd.DataFrame, last_complete_month: pd.Period) -> CohortResult:
    """Build monthly retention for customers whose first observed month is not the first month.

    The first month in the dataset is left-censored: we cannot tell whether a
    customer acquired in Dec 2010 was actually new. Those customers are kept in
    revenue/RFM analyses but excluded from cohort rows.
    """

    identified = sales.loc[~sales["is_guest"]].copy()
    if identified.empty:
        return CohortResult()

    identified["month_start"] = pd.to_datetime(identified["invoice_month"] + "-01")
    first_month = identified["month_start"].min()
    last_month = last_complete_month.to_timestamp(how="start")

    first_purchase = (
        identified.groupby("customer_id", as_index=False)["month_start"].min().rename(
            columns={"month_start": "cohort_start"}
        )
    )
    eligible = first_purchase.loc[
        (first_purchase["cohort_start"] > first_month) & (first_purchase["cohort_start"] <= last_month)
    ]
    if eligible.empty:
        return CohortResult()

    activity = identified.merge(eligible, on="customer_id", how="inner")
    activity = activity.loc[activity["month_start"] <= last_month].copy()
    activity["cohort_month"] = activity["cohort_start"].dt.strftime("%Y-%m")
    activity["month"] = activity["month_start"].dt.strftime("%Y-%m")
    activity["index"] = (
        (activity["month_start"].dt.year - activity["cohort_start"].dt.year) * 12
        + (activity["month_start"].dt.month - activity["cohort_start"].dt.month)
    )

    sizes = (
        activity.groupby("cohort_month", as_index=False)["customer_id"]
        .nunique()
        .rename(columns={"customer_id": "cohort_size"})
        .sort_values("cohort_month")
    )
    active = (
        activity.groupby(["cohort_month", "index"], as_index=False)["customer_id"]
        .nunique()
        .rename(columns={"customer_id": "active_customers"})
    )

    max_index = int(active["index"].max())
    cohorts = list(sizes["cohort_month"])
    months = list(range(max_index + 1))
    counts = (
        active.pivot(index="cohort_month", columns="index", values="active_customers")
        .reindex(index=cohorts, columns=months)
        .fillna(0)
        .astype(int)
    )
    rates = counts.div(sizes.set_index("cohort_month")["cohort_size"], axis=0)

    # Mask cells that are not observable yet (future months after the data ends).
    observable_age = {
        row.cohort_month: (last_month.year - pd.Timestamp(row.cohort_month + "-01").year) * 12
        + (last_month.month - pd.Timestamp(row.cohort_month + "-01").month)
        for row in sizes.itertuples()
    }
    for cohort in rates.index:
        limit = observable_age.get(cohort, -1)
        rates.loc[cohort, [m for m in months if m > limit]] = np.nan
        counts.loc[cohort, [m for m in months if m > limit]] = 0

    long = (
        counts.stack(future_stack=True)
        .rename("active_customers")
        .reset_index()
        .merge(sizes, on="cohort_month", how="left")
    )
    long = long.loc[long["active_customers"] > 0].copy()
    long["retention_rate"] = long["active_customers"] / long["cohort_size"]

    # Pooled retention: all cohorts observed at age N, weighted by cohort size.
    total_by_age = []
    active_by_age = []
    for age in months:
        cohort_sizes = [
            int(sizes.loc[sizes["cohort_month"] == c, "cohort_size"].iloc[0])
            for c in cohorts
            if observable_age.get(c, -1) >= age
        ]
        active_count = int(counts.loc[counts.index.isin(
            [c for c in cohorts if observable_age.get(c, -1) >= age]
        ), age].sum())
        total_by_age.append(sum(cohort_sizes))
        active_by_age.append(active_count)
    pooled = np.divide(
        active_by_age,
        total_by_age,
        out=np.full(len(months), np.nan, dtype=float),
        where=np.array(total_by_age) > 0,
    )
    pooled_series = pd.Series(pooled, index=months, name="pooled_rate")

    def at_age(age: int) -> float | None:
        if age not in pooled_series.index or pd.isna(pooled_series.loc[age]):
            return None
        return float(pooled_series.loc[age])

    summary = {
        "cohorts": int(len(sizes)),
        "customers": int(sizes["cohort_size"].sum()),
        "first_cohort": str(sizes["cohort_month"].min()),
        "last_cohort": str(sizes["cohort_month"].max()),
        "m1": at_age(1),
        "m3": at_age(3),
        "m6": at_age(6),
        "m10": at_age(10),
        "m12": at_age(12),
        "pooled": pooled_series,
        "observable_age": observable_age,
        "last_complete_month": str(last_complete_month),
    }
    return CohortResult(sizes=sizes, rates=rates, counts=counts, long=long, summary=summary)
