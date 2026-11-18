"""Data cleaning & validation pipeline.   data.csv  ->  cleaned_data.csv  (+ cleaning_report.json)

Run:  python data_cleaning.py
Steps: text hygiene -> type correction -> standardise categories -> duplicate removal ->
       fill categorical gaps -> drop invalid rows -> outlier detection (IQR) -> impute numeric gaps ->
       recompute revenue/profit -> derive columns -> validate.
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
RAW_PATH, CLEAN_PATH, REPORT_PATH = ROOT / "data.csv", ROOT / "cleaned_data.csv", ROOT / "cleaning_report.json"

CATEGORIES = ["Electronics", "Fashion", "Home & Kitchen", "Beauty & Personal Care", "Sports & Fitness",
              "Books & Stationery"]
PAYMENTS = ["UPI", "Credit Card", "Debit Card", "Net Banking", "Cash on Delivery", "Wallet"]
STATUSES = ["Delivered", "Shipped", "Cancelled", "Returned"]
CITY_STATE = {"Mumbai": "Maharashtra", "Pune": "Maharashtra", "Nagpur": "Maharashtra", "Delhi": "Delhi",
              "Bengaluru": "Karnataka", "Hyderabad": "Telangana", "Chennai": "Tamil Nadu",
              "Coimbatore": "Tamil Nadu", "Kolkata": "West Bengal", "Ahmedabad": "Gujarat", "Surat": "Gujarat",
              "Jaipur": "Rajasthan", "Lucknow": "Uttar Pradesh", "Chandigarh": "Chandigarh", "Kochi": "Kerala",
              "Indore": "Madhya Pradesh", "Bhopal": "Madhya Pradesh", "Visakhapatnam": "Andhra Pradesh"}
ALIASES = {  # keys are letters-only, lower-case (see key())
    "payment_method": {"cc": "Credit Card", "cod": "Cash on Delivery", "ewallet": "Wallet"},
    "order_status": {"canceled": "Cancelled", "return": "Returned"},
    "city": {"bangalore": "Bengaluru", "bombay": "Mumbai", "newdelhi": "Delhi", "calcutta": "Kolkata",
             "madras": "Chennai", "vizag": "Visakhapatnam"},
    "state": {"tamilnadu": "Tamil Nadu", "tn": "Tamil Nadu", "ka": "Karnataka", "up": "Uttar Pradesh",
              "wb": "West Bengal", "nctofdelhi": "Delhi", "mh": "Maharashtra"},
}
COLUMN_MAP = {"Order ID": "order_id", "Order Date": "order_date", "Customer ID": "customer_id",
              "Customer Name": "customer_name", "Product Name": "product_name", "Product Category": "category",
              "Quantity": "quantity", "Unit Price": "unit_price", "Total Sales": "total_sales",
              "Discount": "discount", "Profit": "profit", "Payment Method": "payment_method", "City": "city",
              "State": "state", "Order Status": "order_status"}
DATE_FORMATS = ["%Y-%m-%d", "%d-%m-%Y", "%b %d, %Y", "%d/%m/%Y"]
NULL_TOKENS = ["", "NA", "N/A", "n/a", "NaN", "nan", "null", "NULL", "None", "-"]
FINAL_COLUMNS = ["order_id", "order_date", "year", "month", "weekday", "customer_id", "customer_name",
                 "product_name", "category", "quantity", "unit_price", "discount", "gross_sales", "total_sales",
                 "profit", "payment_method", "city", "state", "order_status", "is_revenue_order"]


def key(value):
    """Normalise text for matching: lower-case letters only, '&' == 'and'."""
    return re.sub(r"[^a-z]", "", str(value).lower().replace("&", "and"))


def canon(series, canonical, aliases=None):
    """Map messy spellings onto canonical values; anything unknown becomes NaN."""
    lookup = {key(c): c for c in canonical}
    lookup.update(aliases or {})
    keys = series.map(lambda v: key(v) if pd.notna(v) else np.nan)
    return keys.map(lookup)


def parse_dates(series):
    out = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    for fmt in DATE_FORMATS:
        out = out.fillna(pd.to_datetime(series, format=fmt, errors="coerce"))
    return out


def to_number(series):
    return pd.to_numeric(series.astype(str).str.replace(r"[₹,%\s]|INR", "", regex=True), errors="coerce")


def mode_map(df, by, col):
    return df.dropna(subset=[col]).groupby(by)[col].agg(lambda s: s.mode().iat[0])


def iqr_outliers(values, groups, k, min_width):
    """Flag values outside [Q1 - k*IQR, Q3 + k*IQR] computed within each group (IQR floored at min_width)."""
    g = values.groupby(groups)
    q1, q3 = g.transform(lambda x: x.quantile(0.25)), g.transform(lambda x: x.quantile(0.75))
    iqr = np.maximum(q3 - q1, min_width)
    return values.notna() & ((values < q1 - k * iqr) | (values > q3 + k * iqr))


def clean(raw):
    log = {"raw_rows": int(len(raw))}
    df = raw.rename(columns=COLUMN_MAP).copy()

    # 1. Text hygiene: trim whitespace, collapse spaces, turn placeholder tokens into real NaN
    for c in df.columns:
        s = df[c].str.strip().str.replace(r"\s+", " ", regex=True)
        df[c] = s.where(~s.isin(NULL_TOKENS), np.nan)
    log["missing_before"] = {c: int(v) for c, v in df.isna().sum().items() if v > 0}
    log["distinct_labels_before"] = {c: int(df[c].nunique()) for c in
                                     ["category", "payment_method", "order_status", "city", "state"]}

    # 2. Correct data types
    d = df["order_date"]
    log["non_iso_dates_fixed"] = int((d.notna() & ~d.str.match(r"^\d{4}-\d{2}-\d{2}$", na=False)).sum())
    log["currency_text_prices_fixed"] = int(df["unit_price"].str.contains(r"[₹,A-Za-z]", na=False).sum())
    pct = df["discount"].str.contains("%", na=False)
    log["percent_text_discounts_fixed"] = int(pct.sum())
    df["order_date"] = parse_dates(d)
    log["unparseable_dates"] = int((d.notna() & df["order_date"].isna()).sum())
    for c in ["quantity", "unit_price", "total_sales", "profit"]:
        df[c] = to_number(df[c])
    disc = to_number(df["discount"])
    df["discount"] = disc.where(~pct, disc / 100)
    df["quantity"] = df["quantity"].round()

    # 3. Standardise identifiers and categorical labels
    df["order_id"], df["customer_id"] = df["order_id"].str.upper(), df["customer_id"].str.upper()
    df["customer_name"] = df["customer_name"].str.title()
    for col, allowed in [("category", CATEGORIES), ("payment_method", PAYMENTS), ("order_status", STATUSES),
                         ("city", list(CITY_STATE)), ("state", sorted(set(CITY_STATE.values())))]:
        df[col] = canon(df[col], allowed, ALIASES.get(col))
    log["distinct_labels_after"] = {c: int(df[c].nunique()) for c in log["distinct_labels_before"]}

    # 4. Remove duplicates (exact copies first, then repeated order IDs - keep the most complete row)
    n = len(df)
    df = df.drop_duplicates()
    log["exact_duplicates_removed"] = int(n - len(df))
    n = len(df)
    df = (df.assign(_nulls=df.isna().sum(axis=1)).sort_values(["order_id", "_nulls"])
            .drop_duplicates("order_id", keep="first").drop(columns="_nulls"))
    log["duplicate_order_ids_removed"] = int(n - len(df))

    # 5. Fill categorical gaps using other information in the data
    df["category"] = df["category"].fillna(df["product_name"].map(mode_map(df, "product_name", "category")))
    df["category"] = df["category"].fillna("Uncategorised")
    df["customer_name"] = df["customer_name"].fillna(df["customer_id"].map(mode_map(df, "customer_id", "customer_name")))
    df["city"] = df["city"].fillna(df["customer_id"].map(mode_map(df, "customer_id", "city")))
    df["state"] = df["city"].map(CITY_STATE).fillna(df["state"])        # state must agree with city
    unresolved = {"customer_name": "Unknown Customer", "city": "Unknown", "state": "Unknown",
                  "payment_method": "Unknown", "order_status": "Unknown"}
    log["unresolved_set_to_unknown"] = {c: int(df[c].isna().sum()) for c in unresolved}
    df = df.fillna({c: v for c, v in unresolved.items()})

    # 6. Data validation: drop rows that cannot be trusted
    today = pd.Timestamp.today().normalize()
    bad_date = df["order_date"].isna() | (df["order_date"] > today) | (df["order_date"] < pd.Timestamp("2000-01-01"))
    bad_prod = df["product_name"].isna()
    bad_qty = df["quantity"].notna() & (df["quantity"] <= 0)
    log["invalid_rows_dropped"] = {"missing_or_future_date": int(bad_date.sum()), "missing_product": int(bad_prod.sum()),
                                   "non_positive_quantity": int(bad_qty.sum())}
    df = df[~(bad_date | bad_prod | bad_qty)].copy()
    df["year"] = df["order_date"].dt.year

    # 7. Outlier detection (IQR, k=3) -> flag, blank out, then impute below
    df.loc[df["unit_price"] <= 0, "unit_price"] = np.nan
    price_out = iqr_outliers(df["unit_price"], df["product_name"], k=3, min_width=0.10 * df.groupby("product_name")["unit_price"].transform("median"))
    qty_out = iqr_outliers(df["quantity"], df["category"], k=3, min_width=1)
    disc_bad = df["discount"].notna() & ((df["discount"] < 0) | (df["discount"] > 0.9))
    log["outliers_detected"] = {"unit_price_iqr": int(price_out.sum()), "quantity_iqr": int(qty_out.sum()),
                                "invalid_discount": int(disc_bad.sum())}
    df.loc[price_out, "unit_price"], df.loc[qty_out, "quantity"], df.loc[disc_bad, "discount"] = np.nan, np.nan, np.nan

    # 8. Impute numeric gaps (missing + outliers) with robust group medians
    price_fixed, qty_fixed, disc_fixed = df["unit_price"].isna(), df["quantity"].isna(), df["discount"].isna()
    log["imputed"] = {"unit_price": int(price_fixed.sum()), "quantity": int(qty_fixed.sum()),
                      "discount": int(disc_fixed.sum())}
    df["unit_price"] = (df["unit_price"].fillna(df.groupby(["product_name", "year"])["unit_price"].transform("median"))
                        .fillna(df.groupby("product_name")["unit_price"].transform("median")))
    df["quantity"] = df["quantity"].fillna(df.groupby("category")["quantity"].transform("median")).fillna(1).round().clip(lower=1)
    df["discount"] = df["discount"].fillna(df.groupby("category")["discount"].transform("median")).fillna(0)

    # 9. Recalculate revenue and profit
    calc = (df["quantity"] * df["unit_price"] * (1 - df["discount"])).round(2)
    given = df["total_sales"]
    log["total_sales_recalculated"] = int((given.isna() | ((given - calc).abs() > 0.01 * calc.clip(lower=1))).sum())
    df["total_sales"] = calc
    needs_profit = df["profit"].isna() | price_fixed | qty_fixed | disc_fixed
    margin = (df["profit"] / df["total_sales"])[~needs_profit].groupby(df["category"]).median()
    estimate = (df["total_sales"] * df["category"].map(margin).fillna(margin.median())).round(2)
    df["profit"] = df["profit"].where(~needs_profit, estimate)
    log["profit_estimated"] = int(needs_profit.sum())

    # 10. Derived columns
    df["month"] = df["order_date"].dt.strftime("%Y-%m")
    df["weekday"] = df["order_date"].dt.day_name()
    df["quantity"] = df["quantity"].astype(int)
    df["gross_sales"] = (df["quantity"] * df["unit_price"]).round(2)
    df["is_revenue_order"] = df["order_status"].isin(["Delivered", "Shipped"]).astype(int)
    df = df.sort_values(["order_date", "order_id"]).reset_index(drop=True)
    df["order_date"] = df["order_date"].dt.strftime("%Y-%m-%d")
    return df[FINAL_COLUMNS], log


def validate(df):
    """Final data-quality gate. Raises AssertionError if any rule fails."""
    checks = {
        "order_id is unique": df["order_id"].is_unique,
        "no missing values": not df.isna().any().any(),
        "quantity > 0": bool((df["quantity"] > 0).all()),
        "unit_price > 0": bool((df["unit_price"] > 0).all()),
        "0 <= discount <= 0.9": bool(df["discount"].between(0, 0.9).all()),
        "total_sales = qty x price x (1 - discount)":
            bool(np.allclose(df["total_sales"], df["quantity"] * df["unit_price"] * (1 - df["discount"]), atol=0.02)),
        "no future dates": bool((pd.to_datetime(df["order_date"]) <= pd.Timestamp.today()).all()),
        "categories are standard": bool(df["category"].isin(CATEGORIES + ["Uncategorised"]).all()),
        "statuses are standard": bool(df["order_status"].isin(STATUSES + ["Unknown"]).all()),
    }
    failed = [k for k, ok in checks.items() if not ok]
    assert not failed, f"Validation failed: {failed}"
    return {k: True for k in checks}


def main():
    raw = pd.read_csv(RAW_PATH, dtype=str, encoding="utf-8-sig", keep_default_na=False, na_values=NULL_TOKENS)
    df, log = clean(raw)
    log["validation"] = validate(df)
    log["final_rows"] = int(len(df))
    df.to_csv(CLEAN_PATH, index=False, encoding="utf-8")
    REPORT_PATH.write_text(json.dumps(log, indent=2), encoding="utf-8")
    print(f"Cleaned {log['raw_rows']:,} raw rows -> {log['final_rows']:,} rows saved to {CLEAN_PATH.name}")
    print(json.dumps({k: v for k, v in log.items() if k not in ("validation",)}, indent=2))
    print("All validation checks passed.")


if __name__ == "__main__":
    main()
