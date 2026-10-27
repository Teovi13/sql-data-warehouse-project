{#
    Purpose:
        An order cannot be placed after it was shipped or after it was due.
        Orders with a missing date (NULL) are not checked.
#}

select
    sls_ord_num,
    sls_prd_key,
    sls_order_dt,
    sls_ship_dt,
    sls_due_dt
from {{ ref('crm_sales_details') }}
where sls_order_dt > sls_ship_dt
   or sls_order_dt > sls_due_dt
