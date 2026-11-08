{#
===============================================================================
Gold model: fact_sales
===============================================================================
Purpose:
    Sales fact table of the star schema, one row per product within an
    order. Replaces the business keys of product and customer with the keys
    of their dimensions: the durable keys of the current dimensions and the
    version keys of the history dimensions, for the version in force on the
    sale.
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

dim_customers_history as (
    select * from {{ ref('dim_customers_history') }}
),

dim_products_history as (
    select * from {{ ref('dim_products_history') }}
),

sales as (
    select
        *,
        -- Date used to pick the version in force on the sale: the order date
        -- or, when it is NULL, the shipping date (see version_lookup_date)
        coalesce(sls_order_dt, sls_ship_dt) as version_date
    from crm_sales_details
),

final as (
    select
        s.sls_ord_num as order_number,
        pr.product_key,
        ph.product_version_key,
        cu.customer_key,
        ch.customer_version_key,
        s.sls_order_dt as order_date,
        s.sls_ship_dt as shipping_date,
        s.sls_due_dt as due_date,
        s.sls_sales as sales_amount,
        s.sls_quantity as quantity,
        s.sls_price as price
    from sales as s
    -- LEFT JOIN by business key: a sale whose product or customer is missing
    -- keeps a NULL key
    left join dim_products as pr
        on s.sls_prd_key = pr.product_number
    left join dim_customers as cu
        on s.sls_cust_id = cu.customer_id
    -- Customer version in force at midnight of the sale date: versions are
    -- half-open (datetime2), so >= and <; the date is converted to datetime2
    -- at 00:00, no cast needed
    left join dim_customers_history as ch
        on s.sls_cust_id = ch.customer_id
        and s.version_date >= ch.valid_from
        and s.version_date < ch.valid_to
    -- Product version in force on the sale date: versions are whole days
    -- and each one ends the day before the next starts, so BETWEEN
    left join dim_products_history as ph
        on s.sls_prd_key = ph.product_number
        and s.version_date between ph.valid_from and ph.valid_to
)

select * from final
