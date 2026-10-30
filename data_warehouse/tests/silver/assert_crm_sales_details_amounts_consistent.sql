{#
    Purpose:
        Sales must be positive and equal to quantity * price, one row per
        failing sale. Three sales are known exceptions: SO54036, SO54051 and
        SO54139 have neither sales nor price in the source, so they cannot be
        rebuilt. They are tolerated as a warning; a fourth failing sale is an
        error. Limitation: if one of them is fixed and a new one appears, the
        count stays at three and the test does not fail.
#}

{{ config(severity='error', warn_if='>0', error_if='>3') }}

select
    sls_ord_num,
    sls_prd_key,
    sls_sales,
    sls_quantity,
    sls_price
from {{ ref('crm_sales_details') }}
where sls_sales != sls_quantity * sls_price
   or sls_sales is null
   or sls_quantity is null
   or sls_price is null
   or sls_sales <= 0
   or sls_quantity <= 0
   or sls_price <= 0
