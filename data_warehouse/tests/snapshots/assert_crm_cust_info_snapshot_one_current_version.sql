/*
===============================================================================
Singular test: one current version per customer in crm_cust_info_snapshot
===============================================================================
Purpose:
    A type 2 history must have exactly one current version per customer
    (dbt_valid_to = 9999-12-31). Two would mean the snapshot ran on a query
    with a duplicated unique_key. Returns each cst_id with more than one
    current version. A customer with no current version is valid: with
    hard_deletes: invalidate, it means the customer left the source.
===============================================================================
*/

select
    cst_id,
    count(*) as current_versions
from {{ ref('crm_cust_info_snapshot') }}
where dbt_valid_to = '{{ var("scd_end_date") }}'
group by cst_id
having count(*) > 1
