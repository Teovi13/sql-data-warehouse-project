{#
===============================================================================
Silver model: crm_sales_details
===============================================================================
Purpose:
    Sales lines from the CRM, one row per product within an order. Converts
    the yyyymmdd integer dates to DATE (0 or malformed values become NULL)
    and rebuilds sales and price when they are missing, non-positive or
    inconsistent with quantity.
===============================================================================
#}

with

source as (
    select * from {{ source('bronze', 'crm_sales_details') }}
),

cleaned as (
    select
        sls_ord_num,
        sls_prd_key,
        sls_cust_id,
        -- 0 or a value that is not 8 digits long cannot be a yyyymmdd date
        case
            when sls_order_dt = 0 or len(sls_order_dt) != 8 then null
            else cast(cast(sls_order_dt as varchar(8)) as date)
        end as sls_order_dt,
        case
            when sls_ship_dt = 0 or len(sls_ship_dt) != 8 then null
            else cast(cast(sls_ship_dt as varchar(8)) as date)
        end as sls_ship_dt,
        sls_due_dt,
        -- Rebuilt as quantity * |price| when missing, non-positive or inconsistent
        case
            when sls_sales is null or sls_sales <= 0 or sls_sales != sls_quantity * abs(sls_price)
                then sls_quantity * abs(sls_price)
            else sls_sales
        end as sls_sales,
        sls_quantity,
        sls_price
    from source
),

final as (
    select
        sls_ord_num,
        sls_prd_key,
        sls_cust_id,
        sls_order_dt,
        sls_ship_dt,
        sls_due_dt,
        sls_sales,
        sls_quantity,
        -- Derived from the corrected sales; integer division, as in the old procedure
        case
            when sls_price is null or sls_price <= 0
                then sls_sales / nullif(sls_quantity, 0)
            else sls_price
        end as sls_price,
        -- Load timestamp: replaces the DEFAULT GETDATE() of the old Silver DDL
        sysdatetime() as dwh_create_date
    from cleaned
)

select * from final
