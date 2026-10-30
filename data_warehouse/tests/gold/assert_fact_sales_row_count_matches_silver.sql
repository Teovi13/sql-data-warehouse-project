{#
    Purpose:
        Every sale in crm_sales_details must appear exactly once
        in fact_sales.
        The dimension joins are LEFT JOINs on unique keys, so a
        different count
        means a dimension key is duplicated or the model filters
        sales.
#}

select
    s.silver_rows,
    f.gold_rows
from (select count(*) as silver_rows from {{ ref('crm_sales_details') }}) as s
cross join (select count(*) as gold_rows from {{ ref('fact_sales') }}) as f
where s.silver_rows <> f.gold_rows
