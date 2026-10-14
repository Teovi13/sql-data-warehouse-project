# Data Dictionary

This document describes the Gold layer, which is what analysts query, and the
operational table `bronze.load_log`, which records the loads made by the
Python ingestion layer.

# Gold Layer

## gold.dim_customers

Customer dimension. One row per unique customer. Combines identity data
from the CRM system with demographic data (gender, birthdate, country)
from the ERP system.

| Column | Data Type | Description |
|---|---|---|
| `customer_key` | `INT` | Surrogate key. Sequential integer generated with `ROW_NUMBER()`, used to join to `gold.fact_sales`. Has no business meaning outside the warehouse. |
| `customer_id` | `INT` | Original customer identifier from the CRM source system (`cst_id`). |
| `customer_number` | `NVARCHAR(50)` | Business/natural key for the customer (`cst_key`). Used to match customers across CRM and ERP sources. |
| `first_name` | `NVARCHAR(50)` | Customer's first name, trimmed of leading/trailing spaces. |
| `last_name` | `NVARCHAR(50)` | Customer's last name, trimmed of leading/trailing spaces. |
| `country` | `NVARCHAR(50)` | Customer's country of residence, standardized (e.g. `'DE'` → `'Germany'`, `'US'`/`'USA'` → `'United States'`). Value is `'n/a'` when the country is empty in the ERP location table or the customer has no row there (the view uses `COALESCE`), so the column is never `NULL`. |
| `marital_status` | `NVARCHAR(50)` | Customer's marital status, standardized from the CRM source: `'Single'`, `'Married'`, or `'n/a'` if not provided. |
| `gender` | `NVARCHAR(50)` | Customer's gender. Prioritizes the CRM value (`cst_gndr`) when available; falls back to the ERP value (`gen`) when CRM reports `'n/a'`. Possible values: `'Male'`, `'Female'`, `'n/a'`. |
| `birthdate` | `DATE` | Customer's date of birth, sourced from ERP. Can be `NULL` if not provided or if it was in the future in the source data (cleaned in Silver). |
| `create_date` | `DATE` | Date the customer record was originally created in the CRM source system. |

---

## gold.dim_products

Product dimension. One row per **currently active** product (historical/
retired product versions are filtered out — see note below).

| Column | Data Type | Description |
|---|---|---|
| `product_key` | `INT` | Surrogate key. Sequential integer generated with `ROW_NUMBER()`, used to join to `gold.fact_sales`. |
| `product_id` | `INT` | Original product identifier from the CRM source system (`prd_id`). |
| `product_number` | `NVARCHAR(50)` | Business/natural key for the product (`prd_key`), used to join against `sls_prd_key` in the sales data. |
| `product_name` | `NVARCHAR(50)` | Descriptive name of the product. |
| `category_id` | `NVARCHAR(50)` | Foreign key to the category reference table, extracted from the first segment of `prd_key`. |
| `category` | `NVARCHAR(50)` | High-level product category (e.g. `'Bikes'`, `'Components'`, `'Accessories'`), sourced from the ERP category reference table. |
| `subcategory` | `NVARCHAR(50)` | More specific product grouping within a category. |
| `maintenance` | `NVARCHAR(50)` | Indicates whether the product requires maintenance: `'Yes'`, `'No'`, or `'n/a'` when unknown. |
| `cost` | `INT` | Product's standard cost. `0` when the source value was `NULL` or negative (cleaned in Silver). |
| `product_line` | `NVARCHAR(50)` | Product line/family, standardized from a single-letter code: `'Mountain'`, `'Road'`, `'Other Sales'`, `'Touring'`, or `'n/a'`. |
| `start_date` | `DATE` | Date this version of the product became effective/active. |

> **Note:** `gold.dim_products` filters `WHERE prd_end_dt IS NULL`, keeping
> only the current version of each product and discarding historical
> versions tracked in Silver (slowly changing dimension history). Because
> of this filter, `prd_end_dt` itself is not exposed in Gold — every row
> shown here is, by definition, still active.

---

## gold.fact_sales

Sales fact table. One row per line item of a sales order. Grain:
**one row per product sold within one order** (`order_number` +
`product_key`).

| Column | Data Type | Description |
|---|---|---|
| `order_number` | `NVARCHAR(50)` | Business identifier of the sales order (`sls_ord_num`). Not unique by itself at this grain — an order can contain multiple product lines. |
| `product_key` | `INT` | Foreign key to `gold.dim_products.product_key`. Resolved via `product_number` (matched to `sls_prd_key`). |
| `customer_key` | `INT` | Foreign key to `gold.dim_customers.customer_key`. Resolved via `customer_id` (matched to `sls_cust_id`). |
| `order_date` | `DATE` | Date the order was placed. |
| `shipping_date` | `DATE` | Date the order was shipped. |
| `due_date` | `DATE` | Date the order was expected/due. |
| `sales_amount` | `INT` | Total monetary value of this line item. Expected to equal `quantity * price` (validated in Silver quality checks). |
| `quantity` | `INT` | Number of units of the product sold in this line item. |
| `price` | `INT` | Unit price of the product for this line item. |

---

## Relationships

```
gold.dim_customers (1) ──< (N) gold.fact_sales (N) >── (1) gold.dim_products
        customer_key ───────────── customer_key    product_key ───────────── product_key
```

- `gold.fact_sales.customer_key` → `gold.dim_customers.customer_key`
- `gold.fact_sales.product_key` → `gold.dim_products.product_key`

Both are `LEFT JOIN`s in the view definitions, so a sale with no matching
dimension row still appears in `fact_sales` with a `NULL` key rather than
being silently dropped.

---

# Operational Table

## bronze.load_log

Load history. One row per load attempt made by the Python ingestion layer
(`python -m ingestion.main`), whether it succeeded or failed. It is not source
data: nothing in Silver or Gold reads it. Its script,
`scripts/bronze/ddl_load_log.sql`, creates it only if it does not exist and
the table is never truncated, so the history is kept between runs.

| Column | Data Type | Description |
|---|---|---|
| `load_id` | `INT` | Primary key (`PK_load_log`). Sequential number generated by `IDENTITY`, so a higher value is a more recent attempt. |
| `table_name` | `NVARCHAR(257)` | Bronze table that was loaded, as `schema.table` (for example `bronze.crm_cust_info`). |
| `status` | `NVARCHAR(10)` | Outcome of the attempt: `'SUCCESS'` or `'FAILED'` (enforced by `CK_load_log_status`). |
| `rows_loaded` | `INT` | Number of rows loaded. `NULL` when the load failed. |
| `error_message` | `NVARCHAR(2000)` | Error type and message, cut to 2000 characters. `NULL` when the load succeeded. |
| `logged_at` | `DATETIME2(3)` | Moment the row was written. Filled by the database with `SYSDATETIME()` (`DF_load_log_logged_at`). |

Every attempt leaves exactly one row, and a failed load rolls back the table
it was loading, so a `FAILED` row means the previous data is still in place.
