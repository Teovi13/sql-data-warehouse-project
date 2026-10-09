"""Type conversion helpers for loading raw text into typed Bronze columns.

Source files are read as text (see ``readers``). The functions here turn
those strings into the types of the Bronze tables, converting strictly: a
value that does not match the expected format becomes missing instead of
being guessed.
"""

import pandas as pd


def convert_dates(values: pd.Series, date_format: str) -> pd.Series:
    """Convert a text column to ``datetime64[us]``, strictly.

    A date is valid only if formatting it back with ``date_format`` gives
    the original text, so impossible dates (``2023-02-30``) and loose
    formats (``2023-1-5`` with ``%Y-%m-%d``) are rejected. Anything else
    becomes ``NaT``; no exception is raised.

    The result is always ``datetime64[us]``, even for a column with no
    valid value, so its type does not depend on the data.

    A failed conversion looks the same as an already missing value. To
    find the failures, use ``values.notna() & converted.isna()``.
    """
    parsed_dates = pd.to_datetime(values, errors="coerce", format=date_format)
    round_trip = parsed_dates.dt.strftime(date_format)
    return parsed_dates.where(round_trip == values).astype("datetime64[us]")


def convert_integers(
    values: pd.Series,
    minimum: int = -2**31,
    maximum: int = 2**31 - 1,
) -> pd.Series:
    """Convert a text column to a nullable ``Int64`` series, strictly.

    A value is valid only if it is an optional minus sign followed by
    digits (no spaces, plus sign, decimals or scientific notation) and
    lies between ``minimum`` and ``maximum``, both included. Anything
    else becomes ``<NA>``; no exception is raised. The defaults are the
    range of SQL Server ``INT``.

    Bounds beyond +/-2**53 are not supported: the range check uses floats,
    which are exact only up to that limit.

    A failed conversion looks the same as an already missing value. To
    find the failures, use ``values.notna() & converted.isna()``.

    Raises:
        AttributeError: If ``values`` does not contain text.
    """
    # Only text that is entirely an optional minus sign plus digits is
    # considered; everything else is masked to missing before converting.
    looks_valid = values.str.fullmatch(r"-?\d+")
    numbers = pd.to_numeric(values.where(looks_valid), errors="coerce")

    # Out-of-range numbers are masked too. Doing it before astype avoids
    # a TypeError on values that do not fit in 64 bits.
    valid_range = numbers.between(minimum, maximum)
    converted = numbers.where(valid_range).astype("Int64")
    return converted
