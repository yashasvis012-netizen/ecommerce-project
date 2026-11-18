"""Business analysis functions (used by the dashboard, the SQL loader and the tests).

Run:  python analysis.py      -> prints key insights and exports result tables to ./outputs
Definition: "revenue orders" = orders with status Delivered or Shipped (Cancelled/Returned excluded).
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
CLEAN_PATH = ROOT / "cleaned_data.csv"
OUT_DIR = ROOT / "outputs"


def load_clean(path=CLEAN_PATH):
    return pd.read_csv(path, parse_dates=["order_date"])


def revenue_orders(df):
    return df[df["is_revenue_order"] == 1]


def kpis(df):
    """Headline KPIs for any (filtered) slice of orders."""
    r = revenue_orders(df)
    orders, revenue, profit = r["order_id"].nunique(), r["total_sales"].sum(), r["profit"].sum()
    per_customer = r.groupby("customer_id")["order_id"].nunique()
    return {
        "revenue": float(revenue), "profit": float(profit), "orders": int(orders),
        "customers": int(r["customer_id"].nunique()), "units": int(r["quantity"].sum()),
        "aov": float(revenue / orders) if orders else 0.0,
        "margin_pct": float(100 * profit / revenue) if revenue else 0.0,
        "repeat_rate_pct": float(100 * (per_customer >= 2).mean()) if len(per_customer) else 0.0,
        "cancel_rate_pct": float(100 * (df["order_status"] == "Cancelled").mean()) if len(df) else 0.0,
        "return_rate_pct": float(100 * (df["order_status"] == "Returned").mean()) if len(df) else 0.0,
    }


def monthly_trend(df):
    r = revenue_orders(df)
    g = r.groupby("month").agg(revenue=("total_sales", "sum"), profit=("profit", "sum"),
                               orders=("order_id", "nunique"), customers=("customer_id", "nunique")).reset_index()
    g["mom_growth_pct"] = g["revenue"].pct_change() * 100
    g["revenue_ma3"] = g["revenue"].rolling(3, min_periods=1).mean()
    return g


def yearly_summary(df):
    r = revenue_orders(df)
    g = r.groupby("year").agg(revenue=("total_sales", "sum"), profit=("profit", "sum"),
                              orders=("order_id", "nunique"), customers=("customer_id", "nunique")).reset_index()
    g["yoy_growth_pct"] = g["revenue"].pct_change() * 100
    g["aov"] = g["revenue"] / g["orders"]
    return g


def category_performance(df):
    r = revenue_orders(df)
    g = r.groupby("category").agg(revenue=("total_sales", "sum"), profit=("profit", "sum"),
                                  orders=("order_id", "nunique"), units=("quantity", "sum")).reset_index()
    g["margin_pct"] = 100 * g["profit"] / g["revenue"]
    g["aov"] = g["revenue"] / g["orders"]
    g["revenue_share_pct"] = 100 * g["revenue"] / g["revenue"].sum()
    return g.sort_values("revenue", ascending=False).reset_index(drop=True)


def product_performance(df):
    r = revenue_orders(df)
    g = r.groupby(["product_name", "category"]).agg(revenue=("total_sales", "sum"), profit=("profit", "sum"),
                                                    units=("quantity", "sum"), orders=("order_id", "nunique")).reset_index()
    g["margin_pct"] = 100 * g["profit"] / g["revenue"]
    return g


def top_products(df, n=10, by="revenue"):
    return product_performance(df).sort_values(by, ascending=False).head(n).reset_index(drop=True)


def regional(df, level="state", exclude_unknown=True):
    r = revenue_orders(df)
    if exclude_unknown:
        r = r[r[level] != "Unknown"]
    keys = ["state", "city"] if level == "city" else ["state"]
    g = r.groupby(keys).agg(revenue=("total_sales", "sum"), profit=("profit", "sum"),
                            orders=("order_id", "nunique"), customers=("customer_id", "nunique")).reset_index()
    g["aov"] = g["revenue"] / g["orders"]
    g["revenue_share_pct"] = 100 * g["revenue"] / g["revenue"].sum()
    return g.sort_values("revenue", ascending=False).reset_index(drop=True)


def payment_analysis(df):
    g = df.groupby("payment_method").agg(orders=("order_id", "nunique"),
                                         cancel_rate_pct=("order_status", lambda s: 100 * (s == "Cancelled").mean()),
                                         return_rate_pct=("order_status", lambda s: 100 * (s == "Returned").mean())).reset_index()
    g["share_pct"] = 100 * g["orders"] / g["orders"].sum()
    return g.sort_values("orders", ascending=False).reset_index(drop=True)


def status_analysis(df):
    g = df.groupby("order_status").agg(orders=("order_id", "nunique"), order_value=("total_sales", "sum")).reset_index()
    g["share_pct"] = 100 * g["orders"] / g["orders"].sum()
    return g.sort_values("orders", ascending=False).reset_index(drop=True)


def rfm(df):
    """RFM customer segmentation on revenue orders. Returns empty frame if fewer than 5 customers."""
    r = revenue_orders(df)
    if r["customer_id"].nunique() < 5:
        return pd.DataFrame()
    ref = r["order_date"].max() + pd.Timedelta(days=1)
    g = r.groupby("customer_id").agg(customer_name=("customer_name", "first"), last_order=("order_date", "max"),
                                     frequency=("order_id", "nunique"), monetary=("total_sales", "sum")).reset_index()
    g["recency_days"] = (ref - g["last_order"]).dt.days
    g["avg_order_value"] = g["monetary"] / g["frequency"]
    labels = [1, 2, 3, 4, 5]
    g["r_score"] = pd.qcut(g["recency_days"].rank(method="first", ascending=False), 5, labels=labels).astype(int)
    g["f_score"] = pd.qcut(g["frequency"].rank(method="first"), 5, labels=labels).astype(int)
    g["m_score"] = pd.qcut(g["monetary"].rank(method="first"), 5, labels=labels).astype(int)
    g["rfm_total"] = g["r_score"] + g["f_score"] + g["m_score"]

    def segment(row):
        r_, f_ = row["r_score"], row["f_score"]
        if r_ >= 4 and f_ >= 4:
            return "Champions"
        if f_ >= 4 and r_ >= 3:
            return "Loyal Customers"
        if f_ >= 4:
            return "Cannot Lose Them"
        if r_ >= 4:
            return "Potential Loyalists"
        if r_ == 3:
            return "Needs Attention"
        if r_ == 2:
            return "At Risk"
        return "Hibernating"

    g["segment"] = g.apply(segment, axis=1)
    return g


def segment_summary(seg):
    g = seg.groupby("segment").agg(customers=("customer_id", "nunique"), revenue=("monetary", "sum"),
                                   avg_orders=("frequency", "mean"), avg_recency_days=("recency_days", "mean")).reset_index()
    g["revenue_share_pct"] = 100 * g["revenue"] / g["revenue"].sum()
    g["customer_share_pct"] = 100 * g["customers"] / g["customers"].sum()
    return g.sort_values("revenue", ascending=False).reset_index(drop=True)


def customer_behaviour(df):
    r = revenue_orders(df)
    per = r.groupby("customer_id").agg(orders=("order_id", "nunique"), revenue=("total_sales", "sum"))
    if per.empty:
        return {"repeat_rate_pct": 0.0, "avg_orders_per_customer": 0.0, "avg_days_between_orders": 0.0,
                "avg_customer_value": 0.0, "top20_revenue_share_pct": 0.0, "orders_per_customer": per["orders"]}
    gaps = r.sort_values("order_date").groupby("customer_id")["order_date"].diff().dt.days.dropna()
    top = per["revenue"].sort_values(ascending=False)
    k = max(1, int(np.ceil(len(top) * 0.2)))
    return {"repeat_rate_pct": float(100 * (per["orders"] >= 2).mean()),
            "avg_orders_per_customer": float(per["orders"].mean()),
            "avg_days_between_orders": float(gaps.mean()) if len(gaps) else 0.0,
            "avg_customer_value": float(per["revenue"].mean()),
            "top20_revenue_share_pct": float(100 * top.head(k).sum() / top.sum()),
            "orders_per_customer": per["orders"]}


def new_vs_returning(df):
    """New = customer's first order month inside the selected data; Returning = any later month."""
    r = revenue_orders(df).copy()
    r["customer_type"] = np.where(r["month"] == r.groupby("customer_id")["month"].transform("min"), "New", "Returning")
    return r.groupby(["month", "customer_type"]).agg(customers=("customer_id", "nunique"),
                                                      revenue=("total_sales", "sum")).reset_index()


