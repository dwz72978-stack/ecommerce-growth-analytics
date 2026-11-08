"""Loading, validation, cleaning and aggregation of retail transactions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .config import CORE_SKU_PATTERN


class DataValidationError(ValueError):
    """Raised when the input file does not look like a retail transaction table."""


@dataclass(slots=True)
class DataBundle:
    """Cleaned tables shared by every analysis module."""

    raw: pd.DataFrame
    sales: pd.DataFrame
    cancellations: pd.DataFrame
    orders: pd.DataFrame
    customers: pd.DataFrame
    products: pd.DataFrame
    service_products: pd.DataFrame
    monthly: pd.DataFrame
    countries: pd.DataFrame
    rhythm: pd.DataFrame
    quality: dict[str, Any]
    snapshot: pd.Timestamp
    last_complete_month: pd.Period


_ALIASES = {
    "invoiceno": "invoice_no",
    "invoice": "invoice_no",
    "stockcode": "stock_code",
    "description": "description",
    "quantity": "quantity",
    "invoicedate": "invoice_date",
    "unitprice": "unit_price",
    "customerid": "customer_id",
    "country": "country",
}

_REQUIRED = ["invoice_no", "stock_code", "quantity", "invoice_date", "unit_price"]


def _normalise_column_name(name: object) -> str:
    key = re.sub(r"[^a-z0-9]", "", str(name).lower())
    return _ALIASES.get(key, key)


def standardise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Accept both the UCI original headers and this project's snake_case names."""

    renamed = df.rename(columns={c: _normalise_column_name(c) for c in df.columns})
    missing = [c for c in _REQUIRED if c not in renamed.columns]
    if missing:
        raise DataValidationError(
            "Missing required column(s): "
            + ", ".join(missing)
            + ". Expected InvoiceNo/StockCode/Quantity/InvoiceDate/UnitPrice "
            + "(or snake_case equivalents)."
        )
    if "customer_id" not in renamed.columns:
        renamed["customer_id"] = np.nan
    if "country" not in renamed.columns:
        renamed["country"] = "Unknown"
    if "description" not in renamed.columns:
        renamed["description"] = "UNKNOWN"
    return renamed


def load_transactions(path: str | Path) -> pd.DataFrame:
    """Read a CSV/CSV.GZ file and parse the transaction schema."""

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Input file not found: {path}. Run `python scripts/fetch_data.py` or "
            "use --sample to try the bundled sample."
        )

    read_kwargs: dict[str, Any] = {"low_memory": False}
    if path.suffix == ".gz":
        read_kwargs["compression"] = "gzip"

    header = pd.read_csv(path, nrows=0, **read_kwargs)
    normalised = [_normalise_column_name(c) for c in header.columns]
    dtype = {
        original: "string"
        for original, name in zip(header.columns, normalised)
        if name in {"invoice_no", "stock_code"}
    }
    if dtype:
        read_kwargs["dtype"] = dtype

    df = pd.read_csv(path, **read_kwargs)
    df = standardise_columns(df)

    df["invoice_no"] = df["invoice_no"].astype("string").str.strip()
    df["stock_code"] = df["stock_code"].astype("string").str.strip()
    df["description"] = (
        df["description"].astype("string").str.strip().fillna("UNKNOWN").replace("", "UNKNOWN")
    )
    df["country"] = df["country"].astype("string").str.strip().fillna("Unknown").replace("", "Unknown")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    df["customer_id"] = pd.to_numeric(df["customer_id"], errors="coerce").astype("Int64")
    df["invoice_date"] = pd.to_datetime(df["invoice_date"], errors="coerce", format="mixed")
    return df


