"""Generate a realistic (and deliberately messy) e-commerce dataset -> data.csv

Run:  python generate_data.py
~6,000 genuine orders (Jan 2023 - Dec 2025) plus ~180 duplicate rows. Problems are injected on
purpose (missing values, mixed date/number formats, inconsistent spellings, outliers, invalid
values, duplicates) so that data_cleaning.py has real work to do. Currency: Indian Rupees.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
OUT_PATH = ROOT / "data.csv"
SEED, N_ORDERS, N_CUSTOMERS = 42, 6000, 2200
START, END = pd.Timestamp("2023-01-01"), pd.Timestamp("2025-12-31")

# category: (sales weight, cost ratio of list price, [(product, base price in INR)])
CATALOG = {
    "Electronics": (0.22, 0.82, [("Wireless Earbuds", 2499), ("Bluetooth Speaker", 3299), ("Smartwatch", 5999),
                                 ("Power Bank 20000mAh", 1799), ("Gaming Mouse", 1499), ("Smartphone", 18999),
                                 ("Laptop", 52999), ("Tablet", 22999)]),
    "Fashion": (0.24, 0.55, [("Men's Running Shoes", 2799), ("Women's Handbag", 1999), ("Denim Jacket", 2599),
                             ("Cotton T-Shirt", 699), ("Ethnic Kurta Set", 1899), ("Sunglasses", 1299),
                             ("Leather Wallet", 899)]),
    "Home & Kitchen": (0.18, 0.62, [("Air Fryer", 5499), ("Mixer Grinder", 3299), ("Non-Stick Cookware Set", 2499),
                                    ("Vacuum Cleaner", 7999), ("Bedsheet Set", 1599), ("Water Purifier", 12999),
                                    ("LED Desk Lamp", 899)]),
    "Beauty & Personal Care": (0.14, 0.50, [("Vitamin C Serum", 799), ("Hair Dryer", 1599), ("Electric Trimmer", 1499),
                                            ("Perfume 100ml", 1899), ("Sunscreen SPF 50", 499), ("Face Wash Combo", 399)]),
    "Sports & Fitness": (0.12, 0.60, [("Yoga Mat", 899), ("Dumbbell Set 20kg", 2999), ("Badminton Racket", 1899),
                                      ("Football", 799), ("Resistance Bands", 599), ("Fitness Tracker", 2499)]),
    "Books & Stationery": (0.10, 0.65, [("Data Analytics Handbook", 649), ("Python Programming Book", 549),
                                        ("Premium Notebook Set", 399), ("Gel Pen Pack", 249), ("Desk Organizer", 699),
                                        ("Bestseller Fiction Novel", 349)]),
}
CITIES = [("Mumbai", "Maharashtra", 14), ("Pune", "Maharashtra", 6), ("Nagpur", "Maharashtra", 2),
          ("Delhi", "Delhi", 13), ("Bengaluru", "Karnataka", 12), ("Hyderabad", "Telangana", 8),
          ("Chennai", "Tamil Nadu", 8), ("Coimbatore", "Tamil Nadu", 2), ("Kolkata", "West Bengal", 6),
          ("Ahmedabad", "Gujarat", 5), ("Surat", "Gujarat", 3), ("Jaipur", "Rajasthan", 4),
          ("Lucknow", "Uttar Pradesh", 4), ("Chandigarh", "Chandigarh", 2), ("Kochi", "Kerala", 3),
          ("Indore", "Madhya Pradesh", 3), ("Bhopal", "Madhya Pradesh", 2), ("Visakhapatnam", "Andhra Pradesh", 2)]
FIRST = ["Aarav", "Vivaan", "Aditya", "Arjun", "Rohan", "Karan", "Rahul", "Amit", "Vikram", "Siddharth", "Ankit",
         "Manish", "Nikhil", "Pranav", "Suresh", "Priya", "Ananya", "Diya", "Isha", "Kavya", "Neha", "Pooja",
         "Riya", "Sneha", "Shreya", "Meera", "Anjali", "Divya", "Swati", "Tanvi", "Nisha", "Aditi", "Rakesh",
         "Deepak", "Sanjay", "Varun", "Kriti", "Simran", "Lakshmi", "Harsh"]
LAST = ["Sharma", "Verma", "Gupta", "Singh", "Patel", "Reddy", "Nair", "Iyer", "Mehta", "Joshi", "Kapoor", "Malhotra",
        "Chopra", "Bose", "Das", "Khan", "Shah", "Desai", "Kulkarni", "Menon", "Pillai", "Rao", "Agarwal", "Bansal",
        "Chauhan", "Yadav", "Mishra", "Pandey", "Saxena", "Trivedi"]
PAYMENTS = ["UPI", "Credit Card", "Debit Card", "Net Banking", "Cash on Delivery", "Wallet"]
PAY_P = [0.34, 0.20, 0.16, 0.08, 0.17, 0.05]
DISCOUNTS = [0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
DISC_P = [0.30, 0.15, 0.20, 0.12, 0.10, 0.08, 0.05]
DISC_P_FESTIVE = [0.10, 0.10, 0.20, 0.20, 0.20, 0.12, 0.08]
MONTH_W = np.array([0.85, 0.80, 0.90, 0.90, 0.95, 0.90, 1.00, 1.05, 1.10, 1.45, 1.40, 1.30])  # festive Oct-Dec
YEAR_W = {2023: 0.70, 2024: 1.00, 2025: 1.35}  # business growth
COLUMNS = ["Order ID", "Order Date", "Customer ID", "Customer Name", "Product Name", "Product Category", "Quantity",
           "Unit Price", "Total Sales", "Discount", "Profit", "Payment Method", "City", "State", "Order Status"]


def build_clean_orders(rng):
    """Create ~6,000 internally consistent orders (no data problems yet)."""
    city_w = np.array([c[2] for c in CITIES], float)
    city_idx = rng.choice(len(CITIES), N_CUSTOMERS, p=city_w / city_w.sum())
    names = [f"{rng.choice(FIRST)} {rng.choice(LAST)}" for _ in range(N_CUSTOMERS)]
    weight = rng.gamma(0.5, 1.0, N_CUSTOMERS) + 0.02            # a few heavy buyers, many one-timers
    n_days = (END - START).days + 1
    join = (rng.beta(1, 1.6, N_CUSTOMERS) * (n_days - 30)).astype(int)
    join[:200] = 0                                               # customers that exist from day one

    days = pd.date_range(START, END)
    day_w = np.array([MONTH_W[d.month - 1] * YEAR_W[d.year] * (1.15 if d.dayofweek >= 5 else 1.0) for d in days])
    order_days = np.sort(rng.choice(n_days, N_ORDERS, p=day_w / day_w.sum()))

    cats = list(CATALOG)
    cat_p = np.array([CATALOG[c][0] for c in cats])
    prod_p = {c: (lambda w: w / w.sum())(rng.uniform(0.5, 1.5, len(CATALOG[c][2]))) for c in cats}
    rows = []
    for i, day in enumerate(order_days):
        date = START + pd.Timedelta(days=int(day))
        p = weight * (join <= day)
        c = rng.choice(N_CUSTOMERS, p=p / p.sum())
        cat = cats[rng.choice(len(cats), p=cat_p / cat_p.sum())]
        _, cost_ratio, products = CATALOG[cat]
        name, base = products[rng.choice(len(products), p=prod_p[cat])]
        infl = 1 + 0.04 * (date.year - 2023)
        price = float(round(base * infl * rng.uniform(0.95, 1.05)))
        if base > 15000:
            qty = 1
        elif cat == "Electronics":
            qty = int(rng.choice([1, 2, 3], p=[0.8, 0.15, 0.05]))
        else:
            qty = int(rng.choice([1, 2, 3, 4, 5], p=[0.5, 0.25, 0.12, 0.08, 0.05]))
        disc = float(rng.choice(DISCOUNTS, p=DISC_P_FESTIVE if date.month in (10, 11) else DISC_P))
        sales = round(price * qty * (1 - disc), 2)
        profit = round(sales - base * infl * cost_ratio * rng.uniform(0.97, 1.03) * qty, 2)
        pay = str(rng.choice(PAYMENTS, p=PAY_P))
        cancel_p = 0.14 if pay == "Cash on Delivery" else 0.06     # COD orders get cancelled more often
        u = rng.random()
        if u < cancel_p:
            status = "Cancelled"
        elif u < cancel_p + (0.12 if cat == "Fashion" else 0.06):  # fashion is returned more often
            status = "Returned"
        elif date >= pd.Timestamp("2025-12-17"):
            status = "Shipped" if rng.random() < 0.6 else "Delivered"
        else:
            status = "Delivered"
        city, state, _ = CITIES[city_idx[c]]
        rows.append([f"ORD-{100001 + i}", date, f"C{c + 1:04d}", names[c], name, cat, qty, price, sales, disc,
                     profit, pay, city, state, status])
    return pd.DataFrame(rows, columns=COLUMNS)


def make_messy(clean, rng):
    """Inject realistic data-quality problems and return the raw 'export'."""
    raw = clean.astype(object)
    dates = pd.to_datetime(clean["Order Date"]).copy()
    n = len(raw)

    def pick(frac):
        return rng.choice(n, max(1, int(n * frac)), replace=False)

    def vary_text(col, frac, variants=None):
        idx = pick(frac)
        vals = []
        for v in raw.loc[idx, col]:
            opts = list((variants or {}).get(v, [])) + [str(v).lower(), str(v).upper(), f" {v} "]
            vals.append(opts[rng.integers(len(opts))])
        raw.loc[idx, col] = vals

    # --- invalid values and outliers (numeric first, formatting later) ---
    idx = pick(0.004); raw.loc[idx, "Quantity"] = rng.integers(50, 201, len(idx))              # typo quantities
    idx = pick(0.002); raw.loc[idx, "Quantity"] = [-int(v) for v in raw.loc[idx, "Quantity"]]  # negative quantities
    idx = pick(0.0035); raw.loc[idx, "Unit Price"] = [float(v) * 10 for v in raw.loc[idx, "Unit Price"]]
    idx = pick(0.001); raw.loc[idx, "Unit Price"] = [-float(v) for v in raw.loc[idx, "Unit Price"]]
    idx = pick(0.002); raw.loc[idx, "Discount"] = rng.choice([0.95, -0.15], len(idx))
    idx = pick(0.01)
    raw.loc[idx, "Total Sales"] = [round(float(v) * f, 2) for v, f in
                                   zip(raw.loc[idx, "Total Sales"], rng.choice([1.1, 0.9, 1.25], len(idx)))]
    dates.iloc[pick(0.002)] = pd.Timestamp("2030-06-15")                                        # future dates

    # --- mixed formats / wrong data types ---
    fmts = ["%Y-%m-%d", "%d-%m-%Y", "%b %d, %Y", "%d/%m/%Y"]
    choice = rng.choice(4, n, p=[0.70, 0.15, 0.10, 0.05])
    raw["Order Date"] = [d.strftime(fmts[k]) for d, k in zip(dates, choice)]
    idx = pick(0.03); raw.loc[idx, "Unit Price"] = [f"₹{float(v):,.2f}" for v in raw.loc[idx, "Unit Price"]]
    idx = pick(0.04); raw.loc[idx, "Discount"] = [f"{round(float(v) * 100)}%" for v in raw.loc[idx, "Discount"]]
    idx = pick(0.02); raw.loc[idx, "Quantity"] = [f"{v} " for v in raw.loc[idx, "Quantity"]]
    idx = pick(0.015); raw.loc[idx, "Quantity"] = [f"{v}.0" for v in raw.loc[idx, "Quantity"]]

    # --- inconsistent spellings / casing / whitespace ---
    vary_text("Product Category", 0.08, {"Home & Kitchen": ["Home and Kitchen"],
                                         "Beauty & Personal Care": ["Beauty and Personal Care"],
                                         "Books & Stationery": ["Books and Stationery"]})
    vary_text("Payment Method", 0.10, {"UPI": ["Upi"], "Credit Card": ["credit_card", "CC"], "Net Banking": ["NetBanking"],
                                       "Cash on Delivery": ["COD", "Cash On Delivery"], "Wallet": ["E-Wallet"]})
    vary_text("Order Status", 0.08, {"Cancelled": ["Canceled"], "Returned": ["Return"]})
    vary_text("City", 0.10, {"Bengaluru": ["Bangalore"], "Mumbai": ["Bombay"], "Delhi": ["New Delhi"],
                             "Kolkata": ["Calcutta"], "Chennai": ["Madras"], "Visakhapatnam": ["Vizag"]})
    vary_text("State", 0.08, {"Tamil Nadu": ["Tamilnadu", "TN"], "Karnataka": ["KA"], "Uttar Pradesh": ["UP"],
                              "West Bengal": ["WB"], "Delhi": ["NCT of Delhi"], "Maharashtra": ["MH"]})
    vary_text("Customer Name", 0.06)
    idx = pick(0.03); raw.loc[idx, "Customer ID"] = [str(v).lower() for v in raw.loc[idx, "Customer ID"]]
    idx = pick(0.02); raw.loc[idx, "Product Name"] = [f" {v} " for v in raw.loc[idx, "Product Name"]]

    # --- missing values ---
    for col, frac in {"Customer Name": 0.025, "City": 0.02, "State": 0.015, "Payment Method": 0.02, "Discount": 0.03,
                      "Unit Price": 0.01, "Total Sales": 0.012, "Profit": 0.015, "Product Category": 0.01,
                      "Quantity": 0.005, "Order Date": 0.002}.items():
        raw.loc[pick(frac), col] = np.nan

    # --- duplicates: exact copies + near-copies with messy Order IDs ---
    dup = raw.iloc[rng.choice(n, 150, replace=False)]
    near = raw.iloc[rng.choice(n, 30, replace=False)].copy()
    near["Order ID"] = [f" {v.lower()} " for v in near["Order ID"]]
    return pd.concat([raw, dup, near], ignore_index=True).sample(frac=1, random_state=SEED).reset_index(drop=True)


def main():
    rng = np.random.default_rng(SEED)
    clean = build_clean_orders(rng)
    raw = make_messy(clean, rng)
    raw.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
    print(f"data.csv written: {len(raw):,} rows ({len(clean):,} real orders + {len(raw) - len(clean)} duplicates)")


if __name__ == "__main__":
    main()
