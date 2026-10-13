"""Prepare a Bronze table for loading: read its CSV and convert types."""

from collections import Counter

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


def find_column_problems(
    csv_columns: list[str],
    catalog: dict,
) -> dict[str, list[str]]:
    """Compare the columns of a CSV with the columns of its catalog entry.

    The catalog columns (integer, date and text together) are compared with
    ``csv_columns``. The result has three sorted lists: ``not_in_catalog``
    (in the CSV but not in the catalog), ``not_in_csv`` (in the catalog but
    not in the CSV) and ``repeated`` (listed more than once in the catalog).
    All three are empty when the catalog matches the CSV.
    """
    catalog_columns = (
        catalog["integer"] + list(catalog["date"]) + catalog["text"]
    )
    return {
        "not_in_catalog": sorted(set(csv_columns) - set(catalog_columns)),
        "not_in_csv": sorted(set(catalog_columns) - set(csv_columns)),
        "repeated": sorted(
            column
            for column, times in Counter(catalog_columns).items()
            if times > 1
        ),
    }


def prepare_table(table: str) -> pd.DataFrame:
    """Read a table's CSV and return it converted to its Bronze types.

    The integer and date columns come from ``COLUMN_TYPES``; the rest stay
    as text. Raise ``ValueError`` if ``table`` is not in the catalog (before
    any file is read), if the catalog columns do not match the CSV columns,
    or if the conversion adds nulls to a converted column or changes the
    number of rows.
    """
    if table not in COLUMN_TYPES:
        raise ValueError(f"{table} is not in COLUMN_TYPES")
    catalog = COLUMN_TYPES[table]
    raw = read_table(table)
    problems = find_column_problems(list(raw.columns), catalog)
    if any(problems.values()):
        raise ValueError(f"{table}: catalog and CSV columns differ {problems}")
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
