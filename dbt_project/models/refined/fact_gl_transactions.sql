{{ config(
    materialized='incremental',
    unique_key='transaction_id'
) }}

with source_transactions as (
    select
        transaction_id,
        transaction_date,
        territory_key,
        account_id,
        details,
        debit,
        credit
    from {{ ref('stg_gl_transactions') }}
)

select
    st.transaction_id,
    st.transaction_date,
    st.territory_key,
    st.account_id,
    st.details,
    st.debit,
    st.credit,
    -- Normalized amount: debit-normal accounts (debit - credit),
    -- credit-normal accounts (credit - debit). marts.normalize applies the
    -- account-type sign rule on top of this raw split.
    st.debit - st.credit as amount
from source_transactions st
{% if is_incremental() %}
  where st.transaction_date > (select max(transaction_date) from {{ this }})
{% endif %}
