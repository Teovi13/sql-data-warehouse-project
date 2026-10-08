"""Read the source CSV files as raw text, without cleaning anything."""

from pathlib import Path

import pandas as pd

from ingestion.config import SOURCES


def read_raw(path: Path) -> pd.DataFrame:
    """Read a CSV file as-is, with every column as a string.

    Only empty fields become NaN. Text such as ``NA``, ``null`` or ``n/a`` is
    kept as a real value: ``n/a`` is a valid code in ``cst_gndr``, and pandas
    would otherwise turn it into a null.
    """
    return pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,
        na_values=[""],
    )


def read_table(table_name: str) -> pd.DataFrame:
    """Read a source table by its name in ``SOURCES``.

    Raises:
        ValueError: If ``table_name`` is not defined in ``SOURCES``.
        FileNotFoundError: If the CSV file does not exist.
    """
    if table_name not in SOURCES:
        valid_tables = ", ".join(sorted(SOURCES))
        raise ValueError(
            f"Unknown table: {table_name!r}. Valid tables: {valid_tables}")
    path = SOURCES[table_name]
    return read_raw(path)
