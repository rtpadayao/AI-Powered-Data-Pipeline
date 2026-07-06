-- ============================================
-- Postgres Initialization Script
-- Purpose: Create finance schema and GL table
-- ============================================

CREATE SCHEMA IF NOT EXISTS finance;

CREATE TABLE IF NOT EXISTS finance.gl_transactions (
    entry_no VARCHAR(20) PRIMARY KEY,
    date DATE,
    territory_key INT,
    account_key INT,
    details TEXT,
    debit NUMERIC,
    credit NUMERIC
);
