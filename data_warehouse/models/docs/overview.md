{% docs __overview__ %}
# Data Warehouse: dbt transformation layer

This project builds the **Silver** and **Gold** layers of a Medallion data
warehouse on SQL Server, and the snapshots that record the history of its
customers. Bronze is loaded outside dbt, by a Python ingestion layer that
reads the CRM and ERP source files.

| Layer | Built as | Content |
|---|---|---|
| Bronze | Sources (not built by dbt) | Faithful copies of the CSV source files |
| Silver | Tables | Cleaned, standardized and deduplicated data, one model per source table |
| Gold | Views | Star schema: `dim_customers`, `dim_products`, `fact_sales`, and the history dimensions `dim_customers_history`, `dim_products_history` |
| Snapshots | Tables, never dropped | Type 2 history of the customer tables of the CRM and the ERP |

**Status:** official. dbt builds the `silver`, `gold` and `snapshots`
schemas; it replaced the T-SQL scripts that built them first, after a parity
test proved that both produced the same data.

**Where to start:** open the lineage graph (bottom right button) from
`fact_sales` to see how each source table reaches the star schema.

**Conventions**

- Unknown values are `'n/a'`, never `NULL`.
- Surrogate keys are hashes of the business keys.
- Model and column names are the same as in the original T-SQL warehouse.
- History tables: the current version ends on 9999-12-31, and the first one
  starts on 1900-01-01.
{% enddocs %}
