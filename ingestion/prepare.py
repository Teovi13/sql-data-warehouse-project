"""Prepare a Bronze table for loading: read its CSV and convert types."""

import pandas as pd

from ingestion.config import COLUMN_TYPES
from ingestion.converters import convert_types
from ingestion.readers import read_table


def find_changed_nulls(
    raw: pd.DataFrame,
    typed: pd.DataFrame,
    columns: list[str],
) -> dict[str, tuple[int, int]]:
    """Return the columns whose null count differs between two DataFrames.

    Each column maps to ``(nulls_before, nulls_after)``. The result is empty
    when no count changed. ``raw`` and ``typed`` must both have ``columns``.
    """
    nulls_before = raw[columns].isna().sum()
    nulls_after = typed[columns].isna().sum()
    changed = {}
    for column in columns:
        if nulls_before[column] != nulls_after[column]:
            changed[column] = (
                int(nulls_before[column]),
                int(nulls_after[column]),
            )
    return changed


def prepare_table(table: str) -> pd.DataFrame:
    """Read a table's CSV and return it converted to its Bronze types.

    The integer and date columns come from ``COLUMN_TYPES``; the rest stay
    as text. Raise ``ValueError`` if ``table`` is not in the catalog (before
    any file is read) or if the conversion adds nulls to a converted column
    or changes the number of rows.
    """
    if table not in COLUMN_TYPES:
        raise ValueError(f"{table} is not in COLUMN_TYPES")
    catalog = COLUMN_TYPES[table]
    raw = read_table(table)
    typed = convert_types(
        raw,
        integer_columns=catalog["integer"],
        date_columns=catalog["date"],
    )
    converted_columns = catalog["integer"] + list(catalog["date"])
    changed = find_changed_nulls(raw, typed, converted_columns)
    if changed or len(raw) != len(typed):
        rows = f"{len(raw)} -> {len(typed)}"
        raise ValueError(
            f"{table}: conversion lost data, rows {rows}, nulls {changed}"
        )
    return typed
