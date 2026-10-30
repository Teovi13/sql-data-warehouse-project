{#
    Purpose:
        A product version cannot end before it starts. The current version
        (NULL end date) is not checked.
#}

select
    prd_id,
    prd_start_dt,
    prd_end_dt
from {{ ref('crm_prd_info') }}
where prd_end_dt < prd_start_dt
