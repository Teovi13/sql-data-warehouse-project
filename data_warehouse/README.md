# dbt transformation layer

A [dbt](https://docs.getdbt.com/) project that builds the **Silver** and
**Gold** layers of the warehouse as version-controlled `SELECT` models, with
data tests, model and column documentation, and type 2 history of products
and customers. Bronze is loaded outside dbt, by the
[Python ingestion layer](../README.md#python-ingestion-layer) or
`bronze.load_bronze`.

dbt is the official way to build Silver and Gold. The layers were first built
by T-SQL scripts; how the migration was proven and how to roll it back is in
[Migration and cutover](#migration-and-cutover).

---

## What changed compared to the T-SQL scripts

| T-SQL scripts | dbt |
|---|---|
| DDL scripts + `TRUNCATE`/`INSERT` procedures | One `SELECT` per model; dbt creates the table or view, and explicit `cast`s set the column types |
| Run the scripts in the order of the README | `dbt build` runs everything in dependency order (the DAG built from `ref()` and `source()`) |
| `silver.load_silver` loaded table by table: a failure left some tables new, one empty and the rest old | Each table is built aside and swapped in by renaming; a failed model keeps its previous version |
| Quality checks that someone ran and read | 83 data tests with a pass/fail result and an exit code; a failing quality test stops the models built on top of it |
| `GETDATE()` in the logic | One reference date per run (`var('reference_date')`), shared by the model and its test |
| Only the current state of each customer and product in Gold | History tables (type 2): product versions from the CRM, customer changes captured by snapshots, and a fact table that points to the version in force on each sale |

---

## Requirements

- The `DataWarehouse` database with **Bronze loaded** (steps 1 and 2 of
  [How to run this project](../README.md#how-to-run-this-project)).
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
`git add` could publish it). It has two outputs, called **targets**: `prod`
builds the official layers, `dev` builds a private copy for development.
Example with Windows authentication and a named instance:

```yaml
data_warehouse:
  target: dev                        # default: production only with --target prod
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
    prod:
      type: sqlserver
      driver: 'ODBC Driver 18 for SQL Server'
      server: 'YOUR-PC\SQLEXPRESS'
      database: DataWarehouse
      schema: dbo                    # only for objects without a custom schema (none today)
      windows_login: true
      encrypt: true
      trust_cert: true
      threads: 4
```

The target decides where each layer is built
([`macros/generate_schema_name.sql`](macros/generate_schema_name.sql)):

| Target | Silver | Gold | Snapshots | Failing test rows |
|---|---|---|---|---|
| `prod` | `silver` | `gold` | `snapshots` | `dbt_test__audit` |
| `dev` | `dbt_dev_silver` | `dbt_dev_gold` | `dbt_dev_snapshots` | `dbt_dev_dbt_test__audit` |

The default target is `dev`, so nothing reaches the official schemas without
writing `--target prod`. Sources take the database from the target, so the
same project can be built on a copy of the database (see
[Migration and cutover](#migration-and-cutover)).

Check the setup from the project folder:

```powershell
cd data_warehouse
dbt debug --target prod   # ends with "All checks passed!"
dbt deps                  # installs the packages pinned in package-lock.yml
```

---

## Running

Every dbt command runs from `data_warehouse/` with `.venv-dbt` active.

```powershell
dbt build --target prod                     # build and test everything in production, in DAG order
dbt build                                   # the same in the dev schemas
dbt build --select crm_cust_info+           # one model and everything downstream of it
dbt build --select +fact_sales              # one model and everything upstream of it
dbt build --vars "{reference_date: '2027-06-16'}"   # rebuild as of another date
dbt snapshot                                # only the snapshots (dbt build runs them too)
dbt retry                                   # rerun only what failed or was skipped in the last run
```

Expected result of `dbt build` with the included dataset: **100 nodes
(11 models, 3 snapshots, 83 tests, 3 exposures), `PASS=96 WARN=1 NO-OP=3`**.
Exposures run nothing: they are `NO-OP` when everything upstream of them
succeeded, and `SKIP` when something upstream failed. The warning is
`assert_crm_sales_details_amounts_consistent` with 3 rows: the three sales
that have neither `sales` nor `price` in the source and cannot be rebuilt
(SO54036, SO54051, SO54139). A fourth one turns the warning into an error.
The run also prints a warning about the behavior flag
`dbt_sqlserver_enable_safe_type_expansion`: it is set to `false` on purpose
(see [Design decisions](#design-decisions)), and dbt warns on every run while
a behavior flag keeps its old value.

Rows that fail a test are stored in the audit schema of the target; the
command output prints the query to read them.

The snapshots record a change only when dbt runs, so how often production is
built sets the resolution of the customer history. A regular run is two
steps: the Bronze load, then `dbt build --target prod`.

dbt never drops a relation that the project no longer declares (a renamed or
deleted model, or the leftovers of an interrupted run). To find them in the
dev schemas, and drop them once reviewed:

```powershell
dbt run-operation list_orphan_relations                          # list only
dbt run-operation list_orphan_relations --args "{dry_run: false}" # drop (dev target only)
```

The macro only looks at the schemas of the target, and refuses to drop
anything outside `dev`: the production schemas also hold objects that dbt
does not build, such as the report views of the analysis repository.

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
│   ├── generate_schema_name.sql   # Schema names per target: silver in prod, dbt_dev_silver in dev
│   └── list_orphan_relations.sql  # run-operation: list or drop relations no model declares
└── tests/
    ├── generic/
    │   ├── test_no_untrimmed_values.sql # Leading or trailing spaces in text
    │   └── test_one_current_version.sql # At most one current version per key in a snapshot
    ├── bronze/                # Singular test on a source
    ├── silver/                # Singular tests: business rules of Silver
    └── gold/                  # Singular tests: fact table vs Silver, history dimensions, version keys
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
kept working after the cutover. One deliberate difference: `customer_key`
and `product_key` are hashes of the business keys (`varchar(32)`) instead of
`ROW_NUMBER()` values (`bigint`). `fact_sales` also has two columns that the
T-SQL view did not have, `product_version_key` and `customer_version_key`
(see [History](#history-type-2)).

### Tests

| Group | Count | What they check |
|---|---|---|
| Generic, Silver | 25 | Primary keys and the keys used by the Gold joins (`unique`, `not_null`); domains of decoded columns (`accepted_values`); no leading or trailing spaces in key and name columns (`no_untrimmed_values`) |
| Generic, Gold | 36 | Unique surrogate, version and business keys; attributes that must never be NULL; grain of `fact_sales` and of the history dimensions (`dbt_utils.unique_combination_of_columns`); one current version per product and customer (`unique` with `where: is_current = 1`); foreign keys of the fact table (`not_null` + `relationships`, because `relationships` skips NULL keys) |
| Generic, snapshots | 9 | Unique version IDs (`dbt_scd_id`) and at most one current version per key (`one_current_version`) |
| Singular, Bronze | 1 | No ties on the date that `crm_cust_info` uses to keep the latest record per customer |
| Singular, Silver | 6 | Non-negative cost, date order and ranges, `sales = quantity × price` (with a threshold for the three known exceptions), birthdates in range |
| Singular, Gold | 6 | Row count of `fact_sales` against Silver; product versions without gaps or overlaps and customer versions without overlaps; every dated sale finds exactly one product and one customer version; the version keys of a sale belong to its own product and customer |

**Untrimmed text test.** `no_untrimmed_values` compares byte lengths
(`DATALENGTH(col) <> DATALENGTH(TRIM(col))`). SQL Server pads strings with
spaces before comparing them, so `col <> TRIM(col)` and `LEN()` both miss
trailing spaces.

**Tests as gates.** A test on a single model or snapshot stops everything
built on top of it when it fails: if `crm_cust_info` fails a quality test, the
snapshot does not record that data and nothing downstream is rebuilt. Tests
that read two models (such as the row count of `fact_sales` against Silver)
report but do not stop the build.

---

## History (type 2)

Silver keeps only the current state of each customer, and Gold used to keep
only the current version of each product. The history layer adds one row per
**version**, with its validity period, so that a sale can be reported with
the attributes in force when it happened.

| | Products | Customers |
|---|---|---|
| Where the history comes from | The CRM already keeps one row per product version (`prd_start_dt`), so `dim_products_history` is modeled from Silver: no snapshot | The CRM keeps only the current state, so `crm_cust_info_snapshot` captures every change from its first production run (the cutover) |
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

Every model, snapshot and column has a description, written next to its
tests in `_silver__models.yml`, `_gold__models.yml` and `_snapshots.yml`.
Texts shared by several columns are written once as doc blocks in
`models/docs/_shared__docs.md` (the load timestamp, the `'n/a'` convention,
the two surrogate keys, the snapshot columns and the date used to pick a
version) and inserted with `{{ doc('...') }}`; `models/docs/overview.md` is
the home page of the site. The site shows each model with its columns, types,
tests and SQL, and the lineage graph from the Bronze sources to the
exposures. It is the data dictionary of Silver and Gold.

**Descriptions in SQL Server.** `persist_docs`, set for every model and
snapshot in `dbt_project.yml`, writes the descriptions into the database as
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
  AND OBJECT_SCHEMA_NAME(ep.major_id) IN ('silver', 'gold', 'snapshots')
ORDER BY schema_name, object_name, ep.minor_id;
```

With the current project it returns 130 rows: 11 models and 101 of their
columns, and 3 snapshots and 15 of their columns. The descriptions are
stored as plain text, so Markdown (backticks, bold) appears as typed.

**Exposures.** [`models/_exposures.yml`](models/_exposures.yml) declares the
consumers of Gold that live outside dbt: the two report views and the
exploratory scripts of the analysis repository. dbt does not run or check
them; they appear at the end of the lineage and answer which consumers a
change affects:

```powershell
dbt ls --select dim_customers+ --resource-type exposure
```

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
- **One project, two targets.** `generate_schema_name` uses the custom
  schema as is in `prod` (and in `rehearsal`, the target used to rehearse the
  cutover on a copy) and prefixes it with the target schema anywhere else, so
  development can never write to the official layers. dbt's own
  `generate_schema_name_for_env` was not used: outside production it puts
  every model in a single schema.
- **Sources do not name a database**, so they read Bronze from the database
  of the target: the same project builds the real warehouse or a restored
  copy of it.
- **No clustered columnstore in Silver** (`as_columnstore: false`): the
  adapter's default pays off on millions of rows, not on this dataset.
- **Types are set with `cast`.** Without DDL, a column takes the type of its
  expression (a `CASE` of literals becomes `varchar(n)`), so every computed
  text column is cast to the type of the original Silver DDL.
- **`dwh_create_date` is `sysdatetime()`** in each Silver model, replacing
  the `DEFAULT GETDATE()` of the DDL.
- **Documentation lives with the code.** Descriptions sit next to the tests
  of each model, are versioned with it and are written into SQL Server on
  every build.
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
- **Logic inherited from the T-SQL procedures.** The models reproduce the
  T-SQL logic exactly, quirks included, because parity with it was the proof
  of the migration. Known quirks are documented in the models (integer
  division of `sls_price`, exact in every current row and caught by the
  amounts test if it ever is not).

---

## Migration and cutover

The layers were first built by T-SQL scripts (`silver.load_silver` and the
Gold view definitions). The migration ran both warehouses side by side:

1. **Parity.** dbt built into the dev schemas, and a parity test compared
   every dbt model with its T-SQL counterpart on each build, row by row and
   with binary text comparison, until every model matched.
2. **Rehearsal.** The database was backed up and restored as
   `DataWarehouse_rehearsal`, and the whole cutover was run there with a
   `rehearsal` target: dbt replaced the T-SQL tables and views of the copy,
   the report views of the analysis repository were refreshed, and the Gold
   of the copy was compared with the T-SQL Gold of the real database.
3. **Cutover.** On the real database: row counts recorded, a verified backup,
   `dbt build --target prod`, the dependent views refreshed, the row counts
   compared, and `silver.load_silver` dropped. The parity tests and the legacy
   sources were removed, since they would have compared each model with
   itself.

**Views that read Gold.** The report views of the analysis repository are not
built by dbt and are not schema-bound, so SQL Server keeps their old column
metadata when the Gold views change. After a change in the columns or types
of Gold, refresh them:

```sql
EXEC sp_refreshview N'gold.report_customers';
EXEC sp_refreshview N'gold.report_products';
```

To list every object that reads Silver or Gold:

```sql
SELECT DISTINCT OBJECT_SCHEMA_NAME(referencing_id) AS dependent_schema,
       OBJECT_NAME(referencing_id) AS dependent_object
FROM sys.sql_expression_dependencies
WHERE referenced_schema_name IN ('silver', 'gold');
```

**Rolling back.** Silver and Gold derive from Bronze, so the T-SQL version
can always be rebuilt from the git tag `pre-dbt-cutover`, which holds the
last commit where the T-SQL scripts were the official build
(`scripts/silver/ddl_silver.sql`, `scripts/silver/proc_load_silver.sql`,
`scripts/gold/ddl_gold.sql`). A rebuild cannot recover the snapshot history
nor `bronze.load_log`: they are kept by the database backups.

---

## Known limitations

- **Customer history starts with the first production run** (the cutover),
  and has the resolution of the runs: `dbt_valid_from` is the run that
  detected a change, and two changes between runs are recorded as one. The
  development snapshot also keeps changes simulated while building it
  (customers 34 and 12); the production snapshot started clean.
- **The ERP attributes of `dim_customers_history` are not historized yet.**
  Country, birthdate and the ERP gender are the current values in every
  version; their snapshots already collect history, to be combined with the
  CRM history later.
- **Changes in letter case or trailing spaces are not detected** by the
  snapshots: `strategy: check` compares with the case-insensitive database
  collation.
- **Two time zones.** Snapshot timestamps come from `SYSDATETIME()` (server
  local time); `reference_date` and the dbt logs use the run start in UTC.
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
- **Runs are manual.** Nothing schedules the Bronze load and the dbt build
  yet.

---

## Next steps

Schedule the Bronze load and `dbt build --target prod` with an orchestrator;
and combine the ERP snapshots with the CRM history in
`dim_customers_history`.