def _empty_bundle(df: pd.DataFrame, quality: dict[str, Any]) -> DataBundle:
    """Return a usable, empty bundle (used by tests and tiny inputs)."""

    empty = df.iloc[0:0].copy()
    empty["revenue"] = pd.Series(dtype="float64")
    empty["invoice_month"] = pd.Series(dtype="string")
    empty["month_start"] = pd.Series(dtype="datetime64[ns]")
    empty["weekday_num"] = pd.Series(dtype="int64")
    empty["hour"] = pd.Series(dtype="int64")
    empty["is_guest"] = pd.Series(dtype="bool")
    empty["is_core_sku"] = pd.Series(dtype="bool")
    empty_orders = pd.DataFrame(
        columns=[
            "invoice_no",
            "customer_id",
            "country",
            "invoice_date",
            "revenue",
            "units",
            "lines",
            "products",
            "is_guest",
            "invoice_month",
        ]
    )
    empty_customers = pd.DataFrame(
        columns=[
            "customer_id",
            "first_purchase",
            "last_purchase",
            "frequency",
            "monetary",
            "units",
            "avg_order_value",
            "country",
            "recency_days",
            "tenure_days",
        ]
    )
    empty_products = pd.DataFrame(
        columns=["stock_code", "description", "revenue", "units", "orders", "avg_unit_price"]
    )
    empty_monthly = pd.DataFrame(
        columns=[
            "month_start",
            "invoice_month",
            "revenue",
            "orders",
            "customers",
            "units",
            "aov",
            "cancellation_value",
            "cancellation_rate",
            "is_partial",
            "mom",
        ]
    )
    snapshot = pd.Timestamp.today().normalize()
    return DataBundle(
        raw=empty,
        sales=empty,
        cancellations=empty,
        orders=empty_orders,
        customers=empty_customers,
        products=empty_products,
        service_products=empty_products.copy(),
        monthly=empty_monthly,
        countries=pd.DataFrame(columns=["country", "revenue", "orders", "customers", "share"]),
        rhythm=pd.DataFrame(columns=["weekday_num", "hour", "revenue", "orders"]),
        quality=quality,
        snapshot=snapshot,
        last_complete_month=snapshot.to_period("M") - 1,
    )


