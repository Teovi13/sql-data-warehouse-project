{#
===============================================================================
Silver model: erp_loc_a101
===============================================================================
Purpose:
    Customer location from the ERP. Removes the dash from the ID so it
    matches the CRM customer key and standardizes country names; empty or
    missing countries become 'n/a'.
===============================================================================
#}

with

source as (
    select * from {{ source('bronze', 'erp_loc_a101') }}
),

final as (
    select
        -- REPLACE can widen the type; cast back to the old Silver DDL type
        cast(replace(cid, '-', '') as nvarchar(50)) as cid,
        cast(
            case
                when trim(cntry) = 'DE' then 'Germany'
                when trim(cntry) in ('US', 'USA') then 'United States'
                when trim(cntry) = '' or cntry is null then 'n/a'
                else trim(cntry)
            end
        as nvarchar(50)) as cntry,
        -- Load timestamp: replaces the DEFAULT GETDATE() of the old Silver DDL
        sysdatetime() as dwh_create_date
    from source
)

select * from final
