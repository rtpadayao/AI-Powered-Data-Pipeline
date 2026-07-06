-- ============================================
-- dbt Mart: account_aging
-- Purpose: AR/AP aging report — open balances bucketed by age from posting date.
-- Grain: one row per (account_id, aging_bucket).
-- Owner agent: pipeline-generator (aging mart).
--
-- Accounting logic:
--   AR/AP aging shows how long outstanding receivable/payable balances have
--   been open. Aging buckets: 0-30 (current), 31-60, 61-90, 90+ days.
--
--   "Open balance" = net cumulative position of the account (SUM(amount)).
--   SIMPLIFICATION: This GL has no invoice-level or payment-matching data, so
--   we cannot track individual open items. "Open balance" here is the account's
--   net position as of the as-of date. A more sophisticated system would match
--   invoices to payments and age the unmatched items.
--
--   Aging assignment: the entire net balance of each account is placed into the
--   bucket corresponding to the OLDEST posting date for that account. This is
--   conservative — the oldest outstanding item determines the aging. An
--   alternative (weighted-average age) was considered but rejected because it
--   would split a single account's balance across buckets, which is only
--   meaningful with invoice-level granularity we don't have.
--
--   Subclass filter: accounts where SubClass2 IN ('Receivables', 'Trade Payables',
--   'Other Payables'). These cover:
--     - AR: account_ids 30, 40, 41, 42, 50 (Current Assets / Receivables)
--     - Trade AP: account_id 110 (Current Liabilities / Trade Payables)
--     - Other AP: account_ids 120-135 (Current Liabilities / Other Payables)
--   Other Current Liabilities and debt-related accounts are excluded since they
--   are not receivable/payable in the aging sense.
--
-- As-of date: SELECT MAX(date) FROM normalize — the latest posting date in the
-- dataset. This is correct for a static historical dataset; replace with
-- CURRENT_DATE for a live system.
--
-- Only accounts with a non-zero net balance are included.
-- ============================================

{{ config(materialized='view') }}

with as_of_date as (
    select max(date)::date as as_of_date
    from {{ ref('normalize') }}
),

ar_ap_accounts as (
    select
        n.account_id,
        acc.account_name,
        acc."SubClass2",
        sum(n.amount) as open_balance
    from {{ ref('normalize') }} n
    join {{ ref('dim_account') }} acc on n.account_id = acc.account_id
    where acc.account_name in ('Receivables', 'Trade Payables', 'Other Payables')
    group by n.account_id, acc.account_name, acc."SubClass2"
    having sum(n.amount) <> 0
),

oldest_posting as (
    select
        n.account_id,
        min(n.date)::date as oldest_date
    from {{ ref('normalize') }} n
    join {{ ref('dim_account') }} acc on n.account_id = acc.account_id
    where acc.account_name in ('Receivables', 'Trade Payables', 'Other Payables')
    group by n.account_id
),

aged as (
    select
        a.account_id,
        a.account_name,
        a."SubClass2",
        a.open_balance,
        d.as_of_date,
        case
            when (d.as_of_date - o.oldest_date) <= 30 then '0-30 current'
            when (d.as_of_date - o.oldest_date) <= 60 then '31-60'
            when (d.as_of_date - o.oldest_date) <= 90 then '61-90'
            else '90+'
        end as aging_bucket
    from ar_ap_accounts a
    cross join as_of_date d
    join oldest_posting o on a.account_id = o.account_id
)

select
    account_id,
    account_name,
    "SubClass2",
    aging_bucket,
    open_balance,
    as_of_date
from aged
order by account_id, aging_bucket
