from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ecommerce_analytics.basket import mine_basket_rules  # noqa: E402
from ecommerce_analytics.cohort import build_cohorts  # noqa: E402
from ecommerce_analytics.data import prepare_data, standardise_columns  # noqa: E402
from ecommerce_analytics.metrics import compute_kpis, gini  # noqa: E402
from ecommerce_analytics.rfm import high_value_at_risk, score_rfm, summarise_segments  # noqa: E402


def sample_transactions() -> pd.DataFrame:
    rows = [
        # invoice, sku, desc, qty, date, price, customer, country
        ("1001", "12345", "MUG", 2, "2011-01-03 10:00", 10.0, 1, "United Kingdom"),
        ("1001", "12345", "MUG", 2, "2011-01-03 10:00", 10.0, 1, "United Kingdom"),  # duplicate
        ("1001", "23456", "TEA", 1, "2011-01-03 10:00", 5.0, 1, "United Kingdom"),
        ("1002", "23456", "TEA", 3, "2011-01-10 11:00", 20.0, 2, "France"),
        ("C1003", "34567", "BOWL", -1, "2011-01-12 09:00", 10.0, 2, "France"),
        ("1004", "45678", "PLATE", 1, "2011-02-02 12:00", 0.0, 3, "France"),
        ("1004", "45678", "PLATE", 2, "2011-02-02 12:00", 15.0, 3, "France"),
        ("1005", "56789", "CUP", 2, "2011-02-11 14:00", 30.0, 4, "Germany"),
        ("1006", "POST", "POSTAGE", 1, "2011-02-12 14:00", 10.0, None, "Germany"),
        ("1007", "78901", "SAUCER", 1, "2011-03-05 15:00", 50.0, 5, "France"),
        ("1008", "89012", "BAG", 5, "2011-03-06 16:00", 5.0, 6, "France"),
    ]
    df = pd.DataFrame(
        rows,
        columns=[
            "invoice_no",
            "stock_code",
            "description",
            "quantity",
            "invoice_date",
            "unit_price",
            "customer_id",
            "country",
        ],
    )
    return df


class DataTests(unittest.TestCase):
    def test_column_aliases(self) -> None:
        raw = pd.DataFrame(
            {
                "InvoiceNo": ["1"],
                "StockCode": ["12345"],
                "Description": ["MUG"],
                "Quantity": [1],
                "InvoiceDate": ["2011-01-01"],
                "UnitPrice": [2.0],
                "CustomerID": [1],
                "Country": ["UK"],
            }
        )
        standard = standardise_columns(raw)
        self.assertIn("invoice_no", standard.columns)
        self.assertIn("customer_id", standard.columns)

    def test_clean_and_classify(self) -> None:
        bundle = prepare_data(sample_transactions())
        q = bundle.quality
        self.assertEqual(q["source_rows"], 11)
        self.assertEqual(q["duplicate_rows"], 1)
        self.assertEqual(q["clean_rows"], 10)
        self.assertEqual(q["cancellation_rows"], 1)
        self.assertEqual(q["cancellation_invoices"], 1)
        self.assertEqual(q["zero_price_rows"], 1)
        self.assertEqual(q["missing_customer_rows"], 1)
        self.assertGreater(q["cancellation_value"], 0)
        self.assertAlmostEqual(bundle.sales["revenue"].sum(), 260.0)

    def test_core_sku_filter(self) -> None:
        bundle = prepare_data(sample_transactions())
        self.assertIn("56789", set(bundle.products["stock_code"]))
        self.assertNotIn("POST", set(bundle.products["stock_code"]))
        self.assertIn("POST", set(bundle.service_products["stock_code"]))

    def test_orders_and_customers(self) -> None:
        bundle = prepare_data(sample_transactions())
        self.assertEqual(len(bundle.orders), 7)
        self.assertEqual(len(bundle.customers), 6)
        self.assertAlmostEqual(float(bundle.orders["revenue"].sum()), 260.0)


class MetricsTests(unittest.TestCase):
    def test_gini(self) -> None:
        self.assertAlmostEqual(gini(pd.Series([1, 1, 1, 1])), 0.0, places=6)
        self.assertGreater(gini(pd.Series([0, 0, 0, 100])), 0.7)

    def test_kpis(self) -> None:
        bundle = prepare_data(sample_transactions())
        kpis = compute_kpis(bundle)
        self.assertAlmostEqual(kpis.values["total_revenue"], 260.0)
        self.assertEqual(kpis.values["total_orders"], 7)
        self.assertEqual(kpis.values["total_customers"], 6)
        self.assertAlmostEqual(kpis.values["aov"], 260.0 / 7)
        self.assertGreaterEqual(kpis.values["customer_gini"], 0.0)
        self.assertLessEqual(kpis.values["customer_gini"], 1.0)
        self.assertGreaterEqual(kpis.values["top10_customer_share"], 0.0)


