{% docs dwh_create_date %}
Load timestamp: when this row was written by the last dbt build of the model
(`sysdatetime()`). Every row of a build gets the same value. It replaces the
`DEFAULT GETDATE()` of the legacy Silver DDL and is excluded from the parity
tests, because it always differs from the legacy tables.
{% enddocs %}

{% docs unknown_value %}
Unknown values are stored as the text `'n/a'`, never as `NULL`, so that every
`GROUP BY` and Power BI slicer shows them as one explicit group.
{% enddocs %}

{% docs customer_key %}
Surrogate key of the customer: MD5 hash (32 hexadecimal characters) of the CRM
customer ID, built with `dbt_utils.generate_surrogate_key`. It depends only on
the customer itself, so it never changes when other customers are added or
removed. In the legacy warehouse it was a `ROW_NUMBER()` integer.
{% enddocs %}

{% docs product_key %}
Surrogate key of the product: MD5 hash (32 hexadecimal characters) of the
product number, built with `dbt_utils.generate_surrogate_key`. It depends only
on the product itself, so it never changes when other products are added or
removed. In the legacy warehouse it was a `ROW_NUMBER()` integer.
{% enddocs %}

{% docs snapshot_scd_id %}
Unique ID of the version: hash of the snapshot unique key and the run that
captured it.
{% enddocs %}

{% docs snapshot_valid_from %}
Start of the version: the run that captured it.
{% enddocs %}

{% docs snapshot_valid_to %}
End of the version: the run that saw it change or disappear. 9999-12-31 for
the current version.
{% enddocs %}

{% docs snapshot_updated_at %}
Run that captured the version (the same as dbt_valid_from with the check
strategy).
{% enddocs %}
