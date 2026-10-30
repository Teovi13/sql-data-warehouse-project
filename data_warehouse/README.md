# dbt transformation layer

A [dbt](https://docs.getdbt.com/) project that rebuilds the **Silver** and
**Gold** layers of the warehouse — today built by the T-SQL scripts in
[`scripts/`](../scripts/) — as version-controlled `SELECT` models, with data
tests and an automatic parity check against the original warehouse.

**Status: migration in progress.** dbt builds into its own development
schemas (`dbt_dev_silver`, `dbt_dev_gold`), next to the original `silver` and
`gold`, which are still the official layers. Every dbt model is compared row
by row with its legacy counterpart on each build; the cutover (dbt writing to
`silver` and `gold`, and the T-SQL procedures retired) comes later.

---

## What changes compared to the T-SQL scripts

| T-SQL scripts | dbt |
|---|---|
| DDL scripts + `TRUNCATE`/`INSERT` procedures | One `SELECT` per model; dbt creates the table or view, and explicit `cast`s set the column types |
| Run the scripts in the order of the README | `dbt build` runs everything in dependency order (the DAG built from `ref()` and `source()`) |
| `silver.load_silver` loads table by table: a failure leaves some tables new, one empty and the rest old | Each table is built aside and swapped in by renaming; a failed model keeps its previous version |
| Quality checks that someone runs and reads | 54 data tests with a pass/fail result and an exit code; a failing quality test stops the models built on top of it |
| `GETDATE()` in the logic | One reference date per run (`var('reference_date')`), shared by the model and its test |

---

## Requirements

- The `DataWarehouse` database with **Bronze loaded** (by the
  [Python ingestion layer](../README.md#python-ingestion-layer) or
  `bronze.load_bronze`).
- While the migration lasts, the **legacy Silver and Gold built** too
  (`silver.load_silver` and `scripts/gold/ddl_gold.sql`): the parity tests
  compare against them.
- SQL Server 2017 or later, and the Microsoft ODBC Driver 18 for SQL Server.
- Python 3.10 or later (developed with 3.13).
- **dbt Core 1.12** with the community adapter `dbt-sqlserver` 1.12. dbt v2
  (the Fusion engine, now the default `pip install dbt`) does not support
  SQL Server yet, so the versions are pinned in
  [`requirements-dbt.txt`](../requirements-dbt.txt).

---

## Setup

From the repository root, in PowerShell. dbt gets its own virtual
environment, separate from the one of the ingestion layer, so their
dependencies never clash:

```powershell
py -3.13 -m venv .venv-dbt
.venv-dbt\Scripts\Activate.ps1
python -m pip install -r requirements-dbt.txt
dbt --version        # Core 1.12.x, plugin sqlserver 1.12.x
```

Connection settings live outside the repository, in
`%USERPROFILE%\.dbt\profiles.yml` (never inside `data_warehouse/`, where a
`git add` could publish it). Example with Windows authentication and a named
instance:

```yaml
data_warehouse:
  target: dev
  outputs:
    dev:
      type: sqlserver
      driver: 'ODBC Driver 18 for SQL Server'
      server: 'YOUR-PC\SQLEXPRESS'   # single quotes: the backslash stays literal
      database: DataWarehouse
      schema: dbt_dev
      windows_login: true
      encrypt: true
      trust_cert: true               # local self-signed certificate only
      threads: 4
```

Check the setup from the project folder:

```powershell
cd data_warehouse
dbt debug            # ends with "All checks passed!"
```

---

## Running

Every dbt command runs from `data_warehouse/` with `.venv-dbt` active.

```powershell
dbt build                                   # build and test everything, in DAG order
dbt build --select crm_cust_info+           # one model and everything downstream of it
dbt build --select +fact_sales              # one model and everything upstream of it
dbt test  --select test_name:parity_with    # only the parity checks
dbt build --vars "{reference_date: '2027-06-16'}"   # rebuild as of another date
```

Expected result of `dbt build` with the included dataset: **63 nodes
(9 models, 54 tests), `PASS=62 WARN=1`**. The warning is
`assert_crm_sales_details_amounts_consistent` with 3 rows: the three sales
that have neither `sales` nor `price` in the source and cannot be rebuilt
(SO54036, SO54051, SO54139). A fourth one turns the warning into an error.

Rows that fail a test are stored in the schema `dbt_dev_dbt_test__audit`; the
command output prints the query to read them.

---

## Project structure

```
data_warehouse/
├── dbt_project.yml            # Folder configs (materialization, schema), test configs, vars
├── models/
│   ├── bronze/
│   │   └── _bronze__sources.yml   # Bronze tables as sources (loaded outside dbt)
│   ├── legacy/
│   │   └── _legacy__sources.yml   # Legacy silver/gold, only for the parity tests
│   ├── silver/                # 6 models, materialized as tables
│   │   └── _silver__models.yml    # Generic tests of Silver
│   └── gold/                  # 3 models (star schema), materialized as views
│       └── _gold__models.yml      # Generic tests of Gold
├── macros/
│   └── get_column_list.sql    # Column list of a relation (used by the parity test)
└── tests/
    ├── generic/
    │   └── test_parity_with.sql   # Custom generic test: dbt model vs legacy relation
    ├── bronze/                # Singular test on a source
    ├── silver/                # Singular tests: business rules of Silver
    └── gold/                  # Singular tests: grain and row count of the fact table
```

### Models

| Layer | Model | Built as | Built from |
|---|---|---|---|
| Silver | `crm_cust_info`, `crm_prd_info`, `crm_sales_details`, `erp_cust_az12`, `erp_loc_a101`, `erp_px_cat_g1v2` | Table (heap) | One Bronze source each |
| Gold | `dim_customers` | View | `crm_cust_info`, `erp_cust_az12`, `erp_loc_a101` |
| Gold | `dim_products` | View | `crm_prd_info`, `erp_px_cat_g1v2` |
| Gold | `fact_sales` | View | `crm_sales_details`, `dim_customers`, `dim_products` |

Model and column names are the same as in the T-SQL warehouse, so Power BI,
the [analysis repository](https://github.com/Teovi13/sql-data-analysis-project)
and [`docs/data_catalog.md`](../docs/data_catalog.md) keep working after the
cutover.

### Tests

| Group | Count | What they check |
|---|---|---|
| Generic, Silver | 19 | Primary keys and the keys used by the Gold joins (`unique`, `not_null`); domains of decoded columns (`accepted_values`) |
| Generic, Gold | 17 | Unique surrogate and business keys; attributes that must never be NULL; foreign keys of the fact table (`not_null` + `relationships`, because `relationships` skips NULL keys) |
| Parity | 9 | Each model against its legacy counterpart (see below) |
| Singular, Bronze | 1 | No ties on the date that `crm_cust_info` uses to keep the latest record per customer |
| Singular, Silver | 6 | Non-negative cost, date order and ranges, `sales = quantity × price` (with a threshold for the three known exceptions), birthdates in range |
| Singular, Gold | 2 | Grain of `fact_sales` and its row count against Silver |

**Parity test.** `parity_with` returns one row per difference between a dbt
model and its legacy relation: rows only in dbt, rows only in the legacy
relation, and one row when the row counts differ (`EXCEPT` ignores
duplicates). Columns are read from the model at run time, so new columns are
included automatically; load timestamps (`dwh_create_date`) are excluded.
Text columns are compared with `COLLATE Latin1_General_BIN2`: the database
collation is case-insensitive, and without it a change such as `'Yes'` to
`'YES'` would pass unnoticed. Parity tests report but do not stop the build:
they depend on the model and on a legacy source, so dbt does not use them as
a gate for downstream models (quality tests on a single model do).

---

## Design decisions

- **Bronze is a source, not a seed.** It is loaded by the Python layer; seeds
  are meant for small reference tables kept in git.
- **Silver as tables, Gold as views**, as in the T-SQL warehouse. Silver
  holds the heavy logic and is read by several Gold views; Gold views always
  reflect the last Silver build.
- **No clustered columnstore in Silver** (`as_columnstore: false`): the
  adapter's default pays off on millions of rows, not on this dataset.
- **Types are set with `cast`.** Without DDL, a column takes the type of its
  expression (a `CASE` of literals becomes `varchar(n)`), so every computed
  text column is cast to the type of the original Silver DDL.
- **`dwh_create_date` is `sysdatetime()`** in each Silver model, replacing
  the `DEFAULT GETDATE()` of the DDL.
- **One reference date per run.** "Birthdate in the future" is evaluated
  against `var('reference_date')` (default: the run start date, in UTC), used
  by both the model and its test, and can be fixed with `--vars` to reproduce
  any date.
- **Logic kept identical to the T-SQL procedures** until the cutover, so
  parity can prove the migration. Known quirks are documented in the models
  (integer division of `sls_price`, exact in every current row and caught by
  the amounts test if it ever is not).

---

## Known limitations

- **Surrogate keys from `ROW_NUMBER()`.** `customer_key` and `product_key`
  shift if a customer or product with a lower ID is added. Kept for parity;
  to be replaced by hashed business keys.
- **No history in Gold.** Silver keeps every product version, but
  `dim_products` exposes only the current one, so all sales point to the
  current version. Type 2 dimensions (dbt snapshots) are planned.
- **Trailing spaces are not compared.** SQL Server ignores trailing spaces in
  comparisons under any collation, including the binary one of the parity
  test.
- **Tie between customer records.** If two records of a customer share the
  creation date, the choice would be arbitrary; the Bronze test stops the
  build instead. The lasting fix is a source row number from the ingestion
  layer.

---

## Next steps

Hashed surrogate keys and reusable macros; model and column documentation
with `dbt docs`; snapshots for history; and the cutover: a `prod` target that
builds into `silver` and `gold`, retirement of the T-SQL procedures and of
the parity tests.
