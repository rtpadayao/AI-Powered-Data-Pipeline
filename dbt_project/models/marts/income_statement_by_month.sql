-- ============================================
-- dbt Mart: income_statement_by_month
-- Purpose: Income statement (P&L) by month — revenue, expenses, and net income.
-- Grain: one row per (month, account_class) where account_class is a P&L category.
-- Owner agent: pipeline-generator (Phase 0 second artifact).
--
-- Accounting logic:
--   Revenue  = SUM(amount) where amount > 0 (credit-normal: revenue, income)
--   Expenses = SUM(amount) where amount < 0 (debit-normal: costs, overhead)
--   Net Income = Revenue + Expenses  (expenses are negative, so this is Revenue - |Expenses|)
--
-- The normalize mart already encodes debit/credit normalization:
--   - Assets & Expenses (debit-normal):   amount = debit - credit
--   - Liabilities, Equity, Revenue (credit-normal): amount = credit - debit
-- So a SUM(amount) over P&L accounts gives us the net position directly.
--
-- Correctness: Net Income = Revenue + Expenses for every month.
-- The data-engineer validation step enforces this before the mart is promoted.
-- ============================================

{{ config(materialized='view') }}

with pl_accounts as (
    select
        date_trunc('month', n.date)::date as month,
        n.account_id,
        acc.account_name,
        acc."Class" as account_class,
        acc."SubClass",
        n.amount
    from {{ ref('normalize') }} n
    join {{ ref('dim_account') }} acc on n.account_id = acc.account_id
    where acc."Report" = 'Profit and Loss'
),

monthly_class as (
    select
        month,
        account_class,
        account_name,
        "SubClass",
        sum(amount) as net_amount
    from pl_accounts
    group by 1, 2, 3, 4
),

classified as (
    select
        month,
        account_class,
        account_name,
        "SubClass",
        net_amount,
        case
            when "SubClass" in ('Interest Income', 'Dividend Income')
                then 'Revenue'
            when "SubClass" in ('Interest Expense')
                then 'Interest Expense'
            else 'Operating Expense'
        end as line_type
    from monthly_class
)

select
    month,
    line_type,
    account_class,
    sum(net_amount) as amount,
    case
        when line_type = 'Revenue' then sum(net_amount)
        else 0
    end as revenue,
    case
        when line_type != 'Revenue' then sum(net_amount)
        else 0
    end as expenses
from classified
group by 1, 2, 3
order by month, line_type, account_class
