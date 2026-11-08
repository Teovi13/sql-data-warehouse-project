{#
===============================================================================
Generic test: one_current_version
===============================================================================
Purpose:
    For a snapshot: each value of the column (the snapshot unique key) must
    have at most one current version (dbt_valid_to = scd_end_date). Two would
    mean the snapshot ran on a query with a duplicated unique_key. Returns
    each value with more than one current version. A value with no current
    version is valid: with hard_deletes: invalidate, it left the source.
===============================================================================
#}

{% test one_current_version(model, column_name) %}

select
    {{ column_name }},
    count(*) as current_versions
from {{ model }}
where dbt_valid_to = '{{ var("scd_end_date") }}'
group by {{ column_name }}
having count(*) > 1

{% endtest %}
