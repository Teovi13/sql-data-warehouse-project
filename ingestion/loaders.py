"""Load typed DataFrames into the Bronze tables of the data warehouse."""

import re

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

IDENTIFIER = r"[A-Za-z_][A-Za-z0-9_]*"
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
