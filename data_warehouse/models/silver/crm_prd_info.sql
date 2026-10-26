{#
===============================================================================
Silver model: crm_prd_info
===============================================================================
Purpose:
    Product versions from the CRM, one row per version. Splits the product
    key into category ID and product number, replaces negative or missing
    costs with 0, decodes the product line and derives each version end
    date from the start of the next one.
===============================================================================
#}

with

source as (
    select * from {{ source('bronze', 'crm_prd_info') }}
),

cleaned as (
    select
        prd_id,
        prd_key,
        prd_nm,
        case
            when prd_cost is null or prd_cost < 0 then 0
            else prd_cost
        end as prd_cost,
        cast(
            case upper(trim(prd_line))
                when 'M' then 'Mountain'
                when 'R' then 'Road'
                when 'S' then 'Other Sales'
                when 'T' then 'Touring'
                else 'n/a'
            end
        as nvarchar(50)) as prd_line,
        cast(prd_start_dt as date) as prd_start_dt,
        -- A version ends the day before the next one starts; the current
        -- version has no end date. Partitioned by the full Bronze key, as
        -- in the old procedure
        cast(
            lead(prd_start_dt) over (partition by prd_key order by prd_start_dt) - 1
        as date) as prd_end_dt
    from source
),

final as (
    select
        prd_id,
        -- First 5 characters of the key, with '_' instead of '-' to match the ERP category IDs
        cast(replace(substring(prd_key, 1, 5), '-', '_') as nvarchar(50)) as cat_id,
        cast(substring(prd_key, 7, len(prd_key)) as nvarchar(50)) as prd_key,
        prd_nm,
        prd_cost,
        prd_line,
        prd_start_dt,
        prd_end_dt,
        -- Load timestamp: replaces the DEFAULT GETDATE() of the old Silver DDL
        sysdatetime() as dwh_create_date
    from cleaned
)

select * from final
