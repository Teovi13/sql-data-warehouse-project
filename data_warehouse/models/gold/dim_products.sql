{#
===============================================================================
Gold model: dim_products
===============================================================================
Purpose:
    Product dimension of the star schema, one row per product (current
    version only), enriched with the ERP category data.
===============================================================================
#}

with

crm_prd_info as (
    select * from {{ ref('crm_prd_info') }}
),

erp_px_cat_g1v2 as (
    select * from {{ ref('erp_px_cat_g1v2') }}
),

final as (
    select
        -- Surrogate key from the product ID order: it shifts if a product
        -- with a lower ID is added
        row_number() over (order by pn.prd_id) as product_key,
        pn.prd_id as product_id,
        pn.prd_key as product_number,
        pn.prd_nm as product_name,
        pn.cat_id as category_id,
        pc.cat as category,
        pc.subcat as subcategory,
        pc.maintenance,
        pn.prd_cost as cost,
        pn.prd_line as product_line,
        pn.prd_start_dt as start_date
    from crm_prd_info as pn
    left join erp_px_cat_g1v2 as pc
        on pn.cat_id = pc.id
    -- Current version only: older versions have an end date
    where pn.prd_end_dt is null
)

select * from final
