{#
===============================================================================
Gold model: dim_customers_history
===============================================================================
Purpose:
    Customer dimension with history (type 2) on the CRM attributes: one row
    per version of each customer, from crm_cust_info_snapshot, joined with the
    current ERP data. Each version includes valid_from and excludes valid_to,
    so a sale finds the customer version in force on its date with
    valid_from <= date < valid_to.
===============================================================================
#}

with

crm_cust_info_snapshot as (
    select * from {{ ref('crm_cust_info_snapshot') }}
),

erp_cust_az12 as (
    select * from {{ ref('erp_cust_az12') }}
),

erp_loc_a101 as (
    select * from {{ ref('erp_loc_a101') }}
),

final as (
    select
        -- Version key: hash of the customer ID and the moment the snapshot
        -- captured the version (the original dbt_valid_from, not valid_from)
        {{ dbt_utils.generate_surrogate_key(['ci.cst_id', 'ci.dbt_valid_from']) }} as customer_version_key,
        -- Durable key: the same hash as dim_customers.customer_key, equal in
        -- every version of the customer
        {{ dbt_utils.generate_surrogate_key(['ci.cst_id']) }} as customer_key,
        ci.cst_id as customer_id,
        ci.cst_key as customer_number,
        ci.cst_firstname as first_name,
        ci.cst_lastname as last_name,
        -- n/a when the customer has no row in the ERP location table
        coalesce(la.cntry, 'n/a') as country,
        ci.cst_marital_status as marital_status,
        -- CRM is the primary source for gender; the ERP fills in when the
        -- CRM value is n/a
        case
            when ci.cst_gndr != 'n/a' then ci.cst_gndr
            else coalesce(ca.gen, 'n/a')
        end as gender,
        ca.bdate as birthdate,
        ci.cst_create_date as create_date,
        ci.dbt_valid_from as captured_at,
        case
            when ci.dbt_valid_from = min(ci.dbt_valid_from) over (partition by ci.cst_id) then cast( '{{ var("scd_start_date") }}' as datetime2(6))
            else ci.dbt_valid_from
        end as valid_from,
        ci.dbt_valid_to as valid_to,
        cast((case when ci.dbt_valid_to = '{{ var("scd_end_date") }}' then 1 else 0 end) as bit) as is_current
    from crm_cust_info_snapshot as ci
    left join erp_cust_az12 as ca
        on ci.cst_key = ca.cid
    left join erp_loc_a101 as la
        on ci.cst_key = la.cid
)

select * from final
