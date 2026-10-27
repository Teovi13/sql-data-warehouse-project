{#
===============================================================================
Gold model: dim_customers
===============================================================================
Purpose:
    Customer dimension of the star schema, one row per customer. Integrates
    the CRM customer data with the ERP demographics and location.
===============================================================================
#}

with

crm_cust_info as (
    select * from {{ ref('crm_cust_info') }}
),

erp_cust_az12 as (
    select * from {{ ref('erp_cust_az12') }}
),

erp_loc_a101 as (
    select * from {{ ref('erp_loc_a101') }}
),

final as (
    select
        -- Surrogate key from the customer ID order: it shifts if a customer
        -- with a lower ID is added
        row_number() over (order by ci.cst_id) as customer_key,
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
        ci.cst_create_date as create_date
    from crm_cust_info as ci
    left join erp_cust_az12 as ca
        on ci.cst_key = ca.cid
    left join erp_loc_a101 as la
        on ci.cst_key = la.cid
)

select * from final
