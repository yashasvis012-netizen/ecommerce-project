# E-Commerce Sales & Customer Insights Analytics Dashboard

An end-to-end data analytics project: a messy 6,180-row e-commerce export is cleaned and validated with
**Python (Pandas, NumPy)**, analysed with **SQL (SQLite)**, and presented in an interactive
**Streamlit + Plotly** business-intelligence dashboard. Everything runs locally with free tools.

## Business problem
An online retailer selling electronics, fashion, home, beauty, sports and books across 13 Indian states has raw order
exports full of duplicates, missing values and inconsistent formats. Management cannot trust the numbers, and cannot
answer basic questions: *What drives revenue and profit? Where are we strongest? Which customers matter most?
Where are we losing money?*

## Objectives
1. Clean and validate the raw data so every KPI is trustworthy.
2. Measure revenue, profit, order value and growth over time (monthly and yearly).
3. Find the best and worst categories, products and regions.
4. Segment customers (RFM) and measure repeat purchase and retention.
5. Deliver an interactive dashboard with date, category and location filters.
6. Answer 19 business questions in SQL.

## Technologies
Python 3.10+ | Pandas | NumPy | SQLite / SQL (window functions, CTEs) | Streamlit | Plotly | Custom CSS

## Project structure
```
ecommerce-analytics/
├── app.py                 Streamlit dashboard
├── generate_data.py       Creates the messy dataset (data.csv)
├── data.csv               RAW dataset: 6,180 rows, 15 columns
├── data_cleaning.py       Cleaning + validation pipeline -> cleaned_data.csv, cleaning_report.json
├── cleaned_data.csv       Clean dataset: 5,964 rows (used by dashboard and database)
├── analysis.py            KPI, trend, category, regional, RFM and behaviour functions (exports to outputs/)
├── database.sql           SQLite schema: tables, indexes, view
├── build_database.py      Loads cleaned data into ecommerce.db
├── sql_queries/           19 business-question queries (Q01 ... Q19)
├── run_queries.py         Runs every query, saves results to sql_results/
├── test_project.py        7 tests (cleaning rules, formulas, pandas vs SQL reconciliation)
├── requirements.txt, run_all.bat, run_dashboard.bat, .streamlit/config.toml
└── screenshots/           Add your dashboard screenshots here
```

## Dataset description
`data.csv` is synthetic but modelled on real retail behaviour: 3 years (Jan 2023 - Dec 2025), 40 products in 6 categories,
18 cities in 13 states, ~2,200 customers with heavy-tailed buying behaviour, festive-season peaks (Oct-Dec),
year-on-year growth, higher cancellation on Cash on Delivery, higher returns in Fashion, and discount-driven margin loss.

| Column | Description |
|---|---|
| Order ID, Order Date | Unique order key and date |
| Customer ID, Customer Name | Customer identity |
| Product Name, Product Category | 40 products, 6 categories |
| Quantity, Unit Price | Units and list price (INR) |
| Discount | Fraction off list price (0 - 0.30 in valid data) |
| Total Sales | Quantity x Unit Price x (1 - Discount) |
| Profit | Total Sales minus product cost |
| Payment Method, City, State | Payment and delivery location |
| Order Status | Delivered, Shipped, Cancelled, Returned |

**Metric definitions:** revenue and profit count only *Delivered* and *Shipped* orders. Cancelled and Returned orders are
excluded from revenue but analysed separately. AOV = revenue / orders.

## Data cleaning methodology
Implemented in `data_cleaning.py`; each step is logged in `cleaning_report.json` and shown on the dashboard's *Data quality* tab.

| Step | Problem found | Fix |
|---|---|---|
| Text hygiene | Extra spaces, "N/A"/"-" placeholders | Trim, collapse spaces, convert to real nulls |
| Data types | 1,827 dates in 4 formats; 181 prices like "₹1,299.00"; 237 discounts like "10%"; quantities like "3.0 " | Multi-format date parser, numeric conversion, percent to fraction |
| Standardisation | Category 21 spellings -> 6; payment 24 -> 6; status 14 -> 4; city 59 -> 18; state 45 -> 13 | Normalised matching + alias tables (Bangalore -> Bengaluru, COD -> Cash on Delivery ...) |
| Duplicates | 180 duplicate rows (30 hidden by ID casing/spacing) | Normalise IDs, then drop duplicates keeping the most complete row |
| Missing values | Names, city, state, category, payment, price, quantity, discount, profit | Customer/product look-ups first (name, city, category); state derived from city; numbers by product/category medians; unresolved text -> "Unknown" |
| Invalid rows | 24 missing/future dates, 12 negative quantities | Removed |
| Outliers | 21 prices (10x), 24 quantities (50-200), 10 impossible discounts | IQR rule (k = 3) per product / category, replaced with group medians |
| Financial integrity | 389 Total Sales values missing or inconsistent | Recomputed as Quantity x Price x (1 - Discount); 405 profits re-estimated from category margin |
| Validation | - | 9 automated rules (unique IDs, no nulls, valid ranges, formula check, standard labels) must all pass |

