{#
    Purpose:
        Parity check between a dbt model and its legacy counterpart. Returns
        one row per difference: rows only in the dbt model, rows only in the
        legacy relation, and a single row when the row counts differ (EXCEPT
        ignores duplicates, so it cannot catch those on its own). Columns
        come from the dbt model; exclude_columns leaves out those expected to
        differ, such as load timestamps.
        Text columns are compared with a binary collation, so differences in
        case or accents count even though the database collation ignores
        case.
#}

{% test parity_with(model, legacy, exclude_columns=[]) %}
{%- set columns = get_column_list(model, exclude_columns, case_sensitive=true) -%}
{%- set column_csv = columns | join(', ') -%}

with
only_in_dbt as (
    select {{ column_csv }} from {{ model }}
    except
    select {{ column_csv }} from {{ legacy }}
),
only_in_legacy as (
    select {{ column_csv }} from {{ legacy }}
    except
    select {{ column_csv }} from {{ model }}
),
row_counts as (
    select
        (select count(*) from {{ model }}) as dbt_rows,
        (select count(*) from {{ legacy }}) as legacy_rows
)

select 'only_in_dbt' as side, {{ column_csv }} from only_in_dbt
union all
select 'only_in_legacy' as side, {{ column_csv }} from only_in_legacy
union all
select 'row_count_mismatch' as side{% for c in columns %}, null{% endfor %}
from row_counts
where dbt_rows <> legacy_rows

{% endtest %}
