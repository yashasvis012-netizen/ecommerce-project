"""Run every query in ./sql_queries against ecommerce.db, print results and save CSVs to ./sql_results.
Usage:  python run_queries.py            (all queries)
        python run_queries.py Q05        (only files whose name contains 'Q05')
"""
import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
DB_PATH, QUERY_DIR, OUT_DIR = ROOT / "ecommerce.db", ROOT / "sql_queries", ROOT / "sql_results"


def main(pattern=""):
    if not DB_PATH.exists():
        import build_database
        build_database.build()
    OUT_DIR.mkdir(exist_ok=True)
    pd.set_option("display.width", 220, "display.max_columns", 30)
    conn = sqlite3.connect(DB_PATH)
    files = [f for f in sorted(QUERY_DIR.glob("*.sql")) if pattern.lower() in f.name.lower()]
    for f in files:
        sql = f.read_text(encoding="utf-8")
        result = pd.read_sql_query(sql, conn)
        result.to_csv(OUT_DIR / f"{f.stem}.csv", index=False)
        title = sql.splitlines()[0].lstrip("- ").strip()
        print(f"\n{'=' * 100}\n{f.stem}: {title}\n{'=' * 100}")
        print(result.head(15).to_string(index=False))
    conn.close()
    print(f"\n{len(files)} queries executed. Results saved in {OUT_DIR.name}/")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
