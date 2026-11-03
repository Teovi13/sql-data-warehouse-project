{#
    Purpose:
        Lists the relations in the dev schemas (target.schema and
        target.schema_*) that no model, seed or snapshot of the project
        declares: leftovers of renamed or deleted models, or of interrupted
        runs. dbt never drops them on its own. With dry_run=false it drops
        them, only in the dev target. Test failure tables (dbt_test__audit)
        are left alone.
    Usage:
        dbt run-operation list_orphan_relations
        dbt run-operation list_orphan_relations --args "{dry_run: false}"
#}

{% macro list_orphan_relations(dry_run=true) %}
    {%- if not dry_run and target.name != 'dev' -%}
        {{ exceptions.raise_compiler_error('list_orphan_relations only drops in the dev target') }}
    {%- endif -%}

    {%- if not execute -%}
        {{ return(none) }}
    {%- endif -%}

    {{ log('target: ' ~ target.name ~ ', schema: ' ~ target.schema ~ ', dry_run: ' ~ dry_run, info=true) }}

    {%- set expected = [] -%}
    {%- for node in graph.nodes.values() -%}
        {%- if node.resource_type in ['model', 'seed', 'snapshot'] -%}
            {%- do expected.append((node.schema ~ '.' ~ node.alias) | lower) -%}
        {%- endif -%}
    {%- endfor -%}

    {%- set tables_query -%}
        select
            TABLE_SCHEMA as table_schema,
            TABLE_NAME as table_name,
            TABLE_TYPE as table_type
        from INFORMATION_SCHEMA.TABLES
    {%- endset -%}

    {%- set tables_result = run_query(tables_query) -%}

    {%- set orphan = [] -%}
    {%- for row in tables_result.rows -%}
        {%- set schema = row['table_schema'] | lower -%}
        {%- set full_name = (row['table_schema'] ~ '.' ~ row['table_name']) | lower -%}
        {%- if (schema == target.schema | lower or schema.startswith(target.schema | lower ~ '_'))
            and not schema.endswith('dbt_test__audit')
            and full_name not in expected -%}
            {%- do orphan.append(row) -%}
        {%- endif -%}
    {%- endfor -%}

    {%- if orphan | length == 0 -%}
        {{ log('No orphan relations in ' ~ target.schema ~ ' schemas', info=true) }}
    {%- endif -%}

    {%- for row in orphan -%}
        {%- set relation = adapter.get_relation(target.database, row['table_schema'], row['table_name']) -%}

        {%- if dry_run -%}
            {{ log('Orphan (dry run, not dropped): ' ~ relation ~ ' [' ~ row['table_type'] ~ ']', info=true) }}
        {%- else -%}
            {{ log('Dropping orphan: ' ~ relation ~ ' [' ~ row['table_type'] ~ ']', info=true) }}
            {%- do adapter.drop_relation(relation) -%}
        {%- endif -%}
    {%- endfor -%}

{% endmacro %}
