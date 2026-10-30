{#
    Purpose:
        Product cost cannot be negative. Silver replaces negative and missing
        costs with 0, so any row here means that rule was lost.
#}

select
    prd_id,
    prd_cost
from {{ ref('crm_prd_info') }}
where prd_cost < 0
