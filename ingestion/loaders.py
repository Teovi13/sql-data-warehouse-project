"""Load typed DataFrames into the Bronze tables of the data warehouse."""

import re

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

IDENTIFIER = r"[A-Za-z_][A-Za-z0-9_]*"
TABLE_NAME_PATTERN = IDENTIFIER + r"\." + IDENTIFIER


def load_table(engine: Engine, table_name: str, df: pd.DataFrame) -> None:
    """Replace the contents of a table with ``df`` in a single transaction.

    A failed insert rolls the truncate back, so the previous data stays in
    place. The table must already exist; columns are matched by name.

    Raises:
        ValueError: If ``table_name`` is not a valid ``schema.table`` name.
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
