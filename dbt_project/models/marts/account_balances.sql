{{ config(materialized='incremental', unique_key=['statement_date', 'account_id']) }}

with base as (
    select
        n.date,
        n.account_id,
        acc.account_name,
        n.amount
    from {{ ref('normalize') }} n
    join {{ ref('dim_account') }} acc on n.account_id = acc.account_id
),
cumulative as (
    select
        date,
        account_id,
        account_name,
        sum(amount) over (partition by account_id order by date rows unbounded preceding) as balance
    from base
)
select
    date as statement_date,
    account_id,
    account_name,
    balance
from cumulative
{% if is_incremental() %}
where date > (select max(statement_date) from {{ this }})
{% endif %}
