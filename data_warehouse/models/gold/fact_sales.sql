{#
===============================================================================
Gold model: fact_sales
===============================================================================
Purpose:
    Sales fact table of the star schema, one row per product within an
    order. Replaces the business keys of product and customer with the
    surrogate keys of their dimensions.
===============================================================================
#}

with

crm_sales_details as (
    select * from {{ ref('crm_sales_details') }}
),

dim_customers as (
    select * from {{ ref('dim_customers') }}
),

dim_products as (
    select * from {{ ref('dim_products') }}
),

final as (
    select
        sd.sls_ord_num as order_number,
        pr.product_key,
        cu.customer_key,
        sd.sls_order_dt as order_date,
        sd.sls_ship_dt as shipping_date,
        sd.sls_due_dt as due_date,
        sd.sls_sales as sales_amount,
        sd.sls_quantity as quantity,
        sd.sls_price as price
    from crm_sales_details as sd
    -- LEFT JOIN by business key: a sale whose product or customer is missing
    --  keeps a NULL key
    left join dim_products as pr
        on sd.sls_prd_key = pr.product_number
    left join dim_customers as cu
        on sd.sls_cust_id = cu.customer_id
)

select * from final
