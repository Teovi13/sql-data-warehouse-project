"""Run the ingestion of the Bronze tables: validate, prepare and load."""

import pandas as pd
from sqlalchemy.engine import Engine

from ingestion.config import SOURCES
from ingestion.loaders import (
    STATUS_FAILED,
    STATUS_SUCCESS,
    load_and_log,
    write_load_log,
)
from ingestion.prepare import prepare_table
from ingestion.report import run_validations
from ingestion.rules import RULES


def validate_table(table: str, rules: list) -> pd.DataFrame:
    """Run the validation rules of one table and return their report.

    Only the rules whose table is ``table`` are run. A rule that flags rows
    does not stop anything: Bronze keeps the raw data, so those rows are only
    reported. A rule that could not run (it raised an error) does stop, since
    the table would be loaded without having been checked.

    The report is the one from ``run_validations``, with one row per rule.

    Raises:
        ValueError: If ``rules`` has no rule for ``table`` (nothing is run),
            or if any rule of the table could not run.
    """
    table_rules = [rule for rule in rules if rule[0] == table]
    if not table_rules:
        raise ValueError(f"{table}: no validation rules")
    report = run_validations(table_rules)
    crashed = report[report["error"].notna()]
    if not crashed.empty:
        details = [
            f"{row.rule}({row.params}): {row.error}"
            for row in crashed.itertuples()
        ]
        raise ValueError(f"{table}: rules that could not run: {details}")
    return report


def process_table(engine: Engine, table: str) -> pd.DataFrame:
    """Validate, prepare and load one Bronze table.

    Return the validation report, so the caller can show which rules flagged
    rows. A failure while validating or preparing is logged here as
    ``STATUS_FAILED``; a failure while loading is already logged by
    ``load_and_log``. Either way the error is then raised, so each failure
    leaves exactly one row in ``bronze.load_log``. If writing the log also
    fails, that error is raised instead.

    Raises:
        Exception: Any error from ``validate_table``, ``prepare_table`` or
            ``load_and_log``, after it has been logged.
    """
    try:
        report = validate_table(table, RULES)
        typed = prepare_table(table)
    except Exception as error:  # pylint: disable=broad-exception-caught
        write_load_log(
            engine,
            table,
            STATUS_FAILED,
            error_message=f"{type(error).__name__}: {error}",
        )
        raise
    load_and_log(engine, table, typed)
    return report


def ingest_all(engine: Engine) -> pd.DataFrame:
    """Process every table in ``SOURCES`` and return a summary of the run.

    A table that fails does not stop the others: its error is stored in the
    summary and the next table is processed. The summary has one row per
    table, in load order, with the columns ``table``, ``status``
    (``STATUS_SUCCESS`` or ``STATUS_FAILED``), ``flagged`` (number of
    validation rules that flagged rows, ``<NA>`` if the table failed) and
    ``error`` (``"ErrorType: message"`` if the table failed).

    The caller decides what a failed table means, for example exiting with
    a non-zero code.
    """
    results = []
    for table in SOURCES:
        status = STATUS_SUCCESS
        flagged = None
        error = None
        try:
            report = process_table(engine, table)
        except Exception as problem:  # pylint: disable=broad-exception-caught
            status = STATUS_FAILED
            error = f"{type(problem).__name__}: {problem}"
        else:
            flagged = (report["rows"] > 0).sum()
        results.append({
            "table": table,
            "status": status,
            "flagged": flagged,
            "error": error,
        })
    columns = ["table", "status", "flagged", "error"]
    return pd.DataFrame(results, columns=columns).astype({"flagged": "Int64"})
