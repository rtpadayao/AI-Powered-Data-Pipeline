---
name: sql
description: SQL query writing, data modeling, and database design patterns for analytics
paths:
  - dbt_project/**
  - api/**
  - airflow/dags/**
  - infrastructure/postgres/**
---

# SQL Skills

Quick reference for common SQL operations, patterns, and database design for analytics.

> **Note:** This file contains executable code patterns and recipes only. For SQL conventions, prohibitions, and style rules (e.g., "never use SELECT *", "always use explicit JOIN", "JSONB over JSON"), see `.claude/rules/sql_rules.md`.

## Basic Query Patterns

### SELECT with Best Practices
```sql
-- Always specify columns explicitly (never SELECT * in production)
SELECT
    t.id,
    t.date,
    t.amount,
    t.status,
    c.name AS customer_name,
    c.region
FROM transactions t
INNER JOIN customers c ON c.id = t.customer_id
WHERE t.date >= '2024-01-01'
  AND t.status = 'completed'
ORDER BY t.date DESC
LIMIT 100;
```

### Filtering
```sql
-- WHERE for raw rows, HAVING for aggregates
SELECT region, SUM(amount) AS total
FROM transactions
WHERE date >= '2024-01-01'      -- Filter before aggregation
GROUP BY region
HAVING SUM(amount) > 100000      -- Filter after aggregation
ORDER BY total DESC;

-- Date range boundaries (avoid BETWEEN for dates)
SELECT * FROM transactions
WHERE date >= '2024-01-01'
  AND date < '2025-01-01';

-- NULL-safe membership check (NOT IN fails with NULLs)
SELECT * FROM transactions
WHERE customer_id NOT EXISTS (
    SELECT 1 FROM blacklist bl WHERE bl.customer_id = transactions.customer_id
);

-- Pattern matching
SELECT * FROM transactions
WHERE description ILIKE '%refund%';  -- Case-insensitive

-- Set operations
SELECT customer_id FROM active_customers
INTERSECT
SELECT customer_id FROM high_value_customers;
```

### Joins
```sql
-- Explicit JOIN syntax only (never comma joins)
SELECT
    t.id, t.amount,
    c.name AS customer_name,
    p.product_name
FROM transactions t
INNER JOIN customers c ON c.id = t.customer_id
LEFT JOIN products p ON p.id = t.product_id    -- All transactions, even without product
WHERE t.date >= '2024-01-01';

-- Self-join for hierarchy (or use window functions)
SELECT e.name AS employee, m.name AS manager
FROM employees e
LEFT JOIN employees m ON m.id = e.manager_id;

-- Cross join for generating date series
SELECT d.date, r.region
FROM GENERATE_SERIES('2024-01-01'::date, '2024-12-31'::date, '1 day'::interval) AS d(date)
CROSS JOIN (SELECT DISTINCT region FROM transactions) AS r;

-- Multiple join conditions
SELECT *
FROM orders o
INNER JOIN shipments s
    ON s.order_id = o.id
    AND s.warehouse_id = o.warehouse_id;
```

## Aggregation & Grouping

### GROUP BY Patterns
```sql
-- Multiple aggregations in single pass
SELECT
    region,
    product_category,
    COUNT(*) AS transaction_count,
    COUNT(DISTINCT customer_id) AS unique_customers,
    SUM(amount) AS total_revenue,
    AVG(amount) AS avg_transaction,
    PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY amount) AS median_amount,
    MIN(date) AS first_sale,
    MAX(date) AS last_sale
FROM transactions
WHERE status = 'completed'
GROUP BY region, product_category
HAVING SUM(amount) > 10000
ORDER BY total_revenue DESC;

-- GROUPING SETS for multiple aggregation levels in one query
SELECT
    region,
    product_category,
    SUM(amount) AS total_revenue
FROM transactions
GROUP BY GROUPING SETS (
    (region, product_category),   -- Region + Category
    (region),                     -- Region subtotal
    ()                             -- Grand total
);
```

### Window Functions
```sql
-- Running totals and moving averages
SELECT
    date,
    amount,
    SUM(amount) OVER (ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_total,
    AVG(amount) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS ma_7d,
    SUM(amount) OVER (PARTITION BY region ORDER BY date) AS region_running_total
FROM transactions;

-- Ranking
SELECT
    region,
    amount,
    ROW_NUMBER() OVER (PARTITION BY region ORDER BY amount DESC) AS rank_unique,
    RANK() OVER (PARTITION BY region ORDER BY amount DESC) AS rank_with_gaps,
    DENSE_RANK() OVER (PARTITION BY region ORDER BY amount DESC) AS rank_no_gaps
FROM transactions;

-- Lead/Lag for period-over-period comparison
SELECT
    month,
    revenue,
    LAG(revenue, 1) OVER (ORDER BY month) AS prev_month_revenue,
    LAG(revenue, 12) OVER (ORDER BY month) AS same_month_last_year,
    revenue - LAG(revenue, 1) OVER (ORDER BY month) AS mom_change,
    ROUND(
        (revenue / LAG(revenue, 12) OVER (ORDER BY month) - 1) * 100, 2
    ) AS yoy_growth_pct
FROM monthly_summary;

-- Nth value and percentiles
SELECT
    region,
    PERCENTILE_DISC(0.25) WITHIN GROUP (ORDER BY amount) WITHIN GROUP (PARTITION BY region) AS p25,
    PERCENTILE_DISC(0.50) WITHIN GROUP (ORDER BY amount) WITHIN GROUP (PARTITION BY region) AS median,
    PERCENTILE_DISC(0.95) WITHIN GROUP (ORDER BY amount) WITHIN GROUP (PARTITION BY region) AS p95
FROM transactions
GROUP BY region;
```

## CTEs & Subqueries

### CTE Patterns
```sql
-- Chain CTEs for complex transformations
WITH daily_metrics AS (
    SELECT
        date,
        COUNT(*) AS transactions,
        SUM(amount) AS revenue,
        COUNT(DISTINCT customer_id) AS unique_customers
    FROM transactions
    GROUP BY date
),
with_growth AS (
    SELECT
        *,
        LAG(revenue, 1) OVER (ORDER BY date) AS prev_revenue,
        LAG(revenue, 7) OVER (ORDER BY date) AS prev_week_revenue
    FROM daily_metrics
),
final AS (
    SELECT
        *,
        ROUND((revenue / prev_revenue - 1) * 100, 2) AS dod_growth_pct,
        ROUND((revenue / prev_week_revenue - 1) * 100, 2) AS wow_growth_pct
    FROM with_growth
)
SELECT * FROM final
WHERE date >= '2024-01-01'
ORDER BY date DESC;

-- Reuse CTE multiple times (vs subquery)
WITH high_value_customers AS (
    SELECT customer_id
    FROM transactions
    GROUP BY customer_id
    HAVING SUM(amount) > 100000
)
SELECT * FROM transactions
WHERE customer_id IN (SELECT customer_id FROM high_value_customers);
```

### Subquery Patterns
```sql
-- Correlated subquery in SELECT
SELECT
    t.*,
    (SELECT COUNT(*) FROM returns r WHERE r.transaction_id = t.id) AS return_count
FROM transactions t;

-- EXISTS for semi-join
SELECT c.*
FROM customers c
WHERE EXISTS (
    SELECT 1 FROM transactions t
    WHERE t.customer_id = c.id
      AND t.date >= '2024-01-01');

-- Scalar subquery (must return single value)
SELECT
    region,
    SUM(amount) AS total,
    SUM(amount) / (SELECT SUM(amount) FROM transactions) * 100 AS pct_of_total
FROM transactions
GROUP BY region;
```

## Data Types & Schema Design

### Type Selection
```sql
-- Financial data types
CREATE TABLE transactions (
    id              BIGINT PRIMARY KEY,
    transaction_id  VARCHAR(50) UNIQUE NOT NULL,
    customer_id     BIGINT NOT NULL REFERENCES customers(id),
    amount          NUMERIC(15, 2) NOT NULL,  -- Exact decimal, never FLOAT for money
    currency        CHAR(3) NOT NULL DEFAULT 'USD',
    exchange_rate   NUMERIC(10, 6),          -- High precision for FX
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
    description     TEXT,
    category        VARCHAR(100),
    tags            TEXT[],                    -- Array type for multi-value attributes
    metadata        JSONB,                    -- Semi-structured data
    transaction_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ
);

-- Constraints
CREATE TABLE accounts (
    id          BIGSERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    type        VARCHAR(20) NOT NULL CHECK (type IN ('asset', 'liability', 'equity', 'revenue', 'expense')),
    balance     NUMERIC(15, 2) NOT NULL DEFAULT 0 CHECK (balance >= 0),
    parent_id   BIGINT REFERENCES accounts(id),
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE(name, type)
);
```

### Index Strategy
```sql
-- B-tree indexes for common queries
CREATE INDEX idx_transactions_date ON transactions (date);
CREATE INDEX idx_transactions_customer_date ON transactions (customer_id, date);
CREATE INDEX idx_transactions_status ON transactions (status) WHERE status = 'partial';  -- Partial index

-- GIN index for JSONB
CREATE INDEX idx_transactions_metadata ON transactions USING GIN (metadata jsonb_path_ops);

-- GIN index for array columns
CREATE INDEX idx_transactions_tags ON transactions USING GIN (tags);

-- GiST index for geospatial (if using PostGIS)
CREATE INDEX idx_locations_geom ON locations USING GIST (geom);

-- BRIN index for naturally ordered large tables (time-series)
CREATE INDEX idx_transactions_brin_date ON transactions USING BRIN (date);
```

## Date & Time Handling

```sql
-- Date truncation for grouping
SELECT
    DATE_TRUNC('month', transaction_at) AS month,
    DATE_TRUNC('week', transaction_at) AS week,
    DATE_TRUNC('quarter', transaction_at) AS quarter,
    COUNT(*) AS transactions,
    SUM(amount) AS revenue
FROM transactions
GROUP BY 1, 2, 3
ORDER BY 1;

-- Date arithmetic
SELECT
    CURRENT_DATE - INTERVAL '30 days' AS thirty_days_ago,
    DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month - 1 day' AS month_end,
    EXTRACT(DOW FROM CURRENT_DATE) AS day_of_week,  -- 0=Sunday
    EXTRACT(WEEK FROM CURRENT_DATE) AS iso_week;

-- Generate date series for gap filling
WITH date_series AS (
    SELECT generate_series(
        '2024-01-01'::date,
        '2024-12-31'::date,
        '1 day'::interval
    )::date AS date
),
daily_revenue AS (
    SELECT date, SUM(amount) AS revenue
    FROM transactions
    GROUP BY date
)
SELECT
    ds.date,
    COALESCE(dr.revenue, 0) AS revenue,
    AVG(dr.revenue) OVER (ORDER BY ds.date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS ma_7d
FROM date_series ds
LEFT JOIN daily_revenue dr ON dr.date = ds.date
ORDER BY ds.date;

-- Timezone handling
SELECT
    transaction_at AS utc_time,
    transaction_at AT TIME ZONE 'America/New_York' AS eastern_time,
    transaction_at AT TIME ZONE 'Europe/London' AS london_time
FROM transactions;
```

## JSON & Semi-Structured Data

```sql
-- JSONB accessors
SELECT
    metadata->>'customer_name' AS customer_name,          -- Text extraction
    metadata->>'tier' AS tier,                            -- Nested text
    metadata->'address'->>'city' AS city,                 -- Nested object to text
    metadata->'tags' AS tags_array,                        -- Array extraction
    jsonb_array_length(metadata->'tags') AS tag_count
FROM transactions
WHERE metadata->>'tier' = 'enterprise';

-- JSONB containment (@> operator - use GIN index)
SELECT * FROM transactions
WHERE metadata @> '{"tier": "enterprise"}';

-- JSONB existence (?)
SELECT * FROM transactions
WHERE metadata ? 'external_id';  -- Top-level key exists

-- Aggregate to JSON
SELECT
    region,
    jsonb_agg(
        jsonb_build_object('id', id, 'amount', amount) ORDER BY amount DESC
    ) AS top_transactions
FROM transactions
GROUP BY region;

-- Unnest JSON array
SELECT
    t.id,
    jsonb_array_elements_text(t.metadata->'tags') AS tag
FROM transactions t;
```

## Performance & Optimization

### EXPLAIN ANALYZE
```sql
-- Always profile before optimizing
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT region, SUM(amount)
FROM transactions
WHERE date >= '2024-01-01'
GROUP BY region;

-- Key things to look for:
-- Seq Scan on large table → needs index
-- Nested Loop Join on large tables → consider Hash Join
-- Sort Method: external merge → needs more work_mem
-- Actual rows >> Estimated rows → run ANALYZE
```

### Query Optimization Patterns
```sql
-- Avoid functions on indexed columns in WHERE
-- BAD:  WHERE EXTRACT(YEAR FROM date) = 2024
-- GOOD: WHERE date >= '2024-01-01' AND date < '2025-01-01'

-- Avoid leading wildcards
-- BAD:  WHERE description LIKE '%refund%'
-- GOOD: WHERE description ILIKE 'refund%'  -- If pattern allows
-- BETTER: Use full-text search with tsvector/tsquery

-- Limit early with subquery
SELECT * FROM (
    SELECT * FROM large_table
    WHERE status = 'active'
    ORDER BY created_at DESC
    LIMIT 100
) sub
JOIN other_table ON other_table.id = sub.id;

-- Batch updates to avoid long locks
DO $$
DECLARE
    batch_size INT := 10000;
    rows_updated INT;
BEGIN
    LOOP
        UPDATE transactions
        SET status = 'archived'
        WHERE id IN (
            SELECT id FROM transactions
            WHERE date < '2020-01-01' AND status != 'archived'
            LIMIT batch_size
            FOR UPDATE SKIP LOCKED
        );
        GET DIAGNOSTICS rows_updated = ROW_COUNT;
        COMMIT;
        EXIT WHEN rows_updated = 0;
    END LOOP;
END $$;
```

## Views & Abstraction

```sql
-- Staging view (lightweight, no transformation)
CREATE OR REPLACE VIEW stg_transactions AS
SELECT
    id,
    transaction_id,
    customer_id,
    amount,
    currency,
    status,
    transaction_at,
    created_at
FROM transactions
WHERE status != 'deleted';

-- Refined dimension view
CREATE OR REPLACE VIEW dim_customers AS
SELECT
    c.id,
    c.name,
    c.region,
    c.segment,
    COUNT(t.id) AS lifetime_transactions,
    SUM(t.amount) AS lifetime_value,
    MIN(t.transaction_at) AS first_purchase,
    MAX(t.transaction_at) AS last_purchase,
    CASE
        WHEN MAX(t.transaction_at) >= CURRENT_DATE - INTERVAL '90 days' THEN 'active'
        WHEN MAX(t.transaction_at) >= CURRENT_DATE - INTERVAL '365 days' THEN 'at_risk'
        ELSE 'churned'
    END AS customer_status
FROM customers c
LEFT JOIN transactions t ON t.customer_id = c.id
GROUP BY c.id, c.name, c.region, c.segment;

-- Materialized view for expensive aggregations
CREATE MATERIALIZED VIEW mv_monthly_revenue AS
SELECT
    DATE_TRUNC('month', transaction_at) AS month,
    region,
    product_category,
    COUNT(*) AS transactions,
    SUM(amount) AS revenue,
    AVG(amount) AS avg_transaction
FROM transactions
GROUP BY 1, 2, 3
WITH DATA;

CREATE UNIQUE INDEX idx_mv_monthly ON mv_monthly_revenue (month, region, product_category);

-- Refresh without locking
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_monthly_revenue;
```

## Data Quality & Validation

```sql
-- Referential integrity check (find orphaned records)
SELECT t.customer_id, COUNT(*)
FROM transactions t
LEFT JOIN customers c ON c.id = t.customer_id
WHERE c.id IS NULL
GROUP BY t.customer_id;

-- Duplicate detection
SELECT transaction_id, COUNT(*), ARRAY_AGG(id) AS duplicate_ids
FROM transactions
GROUP BY transaction_id
HAVING COUNT(*) > 1;

-- Data profiling query
SELECT
    'transactions' AS table_name,
    COUNT(*) AS row_count,
    COUNT(DISTINCT customer_id) AS unique_customers,
    MIN(transaction_at) AS earliest_date,
    MAX(transaction_at) AS latest_date,
    SUM(CASE WHEN amount IS NULL THEN 1 ELSE 0 END) AS null_amounts,
    SUM(CASE WHEN amount < 0 THEN 1 ELSE 0 END) AS negative_amounts,
    AVG(amount)::NUMERIC(15,2) AS avg_amount,
    STDDEV(amount)::NUMERIC(15,2) AS stddev_amount,
    PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY amount)::NUMERIC(15,2) AS median_amount
FROM transactions;

-- Business rule validation
SELECT 'negative_balances' AS check_name, COUNT(*) AS violations
FROM accounts WHERE balance < 0
UNION ALL
SELECT 'future_dated_transactions', COUNT(*)
FROM transactions WHERE transaction_at > CURRENT_TIMESTAMP + INTERVAL '1 day'
UNION ALL
SELECT 'zero_amount_transactions', COUNT(*)
FROM transactions WHERE amount = 0;
```

## Stored Procedures & Functions

```sql
-- Utility function: calculate running balance
CREATE OR REPLACE FUNCTION fn_running_balance(p_customer_id BIGINT)
RETURNS TABLE(
    transaction_date DATE,
    amount NUMERIC,
    running_total NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        t.date::date,
        t.amount,
        SUM(t.amount) OVER (ORDER BY t.date, t.id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
    FROM transactions t
    WHERE t.customer_id = p_customer_id
    ORDER BY t.date;
END;
$$ LANGUAGE plpgsql STABLE;

-- Cross-tabulation with FILTER
SELECT
    region,
    COUNT(*) FILTER (WHERE EXTRACT(quarter FROM date) = 1) AS q1_count,
    COUNT(*) FILTER (WHERE EXTRACT(quarter FROM date) = 2) AS q2_count,
    COUNT(*) FILTER (WHERE EXTRACT(quarter FROM date) = 3) AS q3_count,
    COUNT(*) FILTER (WHERE EXTRACT(quarter FROM date) = 4) AS q4_count,
    SUM(amount) FILTER (WHERE EXTRACT(quarter FROM date) = 1) AS q1_revenue,
    SUM(amount) FILTER (WHERE EXTRACT(quarter FROM date) = 2) AS q2_revenue,
    SUM(amount) FILTER (WHERE EXTRACT(quarter FROM date) = 3) AS q3_revenue,
    SUM(amount) FILTER (WHERE EXTRACT(quarter FROM date) = 4) AS q4_revenue
FROM transactions
WHERE date >= '2024-01-01'
GROUP BY region;
```

## Geospatial Queries (PostGIS)

```sql
-- Distance calculation between points
SELECT
    c.id AS customer_id,
    d.id AS dealership_id,
    ST_Distance(c.geom::geography, d.geom::geography) / 1609.34 AS distance_miles
FROM customers c
CROSS JOIN dealerships d
WHERE c.longitude IS NOT NULL AND c.latitude IS NOT NULL;

-- Nearest dealership per customer
SELECT DISTINCT ON (c.id)
    c.id AS customer_id,
    d.id AS nearest_dealership,
    ST_Distance(c.geom::geography, d.geom::geography) / 1609.34 AS distance_miles
FROM customers c
CROSS JOIN dealerships d
WHERE c.geom IS NOT NULL
ORDER BY c.id, ST_Distance(c.geom, d.geom);

-- Customers within radius
SELECT c.*
FROM customers c
INNER JOIN dealerships d ON d.id = 1
WHERE ST_DWithin(
    c.geom::geography,
    d.geom::geography,
    50 * 1609.34  -- 50 miles in meters
);

-- Radius search using ST_DWithin (orders table, optimized)
SELECT c.name, t.total_spent
FROM customers c
INNER JOIN LATERAL (
    SELECT SUM(amount) AS total_spent
    FROM transactions t
    WHERE t.customer_id = c.id
    AND t.dealership_id IN (
        SELECT id FROM dealerships
        WHERE ST_DWithin(geom, ST_MakePoint(-104.99, 39.74)::geography, 80467)
    )
) t ON TRUE
WHERE c.geom IS NOT NULL;
```

## Loading & ETL Patterns

### Bulk Loading
```sql
-- COPY for fast bulk load
\COPY staging_transactions(id, date, amount, customer_id, status)
FROM '/path/to/transactions.csv'
WITH (FORMAT csv, HEADER true, DELIMITER ',');

-- UPSERT pattern (insert or update)
INSERT INTO transactions (id, date, amount, status)
VALUES ('txn_001', '2024-01-15', 1500.00, 'completed')
ON CONFLICT (id) DO UPDATE SET
    amount = EXCLUDED.amount,
    status = EXCLUDED.status,
    updated_at = CURRENT_TIMESTAMP;

-- Batch processing with watermark
DO $$
DECLARE
    last_processed_id BIGINT := 0;
    batch_size INT := 5000;
    rows_affected INT;
BEGIN
    LOOP
        WITH to_process AS (
            SELECT id, amount, date
            FROM transactions
            WHERE id > last_processed_id
            ORDER BY id
            LIMIT batch_size
        )
        INSERT INTO daily_summary (date, total_amount, transaction_count)
        SELECT date, SUM(amount), COUNT(*)
        FROM to_process
        GROUP BY date
        ON CONFLICT (date) DO UPDATE SET
            total_amount = daily_summary.total_amount + EXCLUDED.total_amount,
            transaction_count = daily_summary.transaction_count + EXCLUDED.transaction_count;

        GET DIAGNOSTICS rows_affected = ROW_COUNT;
        EXIT WHEN rows_affected = 0;

        SELECT MAX(id) INTO last_processed_id FROM to_process;
        COMMIT;
        RAISE NOTICE 'Processed batch up to ID %', last_processed_id;
    END LOOP;
END $$;
```

