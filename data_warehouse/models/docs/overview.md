{% docs __overview__ %}
# Data Warehouse: dbt transformation layer

This project rebuilds the **Silver** and **Gold** layers of a Medallion data
warehouse on SQL Server. Bronze is loaded outside dbt, by a Python ingestion
layer that reads the CRM and ERP source files.

| Layer | Built as | Content |
|---|---|---|
| Bronze | Sources (not built by dbt) | Faithful copies of the CSV source files |
| Silver | Tables | Cleaned, standardized and deduplicated data, one model per source table |
| Gold | Views | Star schema: `dim_customers`, `dim_products`, `fact_sales` |

**Status:** migration in progress. dbt builds into its own development
schemas and every model is compared with the legacy T-SQL warehouse by a
parity test on each build.

**Where to start:** open the lineage graph (bottom right button) from
`fact_sales` to see how each source table reaches the star schema.

**Conventions**

- Unknown values are `'n/a'`, never `NULL`.
- Surrogate keys are hashes of the business keys.
- Model and column names are the same as in the legacy warehouse.
{% enddocs %}
