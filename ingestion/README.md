# Python ingestion layer

Python package that loads the six Bronze tables of the data warehouse from the
CSV files in [`datasets/`](../datasets/): it validates them, converts their
types, loads each table in a transaction and records every attempt in
`bronze.load_log`.

This file is for reading or changing the code. To run it, follow step 2,
option A, of [How to run this project](../README.md#how-to-run-this-project).
Its configuration, output, exit codes and troubleshooting are in
[Python ingestion layer](../README.md#python-ingestion-layer) in the main
README.

## Tests and code style

The tests need no database, no ODBC driver and no `.env`: they replace the
database and the file reads with fakes. Run these commands from the
repository root:

```powershell
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest
.venv\Scripts\python -m pycodestyle ingestion tests
.venv\Scripts\python -m pydocstyle ingestion tests
.venv\Scripts\python -m pylint ingestion tests
```

## Modules

| Module | Responsibility |
|---|---|
| `config.py` | Source CSV of each Bronze table and the type (integer, date, text) of each column |
| `readers.py` | Reads a CSV as raw text; only empty fields become null (`n/a` stays a value) |
| `validators.py` | The `find_*` checks; each returns the rows it flags |
| `rules.py` | Catalog of rules: which check runs on which column of which table |
| `report.py` | Runs the rules and returns one report row per rule; a rule that crashes is recorded, not fatal |
| `converters.py` | Strict conversion of text to `INT` and `DATE` |
| `prepare.py` | Reads a table and converts its types; rejects it if the conversion loses data |
| `loaders.py` | Transactional load of a table, row-count check, and writing to `bronze.load_log` |
| `db.py` | Builds the SQLAlchemy engine from the environment and checks the connection |
| `pipeline.py` | Validate → prepare → load → log for one table, and for all of them |
| `main.py` | Entry point: logging, connection check, summary and exit code |

## Design decisions

- **Bronze stays raw; the rules inform.** A rule that flags rows is logged
  but never blocks a load, because cleaning belongs to Silver. What does
  stop a table: it has no rules defined, a rule could not run (the table
  would be loaded unchecked), or it cannot be prepared (next point).
- **Strict, all-or-nothing type conversion.** A value becomes an `INT` or a
  `DATE` only if it matches exactly: `2023-02-30` and `2023-1-5` are not
  dates, `1e3` and `12.0` are not integers. If converting would turn any
  value into a null, change the number of rows, or if the CSV columns do not
  match the ones in `config.py`, the table is rejected instead of being
  loaded with silent data loss.
- **One transaction per table.** `TRUNCATE`, insert and row count run
  together. On any error the previous content stays in place. Tables loaded
  before a failure stay loaded.
- **The log survives failures.** Each `bronze.load_log` row is written in its
  own transaction, so a rollback does not erase the record of the failure.
  Unlike the Bronze tables, this one is history: its script never drops it.
- **Fail closed.** An empty run or an unknown status counts as a failure
  (exit code 1), never as a success.
- **Safe defaults.** Inserts are sent in batches (`fast_executemany`),
  parameter values are hidden from error messages and logs (they are customer
  data), and table names are checked against a strict `schema.table` pattern
  before they are placed in SQL text.
- **Same result as `BULK INSERT`.** With the included dataset, the six Bronze
  tables loaded by the Python layer were compared with the ones loaded by
  `proc_load_bronze.sql`: same row counts, and no row present in one load and
  missing in the other.

## Known limitations

- Each CSV file is read completely into memory, and twice (validation, then
  preparation). That is fine for this dataset, but not for files larger than
  the available memory.
- Flagged rows are counted, not stored: the log says how many rows each rule
  flagged, not which ones. There is no quarantine table for them yet.
- Every run is a full reload: it replaces the whole content of each table.
  There are no incremental loads.
- Only the Bronze layer is loaded. CSV files must be UTF-8, and only Windows
  authentication is supported.
