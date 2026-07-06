{{ config(materialized='view') }}

with source_data as (
    select
        entry_no as transaction_id,
        date as transaction_date,
        territory_key,
        account_key as account_id,
        details,
        debit::numeric as debit,
        credit::numeric as credit
    from finance.gl_transactions
)

select
    transaction_id,
    transaction_date,
    territory_key,
    account_id,
    details,
    debit,
    credit
from source_data