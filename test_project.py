"""Sanity tests: python test_project.py   (also works with `pytest`)."""
import sqlite3

import numpy as np
import pandas as pd

import analysis as an
import build_database
import data_cleaning as dc

DF = an.load_clean()
RAW = pd.read_csv(dc.RAW_PATH, dtype=str, encoding="utf-8-sig")


def test_raw_dataset_is_large_and_messy():
    assert len(RAW) >= 5000
    assert RAW.duplicated().sum() > 0 and RAW.isna().sum().sum() > 0


def test_cleaned_data_passes_validation():
    assert all(dc.validate(DF).values())
    assert DF["order_id"].is_unique and not DF.isna().any().any()


def test_financial_formulas():
    assert np.allclose(DF["gross_sales"], DF["quantity"] * DF["unit_price"], atol=0.01)
    assert np.allclose(DF["total_sales"], DF["gross_sales"] * (1 - DF["discount"]), atol=0.02)


def test_kpis_match_manual_calculation():
    valid = DF[DF["order_status"].isin(["Delivered", "Shipped"])]
    k = an.kpis(DF)
    assert abs(k["revenue"] - valid["total_sales"].sum()) < 0.01
    assert abs(k["profit"] - valid["profit"].sum()) < 0.01
    assert k["orders"] == valid["order_id"].nunique()
    assert abs(k["aov"] - valid["total_sales"].sum() / len(valid)) < 0.01


def test_group_tables_reconcile_with_total():
    total = an.kpis(DF)["revenue"]
    for table in (an.monthly_trend(DF), an.yearly_summary(DF), an.category_performance(DF)):
        assert abs(table["revenue"].sum() - total) < 0.5
    assert abs(an.category_performance(DF)["revenue_share_pct"].sum() - 100) < 1e-6


def test_rfm_segmentation():
    seg, r = an.rfm(DF), an.revenue_orders(DF)
    assert len(seg) == r["customer_id"].nunique()
    assert seg[["r_score", "f_score", "m_score"]].stack().between(1, 5).all()
    assert abs(seg["monetary"].sum() - r["total_sales"].sum()) < 0.5


def test_sql_results_match_pandas():
    build_database.build()
    conn = sqlite3.connect(build_database.DB_PATH)
    rev, orders = conn.execute("SELECT SUM(total_sales), COUNT(DISTINCT order_id) FROM revenue_orders").fetchone()
    k = an.kpis(DF)
    assert abs(rev - k["revenue"]) < 0.5 and orders == k["orders"]
    repeat = conn.execute("""SELECT SUM(n >= 2) FROM (SELECT COUNT(*) n FROM revenue_orders GROUP BY customer_id)""").fetchone()[0]
    per = an.revenue_orders(DF).groupby("customer_id")["order_id"].nunique()
    assert repeat == int((per >= 2).sum())
    conn.close()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS  {t.__name__}")
    print(f"\nAll {len(tests)} tests passed.")
