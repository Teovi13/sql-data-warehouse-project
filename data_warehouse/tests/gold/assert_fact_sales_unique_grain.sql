{#
    Purpose:
        The grain of fact_sales is one row per product within an order, so the
        pair (order_number, product_key) cannot repeat.
#}

select
    order_number,
    product_key,
    count(*) as duplicate_count
from {{ ref('fact_sales') }}
group by order_number, product_key
having count(*) > 1
