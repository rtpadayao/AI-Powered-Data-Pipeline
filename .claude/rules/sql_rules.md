---
  name: sql
  description: Rules for SQL query writing, data modeling, and database design patterns for analytics
  paths:
    - dbt_project/**
    - api/**
    - airflow/dags/**
    - infrastructure/postgres/**
---

# SQL Development Rules

## General SQL Style
  - Use uppercase for all SQL keywords (SELECT, FROM, WHERE, JOIN, GROUP BY, ORDER BY, etc.)
  - Use lowercase with underscores for table names, column names, and aliases
  - Always use explicit `JOIN` syntax — never use comma-separated joins in the `FROM` clause
  - Use meaningful aliases for tables and qualify all column references with aliases
  - End every statement with a semicolon
  - Use single quotes for string literals, never double quotes
  - Prefer `COALESCE()` over `IFNULL()` or `ISNULL()` for NULL handling

## SELECT Query Structure
  1. **Column Selection**: Always specify columns explicitly — never use `SELECT *` in production queries or models.
  2. **Logical Clause Order**: Follow the standard order: `SELECT → FROM → JOIN → WHERE → GROUP BY → HAVING → ORDER BY → LIMIT`.
  3. **ORDER BY Safety**: Always include `ORDER BY` when using `LIMIT` to ensure deterministic results.
  4. **DISTINCT Use**: Use `DISTINCT` deliberately — it is often a sign of a poorly constructed join. Prefer `DISTINCT ON (columns)` in PostgreSQL.
  5. **NULL Handling**: Use `IS NULL` / `IS NOT NULL` (not `= NULL`). Sort NULLs explicitly with `NULLS FIRST` or `NULLS LAST`. Use `COALESCE(column, default_value)` for fallbacks.

## Filtering (WHERE / HAVING)
  1. **WHERE vs HAVING**: Filter raw rows with `WHERE` before aggregation. Filter aggregated results with `HAVING` after `GROUP BY`.
  2. **IN vs EXISTS**: Use `IN` for small static lists. Use `EXISTS` with a correlated subquery for large or dynamic sets.
  3. **BETWEEN Caution**: `BETWEEN` is inclusive on both ends. For date ranges, prefer `>= AND <` to avoid boundary issues.
  4. **Pattern Matching**: Use `LIKE` for simple patterns. Use `ILIKE` in PostgreSQL for case-insensitive matching.
  5. **Negation with NULLs**: `NOT IN (subquery)` returns no rows if the subquery contains a NULL. Use `NOT EXISTS` instead.

## Joins
  1. **Join Type Clarity**: Use `INNER JOIN` when both sides must match. Use `LEFT JOIN` when all rows from the left table are required. Avoid `RIGHT JOIN`.
  2. **Join Order**: Place the largest/fact table first, then join dimension tables. Filter early in `WHERE` on the driving table.
  3. **Composite Keys**: When joining on multiple columns, list all join conditions in the `ON` clause. Never move join conditions to `WHERE` for `OUTER JOINs`.
  4. **Cross Joins**: Use `CROSS JOIN` only when a Cartesian product is intentional. Always validate row counts.
  5. **Self-Joins**: Use self-joins for hierarchical data. Use window functions (`LAG`, `LEAD`) as a more performant alternative for adjacent-row comparisons.

## Aggregation (GROUP BY)
  1. **GROUP BY Semantics**: Every column in `SELECT` must either be in `GROUP BY` or wrapped in an aggregate function.
  2. **HAVING Clause**: Use `HAVING` to filter on aggregate results. Apply non-aggregate filters in `WHERE` for better performance.
  3. **Multiple Aggregations**: Use a single `GROUP BY` with multiple aggregate functions rather than separate subqueries.
  4. **GROUPING SETS**: Use `GROUPING SETS`, `ROLLUP`, or `CUBE` for multi-level aggregation in a single query.
  5. **Ordered Set Aggregates**: Use `PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY column)` for median. Use `MODE() WITHIN GROUP (ORDER BY column)` for most frequent value.

## Window Functions
  1. **Window Function Syntax**: Use the `OVER()` clause with `PARTITION BY` for grouping and `ORDER BY` for ranking.
  2. **Ranking Functions**: Use `ROW_NUMBER()` for unique ranks, `RANK()` for gaps after ties, `DENSE_RANK()` for no gaps. Always include `ORDER BY` inside `OVER()`.
  3. **Offset Functions**: Use `LAG(column, n, default)` and `LEAD(column, n, default)` to access previous/next row values. Always provide a default.
  4. **Running Totals & Moving Averages**: Use `SUM() OVER (ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)` for running totals.
  5. **Frame Specification**: Be explicit about window frames. `RANGE` includes ties; `ROWS` does not.

## Subqueries & CTEs
  1. **CTEs over Subqueries**: Prefer `WITH` clauses (CTEs) over nested subqueries for readability and reuse.
  2. **CTE Chaining**: Chain multiple CTEs for complex logic: `WITH step1 AS (...), step2 AS (SELECT * FROM step1 ...) SELECT * FROM step2`.
  3. **Correlated Subqueries**: Use correlated subqueries in `SELECT` or `WHERE EXISTS` for row-by-row evaluation. Ensure the inner query is selective.
  4. **Scalar Subqueries**: A scalar subquery in `SELECT` must return exactly one row and one column. Use `LIMIT 1` or an aggregate to guarantee this.

## Set Operations
  1. **UNION vs UNION ALL**: Use `UNION ALL` when duplicates are acceptable or impossible — it is faster. Use `UNION` only when deduplication is required.
  2. **INTERSECT**: Use `INTERSECT` to find rows common to both queries.
  3. **EXCEPT**: Use `EXCEPT` to find rows in the first query but not the second. Be aware that `EXCEPT` is not commutative.
  4. **Column Matching**: All queries in a set operation must have the same number of columns with compatible types.

## Data Types & Schema Design
  1. **Type Selection**: Use `INTEGER` for whole numbers, `NUMERIC(precision, scale)` for exact financial amounts (never `FLOAT` for money), `VARCHAR(n)` for bounded text, `TEXT` for unbounded text, `BOOLEAN` for flags, `DATE` / `TIMESTAMPTZ` for temporal data.
  2. **Primary Keys**: Every table must have a primary key. Use `SERIAL` / `GENERATED ALWAYS AS IDENTITY` for surrogate keys.
  3. **Foreign Keys**: Define foreign key constraints with `REFERENCES`. Use `ON DELETE CASCADE` for dependent child rows, `ON DELETE SET NULL` for optional relationships.
  4. **NOT NULL Constraints**: Add `NOT NULL` to columns that should never be empty. Use `DEFAULT` values for optional columns.
  5. **CHECK Constraints**: Use `CHECK` constraints for domain validation.

## Normalization & Data Modeling
  1. **Third Normal Form (3NF)**: Design tables to 3NF — every non-key column must depend on the key, the whole key, and nothing but the key.
  2. **Star Schema for Analytics**: For analytical workloads, use a star schema with fact tables surrounded by dimension tables.
  3. **Slowly Changing Dimensions (SCD)**: Use Type 1 (overwrite) for corrections, Type 2 (new row with effective dates) for historical tracking, Type 3 (add column) for limited history.
  4. **Surrogate vs Natural Keys**: Use surrogate keys as primary keys in the data warehouse. Store natural/business keys as separate columns with unique constraints.
  5. **Naming Conventions**: Tables: singular (`customer`, not `customers`). Columns: `snake_case`. Foreign keys: `referenced_table_id`. Indexes: `idx_<table>_<column>`. Views: `vw_<purpose>` or `dim_` / `fact_` prefix.

## Date & Time Handling
  1. **Timestamps**: Use `TIMESTAMPTZ` for all event timestamps. Store in UTC. Convert to local time at the application layer or with `AT TIME ZONE`.
  2. **Date Truncation**: Use `DATE_TRUNC('month', timestamp_col)` for month-level grouping.
  3. **Date Arithmetic**: Use interval arithmetic: `CURRENT_DATE - INTERVAL '30 days'`, `date_col + INTERVAL '1 month'`.
  4. **Date Series Generation**: Use `GENERATE_SERIES(start, stop, step)` to create date series for gap-filling.
  5. **Extract Date Parts**: Use `EXTRACT(YEAR FROM date_col)`, `EXTRACT(MONTH FROM date_col)`, `EXTRACT(DOW FROM date_col)`.

## JSON & Semi-Structured Data
  1. **JSONB over JSON**: Use `JSONB` (binary JSON) — it supports indexing, is faster to process, and deduplicates keys.
  2. **JSONB Accessors**: Use `->` to get a JSON object, `->>` to get text, `#>` for path access, `#>>` for path-to-text.
  3. **JSONB Indexing**: Create GIN indexes on JSONB columns for containment queries.
  4. **JSON Aggregation**: Use `JSON_AGG()` and `JSON_BUILD_OBJECT()` to construct JSON from relational data.
  5. **When to Use JSON**: Use JSONB for flexible, schema-evolving data. Use normalized columns for data that is queried, filtered, or joined regularly.

## Arrays
  1. **Array Aggregation**: Use `ARRAY_AGG(column ORDER BY sort_col)` to collect values into an array per group.
  2. **Array Unnesting**: Use `UNNEST(array_col)` to expand arrays into rows. Use `WITH ORDINALITY` to preserve element positions.
  3. **Array Operators**: Use `ANY(array)` for membership checks, `&&` for overlap, `@>` for containment, `<@` for contained-by.
  4. **Array Construction**: Use `ARRAY[val1, val2, val3]` for literal arrays. Use `ARRAY(subquery)` to build arrays from query results.

## Performance & Optimization
  1. **EXPLAIN ANALYZE**: Always run `EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)` on queries before deploying to production.
  2. **Index Strategy**: Create B-tree indexes on columns used in `WHERE`, `JOIN`, and `ORDER BY`. Create GIN indexes for JSONB and array columns. Create partial indexes for frequently filtered subsets.
  3. **Index Types**: Use B-tree for equality and range queries. Use GIN for full-text search, JSONB, and array containment. Use GiST for geospatial. Use BRIN for naturally ordered large tables.
  4. **Avoid SELECT ***: Selecting all columns prevents index-only scans, increases I/O, and breaks when schema changes.
  5. **Batch Operations**: For large updates/deletes, process in batches using `LIMIT` with a loop or `ctid` ranges to avoid long-running locks.
  6. **Vacuum & Analyze**: Run `ANALYZE` after bulk loads to update statistics. Monitor table bloat and schedule `VACUUM` for high-churn tables.

## Views & Abstraction Layers
  1. **View Naming**: Use `vw_` prefix for general views, `dim_` for dimension views, `fact_` for fact views, `rpt_` for report views, `stg_` for staging views.
  2. **Updatable Views**: Simple views (single table, no aggregation) are updatable. Use `INSTEAD OF` triggers for complex view updates.
  3. **Materialized Views**: Use `MATERIALIZED VIEW` for expensive aggregations that don't need real-time data. Refresh with `REFRESH MATERIALIZED VIEW CONCURRENTLY`.
  4. **View Layering**: Build views in layers: staging → refined → marts. Each layer should only depend on the layer below.

## Stored Procedures & Functions
  1. **Function Naming**: Use `fn_` prefix for scalar functions, `sp_` for stored procedures.
  2. **Immutable vs Volatile**: Mark functions as `IMMUTABLE`, `STABLE`, or `VOLATILE` to enable query planner optimizations.
  3. **Error Handling**: Use `BEGIN ... EXCEPTION ... END` blocks in PL/pgSQL. Use `RAISE NOTICE` for logging, `RAISE EXCEPTION` for fatal errors.
  4. **SQL vs PL/pgSQL**: Prefer SQL functions for simple queries (they can be inlined). Use PL/pgSQL for procedural logic.

## Data Quality & Validation
  1. **Schema Constraints**: Enforce data quality at the database level with `NOT NULL`, `CHECK`, `UNIQUE`, and `FOREIGN KEY` constraints.
  2. **Data Profiling**: Profile new datasets with: `SELECT COUNT(*), COUNT(DISTINCT col), SUM(CASE WHEN col IS NULL THEN 1 ELSE 0 END), MIN(col), MAX(col) FROM table`.
  3. **Referential Integrity**: After loads, validate foreign keys: `SELECT child.fk_col FROM child LEFT JOIN parent ON child.fk_col = parent.pk_col WHERE parent.pk_col IS NULL`.
  4. **Duplicate Detection**: Use `GROUP BY ... HAVING COUNT(*) > 1` to find duplicates. Use `ROW_NUMBER() OVER (PARTITION BY key_cols ORDER BY created_at)` to identify rows to keep.

## Geospatial Data
  1. **Point Storage**: Use `POINT(longitude, latitude)` for location data. For production, use PostGIS with `GEOMETRY` or `GEOGRAPHY` types.
  2. **Distance Calculation**: Use `ST_Distance(geog1, geog2)` for meter-based geodesic distance in PostGIS.
  3. **Nearest Neighbor**: Use `DISTINCT ON` with `ORDER BY distance` for per-group nearest neighbor. For PostGIS, use `ST_DWithin()` and `LATERAL JOIN` with `ORDER BY <->`.
  4. **Spatial Indexing**: Create GiST indexes on geometry columns.

## Inferential Statistics with SQL
  1. **Descriptive Statistics**: Calculate mean (`AVG`), median (`PERCENTILE_DISC(0.5)`), mode (`MODE() WITHIN GROUP`), standard deviation (`STDDEV`), variance (`VAR_SAMP`), and percentiles (`PERCENTILE_CONT`).
  2. **Correlation**: Use `CORR(x, y)` for Pearson correlation. Use `REGR_SLOPE(y, x)` and `REGR_INTERCEPT(y, x)` for simple linear regression.
  3. **Hypothesis Testing**: Calculate t-statistics manually: `(avg - hypothesized_mean) / (stddev / SQRT(n))`.
  4. **Cohort Analysis**: Use `DATE_TRUNC` with `first_event_date` to group users into cohorts. Use window functions for retention rates.

## Data Loading & ETL Patterns
  1. **COPY Command**: Use `\COPY` (psql) or `COPY` (server-side) for bulk data loading. It is 10-50x faster than `INSERT`.
  2. **Staging Tables**: Load raw data into staging tables first (`stg_` prefix), then transform and load into production tables.
  3. **Upsert Pattern**: Use `INSERT ... ON CONFLICT (key) DO UPDATE SET ...` for idempotent loads.
  4. **Incremental Loading**: Use `WHERE updated_at > (SELECT MAX(updated_at) FROM target_table)` or watermark tables to load only new/changed records.
  5. **Transaction Wrapping**: Wrap ETL steps in a single transaction: `BEGIN; ... COMMIT;`.
