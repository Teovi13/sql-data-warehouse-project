/*
===============================================================================
Singular test: the version keys of fact_sales belong to the right product
and customer
===============================================================================
Purpose:
    relationships only checks that a version key exists in its history
    dimension. This test checks that the version belongs to the same product
    and customer as the durable keys of the sale: a version of another product
    would pass relationships but report the sale with the wrong attributes.
    Returns each sale whose version keys point to another product or customer.
===============================================================================
*/

select
    s.order_number,
    s.customer_key,
    ch.customer_key as version_customer_key,
    s.product_key,
    ph.product_key as version_product_key
from {{ ref('fact_sales') }} as s
inner join {{ ref('dim_customers_history') }} as ch
    on s.customer_version_key = ch.customer_version_key
inner join {{ ref('dim_products_history') }} as ph
    on s.product_version_key = ph.product_version_key
where s.customer_key <> ch.customer_key
    or s.product_key <> ph.product_key
