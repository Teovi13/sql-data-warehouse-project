{#
    Purpose:
        crm_cust_info keeps the most recent record of each customer by
        cst_create_date. Two records of the same customer with the same
        creation date make that choice arbitrary (the result could change
        between runs), so the build stops before Silver is built.
        Long-term fix: a source row number added by the ingestion layer.
#}

select
    cst_id,
    cst_create_date,
    count(*) as n_records
from {{ source('bronze', 'crm_cust_info') }}
where cst_id is not null
group by cst_id, cst_create_date
having count(*) > 1
