-- ============================================
-- dbt Mart: gross_profit_mom_variance
-- Purpose: Gross profit by month with month-over-month % change (variance).
-- Grain: one row per month (first-of-month DATE).
-- Owner agent: pipeline-generator (Phase 0 fourth artifact).
--
-- Accounting logic:
--   Gross Profit = Revenue - COGS
--   MoM % change = (gross_profit - lag(gross_profit)) / nullif(lag(gross_profit), 0) * 100
--
-- The normalize mart already encodes debit/credit normalization:
--   - Assets & Expenses (debit-normal, account_id <= 100):   amount = debit - credit
--   - Liabilities, Equity, Revenue (credit-normal, id > 100): amount = credit - debit
-- So SUM(amount) over P&L accounts gives the signed position directly:
--   revenue accounts contribute positively, expense/cogs accounts contribute negatively.
--
-- SubClass -> line mapping (driven by the chart_of_accounts seed; dim_account is the source):
--   Revenue (top-line trading + other income):
--     'Sales', 'Sales Return'  (Sales Return is contra-revenue, net of Sales)
--     'Interest Income', 'Dividend Income',
--     'Gain/Loss on Sales of Asset', 'Exchange Loss/Gain'
--   COGS (cost of goods sold / cost of sales):
--     'Cost of Sales'            (the only distinct COGS subclass in this chart of accounts)
--   Excluded from gross profit (operating / non-operating below the gross line):
--     'Operating Expenses', 'Depreciation & Amortization',
--     'Interest Expense', 'Taxation'
--
-- Honesty note: this chart of accounts uses a "Trading account" structure
-- (Sales / Cost of Sales) rather than a manufacturer's "Revenue / COGS" breakdown.
-- 'Cost of Sales' is the only line that maps to COGS; all other expense lines are
-- operating/non-operating and sit below gross profit. Revenue is taken as the
-- trading top line (Sales net of Sales Return) plus other operating/non-operating
-- income lines (Interest Income, Dividend Income, Gain/Loss on Sale, Exchange
-- Loss/Gain) so the mart reflects total incoming economic benefit above the gross line.
--
-- Correctness: gross_profit = revenue - cogs for every row; MoM% matches the
-- window-function LAG(gross_profit) OVER (ORDER BY month). The data-engineer
-- validation step enforces both before the mart is promoted.
-- ============================================

{{ config(materialized='view') }}

with pl_accounts as (
    select
        n.date,
        n.account_id,
        n.amount,
        acc."Class",
        acc."SubClass",
        acc."SubClass2"
    from {{ ref('normalize') }} n
    join {{ ref('dim_account') }} acc
        on n.account_id = acc.account_id
    where acc."Report" = 'Profit and Loss'
),

classified as (
    select
        date_trunc('month', date)::date as month,
        amount,
        case
            when "SubClass" in (
                'Sales',
                'Sales Return',
                'Interest Income',
                'Dividend Income',
                'Gain/Loss on Sales of Asset',
                'Exchange Loss/Gain'
            ) then 'Revenue'
            when "SubClass" in ('Cost of Sales') then 'COGS'
            else 'Below Gross Profit'
        end as line_type
    from pl_accounts
),

monthly_totals as (
    select
        month,
        sum(case when line_type = 'Revenue' then amount else 0 end) as revenue,
        sum(case when line_type = 'COGS' then amount else 0 end) as cogs
    from classified
    group by month
),

with_gross_profit as (
    select
        month,
        revenue,
        cogs,
        revenue - cogs as gross_profit
    from monthly_totals
)

select
    month,
    revenue,
    cogs,
    gross_profit,
    (gross_profit - lag(gross_profit) over (order by month))
        / nullif(lag(gross_profit) over (order by month), 0) * 100
        as gross_profit_mom_pct
from with_gross_profit
order by month
