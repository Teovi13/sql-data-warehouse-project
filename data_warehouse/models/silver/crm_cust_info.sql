{#
===============================================================================
Silver model: crm_cust_info
===============================================================================
Purpose:
    Customer master data from the CRM, one row per customer. Keeps the most
    recent record of each customer (by creation date), drops rows without an
    ID, trims names and decodes marital status and gender.
===============================================================================
#}

with

source as (
    select * from {{ source('bronze', 'crm_cust_info') }}
),

with_flag as (
    select
        *,
        -- 1 = most recent record of each customer
        row_number() over (partition by cst_id order by cst_create_date desc) as flag_last
    from source
    where cst_id is not null
),

final as (
    select
        cst_id,
        cst_key,
        trim(cst_firstname) as cst_firstname,
        trim(cst_lastname) as cst_lastname,
        -- Codes and full words are both accepted; anything else becomes 'n/a'
        cast(
            case
                when upper(trim(cst_marital_status)) in ('S', 'SINGLE') then 'Single'
                when upper(trim(cst_marital_status)) in ('M', 'MARRIED') then 'Married'
                else 'n/a'
            end
        as nvarchar(50)) as cst_marital_status,
        cast(
            case
                when upper(trim(cst_gndr)) = 'F' then 'Female'
                when upper(trim(cst_gndr)) = 'M' then 'Male'
                else 'n/a'
            end
        as nvarchar(50)) as cst_gndr,
        cst_create_date,
        -- Load timestamp: replaces the DEFAULT GETDATE() of the old Silver DDL
        sysdatetime() as dwh_create_date
    from with_flag
    where flag_last = 1
)

select * from final
