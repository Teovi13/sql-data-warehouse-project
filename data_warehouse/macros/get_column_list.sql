{#
    Purpose:
        Returns the column names of a relation, quoted, in their table order,
        leaving out the ones listed in exclude_columns (case-insensitive).
        With case_sensitive=true, text columns are returned as
        "col" collate Latin1_General_BIN2 as "col", so comparisons on them
        are exact (case, accents) regardless of the database collation.
        Used by tests that compare two relations column by column.
#}

{% macro get_column_list(relation, exclude_columns=[], case_sensitive=false) %}
    {%- set excluded = exclude_columns | map('lower') | list -%}
    {%- set names = [] -%}
    {%- for column in adapter.get_columns_in_relation(relation) -%}
        {%- if column.name | lower not in excluded -%}
            {%- set quoted = adapter.quote(column.name) -%}
            {%- if case_sensitive and column.is_string() -%}
                {%- do names.append(quoted ~ ' collate Latin1_General_BIN2 as ' ~ quoted) -%}
            {%- else -%}
                {%- do names.append(quoted) -%}
            {%- endif -%}
        {%- endif -%}
    {%- endfor -%}
    {{ return(names) }}
{% endmacro %}