def prepare_data(df: pd.DataFrame) -> DataBundle:
    """Validate, de-duplicate, classify and aggregate the transaction table."""

    source_rows = len(df)
    df = standardise_columns(df)

    for col in ["invoice_no", "stock_code"]:
        df[col] = df[col].astype("string").str.strip()
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    df["customer_id"] = pd.to_numeric(df["customer_id"], errors="coerce").astype("Int64")
    df["invoice_date"] = pd.to_datetime(df["invoice_date"], errors="coerce", format="mixed")

    essential = ["invoice_no", "stock_code", "quantity", "invoice_date", "unit_price"]
    invalid_mask = df[essential].isna().any(axis=1) | (df["invoice_no"] == "") | (df["stock_code"] == "")
    invalid_rows = int(invalid_mask.sum())
    parsed = df.loc[~invalid_mask].copy()
    parsed["description"] = (
        parsed["description"].astype("string").str.strip().fillna("UNKNOWN").replace("", "UNKNOWN")
    )
    parsed["country"] = (
        parsed["country"].astype("string").str.strip().fillna("Unknown").replace("", "Unknown")
    )

    duplicate_rows = int(parsed.duplicated().sum())
    clean = parsed.drop_duplicates().copy().reset_index(drop=True)

    clean["invoice_no"] = clean["invoice_no"].astype("string")
    clean["stock_code"] = clean["stock_code"].astype("string").str.upper()
    clean["is_cancellation"] = clean["invoice_no"].str.upper().str.startswith("C", na=False)
    clean["revenue"] = clean["quantity"] * clean["unit_price"]
    clean["invoice_month"] = clean["invoice_date"].dt.strftime("%Y-%m")
    clean["month_start"] = clean["invoice_date"].dt.to_period("M").dt.to_timestamp()
    clean["weekday_num"] = clean["invoice_date"].dt.weekday.astype("int64")
    clean["hour"] = clean["invoice_date"].dt.hour.astype("int64")
    clean["is_guest"] = clean["customer_id"].isna()
    clean["is_core_sku"] = clean["stock_code"].str.match(CORE_SKU_PATTERN, na=False)

    sales_mask = (clean["quantity"] > 0) & (clean["unit_price"] > 0) & (~clean["is_cancellation"])
    sales = clean.loc[sales_mask].copy()
    cancellations = clean.loc[clean["is_cancellation"]].copy()
    cancellations["cancellation_value"] = (cancellations["quantity"] * cancellations["unit_price"]).abs()

    if sales.empty:
        quality = _quality_metrics(source_rows, parsed, duplicate_rows, invalid_rows, clean, sales, cancellations)
        return _empty_bundle(clean, quality)

    sales = sales.reset_index(drop=True)
    cancellations = cancellations.reset_index(drop=True)

    orders = build_orders(sales)
    max_date = sales["invoice_date"].max().normalize()
    snapshot = max_date + pd.Timedelta(days=1)
    customers = build_customers(sales, snapshot)
    products, service_products = build_products(sales)
    monthly = build_monthly(sales, cancellations)
    countries = build_countries(sales)
    rhythm = build_rhythm(sales)

    quality = _quality_metrics(source_rows, parsed, duplicate_rows, invalid_rows, clean, sales, cancellations)
    month_end = sales["month_start"].max() + pd.offsets.MonthEnd(0)
    last_complete_month = (
        sales["month_start"].max().to_period("M")
        if max_date >= month_end
        else (sales["month_start"].max().to_period("M") - 1)
    )

    return DataBundle(
        raw=clean,
        sales=sales,
        cancellations=cancellations,
        orders=orders,
        customers=customers,
        products=products,
        service_products=service_products,
        monthly=monthly,
        countries=countries,
        rhythm=rhythm,
        quality=quality,
        snapshot=snapshot,
        last_complete_month=last_complete_month,
    )


def build_orders(sales: pd.DataFrame) -> pd.DataFrame:
    orders = (
        sales.groupby("invoice_no", as_index=False)
        .agg(
            customer_id=("customer_id", "first"),
            country=("country", "first"),
            invoice_date=("invoice_date", "min"),
            revenue=("revenue", "sum"),
            units=("quantity", "sum"),
            lines=("stock_code", "size"),
            products=("stock_code", "nunique"),
            is_guest=("is_guest", "max"),
            invoice_month=("invoice_month", "first"),
        )
        .sort_values("invoice_date")
        .reset_index(drop=True)
    )
    return orders


def build_customers(sales: pd.DataFrame, snapshot: pd.Timestamp) -> pd.DataFrame:
    identified = sales.loc[~sales["is_guest"]].copy()
    if identified.empty:
        return pd.DataFrame()

    def _mode_country(values: pd.Series) -> str:
        modes = values.mode(dropna=True)
        return str(modes.iloc[0]) if not modes.empty else "Unknown"

    customers = (
        identified.groupby("customer_id", as_index=False)
        .agg(
            first_purchase=("invoice_date", "min"),
            last_purchase=("invoice_date", "max"),
            frequency=("invoice_no", "nunique"),
            monetary=("revenue", "sum"),
            units=("quantity", "sum"),
            country=("country", _mode_country),
        )
        .reset_index(drop=True)
    )
    customers["avg_order_value"] = customers["monetary"] / customers["frequency"].clip(lower=1)
    customers["recency_days"] = (snapshot - customers["last_purchase"]).dt.days.clip(lower=0)
    customers["tenure_days"] = (snapshot - customers["first_purchase"]).dt.days.clip(lower=0)
    customers["customer_id"] = customers["customer_id"].astype("Int64")
    return customers.sort_values("monetary", ascending=False).reset_index(drop=True)


