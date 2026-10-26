{#
===============================================================================
Silver model: erp_cust_az12
===============================================================================
Purpose:
    Customer demographics from the ERP. Removes the 'NAS' prefix so the ID
    matches the CRM customer key, nulls birthdates in the future and
    standardizes gender.
===============================================================================
#}

with

source as (
    select * from {{ source('bronze', 'erp_cust_az12') }}
),

final as (
    select
        cast(
            case
                when left(cid, 3) = 'NAS' then substring(cid, 4, len(cid))
                else cid
            end
        as nvarchar(50)) as cid,
        -- Depends on the run date: a birthdate after today becomes NULL
        case
            when bdate > getdate() then null
            else bdate
        end as bdate,
        cast(
            case
                when upper(trim(gen)) in ('M', 'MALE') then 'Male'
                when upper(trim(gen)) in ('F', 'FEMALE') then 'Female'
                else 'n/a'
            end
        as nvarchar(20)) as gen,
        -- Load timestamp: replaces the DEFAULT GETDATE() of the old Silver DDL
        sysdatetime() as dwh_create_date
    from source
)

select * from final
