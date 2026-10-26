{#
===============================================================================
Silver model: erp_px_cat_g1v2
===============================================================================
Purpose:
    Product category reference from the ERP. Standardizes the maintenance
    flag; category and subcategory pass through unchanged.
===============================================================================
#}

select
    id,
    cat,
    subcat,
    -- Case and spacing vary in the source; anything else becomes 'n/a'
    case upper(trim(maintenance))
        when 'YES' then 'Yes'
        when 'NO' then 'No'
        else 'n/a'
    end as maintenance
from {{ source('bronze', 'erp_px_cat_g1v2') }}
