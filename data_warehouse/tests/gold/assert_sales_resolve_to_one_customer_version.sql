/*
===============================================================================
Singular test: every dated sale resolves to exactly one customer version
===============================================================================
Purpose:
    The point-in-time join of a fact table needs exactly one customer version
    in force on each order date: none leaves the sale without a customer, two
    would duplicate it. Returns each sale with an order date that matches a
    number of versions other than one. Sales without an order date are left
    out: they cannot be placed in time (handled in fact_sales).
===============================================================================
*/

select
    s.sls_ord_num,
    s.sls_order_dt,
    s.sls_cust_id,
    count(ch.customer_version_key) as matching_versions
from {{ ref('crm_sales_details') }} as s
left join {{ ref('dim_customers_history') }} as ch
    on s.sls_cust_id = ch.customer_id
    and s.sls_order_dt >= ch.valid_from
    and s.sls_order_dt < ch.valid_to
where s.sls_order_dt is not null
group by s.sls_ord_num, s.sls_cust_id, s.sls_order_dt
having count(ch.customer_version_key) <> 1
