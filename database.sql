-- SQLite schema for the E-Commerce Analytics project.
-- Loaded by build_database.py (cleaned_data.csv -> ecommerce.db). Works in SQLite 3.25+ (window functions).

DROP VIEW  IF EXISTS revenue_orders;
DROP TABLE IF EXISTS customer_segments;
DROP TABLE IF EXISTS orders;

CREATE TABLE orders (
    order_id          TEXT PRIMARY KEY,
    order_date        TEXT    NOT NULL,           -- ISO format YYYY-MM-DD
    year              INTEGER NOT NULL,
    month             TEXT    NOT NULL,           -- YYYY-MM
    weekday           TEXT    NOT NULL,
    customer_id       TEXT    NOT NULL,
    customer_name     TEXT    NOT NULL,
    product_name      TEXT    NOT NULL,
    category          TEXT    NOT NULL,
    quantity          INTEGER NOT NULL CHECK (quantity > 0),
    unit_price        REAL    NOT NULL CHECK (unit_price > 0),
    discount          REAL    NOT NULL CHECK (discount BETWEEN 0 AND 0.9),
    gross_sales       REAL    NOT NULL,           -- quantity x unit_price
    total_sales       REAL    NOT NULL,           -- gross_sales x (1 - discount)
    profit            REAL    NOT NULL,
    payment_method    TEXT    NOT NULL,
    city              TEXT    NOT NULL,
    state             TEXT    NOT NULL,
    order_status      TEXT    NOT NULL,           -- Delivered | Shipped | Cancelled | Returned
    is_revenue_order  INTEGER NOT NULL CHECK (is_revenue_order IN (0, 1))
);

CREATE INDEX idx_orders_date     ON orders (order_date);
CREATE INDEX idx_orders_customer ON orders (customer_id);
CREATE INDEX idx_orders_category ON orders (category);
CREATE INDEX idx_orders_state    ON orders (state, city);

-- Only orders that produced revenue (Delivered or Shipped). Most business queries use this view.
CREATE VIEW revenue_orders AS
SELECT * FROM orders WHERE is_revenue_order = 1;

-- RFM customer segmentation (computed in Python by analysis.rfm(), stored for SQL analysis).
CREATE TABLE customer_segments (
    customer_id      TEXT PRIMARY KEY,
    customer_name    TEXT,
    last_order       TEXT,
    frequency        INTEGER,
    monetary         REAL,
    recency_days     INTEGER,
    avg_order_value  REAL,
    r_score          INTEGER,
    f_score          INTEGER,
    m_score          INTEGER,
    rfm_total        INTEGER,
    segment          TEXT
);
