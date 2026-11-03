{#
    Purpose:
        Fails for values with leading or trailing spaces. Compares byte
        lengths (DATALENGTH) because SQL Server pads strings with spaces
        before comparing them, so value <> trim(value) and LEN() both miss
        trailing spaces. TRIM removes spaces only, not tabs or line breaks.
#}

{% test no_untrimmed_values(model, column_name) %}

select {{ column_name }}
from {{ model }}
where datalength({{ column_name }}) <> datalength(trim({{ column_name }}))

{% endtest %}
