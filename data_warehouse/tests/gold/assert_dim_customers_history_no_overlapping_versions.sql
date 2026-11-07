/*
===============================================================================
Singular test: no overlapping versions in dim_customers_history
===============================================================================
Purpose:
    Versions are half-open periods [valid_from, valid_to): the next version
    of a customer may start exactly when the previous one ends, or later (a
    gap: the customer left the source and came back, valid with
    hard_deletes: invalidate), but never before, which would put the
    customer in two versions at once. Returns each version whose next
    version starts before it ends.
===============================================================================
*/

with

next_version as (
    select
        customer_version_key,
        customer_id,
        valid_from,
        valid_to,
        lead(valid_from) over (partition by customer_id order by valid_from) as next_start
    from {{ ref('dim_customers_history') }}
),

final as (
    select
        customer_version_key,
        customer_id,
        valid_from,
        valid_to,
        next_start
    from next_version
    where next_start is not null
        and next_start < valid_to
)

select * from final
