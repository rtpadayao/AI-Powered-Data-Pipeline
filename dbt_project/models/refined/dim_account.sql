{{ config(materialized='table') }}

with source_accounts as (
    select
        "Account_key" as account_id,
        "Report",
        "Class",
        "SubClass",
        "SubClass2",
        "Account" as account_name,
        "SubAccount" as sub_account_name
    from {{ ref('chart_of_accounts') }}
)

select
    account_id,
    "Report",
    "Class",
    "SubClass",
    "SubClass2",
    account_name,
    sub_account_name
from source_accounts