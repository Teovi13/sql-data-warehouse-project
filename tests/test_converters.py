"""Tests for convert_types: strict conversion of the listed columns."""

import pandas as pd
import pytest

from ingestion.converters import convert_types


def test_integers_are_converted_strictly():
    """Only an optional minus sign plus digits becomes a number."""
    table = pd.DataFrame({"id": ["1", "-7", "abc", "1.5", " 3", None]})
    result = convert_types(table, integer_columns=["id"])
    assert str(result["id"].dtype) == "Int64"
    assert result["id"].isna().tolist() == [
        False, False, True, True, True, True,
    ]
    assert result["id"].dropna().tolist() == [1, -7]


def test_dates_are_converted_strictly():
    """Impossible dates and loose formats become missing, not guessed."""
    table = pd.DataFrame({
        "day": ["2023-01-05", "2023-02-30", "2023-1-5", None],
    })
    result = convert_types(table, date_columns={"day": "%Y-%m-%d"})
    assert str(result["day"].dtype) == "datetime64[us]"
    assert result["day"].isna().tolist() == [False, True, True, True]
    assert result["day"].dropna().dt.strftime("%Y-%m-%d").tolist() == [
        "2023-01-05",
    ]


def test_other_columns_are_left_alone_and_the_input_is_not_modified():
    """Unlisted columns keep their text; the original table is untouched."""
    table = pd.DataFrame({"id": ["1", "2"], "name": ["Ana", " Luis "]})
    original = table.copy()
    result = convert_types(table, integer_columns=["id"])
    assert result["name"].tolist() == ["Ana", " Luis "]
    pd.testing.assert_frame_equal(table, original)


def test_nothing_to_convert_returns_an_equal_copy():
    """Without column lists the result equals the input but is a new table."""
    table = pd.DataFrame({"id": ["1", "2"]})
    result = convert_types(table)
    pd.testing.assert_frame_equal(result, table)
    assert result is not table


def test_a_listed_column_that_does_not_exist_raises():
    """A catalog column missing from the table is a loud error."""
    table = pd.DataFrame({"id": ["1"]})
    with pytest.raises(KeyError):
        convert_types(table, integer_columns=["missing"])
