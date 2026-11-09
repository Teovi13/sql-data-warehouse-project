{#
===============================================================================
Macro: generate_schema_name
===============================================================================
Purpose:
    Overrides how dbt names the schema of each model, snapshot and test audit
    table. In the prod target, the custom schema is used as is (silver, gold,
    snapshots), so dbt builds the official layers. In any other target, the
    default behavior is kept, <target schema>_<custom schema> (for example
    dbt_dev_silver), so development never touches the official schemas.
===============================================================================
#}

{% macro generate_schema_name(custom_schema_name, node) %}

{%- if target.name in ['prod', 'rehearsal'] and custom_schema_name is not none -%}
    {{ custom_schema_name | trim }}
{%- else -%}
    {{ default__generate_schema_name(custom_schema_name, node) }}
{%- endif -%}
{% endmacro %}
