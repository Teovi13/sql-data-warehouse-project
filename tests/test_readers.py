"""Tests for read_raw: the CSV is read as text and nothing is cleaned."""

import pytest

from ingestion.config import SOURCES
from ingestion.readers import read_raw, read_table


def write_csv(tmp_path, content):
    """Write ``content`` to a CSV file in ``tmp_path`` and return its path."""
    path = tmp_path / "sample.csv"
    path.write_text(content, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "text", ["n/a", "N/A", "NA", "null", "NULL", "NaN", "None"])
def test_null_looking_text_is_kept_as_a_value(tmp_path, text):
    """Only an empty field is null: ``n/a`` is a real code in ``cst_gndr``."""
    path = write_csv(tmp_path, f"id,gndr\n1,{text}\n")
    df = read_raw(path)
    assert df.loc[0, "gndr"] == text


def test_empty_field_becomes_null(tmp_path):
    """An empty field is the one thing that reads as null."""
    path = write_csv(tmp_path, "id,gndr\n1,\n")
    df = read_raw(path)
    assert df["gndr"].isna().all()


def test_numbers_stay_text_with_their_leading_zeros(tmp_path):
    """Every column is a string, so ``007`` does not turn into ``7``."""
    path = write_csv(tmp_path, "id,qty\n007,5\n")
    df = read_raw(path)
    assert df.loc[0, "id"] == "007"
    assert df.loc[0, "qty"] == "5"


def test_spaces_and_case_are_not_cleaned(tmp_path):
    """Bronze is a copy of the source: spaces and capitals are kept."""
    path = write_csv(tmp_path, "id,name\n1, Ana MARIA \n")
    df = read_raw(path)
    assert df.loc[0, "name"] == " Ana MARIA "


def test_header_is_not_counted_as_a_row(tmp_path):
    """The first line gives the column names and only the rest are rows."""
    path = write_csv(tmp_path, "id,name\n1,a\n2,b\n3,c\n")
    df = read_raw(path)
    assert list(df.columns) == ["id", "name"]
    assert len(df) == 3


def test_unknown_table_lists_the_valid_ones():
    """A table that is not in ``SOURCES`` is rejected with the valid names."""
    with pytest.raises(ValueError) as error:
        read_table("bronze.does_not_exist")
    assert "bronze.does_not_exist" in str(error.value)
    for table_name in SOURCES:
        assert table_name in str(error.value)
