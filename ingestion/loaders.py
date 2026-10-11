"""Load typed DataFrames into Bronze tables and record the load outcomes."""

import re

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

ERROR_MESSAGE_MAX_LENGTH = 2000  # matches bronze.load_log.error_message
IDENTIFIER = r"[A-Za-z_][A-Za-z0-9_]*"
STATUS_FAILED = "FAILED"
STATUS_SUCCESS = "SUCCESS"
TABLE_NAME_PATTERN = IDENTIFIER + r"\." + IDENTIFIER


class ReconciliationError(Exception):
    """Raised when a table's row count differs from the expected one."""


def check_row_count(table_name: str, expected: int, actual: int) -> None:
    """Compare the actual row count of a table with the expected one.

    Raises:
        ReconciliationError: If the counts differ.
    """
    if expected != actual:
        raise ReconciliationError(
            f"{table_name}: expected {expected} rows, found {actual}"
        )


def load_and_log(engine: Engine, table_name: str, df: pd.DataFrame) -> None:
    """Load a table with ``load_table`` and log the outcome.

    A failed load is logged as ``STATUS_FAILED`` with the error type and
    message. If writing the log also fails, that error is raised instead; a
    successful load is already committed by then.

    Raises:
        Exception: Any error from ``load_table``, re-raised after logging it.
    """
    try:
        load_table(engine, table_name, df)
    except Exception as error:
        write_load_log(
            engine,
            table_name,
            STATUS_FAILED,
            error_message=f"{type(error).__name__}: {error}",
        )
        raise
    # Only reached on success: the except block always re-raises.
    write_load_log(engine, table_name, STATUS_SUCCESS, rows_loaded=len(df))


def load_table(engine: Engine, table_name: str, df: pd.DataFrame) -> None:
    """Replace the contents of a table with ``df`` in a single transaction.

    On any error the truncate is rolled back, so the previous data stays in
    place. The table must already exist; columns are matched by name.

    Raises:
        ValueError: If ``table_name`` is not a valid ``schema.table`` name.
        ReconciliationError: If the table's row count differs from ``len(df)``.
    """
    # Identifiers cannot be bound parameters, so validate the name before
    # it is formatted into the SQL text.
    if not re.fullmatch(TABLE_NAME_PATTERN, table_name):
        raise ValueError(f"Invalid table name: {table_name!r}")
    # to_sql wants schema and table apart (a dotted name is one identifier).
    schema, table = table_name.split(".")
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {table_name}"))
        # Reuse the connection so the insert joins the transaction.
        df.to_sql(
            name=table,
            con=connection,
            schema=schema,
            if_exists="append",
            index=False,
        )
        count_query = text(f"SELECT COUNT(*) FROM {table_name}")
        row_count = connection.execute(count_query).scalar_one()
        check_row_count(table_name, len(df), row_count)


def write_load_log(
    engine: Engine,
    table_name: str,
    status: str,
    rows_loaded: int | None = None,
    error_message: str | None = None,
) -> None:
    """Record the outcome of a load in ``bronze.load_log``.

    The row is written in its own transaction, so it survives the rollback
    of a failed load. ``status`` must be ``STATUS_SUCCESS`` or
    ``STATUS_FAILED``; the database rejects anything else. ``error_message``
    is cut to ``ERROR_MESSAGE_MAX_LENGTH`` characters.
    """
    # A message wider than the column would make this INSERT fail too.
    if error_message is not None:
        error_message = error_message[:ERROR_MESSAGE_MAX_LENGTH]
    # Bound parameters: error messages contain quotes that break an f-string.
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO bronze.load_log "
                "(table_name, status, rows_loaded, error_message) "
                "VALUES (:table_name, :status, :rows_loaded, :error_message)"
            ),
            {
                "table_name": table_name,
                "status": status,
                "rows_loaded": rows_loaded,
                "error_message": error_message,
            },
        )
