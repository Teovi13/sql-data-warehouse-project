# dbt transformation layer

A [dbt](https://docs.getdbt.com/) project that rebuilds the **Silver** and
**Gold** layers of the warehouse — today built by the T-SQL scripts in
[`scripts/`](../scripts/) — as version-controlled `SELECT` models, with data
tests, model and column documentation, an automatic parity check against the
original warehouse, and type 2 history of products and customers.

**Status: migration in progress.** dbt builds into its own development
schemas (`dbt_dev_silver`, `dbt_dev_gold`, `dbt_dev_snapshots`), next to the original `silver` and
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
| Quality checks that someone runs and reads | 93 data tests with a pass/fail result and an exit code; a failing quality test stops the models built on top of it |
| `GETDATE()` in the logic | One reference date per run (`var('reference_date')`), shared by the model and its test |
| Only the current state of each customer and product in Gold | History tables (type 2): product versions from the CRM, customer changes captured by snapshots, and a fact table that points to the version in force on each sale |

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
dbt snapshot                                # only the snapshots (dbt build runs them too)
dbt retry                                   # rerun only what failed or was skipped in the last run
```

Expected result of `dbt build` with the included dataset: **110 nodes
(11 models, 3 snapshots, 93 tests, 3 exposures), `PASS=106 WARN=1 NO-OP=3`**. Exposures
run nothing: they are `NO-OP` when everything upstream of them succeeded, and
`SKIP` when something upstream failed. The warning is
`assert_crm_sales_details_amounts_consistent` with 3 rows: the three sales
that have neither `sales` nor `price` in the source and cannot be rebuilt
(SO54036, SO54051, SO54139). A fourth one turns the warning into an error.
The run also prints a warning about the behavior flag
`dbt_sqlserver_enable_safe_type_expansion`: it is set to `false` on purpose
(see [Design decisions](#design-decisions)), and dbt warns on every run while
a behavior flag keeps its old value.

Rows that fail a test are stored in the schema `dbt_dev_dbt_test__audit`; the
command output prints the query to read them.

dbt never drops a relation that the project no longer declares (a renamed or
deleted model, or the leftovers of an interrupted run). To find them in the
dev schemas, and drop them once reviewed:

```powershell
dbt run-operation list_orphan_relations                          # list only
dbt run-operation list_orphan_relations --args "{dry_run: false}" # drop (dev target only)
```

Documentation site (see [Documentation](#documentation)):

```powershell
dbt docs generate            # site data in target/ (manifest.json, catalog.json)
dbt docs serve               # site at http://localhost:8080
dbt docs generate --static   # also target/static_index.html: one file, opens without a server
```

---

## Project structure

```
data_warehouse/
├── dbt_project.yml            # Folder configs (materialization, schema), test configs, vars, flags
├── packages.yml               # dbt packages (dbt_utils)
├── package-lock.yml           # Exact package versions installed by dbt deps
├── models/
│   ├── _exposures.yml         # Consumers of Gold outside dbt (analysis repository)
│   ├── bronze/
│   │   └── _bronze__sources.yml   # Bronze tables as sources (loaded outside dbt)
│   ├── legacy/
│   │   └── _legacy__sources.yml   # Legacy silver/gold, only for the parity tests
│   ├── silver/                # 6 models, materialized as tables
│   │   └── _silver__models.yml    # Descriptions and generic tests of Silver
│   ├── gold/                  # 5 models (star schema + 2 history dimensions), materialized as views
│   │   └── _gold__models.yml      # Descriptions and generic tests of Gold
│   └── docs/
│       ├── _shared__docs.md       # Doc blocks reused by several columns
│       └── overview.md            # Home page of the documentation site
├── snapshots/
│   └── _snapshots.yml         # 3 snapshots: type 2 history of the CRM and ERP customer tables
├── macros/
│   ├── get_column_list.sql    # Column list of a relation (used by the parity test)
│   └── list_orphan_relations.sql  # run-operation: list or drop relations no model declares
└── tests/
    ├── generic/
    │   ├── test_parity_with.sql        # dbt model vs legacy relation
    │   ├── test_no_untrimmed_values.sql # Leading or trailing spaces in text
    │   └── test_one_current_version.sql # At most one current version per key in a snapshot
    ├── bronze/                # Singular test on a source
    ├── silver/                # Singular tests: business rules of Silver
    └── gold/                  # Singular tests: fact table vs Silver and legacy, history dimensions
```

### Models

| Layer | Model | Built as | Built from |
|---|---|---|---|
| Silver | `crm_cust_info`, `crm_prd_info`, `crm_sales_details`, `erp_cust_az12`, `erp_loc_a101`, `erp_px_cat_g1v2` | Table (heap) | One Bronze source each |
| Gold | `dim_customers` | View | `crm_cust_info`, `erp_cust_az12`, `erp_loc_a101` |
| Gold | `dim_products` | View | `crm_prd_info`, `erp_px_cat_g1v2` |
| Gold | `fact_sales` | View | `crm_sales_details`, `dim_customers`, `dim_products`, `dim_customers_history`, `dim_products_history` |
| Gold | `dim_products_history` | View | `crm_prd_info`, `erp_px_cat_g1v2` |
| Gold | `dim_customers_history` | View | `crm_cust_info_snapshot`, `erp_cust_az12`, `erp_loc_a101` |
| Snapshots | `crm_cust_info_snapshot`, `erp_loc_a101_snapshot`, `erp_cust_az12_snapshot` | Table, never dropped | One Silver model each |

Model and column names are the same as in the T-SQL warehouse, so the
[analysis repository](https://github.com/Teovi13/sql-data-analysis-project)
and [`docs/data_catalog.md`](../docs/data_catalog.md) keep working after the
cutover. One deliberate difference: `customer_key` and `product_key` are hashes
of the business keys (`varchar(32)`) instead of `ROW_NUMBER()` values (`bigint`),
so consumers that store or type these keys need updating at the cutover.
`fact_sales` also has two columns that the legacy view does not have,
`product_version_key` and `customer_version_key` (see [History](#history-type-2)).

### Tests

| Group | Count | What they check |
|---|---|---|
| Generic, Silver | 25 | Primary keys and the keys used by the Gold joins (`unique`, `not_null`); domains of decoded columns (`accepted_values`); no leading or trailing spaces in key and name columns (`no_untrimmed_values`) |
| Generic, Gold | 36 | Unique surrogate, version and business keys; attributes that must never be NULL; grain of `fact_sales` and of the history dimensions (`dbt_utils.unique_combination_of_columns`); one current version per product and customer (`unique` with `where: is_current = 1`); foreign keys of the fact table (`not_null` + `relationships`, because `relationships` skips NULL keys) |
| Generic, snapshots | 9 | Unique version IDs (`dbt_scd_id`) and at most one current version per key (`one_current_version`) |
| Parity | 9 | Each model against its legacy counterpart (see below) |
| Singular, Bronze | 1 | No ties on the date that `crm_cust_info` uses to keep the latest record per customer |
| Singular, Silver | 6 | Non-negative cost, date order and ranges, `sales = quantity × price` (with a threshold for the three known exceptions), birthdates in range |
| Singular, Gold | 7 | Row count of `fact_sales` against Silver; every sale resolves to the same customer and product as in the legacy warehouse; product versions without gaps or overlaps and customer versions without overlaps; every dated sale finds exactly one product and one customer version; the version keys of a sale belong to its own product and customer |

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

## History (type 2)

Silver keeps only the current state of each customer, and Gold used to keep
only the current version of each product. The history layer adds one row per
**version**, with its validity period, so that a sale can be reported with
the attributes in force when it happened.

| | Products | Customers |
|---|---|---|
| Where the history comes from | The CRM already keeps one row per product version (`prd_start_dt`), so `dim_products_history` is modeled from Silver: no snapshot | The CRM keeps only the current state, so `crm_cust_info_snapshot` captures every change from its first run (2026-11-06) |
| Validity period | Whole days, both ends inclusive: each version ends the day before the next starts (`BETWEEN`) | `datetime2`, half-open: each version ends at the instant the next starts (`valid_from <= t < valid_to`) |
| Gaps between versions | Never (tested) | Allowed: a customer missing from the source has no current version while it is missing (`hard_deletes: invalidate`) |
| Keys | `product_key`, the same as in `dim_products`, equal in every version; `product_version_key`, hash of the product number and the start date | `customer_key`, the same as in `dim_customers`; `customer_version_key`, hash of the customer ID and the moment the snapshot captured the version |

The first version of each product and customer is valid from
`var('scd_start_date')` (1900-01-01): before the first known version, no
history was recorded, and the first known state is the best information
about the past. The current version ends at `var('scd_end_date')`
(9999-12-31). The original start is kept in `start_date` and `captured_at`.

**Snapshots.** A snapshot compares a Silver model with its previous run and
closes the version of every row whose compared columns changed
(`strategy: check`). It is state, not a derived table: it cannot be rebuilt
from Bronze, so it is never dropped, and its history starts on its first run.
Only business attributes are compared: never `dwh_create_date`, which changes
on every build, nor values that depend on the run date (the ERP birthdate,
which Silver nulls when it is in the future). `erp_loc_a101_snapshot` and
`erp_cust_az12_snapshot` collect the history of the ERP country and gender;
no model uses them yet.

**The fact table.** Each sale carries two keys per dimension (Kimball type 7):
the durable key (`product_key`, `customer_key`) joins the current dimensions,
and the version key joins the history dimensions with the version in force
on the sale date. 16 of the 220 sales point to an older product version. 34
sales have no valid order date: the version is picked with the shipping date
(1 to 10 days after the order in the rest of the sales), and `order_date`
stays NULL.

---

## Documentation

Every model and column has a description, written next to its tests in
`_silver__models.yml` and `_gold__models.yml`. Texts shared by several columns
are written once as doc blocks in `models/docs/_shared__docs.md` (the load
timestamp, the `'n/a'` convention, the two surrogate keys, the snapshot
columns and the date used to pick a version) and inserted
with `{{ doc('...') }}`; `models/docs/overview.md` is the home page of the
site. The site shows each model with its columns, types, tests and SQL, and
the lineage graph from the Bronze sources to the exposures.

**Descriptions in SQL Server.** `persist_docs`, set for every model and snapshot in
`dbt_project.yml`, writes the descriptions into the database as
`MS_Description` extended properties each time a model is built. They are
visible in SSMS (object Properties → Extended Properties) and in any tool
that reads them:

```sql
SELECT OBJECT_SCHEMA_NAME(ep.major_id)  AS schema_name,
       OBJECT_NAME(ep.major_id)         AS object_name,
       c.name                           AS column_name,  -- NULL: the model itself
       CAST(ep.value AS NVARCHAR(4000)) AS description
FROM sys.extended_properties AS ep
LEFT JOIN sys.columns AS c
    ON c.object_id = ep.major_id
   AND c.column_id = ep.minor_id
WHERE ep.name = 'MS_Description'
  AND OBJECT_SCHEMA_NAME(ep.major_id) IN ('dbt_dev_silver', 'dbt_dev_gold', 'dbt_dev_snapshots')
ORDER BY schema_name, object_name, ep.minor_id;
```

With the current project it returns 130 rows: 11 models and 101 of their
columns, and 3 snapshots and 15 of their columns. The
descriptions are stored as plain text, so Markdown (backticks, bold) appears
as typed.

**Exposures.** [`models/_exposures.yml`](models/_exposures.yml) declares the
consumers of Gold that live outside dbt: the two report views and the
exploratory scripts of the analysis repository. dbt does not run or check
them; they appear at the end of the lineage and answer which consumers a
change affects:

```powershell
dbt ls --select dim_customers+ --resource-type exposure
```

Until the cutover those consumers still read the legacy `gold` views, not the
dbt models.

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
- **Documentation lives with the code.** Descriptions sit next to the tests
  of each model, are versioned with it and are written into SQL Server on
  every build. Until the cutover, [`docs/data_catalog.md`](../docs/data_catalog.md)
  remains the dictionary of the official Gold views.
- **Surrogate keys are hashes of the business keys**
  (`dbt_utils.generate_surrogate_key`: MD5 of `cst_id` and of the product
  number). A key depends only on its own customer or product, so it never
  shifts when other rows are added, which snapshots and incremental fact
  tables need.
- **One reference date per run.** "Birthdate in the future" is evaluated
  against `var('reference_date')` (default: the run start date, in UTC), used
  by both the model and its test, and can be fixed with `--vars` to reproduce
  any date.
- **History is modeled from the source when the source keeps it.** Product
  versions come from the CRM; a snapshot would duplicate them and miss every
  version older than its first run. Snapshots are for sources that keep only
  the current state.
- **Snapshots read Silver, not Bronze.** A snapshot needs a unique key, and
  Bronze has duplicated customer IDs; Silver deduplicates them. The cost: a
  change in the Silver logic is recorded as a change of the affected rows.
- **Validity bounds are variables** (`scd_start_date`, `scd_end_date`), used
  by the snapshots, the history dimensions and their tests. `scd_end_date`
  must never change once a snapshot has data.
- **Column types of the snapshots are never widened across type families
  automatically** (`flags.dbt_sqlserver_enable_safe_type_expansion: false`):
  on a table that cannot be rebuilt, such a change in Silver must be
  reviewed.
- **Logic kept identical to the T-SQL procedures** until the cutover, so
  parity can prove the migration. Known quirks are documented in the models
  (integer division of `sls_price`, exact in every current row and caught by
  the amounts test if it ever is not).

---

## Known limitations

- **Customer history starts on 2026-11-06**, the first snapshot run, and
  has the resolution of the runs: `dbt_valid_from` is the run that detected a
  change, and two changes between runs are recorded as one. The development
  snapshot also keeps changes simulated while building it (customers 34 and
  12); the production snapshot will start clean.
- **The ERP attributes of `dim_customers_history` are not historized yet.**
  Country, birthdate and the ERP gender are the current values in every
  version; their snapshots already collect history, to be combined with the
  CRM history later.
- **Changes in letter case or trailing spaces are not detected** by the
  snapshots: `strategy: check` compares with the case-insensitive database
  collation.
- **Two time zones.** Snapshot timestamps come from `SYSDATETIME()` (server
  local time); `reference_date` and the dbt logs use the run start in UTC.
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
- **Descriptions are not tested.** dbt fails on a `doc()` block that does
  not exist, but not on a description placed on the wrong column or on Jinja
  left half-deleted, which is then stored as text. After editing
  descriptions, this query must return no rows:
  ```sql
  SELECT OBJECT_SCHEMA_NAME(major_id) AS schema_name,
         OBJECT_NAME(major_id)        AS object_name,
         minor_id
  FROM sys.extended_properties
  WHERE name = 'MS_Description'
    AND (CAST(value AS NVARCHAR(4000)) LIKE '%{{%'
      OR CAST(value AS NVARCHAR(4000)) LIKE '%}}%'
      OR CAST(value AS NVARCHAR(4000)) LIKE '%{[%]%');
  ```
- **Tie between customer records.** If two records of a customer share the
  creation date, the choice would be arbitrary; the Bronze test stops the
  build instead. The lasting fix is a source row number from the ingestion
  layer.

---

## Next steps

Combine the ERP snapshots with the CRM history in `dim_customers_history`;
and the cutover: a `prod` target that builds into `silver`, `gold` and
`snapshots`, retirement of the T-SQL procedures and of the parity tests, and
the dbt documentation as the only data dictionary of Gold.
