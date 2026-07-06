{{ config(materialized='incremental', unique_key=['statement_date', 'account_class']) }}

with base_account as (
    select
        n.date,
        acc.account_id,
        acc."Class" as account_class,
        n.amount
    from {{ ref('normalize') }} n
    join {{ ref('dim_account') }} acc on n.account_id = acc.account_id
),
cumulative as (
    select
        date,
        account_class,
        sum(amount) over (partition by account_class order by date rows unbounded preceding) as balance
    from base_account
    where account_class in ('Assets', 'Liabilities', 'Equity')
)
select
    date as statement_date,
    'Balance Sheet' as statement_type,
    account_class,
    balance
from cumulative
{% if is_incremental() %}
where date > (select max(statement_date) from {{ this }})
{% endif %}
