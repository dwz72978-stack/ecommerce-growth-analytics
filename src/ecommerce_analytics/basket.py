"""Market-basket analysis on the most frequently purchased merchandise."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass(slots=True)
class BasketResult:
    rules: pd.DataFrame = field(default_factory=pd.DataFrame)
    orders_considered: int = 0
    products_considered: int = 0
    pair_count: int = 0


def _short_name(value: object, limit: int = 34) -> str:
    text = str(value).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def mine_basket_rules(
    sales: pd.DataFrame,
    products: pd.DataFrame,
    top_n: int = 60,
    min_pair_orders: int = 25,
    min_confidence: float = 0.10,
    min_lift: float = 1.20,
    limit: int = 8,
) -> BasketResult:
    """Mine directional association rules among the top-N merchandise SKUs.

    The basket universe is invoices containing at least two *distinct* core
    merchandise SKUs. Support is therefore relative to multi-line merchandise
    baskets, not to all invoices.
    """

    core = sales.loc[sales["is_core_sku"]]
    if core.empty:
        return BasketResult()

    counts = core.groupby("stock_code")["invoice_no"].nunique().sort_values(ascending=False)
    top_skus = list(counts.head(top_n).index)
    if len(top_skus) < 2:
        return BasketResult()

    subset = core.loc[core["stock_code"].isin(top_skus), ["invoice_no", "stock_code"]].drop_duplicates()
    basket = (pd.crosstab(subset["invoice_no"], subset["stock_code"]) > 0).astype(np.int32)
    basket = basket.loc[basket.sum(axis=1) >= 2]
    if len(basket) < 2:
        return BasketResult()

    matrix = basket.to_numpy(dtype=np.int32)
    co = matrix.T @ matrix
    n_orders = int(matrix.shape[0])
    item_orders = np.diag(co).astype(float)

    names = (
        products.set_index("stock_code")["description"].to_dict()
        if not products.empty
        else {}
    )

    rows: list[dict[str, object]] = []
    for i in range(len(top_skus)):
        for j in range(i + 1, len(top_skus)):
            pair_orders = int(co[i, j])
            if pair_orders < min_pair_orders:
                continue

            support = pair_orders / n_orders
            conf_ij = pair_orders / item_orders[i] if item_orders[i] else 0.0
            conf_ji = pair_orders / item_orders[j] if item_orders[j] else 0.0
            lift = pair_orders * n_orders / (item_orders[i] * item_orders[j])

            if conf_ij >= conf_ji:
                antecedent, consequent, confidence = top_skus[i], top_skus[j], conf_ij
            else:
                antecedent, consequent, confidence = top_skus[j], top_skus[i], conf_ji

            if confidence < min_confidence or lift < min_lift:
                continue

            rows.append(
                {
                    "antecedent_code": antecedent,
                    "consequent_code": consequent,
                    "antecedent": _short_name(names.get(antecedent, antecedent)),
                    "consequent": _short_name(names.get(consequent, consequent)),
                    "pair_orders": pair_orders,
                    "support": float(support),
                    "confidence": float(confidence),
                    "lift": float(lift),
                }
            )

    rules = pd.DataFrame(rows)
    if rules.empty:
        return BasketResult(orders_considered=n_orders, products_considered=len(top_skus))
    rules = (
        rules.sort_values(["lift", "pair_orders", "confidence"], ascending=False)
        .head(limit)
        .reset_index(drop=True)
    )
    return BasketResult(
        rules=rules,
        orders_considered=n_orders,
        products_considered=len(top_skus),
        pair_count=len(rows),
    )
