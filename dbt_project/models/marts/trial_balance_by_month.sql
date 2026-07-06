-- ============================================
-- dbt Mart: trial_balance_by_month
-- Purpose: Trial balance by month — debits and credits per account per month.
-- Grain: one row per (month, account_id).
-- Owner agent: pipeline-generator (Phase 0 thin slice).
--
-- Accounting correctness: SUM(total_debit) = SUM(total_credit) for every month.
-- This is the core invariant a trial balance must satisfy. The data-engineer
-- validation step enforces it before this mart is promoted to production.
-- ============================================

{{ config(materialized='view') }}

with monthly_account as (
    select
        date_trunc('month', date)::date as month,
        account_id,
        coalesce(sum(debit), 0)::numeric as total_debit,
        coalesce(sum(credit), 0)::numeric as total_credit
    from {{ ref('normalize') }}
    group by 1, 2
),

balanced as (
    select
        month,
        account_id,
        total_debit,
        total_credit,
        (total_debit - total_credit)::numeric as net_amount
    from monthly_account
)

select
    b.month,
    b.account_id,
    acc.account_name,
    acc."Class" as account_class,
    b.total_debit,
    b.total_credit,
    b.net_amount
from balanced b
join {{ ref('dim_account') }} acc on b.account_id = acc.account_id
order by b.month, b.account_id
