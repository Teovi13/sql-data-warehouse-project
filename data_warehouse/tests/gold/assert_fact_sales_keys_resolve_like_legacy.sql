{#
    Purpose:
        The surrogate keys of Gold are hashes in dbt and ROW_NUMBER values in
        the legacy warehouse, so the parity tests of Gold leave them out. This
        test checks what they must still agree on: each sale, resolved through
        the dimensions of its own warehouse, points to the same customer and
        product (business keys). Remove it, with the parity tests, at the
        cutover.
#}

with

dbt_side as (
    select
        s.order_number,
        c.customer_id,
        p.product_number
    from {{ ref('fact_sales') }} as s
    left join {{ ref('dim_customers') }} as c
        on s.customer_key = c.customer_key
    left join {{ ref('dim_products') }} as p
        on s.product_key = p.product_key
),

legacy_side as (
    select
        s.order_number,
        c.customer_id,
        p.product_number
    from {{ source('legacy_gold', 'fact_sales') }} as s
    left join {{ source('legacy_gold', 'dim_customers') }} as c
        on s.customer_key = c.customer_key
    left join {{ source('legacy_gold', 'dim_products') }} as p
        on s.product_key = p.product_key
),

only_in_dbt as (
    select * from dbt_side
    except
    select * from legacy_side
),

only_in_legacy as (
    select * from legacy_side
    except
    select * from dbt_side
)

select 'only_in_dbt' as side, * from only_in_dbt
union all
select 'only_in_legacy' as side, * from only_in_legacy
