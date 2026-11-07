{#
===============================================================================
Gold model: dim_products_history
===============================================================================
Purpose:
    Product dimension with history (type 2): one row per version of each
    product, taken from the CRM product versions, with the validity period of
    each version so that a sale can be joined to the version in force on its
    order date. dim_products keeps only the current versions.
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
        -- Version key: hash of the product number and the start date of the
        -- version, so each version keeps its key whatever the CRM IDs are
        {{ dbt_utils.generate_surrogate_key(['pn.prd_key', 'pn.prd_start_dt']) }} as product_version_key,
        -- Durable key: the same hash as dim_products.product_key, equal in
        -- every version of the product
        {{ dbt_utils.generate_surrogate_key(['pn.prd_key']) }} as product_key,
        pn.prd_id as product_id,
        pn.prd_key as product_number,
        pn.prd_nm as product_name,
        pn.cat_id as category_id,
        pc.cat as category,
        pc.subcat as subcategory,
        pc.maintenance,
        pn.prd_cost as cost,
        pn.prd_line as product_line,
        pn.prd_start_dt as start_date,
        case
            when pn.prd_start_dt = min(pn.prd_start_dt) over (partition by pn.prd_key) then cast('{{ var("scd_start_date") }}' as date)
            else pn.prd_start_dt
        end as valid_from,
        coalesce(pn.prd_end_dt, cast('{{ var("scd_end_date") }}' as date)) as valid_to,
        cast((case when pn.prd_end_dt is null then 1 else 0 end) as bit) as is_current
    from crm_prd_info as pn
    left join erp_px_cat_g1v2 as pc
        on pn.cat_id = pc.id
)

select * from final