Result: **6,180 raw rows -> 5,964 clean rows, zero missing values.**

## Key findings
(Delivered + Shipped orders, Jan 2023 - Dec 2025)

* **Scale:** ₹3.16 Cr revenue, ₹64.6 L profit (20.5% margin), 5,093 orders, 1,278 customers, ₹6,196 average order value.
* **Growth:** revenue grew 40.1% in 2024 and 51.1% in 2025. Oct-Dec months run about 30% above an average month.
* **Electronics is a revenue trap:** 49.8% of revenue but only 8.0% margin, and margin fell from 9.6% (2023) to 6.8% (2025).
  Home & Kitchen (29.7% margin) earns more than twice Electronics' profit on 57% of its sales. Beauty has the best margin (44.2%).
* **Discounts destroy margin:** orders with 21-30% discounts earn a 5.2% margin vs 28.2% with no discount, with no lift in units per order.
* **Geography:** Maharashtra brings 27.5% of revenue; Mumbai (₹55.1 L), Bengaluru and Delhi are the top cities.
* **Cash on Delivery** orders are cancelled at 13.1% vs about 6% for prepaid methods; roughly 15% of orders are cancelled or returned.
* **Customers:** 66.9% buy more than once. 23% of customers (Champions) deliver 51% of revenue. Year-over-year retention is 68% (2024) and 71% (2025).
  105 "Cannot Lose Them" customers (11% of revenue) have gone quiet for about a year: a ready-made win-back list.

**Recommendations:** shift marketing to higher-margin categories, cap discounts at 15-20%, nudge COD buyers toward UPI,
run a win-back campaign for high-value lapsed customers, and stock up for Oct-Dec.

## How to install and run (Windows)
1. Install **Python 3.10 or newer** from python.org. Tick **"Add Python to PATH"** during setup.
2. Unzip the project and open **Command Prompt** in the folder (type `cmd` in the folder's address bar).
3. **Quick start:** run `run_all.bat`. It creates a virtual environment, installs packages, rebuilds data, database and
   SQL results, runs the tests, and opens the dashboard at http://localhost:8501.

Manual steps:
```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python generate_data.py
python data_cleaning.py
python analysis.py
python build_database.py
python run_queries.py
python test_project.py
streamlit run app.py
```
Next time, just run `run_dashboard.bat`. The generated files are already included, and if `cleaned_data.csv` is missing
the dashboard rebuilds it automatically. Run a single query with `python run_queries.py Q05`.
To explore SQL visually, open `ecommerce.db` in the free **DB Browser for SQLite**.

**Troubleshooting:** "python is not recognized" means Python is not on PATH (reinstall and tick the box).
Use `py -m venv venv` if `python` fails. If port 8501 is busy: `streamlit run app.py --server.port 8502`.

## SQL business questions (`sql_queries/`)
Q01 top 10 products | Q02 revenue and margin by category | Q03 monthly growth (LAG) | Q04 yearly growth |
Q05 repeat customers | Q06 average order value | Q07 most profitable products | Q08 state performance |
Q09 top cities | Q10 yearly retention | Q11 payment method and cancellations | Q12 order status |
Q13 top customers | Q14 discount impact | Q15 weekday pattern | Q16 RFM segments | Q17 margin by year |
Q18 seasonality index | Q19 cohort retention

## Dashboard features
* Sidebar filters: date range, category, state, city (all combine)
* KPI cards with change vs the previous period: revenue, orders, customers, profit, AOV, margin, repeat rate, cancellations, returns
* Tabs: Overview (monthly trend, category, payments, status), Products (top 10, treemap, margins), Geography (state, city, treemap),
  Customers (RFM segments, behaviour, new vs returning), Data quality (cleaning report, data table, CSV download)

## Screenshots
Run the dashboard, take screenshots of each tab, save them in `screenshots/` and uncomment the lines below.
<!--
![Overview](screenshots/overview.png)
![Products](screenshots/products.png)
![Geography](screenshots/geography.png)
![Customers](screenshots/customers.png)
-->

## Resume project description
**E-Commerce Sales & Customer Insights Analytics Dashboard** | Python, Pandas, SQL, Streamlit, Plotly
* Cleaned and validated 6,000+ messy e-commerce orders (duplicates, mixed date formats, 11 columns with missing values,
  outliers) with a reproducible Pandas pipeline and 9 automated validation rules.
* Wrote 19 SQL queries (CTEs, window functions, cohorts) on SQLite covering growth, retention, profitability and regional performance.
* Built an interactive Streamlit and Plotly dashboard with 12+ KPIs/charts and date, category and location filters.
* Segmented 1,278 customers with RFM analysis, finding that 23% of customers generate 51% of revenue.
* Uncovered that Electronics drives 50% of revenue at only 8% margin and that heavy discounts cut margin from 28% to 5%.

## Interview talking points
* Why revenue excludes cancelled/returned orders, and how it changes AOV.
* Why IQR (k=3, with a floor) was used per product instead of a global rule.
* How RFM scores are built with rank-based quintiles and mapped to segments.
* How pandas results were reconciled with SQL results in `test_project.py`.
