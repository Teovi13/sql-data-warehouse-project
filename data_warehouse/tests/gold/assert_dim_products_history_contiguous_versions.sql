/*
===============================================================================
Singular test: versions of each product in dim_products_history are contiguous
===============================================================================
Purpose:
    Each version must start exactly one day after the previous version of
    the same product ends. A later start leaves a gap (a sale on those days
    finds no version); an earlier one is an overlap (a sale would match two
    versions). Returns each version whose next version breaks that rule.
===============================================================================
*/

with

next_version as (
    select
        product_version_key,
        product_number,
        valid_from,
        valid_to,
        lead(valid_from) over (partition by product_number order by valid_from) as next_start
    from {{ ref('dim_products_history') }}
),

final as (
    select
        product_version_key,
        product_number,
        valid_from,
        valid_to,
        next_start
    from next_version
    where next_start is not null
        and dateadd(day, -1, next_start) <> valid_to
)

select * from final
