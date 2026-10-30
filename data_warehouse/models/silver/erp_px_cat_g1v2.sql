{#
===============================================================================
Silver model: erp_px_cat_g1v2
===============================================================================
Purpose:
    Product category reference from the ERP. Standardizes the maintenance
    flag; category and subcategory pass through unchanged.
===============================================================================
#}

with

source as (
    select * from {{ source('bronze', 'erp_px_cat_g1v2') }}
),

final as (
    select
        id,
        cat,
        subcat,
        -- Case and spacing vary in the source; anything else becomes 'n/a'.
        -- Cast to the type of the old Silver DDL (a CASE of literals is varchar(3))
        cast(
            case upper(trim(maintenance))
                when 'YES' then 'Yes'
                when 'NO' then 'No'
                else 'n/a'
            end
        as nvarchar(50)) as maintenance,
        -- Load timestamp: replaces the DEFAULT GETDATE() of the old Silver DDL
        sysdatetime() as dwh_create_date
    from source
)

select * from final