def _description_lookup(core: pd.DataFrame) -> pd.DataFrame:
    counts = (
        core.groupby(["stock_code", "description"], as_index=False)
        .size()
        .sort_values(["stock_code", "size"], ascending=[True, False])
        .drop_duplicates("stock_code")
        .rename(columns={"size": "description_count"})
    )
    return counts[["stock_code", "description"]]


def build_products(sales: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return merchandise products and non-merchandise/service lines separately."""

    core = sales.loc[sales["is_core_sku"]].copy()
    if core.empty:
        empty = pd.DataFrame(
            columns=["stock_code", "description", "revenue", "units", "orders", "avg_unit_price"]
        )
        return empty, empty.copy()

    desc = _description_lookup(core)
    agg = (
        core.groupby("stock_code", as_index=False)
        .agg(
            revenue=("revenue", "sum"),
            units=("quantity", "sum"),
            orders=("invoice_no", "nunique"),
            first_sold=("invoice_date", "min"),
            last_sold=("invoice_date", "max"),
        )
        .merge(desc, on="stock_code", how="left")
    )
    agg["description"] = agg["description"].fillna("UNKNOWN")
    agg["avg_unit_price"] = agg["revenue"] / agg["units"].clip(lower=1)
    agg = agg.sort_values("revenue", ascending=False).reset_index(drop=True)
    agg["revenue_share"] = agg["revenue"] / agg["revenue"].sum()
    agg["cumulative_share"] = agg["revenue_share"].cumsum()
    agg["rank"] = np.arange(1, len(agg) + 1)
    agg["revenue_rank_pct"] = agg["rank"] / len(agg)
    agg = agg[
        [
            "rank",
            "stock_code",
            "description",
            "revenue",
            "units",
            "orders",
            "avg_unit_price",
            "revenue_share",
            "cumulative_share",
            "revenue_rank_pct",
            "first_sold",
            "last_sold",
        ]
    ]

    service = sales.loc[~sales["is_core_sku"]].copy()
    service_table = (
        service.groupby("stock_code", as_index=False)
        .agg(
            description=("description", "first"),
            revenue=("revenue", "sum"),
            units=("quantity", "sum"),
            orders=("invoice_no", "nunique"),
        )
        .sort_values("revenue", ascending=False)
        .reset_index(drop=True)
    )
    service_table["revenue_share"] = service_table["revenue"] / max(service_table["revenue"].sum(), 1)
    return agg, service_table


def build_monthly(sales: pd.DataFrame, cancellations: pd.DataFrame) -> pd.DataFrame:
    if sales.empty:
        return pd.DataFrame()

    sales_agg = (
        sales.groupby("month_start", as_index=False)
        .agg(
            revenue=("revenue", "sum"),
            orders=("invoice_no", "nunique"),
            customers=("customer_id", "nunique"),
            units=("quantity", "sum"),
        )
        .sort_values("month_start")
    )

    if cancellations.empty:
        cancel_agg = pd.DataFrame(columns=["month_start", "cancellation_value"])
    else:
        cancel_agg = (
            cancellations.groupby("month_start", as_index=False)["cancellation_value"]
            .sum()
            .sort_values("month_start")
        )

    start = sales["month_start"].min()
    end = sales["month_start"].max()
    months = pd.DataFrame({"month_start": pd.date_range(start, end, freq="MS")})
    monthly = months.merge(sales_agg, on="month_start", how="left").merge(
        cancel_agg, on="month_start", how="left"
    )
    for col in ["revenue", "orders", "customers", "units", "cancellation_value"]:
        monthly[col] = monthly[col].fillna(0)

    monthly["invoice_month"] = monthly["month_start"].dt.strftime("%Y-%m")
    monthly["aov"] = np.where(monthly["orders"] > 0, monthly["revenue"] / monthly["orders"], 0.0)
    monthly["cancellation_rate"] = np.where(
        monthly["revenue"] > 0, monthly["cancellation_value"] / monthly["revenue"], 0.0
    )
    last_date = sales["invoice_date"].max().normalize()
    monthly["is_partial"] = (monthly["month_start"] + pd.offsets.MonthEnd(0)) > last_date

    # Month-over-month growth is only defined between two complete months.
    valid_growth = (~monthly["is_partial"]) & (~monthly["is_partial"].shift(1, fill_value=False))
    monthly["mom"] = monthly["revenue"].pct_change().where(valid_growth)

    return monthly.reset_index(drop=True)


def build_countries(sales: pd.DataFrame) -> pd.DataFrame:
    countries = (
        sales.groupby("country", as_index=False)
        .agg(
            revenue=("revenue", "sum"),
            orders=("invoice_no", "nunique"),
            customers=("customer_id", "nunique"),
        )
        .sort_values("revenue", ascending=False)
        .reset_index(drop=True)
    )
    countries["share"] = countries["revenue"] / countries["revenue"].sum()
    return countries


def build_rhythm(sales: pd.DataFrame) -> pd.DataFrame:
    agg = (
        sales.groupby(["weekday_num", "hour"], as_index=False)
        .agg(revenue=("revenue", "sum"), orders=("invoice_no", "nunique"))
        .sort_values(["weekday_num", "hour"])
    )
    grid = pd.MultiIndex.from_product([range(7), range(24)], names=["weekday_num", "hour"]).to_frame(
        index=False
    )
    rhythm = grid.merge(agg, on=["weekday_num", "hour"], how="left").fillna({"revenue": 0, "orders": 0})
    return rhythm.sort_values(["weekday_num", "hour"]).reset_index(drop=True)


def _quality_metrics(
    source_rows: int,
    parsed: pd.DataFrame,
    duplicate_rows: int,
    invalid_rows: int,
    clean: pd.DataFrame,
    sales: pd.DataFrame,
    cancellations: pd.DataFrame,
) -> dict[str, Any]:
    total_rows = len(clean)
    revenue = float(sales["revenue"].sum()) if not sales.empty else 0.0
    cancel_value = (
        float(cancellations["cancellation_value"].sum()) if not cancellations.empty else 0.0
    )
    guest_revenue = float(sales.loc[sales["is_guest"], "revenue"].sum()) if not sales.empty else 0.0
    guest_orders = (
        int(sales.loc[sales["is_guest"], "invoice_no"].nunique()) if not sales.empty else 0
    )
    orders = int(sales["invoice_no"].nunique()) if not sales.empty else 0

    return {
        "source_rows": int(source_rows),
        "parsed_rows": int(len(parsed)),
        "invalid_rows": int(invalid_rows),
        "duplicate_rows": int(duplicate_rows),
        "clean_rows": int(total_rows),
        "sales_rows": int(len(sales)),
        "cancellation_rows": int(len(cancellations)),
        "cancellation_invoices": int(cancellations["invoice_no"].nunique())
        if not cancellations.empty
        else 0,
        "cancellation_value": cancel_value,
        "cancellation_rate": cancel_value / revenue if revenue else 0.0,
        "missing_customer_rows": int(clean["customer_id"].isna().sum()),
        "missing_customer_share": float(clean["customer_id"].isna().mean()) if total_rows else 0.0,
        "negative_quantity_rows": int((clean["quantity"] < 0).sum()),
        "zero_price_rows": int((clean["unit_price"] <= 0).sum()),
        "guest_revenue_share": guest_revenue / revenue if revenue else 0.0,
        "guest_order_share": guest_orders / orders if orders else 0.0,
        "countries": int(clean["country"].nunique()),
        "products": int(sales["stock_code"].nunique()) if not sales.empty else 0,
        "customers": int(sales["customer_id"].nunique()) if not sales.empty else 0,
        "date_min": sales["invoice_date"].min() if not sales.empty else pd.NaT,
        "date_max": sales["invoice_date"].max() if not sales.empty else pd.NaT,
    }
