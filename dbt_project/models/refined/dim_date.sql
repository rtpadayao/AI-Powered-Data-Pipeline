{{ config(materialized='table') }}

with date_range as (
    select
        (date '2020-01-01' + (sequence.day)::int) as date_value
    from generate_series(0, (current_date - date '2020-01-01')) as sequence(day)
)
select
    date_value as date_id,
    extract(year from date_value)::int as year,
    extract(month from date_value)::int as month,
    extract(day from date_value)::int as day,
    to_char(date_value, 'TMMon') || ' ' || extract(year from date_value)::text as month_year,
    case when extract(dow from date_value) in (0,6) then true else false end as is_weekend
from date_range