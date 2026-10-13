"""Tests for prepare_table: a conversion must never lose data silently."""

import pandas as pd
import pytest

from ingestion import prepare

TABLE = "test.table"
CATALOG = {
    TABLE: {
        "integer": ["id"],
        "date": {"created": "%Y-%m-%d"},
        "text": ["name"],
    },
}


def use_table(monkeypatch, rows):
    """Make ``prepare_table`` read ``rows`` instead of a CSV file."""
    frame = pd.DataFrame(rows, dtype=str)
    monkeypatch.setattr(prepare, "COLUMN_TYPES", CATALOG)
    monkeypatch.setattr(prepare, "read_table", lambda _table: frame)


def test_clean_table_is_converted(monkeypatch):
    """Valid values are converted; a value that was already null is fine."""
    use_table(monkeypatch, {
        "id": ["1", None],
        "created": ["2025-10-06", "2025-10-07"],
        "name": ["a", "b"],
    })
    typed = prepare.prepare_table(TABLE)
    assert typed["id"].dtype == "Int64"
    assert typed["created"].dtype == "datetime64[us]"
    assert typed["name"].tolist() == ["a", "b"]


def test_bad_date_raises(monkeypatch):
    """An impossible date would become null, so the table is rejected."""
    use_table(monkeypatch, {
        "id": ["1"],
        "created": ["2025-02-30"],
        "name": ["teo"],
    })
    with pytest.raises(ValueError) as error:
        prepare.prepare_table(TABLE)
    assert "{'created': (0, 1)}" in str(error.value)


def test_bad_integer_raises(monkeypatch):
    """Text in an integer column would become null, so it is rejected."""
    use_table(monkeypatch, {
        "id": ["abc"],
        "created": ["2006-06-05"],
        "name": ["teo"],
    })
    with pytest.raises(ValueError) as error:
        prepare.prepare_table(TABLE)
    assert "{'id': (0, 1)}" in str(error.value)


def test_unknown_table_fails_before_reading(monkeypatch):
    """A table missing from the catalog raises before any file is read."""
    def fail_if_called(table):
        raise AssertionError(f"read_table was called for {table}")

    monkeypatch.setattr(prepare, "COLUMN_TYPES", CATALOG)
    monkeypatch.setattr(prepare, "read_table", fail_if_called)
    with pytest.raises(ValueError) as error:
        prepare.prepare_table("nope")
    assert "nope" in str(error.value)
