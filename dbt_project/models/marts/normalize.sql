-- ============================================
-- dbt Transformation Model
-- Purpose: Normalize Debit/Credit into Amount
-- ============================================

{{ config(materialized='incremental', unique_key='entry_no') }}

with source_data as (
    select
        transaction_id as entry_no,   -- keeping entry_no for compatibility
        transaction_date as date,
        territory_key,
        account_id,
        details,
        debit,
        credit
    from {{ ref('fact_gl_transactions') }}
),

normalized as (
    select
        entry_no,
        date,
        territory_key,
        account_id,
        details,
        debit,
        credit,
        case
            when account_id <= 100
                then debit - credit   -- Assets & Expenses (debit-normal)
            when account_id > 100
                then credit - debit   -- Liabilities, Equity, Revenue (credit-normal)
            else 0
        end as amount
    from source_data
)

select
    entry_no,
    date,
    territory_key,
    account_id,
    details,
    debit,
    credit,
    amount
from normalized

{% if is_incremental() %}
  where date > (select max(date) from {{ this }})
{% endif %}