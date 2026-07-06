-- ============================================
-- dbt Mart: balance_sheet_by_month
-- Purpose: Balance sheet by month — cumulative balances per (month, account_class).
-- Grain: one row per (month, account_class) where account_class is Assets/Liabilities/Equity.
-- Owner agent: pipeline-generator (Phase 0 third artifact).
--
-- Accounting logic:
--   The normalize mart (ref('normalize')) exposes a signed `amount` column that
--   already applies debit/credit normalization per account_id:
--     - Assets & Expenses (debit-normal, account_id <= 100):  amount = debit - credit
--     - Liabilities, Equity, Revenue (credit-normal, account_id > 100): amount = credit - debit
--
--   For a balance sheet we want cumulative balances of permanent accounts
--   (Assets, Liabilities, Equity) as of each month-end. Per-month net is
--   SUM(amount); a running total across months gives the cumulative balance:
--       SUM(SUM(amount)) OVER (PARTITION BY account_class ORDER BY month)
--
-- Correctness: Assets = Liabilities + Equity for every month (the accounting
-- equation). The data-engineer validation step enforces this before the mart
-- is promoted to production.
-- ============================================

{{ config(materialized='view') }}

with bs_accounts as (
    select
        date_trunc('month', n.date)::date as month,
        acc."Class" as account_class,
        sum(n.amount) as net_amount
    from {{ ref('normalize') }} n
    join {{ ref('dim_account') }} acc on n.account_id = acc.account_id
    where acc."Report" = 'Balance Sheet'
    group by 1, 2
),

cumulative as (
    select
        month,
        account_class,
        net_amount,
        sum(net_amount) over (
            partition by account_class
            order by month
            rows between unbounded preceding and current row
        ) as balance
    from bs_accounts
)

select
    month,
    account_class,
    balance
from cumulative
order by month, account_class