class RFMTests(unittest.TestCase):
    def make_customers(self) -> pd.DataFrame:
        snapshot = pd.Timestamp("2011-04-01")
        rows = []
        # recent, frequent, high value
        rows.append((1, "2011-03-30", 12, 9000.0, 750.0, "United Kingdom"))
        # recent, one purchase, low value
        rows.append((2, "2011-03-28", 1, 40.0, 40.0, "France"))
        # old, frequent, high value
        rows.append((3, "2010-12-01", 10, 6000.0, 600.0, "France"))
        # old, one purchase, low value
        rows.append((4, "2010-11-01", 1, 20.0, 20.0, "Germany"))
        # recent, twice, medium
        rows.append((5, "2011-03-01", 2, 300.0, 150.0, "France"))
        # recent-ish, 4 purchases
        rows.append((6, "2011-02-01", 4, 1200.0, 300.0, "France"))
        df = pd.DataFrame(
            rows,
            columns=["customer_id", "last_purchase", "frequency", "monetary", "avg_order_value", "country"],
        )
        df["first_purchase"] = df["last_purchase"]
        df["units"] = df["frequency"]
        df["recency_days"] = (snapshot - pd.to_datetime(df["last_purchase"])).dt.days
        df["tenure_days"] = 120
        return df

    def test_scores_and_segments(self) -> None:
        scored = score_rfm(self.make_customers(), pd.Timestamp("2011-04-01"))
        self.assertTrue(scored["r_score"].between(1, 5).all())
        self.assertTrue(scored["f_score"].between(1, 5).all())
        self.assertTrue(scored["m_score"].between(1, 5).all())
        self.assertEqual(len(scored), 6)
        segments = set(scored["segment"])
        self.assertIn("Champions", segments)
        self.assertTrue(segments & {"Lost", "Hibernating", "At Risk"})
        summary = summarise_segments(scored)
        self.assertEqual(len(summary), 8)
        self.assertAlmostEqual(float(summary["customer_share"].sum()), 1.0, places=6)
        self.assertAlmostEqual(float(summary["revenue_share"].sum()), 1.0, places=6)

    def test_high_value_at_risk(self) -> None:
        scored = score_rfm(self.make_customers(), pd.Timestamp("2011-04-01"))
        hvar = high_value_at_risk(scored)
        self.assertGreaterEqual(hvar["customers"], 1)
        self.assertGreater(hvar["revenue"], 0)


class CohortTests(unittest.TestCase):
    def test_retention_matrix(self) -> None:
        rows = [
            ("INV0", 99, "2010-12-10", "2010-12"),
            ("INV3", 1, "2011-01-10", "2011-01"),
            ("INV4", 2, "2011-01-11", "2011-01"),
            ("INV5", 1, "2011-02-10", "2011-02"),
            ("INV6", 1, "2011-03-10", "2011-03"),
            ("INV7", 2, "2011-03-11", "2011-03"),
            ("INV8", 3, "2011-02-12", "2011-02"),
            ("INV9", 3, "2011-03-12", "2011-03"),
            ("INV10", 4, "2011-03-13", "2011-03"),
        ]
        sales = pd.DataFrame(rows, columns=["invoice_no", "customer_id", "invoice_date", "invoice_month"])
        sales["is_guest"] = False
        sales["invoice_date"] = pd.to_datetime(sales["invoice_date"])
        result = build_cohorts(sales, pd.Period("2011-03", "M"))
        self.assertEqual(result.summary["cohorts"], 3)
        self.assertAlmostEqual(float(result.rates.loc["2011-01", 1]), 0.5)
        self.assertAlmostEqual(float(result.rates.loc["2011-01", 2]), 1.0)
        self.assertAlmostEqual(float(result.rates.loc["2011-02", 1]), 1.0)
        self.assertTrue(pd.isna(result.rates.loc["2011-03", 1]))


class BasketTests(unittest.TestCase):
    def test_pair_rule(self) -> None:
        rows = []
        baskets = [
            ("1", ["11111", "22222"]),
            ("2", ["11111", "22222"]),
            ("3", ["11111", "33333"]),
            ("4", ["22222", "33333"]),
            ("5", ["11111", "22222", "33333"]),
        ]
        for invoice, skus in baskets:
            for sku in skus:
                rows.append((invoice, sku, 1, "2011-01-01", 1.0, 1, "UK", True))
        sales = pd.DataFrame(
            rows,
            columns=["invoice_no", "stock_code", "quantity", "invoice_date", "unit_price", "customer_id", "country", "is_core_sku"],
        )
        products = pd.DataFrame(
            {
                "stock_code": ["11111", "22222", "33333"],
                "description": ["ALPHA", "BETA", "GAMMA"],
            }
        )
        result = mine_basket_rules(
            sales,
            products,
            top_n=3,
            min_pair_orders=2,
            min_confidence=0.1,
            min_lift=0.5,
        )
        self.assertFalse(result.rules.empty)
        self.assertEqual(result.orders_considered, 5)
        self.assertTrue((result.rules["lift"] > 0).all())
        self.assertTrue(result.rules["confidence"].between(0, 1).all())


if __name__ == "__main__":
    unittest.main()