def main():
    df = load_clean()
    k = kpis(df)
    print("=== KPIs (Delivered + Shipped orders) ===")
    for name, v in k.items():
        print(f"{name:>18}: {v:,.2f}")
    tables = {"monthly_trend": monthly_trend(df), "yearly_summary": yearly_summary(df),
              "category_performance": category_performance(df), "top_products_revenue": top_products(df, 10),
              "top_products_profit": top_products(df, 10, "profit"), "state_performance": regional(df, "state"),
              "city_performance": regional(df, "city"), "payment_analysis": payment_analysis(df),
              "status_analysis": status_analysis(df), "customer_segments": rfm(df),
              "segment_summary": segment_summary(rfm(df)), "new_vs_returning": new_vs_returning(df)}
    OUT_DIR.mkdir(exist_ok=True)
    for name, t in tables.items():
        t.to_csv(OUT_DIR / f"{name}.csv", index=False)
    pd.set_option("display.width", 200, "display.max_columns", 20, "display.float_format", "{:,.2f}".format)
    for name in ["yearly_summary", "category_performance", "top_products_revenue", "state_performance",
                 "payment_analysis", "status_analysis", "segment_summary"]:
        print(f"\n=== {name} ===")
        print(tables[name].head(10).to_string(index=False))
    b = customer_behaviour(df)
    print("\n=== Customer behaviour ===")
    for name, v in b.items():
        if name != "orders_per_customer":
            print(f"{name:>26}: {v:,.2f}")
    print(f"\nExported {len(tables)} tables to {OUT_DIR}")


if __name__ == "__main__":
    main()
