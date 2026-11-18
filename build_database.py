"""Build ecommerce.db (SQLite) from cleaned_data.csv using database.sql.   Run: python build_database.py"""
import sqlite3
from pathlib import Path

import analysis as an

ROOT = Path(__file__).parent
DB_PATH = ROOT / "ecommerce.db"


def build(db_path=DB_PATH):
    df = an.load_clean()
    seg = an.rfm(df)
    seg["last_order"] = seg["last_order"].dt.strftime("%Y-%m-%d")
    df["order_date"] = df["order_date"].dt.strftime("%Y-%m-%d")
    if Path(db_path).exists():
        Path(db_path).unlink()
    conn = sqlite3.connect(db_path)
    conn.executescript((ROOT / "database.sql").read_text(encoding="utf-8"))
    cols = [r[1] for r in conn.execute("PRAGMA table_info(orders)")]
    df[cols].to_sql("orders", conn, if_exists="append", index=False)
    seg_cols = [r[1] for r in conn.execute("PRAGMA table_info(customer_segments)")]
    seg[seg_cols].to_sql("customer_segments", conn, if_exists="append", index=False)
    conn.commit()
    n_orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    n_cust = conn.execute("SELECT COUNT(*) FROM customer_segments").fetchone()[0]
    conn.close()
    print(f"{Path(db_path).name} built: {n_orders:,} orders, {n_cust:,} segmented customers")


if __name__ == "__main__":
    build()
