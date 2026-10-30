{#
    Purpose:
        Order, ship and due dates must fall between 1900-01-01 and
        2050-01-01. Missing dates (NULL) are not checked.
#}

select
    sls_ord_num,
    sls_prd_key,
    sls_order_dt,
    sls_ship_dt,
    sls_due_dt
from {{ ref('crm_sales_details') }}
where sls_order_dt not between '1900-01-01' and '2050-01-01'
   or sls_ship_dt  not between '1900-01-01' and '2050-01-01'
   or sls_due_dt   not between '1900-01-01' and '2050-01-01'
