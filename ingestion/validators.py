"""Data quality validators for pandas DataFrames.

Every ``find_*`` function takes a DataFrame and returns the rows it flags, so
an empty result means nothing was flagged. Columns are given by name and are
expected to hold raw text. ``date_format`` is a ``strptime`` pattern such as
``%Y-%m-%d``.
"""

import pandas as pd

from ingestion.converters import convert_dates


def find_nulls(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Return rows where ``column`` is null."""
    return df[df[column].isna()]


def find_duplicates(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Return every row whose ``column`` value appears more than once.

    Null values are ignored.
    """
    values = df[column]
    return df[values.notna() & values.duplicated(keep=False)]


def find_untrimmed(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Return rows where ``column`` has leading or trailing whitespace.

    Null values are ignored.
    """
    values = df[column]
    has_value = values.notna()
    differs = values != values.str.strip()
    return df[has_value & differs]


def find_invalid_values(
    df: pd.DataFrame, column: str, allowed: list[str]
) -> pd.DataFrame:
    """Return rows whose ``column`` value is not in ``allowed``.

    Values are stripped and compared case-insensitively, so ``" m "``
    matches ``"M"``. Null values are ignored.
    """
    allowed_upper = [item.upper() for item in allowed]
    values = df[column].str.strip().str.upper()
    has_value = values.notna()
    not_allowed = ~values.isin(allowed_upper)
    return df[has_value & not_allowed]


def find_non_positive(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Return rows where ``column`` is zero or negative.

    Null and non-numeric values are ignored.
    """
    numbers = pd.to_numeric(df[column], errors="coerce")
    non_positive = numbers <= 0
    return df[non_positive]


def find_invalid_dates(
    df: pd.DataFrame, column: str, date_format: str
) -> pd.DataFrame:
    """Return rows whose ``column`` is not a valid ``date_format`` date.

    With ``%Y-%m-%d``, impossible dates and loose formats such as
    ``2023-1-5`` are flagged. Null values are ignored.
    """
    values = df[column]
    parsed_dates = convert_dates(values, date_format)
    has_value = values.notna()
    return df[has_value & parsed_dates.isna()]


def find_prefixed(
    df: pd.DataFrame, column: str, prefix: str, ignore_case: bool = False
) -> pd.DataFrame:
    """Return rows where ``column`` starts with ``prefix``.

    Set ``ignore_case`` for a case-insensitive match. Null values never
    match.
    """
    values = df[column]
    if ignore_case:
        values = values.str.upper()
        prefix = prefix.upper()
    starts_with_prefix = values.str.startswith(prefix).fillna(False)
    return df[starts_with_prefix]


def find_containing(
    df: pd.DataFrame, column: str, text: str, ignore_case: bool = False
) -> pd.DataFrame:
    """Return rows where ``column`` contains ``text``.

    ``text`` is matched literally, not as a regular expression. Set
    ``ignore_case`` for a case-insensitive match. Null values never match.
    """
    values = df[column]
    if ignore_case:
        values = values.str.upper()
        text = text.upper()
    contains_text = values.str.contains(text, regex=False).fillna(False)
    return df[contains_text]


def find_not_uppercase(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Return rows where ``column`` is not already upper case.

    Null values are ignored.
    """
    values = df[column]
    has_value = values.notna()
    differs = values != values.str.upper()
    return df[has_value & differs]


def find_future_dates(
    df: pd.DataFrame,
    column: str,
    date_format: str,
    as_of: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Return rows whose ``column`` date is later than ``as_of``.

    ``as_of`` defaults to the current time, so the result changes with the
    day the check runs; pass a fixed value for reproducible runs. Null and
    invalid dates are ignored.
    """
    if as_of is None:
        as_of = pd.Timestamp.now()
    parsed_dates = convert_dates(df[column], date_format)
    return df[parsed_dates > as_of]


def find_date_order_violations(
    df: pd.DataFrame,
    earlier: str,
    later: str,
    date_format: str,
) -> pd.DataFrame:
    """Return rows where the ``earlier`` date is after the ``later`` date.

    Equal dates are allowed. Rows with a null or invalid date in either
    column are ignored.
    """
    earlier_parsed = convert_dates(df[earlier], date_format)
    later_parsed = convert_dates(df[later], date_format)
    return df[earlier_parsed > later_parsed]


def find_total_mismatches(
    df: pd.DataFrame,
    total: str,
    quantity: str,
    unit_price: str,
) -> pd.DataFrame:
    """Return rows where ``total`` differs from ``quantity * unit_price``.

    The comparison is exact, with no rounding tolerance. Rows with a null or
    non-numeric value in any of the three columns are ignored.
    """
    totals = pd.to_numeric(df[total], errors="coerce")
    quantities = pd.to_numeric(df[quantity], errors="coerce")
    unit_prices = pd.to_numeric(df[unit_price], errors="coerce")
    all_present = totals.notna() & quantities.notna() & unit_prices.notna()
    return df[all_present & (totals != quantities * unit_prices)]
