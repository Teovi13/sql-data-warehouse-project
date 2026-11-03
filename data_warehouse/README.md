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
| Quality checks that someone runs and reads | 61 data tests with a pass/fail result and an exit code; a failing quality test stops the models built on top of it |
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
- The dbt package [`dbt_utils`](https://hub.getdbt.com/dbt-labs/dbt_utils/latest/)
  1.x, installed with `dbt deps` (see [Packages](#packages)).

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
dbt deps             # installs the packages pinned in package-lock.yml
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
(9 models, 61 tests), `PASS=69 WARN=1`**. The warning is
`assert_crm_sales_details_amounts_consistent` with 3 rows: the three sales
that have neither `sales` nor `price` in the source and cannot be rebuilt
(SO54036, SO54051, SO54139). A fourth one turns the warning into an error.

Rows that fail a test are stored in the schema `dbt_dev_dbt_test__audit`; the
command output prints the query to read them.

dbt never drops a relation that the project no longer declares (a renamed or
deleted model, or the leftovers of an interrupted run). To find them in the
dev schemas, and drop them once reviewed:

```powershell
dbt run-operation list_orphan_relations                          # list only
dbt run-operation list_orphan_relations --args "{dry_run: false}" # drop (dev target only)
```

---

## Project structure

```
data_warehouse/
├── dbt_project.yml            # Folder configs (materialization, schema), test configs, vars
├── packages.yml               # dbt packages (dbt_utils)
├── package-lock.yml           # Exact package versions installed by dbt deps
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
│   ├── get_column_list.sql    # Column list of a relation (used by the parity test)
│   └── list_orphan_relations.sql  # run-operation: list or drop relations no model declares
└── tests/
    ├── generic/
    │   ├── test_parity_with.sql        # dbt model vs legacy relation
    │   └── test_no_untrimmed_values.sql # Leading or trailing spaces in text
    ├── bronze/                # Singular test on a source
    ├── silver/                # Singular tests: business rules of Silver
    └── gold/                  # Singular tests: row count of the fact table, key resolution vs legacy
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
cutover. One deliberate difference: `customer_key` and `product_key` are hashes
of the business keys (`varchar(32)`) instead of `ROW_NUMBER()` values (`bigint`),
so consumers that store or type these keys need updating at the cutover.

### Tests

| Group | Count | What they check |
|---|---|---|
| Generic, Silver | 25 | Primary keys and the keys used by the Gold joins (`unique`, `not_null`); domains of decoded columns (`accepted_values`); no leading or trailing spaces in key and name columns (`no_untrimmed_values`) |
| Generic, Gold | 18 | Unique surrogate and business keys; attributes that must never be NULL; grain of `fact_sales` (`dbt_utils.unique_combination_of_columns`); foreign keys of the fact table (`not_null` + `relationships`, because `relationships` skips NULL keys) |
| Parity | 9 | Each model against its legacy counterpart (see below) |
| Singular, Bronze | 1 | No ties on the date that `crm_cust_info` uses to keep the latest record per customer |
| Singular, Silver | 6 | Non-negative cost, date order and ranges, `sales = quantity × price` (with a threshold for the three known exceptions), birthdates in range |
| Singular, Gold | 2 | Row count of `fact_sales` against Silver; every sale resolves to the same customer and product as in the legacy warehouse |

**Untrimmed text test.** `no_untrimmed_values` compares byte lengths
(`DATALENGTH(col) <> DATALENGTH(TRIM(col))`). SQL Server pads strings with
spaces before comparing them, so `col <> TRIM(col)` (the check in
`tests/quality_checks_silver.sql`) and `LEN()` both miss trailing spaces.

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

In Gold, the surrogate keys are left out of the parity tests, because they are
hashes in dbt and `ROW_NUMBER()` values in the legacy views. What they must
still agree on is checked by `assert_fact_sales_keys_resolve_like_legacy`:
each sale, resolved through the dimensions of its own warehouse, points to the
same customer and product (business keys).

---

## Packages

[`packages.yml`](packages.yml) installs `dbt_utils` 1.x (exact version in
`package-lock.yml`). Not every `dbt_utils` macro is T-SQL: with dbt-sqlserver
1.12, `generate_surrogate_key`, `unique_combination_of_columns`,
`expression_is_true`, `accepted_range` and `not_empty_string` work, while
`at_least_one` (`LIMIT`, and a CTE inside a subquery) and `equal_rowcount`
(`GROUP BY` on a column alias) fail. Compile and run any new macro on SQL
Server before relying on it. The community shim package `tsql_utils` is not
used: its overrides are named for the Fabric adapter, which dbt-sqlserver
1.12 no longer builds on, so dbt never dispatches to them.

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
- **Surrogate keys are hashes of the business keys**
  (`dbt_utils.generate_surrogate_key`: MD5 of `cst_id` and of the product
  number). A key depends only on its own customer or product, so it never
  shifts when other rows are added, which snapshots and incremental fact
  tables need.
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

- **No history in Gold.** Silver keeps every product version, but
  `dim_products` exposes only the current one, so all sales point to the
  current version. Type 2 dimensions (dbt snapshots) are planned.
- **Trailing spaces are not compared by the parity test.** SQL Server
  ignores trailing spaces in comparisons under any collation, including the
  binary one. `no_untrimmed_values` covers the key and name columns of
  Silver; other text columns are not checked.
- **Parity needs matching column types.** If a column changes type between a
  model and its legacy relation, `parity_with` stops with a SQL Server error
  (an invalid `COLLATE` or a failed conversion) instead of listing rows.
- **Hashes of non-Latin text.** On SQL Server, `generate_surrogate_key` casts
  values to `varchar` before hashing, so characters outside the code page
  become `?`. The current business keys are numbers and ASCII codes.
- **Tie between customer records.** If two records of a customer share the
  creation date, the choice would be arbitrary; the Bronze test stops the
  build instead. The lasting fix is a source row number from the ingestion
  layer.

---

## Next steps

Model and column documentation with `dbt docs`; snapshots for history; and
the cutover: a `prod` target that builds into `silver` and `gold`, retirement
of the T-SQL procedures and of the parity tests.
