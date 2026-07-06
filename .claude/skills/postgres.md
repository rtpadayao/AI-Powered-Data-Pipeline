---
name: postgres
description: PostgreSQL database administration, optimization, and operations skills
paths:
  - infrastructure/postgres/**
  - api/**
  - dbt_project/**
---

# PostgreSQL Skills

Quick reference for PostgreSQL operations, administration, and optimization for the financial data pipeline.

## Database Connection

### Connect via Docker
```bash
# Connect to the running PostgreSQL container
docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB

# Or with explicit credentials
docker compose exec postgres psql -U airflow -d finance
```

### Connection String Format
```
postgresql://user:password@host:5432/database
```

### Test Connection
```bash
# Quick health check
docker compose exec postgres pg_isready -U $POSTGRES_USER

# Check database size
docker compose exec postgres psql -U $POSTGRES_USER -c "SELECT pg_size_pretty(pg_database_size('$POSTGRES_DB'));"
```

## Schema & Table Operations

### Initialize Database
```bash
# Run the init script
docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -f /docker-entrypoint-initdb.d/init-db.sql
```

### List Schemas and Tables
```sql
-- List all schemas
SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('pg_catalog', 'information_schema');

-- List tables in finance schema
SELECT table_name, table_type FROM information_schema.tables WHERE table_schema = 'finance';

-- Table size
SELECT
    relname AS table_name,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
    pg_size_pretty(pg_relation_size(relid)) AS data_size,
    pg_size_pretty(pg_indexes_size(relid)) AS index_size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```

### Create Schema and Tables
```sql
-- Create schema
CREATE SCHEMA IF NOT EXISTS finance;

-- Create table with proper constraints
CREATE TABLE IF NOT EXISTS finance.gl_transactions (
    entry_no     VARCHAR(20) PRIMARY KEY,
    date         DATE NOT NULL,
    territory_key INTEGER NOT NULL,
    account_key  INTEGER NOT NULL,
    details      TEXT,
    debit        NUMERIC(15, 2) DEFAULT 0 CHECK (debit >= 0),
    credit       NUMERIC(15, 2) DEFAULT 0 CHECK (credit >= 0),
    created_at   TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Add indexes
CREATE INDEX idx_gl_date ON finance.gl_transactions (date);
CREATE INDEX idx_gl_account ON finance.gl_transactions (account_key);
CREATE INDEX idx_gl_territory ON finance.gl_transactions (territory_key);
CREATE INDEX idx_gl_date_account ON finance.gl_transactions (date, account_key);
```

### Alter Table
```sql
-- Add column
ALTER TABLE finance.gl_transactions ADD COLUMN IF NOT EXISTS currency CHAR(3) DEFAULT 'USD';

-- Add constraint
ALTER TABLE finance.gl_transactions ADD CONSTRAINT chk_debit_positive CHECK (debit >= 0);

-- Rename column
ALTER TABLE finance.gl_transactions RENAME COLUMN details TO transaction_details;

-- Drop column (careful!)
ALTER TABLE finance.gl_transactions DROP COLUMN IF EXISTS obsolete_col;
```

## Query Operations

### Basic Analytical Queries
```sql
-- Daily transaction summary
SELECT
    date,
    COUNT(*) AS transaction_count,
    SUM(debit) AS total_debits,
    SUM(credit) AS total_credits,
    SUM(debit - credit) AS net_amount
FROM finance.gl_transactions
WHERE date >= '2024-01-01'
GROUP BY date
ORDER BY date DESC;

-- Account balance summary
SELECT
    account_key,
    SUM(debit) AS total_debits,
    SUM(credit) AS total_credits,
    SUM(debit - credit) AS balance
FROM finance.gl_transactions
GROUP BY account_key
ORDER BY ABS(SUM(debit - credit)) DESC;

-- Territory performance
SELECT
    territory_key,
    COUNT(*) AS transactions,
    SUM(debit) AS total_debits,
    AVG(debit) AS avg_debit
FROM finance.gl_transactions
WHERE date >= '2024-01-01'
GROUP BY territory_key
ORDER BY total_debits DESC;
```

### Window Functions for Analytics
```sql
-- Running balance per account
SELECT
    entry_no,
    date,
    account_key,
    debit,
    credit,
    SUM(debit - credit) OVER (
        PARTITION BY account_key
        ORDER BY date, entry_no
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS running_balance
FROM finance.gl_transactions
ORDER BY account_key, date;

-- Month-over-month comparison
SELECT
    DATE_TRUNC('month', date) AS month,
    account_key,
    SUM(debit - credit) AS net_amount,
    LAG(SUM(debit - credit)) OVER (
        PARTITION BY account_key ORDER BY DATE_TRUNC('month', date)
    ) AS prev_month,
    ROUND(
        (SUM(debit - credit) / NULLIF(LAG(SUM(debit - credit)) OVER (
            PARTITION BY account_key ORDER BY DATE_TRUNC('month', date)
        ), 0) - 1) * 100, 2
    ) AS mom_growth_pct
FROM finance.gl_transactions
GROUP BY DATE_TRUNC('month', date), account_key
ORDER BY account_key, month;
```

## Performance & Optimization

### EXPLAIN ANALYZE
```sql
-- Profile a query
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT account_key, SUM(debit - credit) AS balance
FROM finance.gl_transactions
WHERE date >= '2024-01-01'
GROUP BY account_key;

-- Key things to watch:
-- Seq Scan on large table → needs index
-- Nested Loop on large sets → consider Hash Join
-- Sort Method: external merge → increase work_mem
-- Buffers: read=high vs shared hit=low → needs better caching
```

### Index Management
```sql
-- List existing indexes
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'finance'
ORDER BY tablename;

-- Check index usage
SELECT
    indexrelname AS index_name,
    idx_scan AS times_used,
    idx_tup_read AS rows_read,
    idx_tup_fetch AS rows_fetched,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'finance'
ORDER BY idx_scan DESC;

-- Find unused indexes (candidates for removal)
SELECT
    indexrelname AS index_name,
    idx_scan AS times_used,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND indexrelname NOT LIKE '%_pkey'
ORDER BY pg_relation_size(indexrelid) DESC;

-- Create index concurrently (no table lock)
CREATE INDEX CONCURRENTLY idx_gl_details_gin
ON finance.gl_transactions USING GIN (details gin_trgm_ops);
```

### Vacuum & Maintenance
```sql
-- Check table bloat (dead tuples)
SELECT
    relname AS table_name,
    n_live_tup AS live_rows,
    n_dead_tup AS dead_rows,
    ROUND(n_dead_tup * 100.0 / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_pct,
    last_vacuum,
    last_autovacuum
FROM pg_stat_user_tables
WHERE schemaname = 'finance'
ORDER BY n_dead_tup DESC;

-- Manual vacuum (non-blocking)
VACUUM (VERBOSE, ANALYZE) finance.gl_transactions;

-- Full vacuum (reclaims space but locks table - use during maintenance)
VACUUM FULL finance.gl_transactions;

-- Update statistics
ANALYZE finance.gl_transactions;
```

### Configuration Tuning
```sql
-- Check current settings
SHOW work_mem;
SHOW shared_buffers;
SHOW effective_cache_size;
SHOW random_page_cost;

-- Set for session (analytical workload)
SET work_mem = '256MB';
SET effective_cache_size = '4GB';
SET random_page_cost = 1.1;  -- SSD

-- Recommended for analytics (postgresql.conf):
-- shared_buffers = 25% of RAM
-- work_mem = 256MB (per sort/hash operation)
-- maintenance_work_mem = 1GB
-- effective_cache_size = 50-75% of RAM
-- random_page_cost = 1.1 (SSD) or 4.0 (HDD)
-- max_parallel_workers_per_gather = 4
-- work_mem is PER operation — a query with 3 sorts uses 3x work_mem
```

## Monitoring Queries

### Connection & Activity
```sql
-- Current connections
SELECT
    datname AS database,
    state,
    COUNT(*) AS connections,
    MAX(EXTRACT(EPOCH FROM (now() - state_change))) AS max_idle_seconds
FROM pg_stat_activity
GROUP BY datname, state
ORDER BY connections DESC;

-- Long-running queries (> 30 seconds)
SELECT
    pid,
    now() - query_start AS duration,
    state,
    LEFT(query, 100) AS query_preview
FROM pg_stat_activity
WHERE state != 'idle'
  AND now() - query_start > INTERVAL '30 seconds'
ORDER BY duration DESC;

-- Blocking queries
SELECT
    blocked.pid AS blocked_pid,
    blocking.pid AS blocking_pid,
    blocked.query AS blocked_query,
    blocking.query AS blocking_query
FROM pg_stat_activity blocked
JOIN pg_stat_activity blocking ON blocking.pid = ANY(
    SELECT unnest(pg_blocking_pids(blocked.pid))
)
WHERE blocked.wait_event_type IS NOT NULL;
```

### Database Statistics
```sql
-- Database overview
SELECT
    datname AS database,
    pg_size_pretty(pg_database_size(datname)) AS size,
    numbackends AS active_connections,
    xact_commit AS total_commits,
    xact_rollback AS total_rollbacks,
    blks_read AS disk_reads,
    blks_hit AS cache_hits,
    ROUND(blks_hit * 100.0 / NULLIF(blks_read + blks_hit, 0), 2) AS cache_hit_ratio
FROM pg_stat_database
WHERE datname = current_database();

-- Table statistics
SELECT
    relname AS table_name,
    seq_scan AS sequential_scans,
    seq_tup_read AS rows_from_seq_scan,
    idx_scan AS index_scans,
    idx_tup_fetch AS rows_from_index,
    n_live_tup AS live_rows,
    n_dead_tup AS dead_rows,
    n_tup_ins AS total_inserts,
    n_tup_upd AS total_updates,
    n_tup_del AS total_deletes
FROM pg_stat_user_tables
WHERE schemaname = 'finance'
ORDER BY n_live_tup DESC;
```

## Backup & Recovery

### Logical Backup (pg_dump)
```bash
# Backup single database
docker compose exec postgres pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup_$(date +%Y%m%d).sql

# Backup specific schema
docker compose exec postgres pg_dump -U $POSTGRES_USER -n finance $POSTGRES_DB > finance_backup.sql

# Compressed backup
docker compose exec postgres pg_dump -U $POSTGRES_USER -Fc $POSTGRES_DB > backup.dump

# Restore from SQL
docker compose exec -T postgres psql -U $POSTGRES_USER -d $POSTGRES_DB < backup_20240101.sql

# Restore from custom format
docker compose exec postgres pg_restore -U $POSTGRES_USER -d $POSTGRES_DB backup.dump
```

### Quick Data Export/Import
```bash
# Export table to CSV
docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB \
  -c "\COPY finance.gl_transactions TO '/tmp/gl_transactions.csv' WITH CSV HEADER"

# Import from CSV
docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB \
  -c "\COPY finance.gl_transactions FROM '/tmp/gl_transactions.csv' WITH CSV HEADER"
```

## Security

### User & Role Management
```sql
-- Create read-only role
CREATE ROLE finance_reader;
GRANT USAGE ON SCHEMA finance TO finance_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA finance TO finance_reader;

-- Create read-write role
CREATE ROLE finance_writer;
GRANT USAGE ON SCHEMA finance TO finance_writer;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA finance TO finance_writer;

-- Assign roles
GRANT finance_reader TO analyst_user;
GRANT finance_writer TO etl_user;

-- Row-level security (example: users see only their territory)
ALTER TABLE finance.gl_transactions ENABLE ROW LEVEL SECURITY;
CREATE POLICY territory_filter ON finance.gl_transactions
    USING (territory_key = current_setting('app.current_territory')::INTEGER);
```

### Connection Security
```bash
# Check SSL status
docker compose exec postgres psql -U $POSTGRES_USER -c "SHOW ssl;"

# Check pg_hba.conf authentication rules
docker compose exec postgres psql -U $POSTGRES_USER -c "SHOW hba_file;"
```

## Docker-Specific Operations

### Container Management
```bash
# Check container health
docker compose ps postgres

# View logs
docker compose logs -f postgres

# Restart service
docker compose restart postgres

# Execute single command
docker compose exec postgres psql -U $POSTGRES_USER -c "SELECT 1;"
```

### Volume & Persistence
```bash
# Check volume
docker volume ls | grep postgres

# Inspect volume
docker volume inspect cc_AI-Powered_Airflow_postgres_data

# Volume backup (snapshot)
docker run --rm -v cc_AI-Powered_Airflow_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_volume.tar.gz -C /data .
```

## Troubleshooting

### Common Issues
```bash
# Connection refused
docker compose ps postgres  # Check if running
docker compose logs postgres  # Check logs

# Authentication failed
cat .env | grep POSTGRES  # Verify credentials
docker compose exec postgres psql -U $POSTGRES_USER -c "SHOW hba_file;"

# Out of disk space
docker compose exec postgres psql -U $POSTGRES_USER -c "SELECT pg_size_pretty(pg_database_size(datname)) FROM pg_stat_database;"
docker system df  # Check Docker disk usage

# Query hangs
docker compose exec postgres psql -U $POSTGRES_USER -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'active' AND query_start < now() - interval '5 minutes';"

# Too many connections
docker compose exec postgres psql -U $POSTGRES_USER -c "SELECT count(*) FROM pg_stat_activity;"
# Fix: increase pool_size in compose or add PgBouncer
```

## Best Practices

### Schema Design
1. Use `NUMERIC(15, 2)` for monetary values — never `FLOAT`
2. Use `TIMESTAMPTZ` for all timestamps, store in UTC
3. Always define primary keys and foreign keys
4. Use `CHECK` constraints for data validation at the DB level
5. Prefer `INTEGER` or `BIGINT` surrogate keys for fact tables

### Performance
1. Create indexes on columns used in WHERE, JOIN, ORDER BY
2. Use `EXPLAIN ANALYZE` on all queries before deploying
3. Set `work_mem` higher for analytical queries (256MB+)
4. Use `COPY` for bulk loading (10-50x faster than INSERT)
5. Run `ANALYZE` after bulk loads to update statistics

### Operations
1. Monitor dead tuples and autovacuum regularly
2. Set `log_min_duration_statement` to catch slow queries
3. Use connection pooling (PgBouncer) for production
4. Test backup restoration quarterly
5. Use migrations (Alembic/dbt) for schema changes — never ad-hoc DDL
