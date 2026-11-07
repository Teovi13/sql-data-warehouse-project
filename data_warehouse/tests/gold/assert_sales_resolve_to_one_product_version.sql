/*
===============================================================================
Singular test: every dated sale resolves to exactly one product version
===============================================================================
Purpose:
    The point-in-time join of a fact table needs exactly one product version
    in force on each order date: none leaves the sale without a product, two
    would duplicate it. Returns each sale with an order date that matches a
    number of versions other than one. Sales without an order date are left
    out: they cannot be placed in time (handled in fact_sales).
===============================================================================
*/

select
    s.sls_ord_num,
    s.sls_order_dt,
    s.sls_prd_key,
    count(ph.product_version_key) as matching_versions
from {{ ref('crm_sales_details') }} as s
left join {{ ref('dim_products_history') }} as ph
    on s.sls_prd_key = ph.product_number
    and s.sls_order_dt between ph.valid_from and ph.valid_to
where s.sls_order_dt is not null
group by s.sls_ord_num, s.sls_prd_key, s.sls_order_dt
having count(ph.product_version_key) <> 1
