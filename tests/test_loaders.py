"""Tests for the parts of ``loaders`` that need no database."""

import pandas as pd
import pytest

from ingestion import loaders
from ingestion.loaders import (
    STATUS_FAILED,
    STATUS_SUCCESS,
    ReconciliationError,
    check_row_count,
    load_and_log,
    load_table,
)

ENGINE = object()
TABLE = "bronze.sample"
FRAME = pd.DataFrame({"id": [1, 2, 3]})


def test_matching_row_count_does_not_raise():
    """Equal counts pass silently."""
    check_row_count(TABLE, 3, 3)


@pytest.mark.parametrize("expected, actual", [(3, 2), (2, 3)])
def test_different_row_count_raises(expected, actual):
    """Fewer or more rows than expected both fail, naming table and counts."""
    with pytest.raises(ReconciliationError) as error:
        check_row_count(TABLE, expected, actual)
    message = f"{TABLE}: expected {expected} rows, found {actual}"
    assert str(error.value) == message


@pytest.mark.parametrize("table_name", [
    "customers",
    "bronze.customers.extra",
    "bronze.customers; DROP TABLE bronze.customers",
    "bronze.my table",
    "1bronze.customers",
    "",
])
def test_invalid_table_name_is_rejected_before_any_sql(table_name):
    """A name that is not ``schema.table`` never reaches the database.

    ``ENGINE`` is a bare object: if ``load_table`` touched it, this test would
    fail with an ``AttributeError`` instead of the expected ``ValueError``.
    """
    with pytest.raises(ValueError, match="Invalid table name"):
        load_table(ENGINE, table_name, FRAME)


def use_fakes(monkeypatch, load_error=None):
    """Replace ``load_table`` and ``write_load_log`` with recording fakes.

    Return the list of calls, in order. A load call is
    ``("load", engine, table_name, rows)``; a log call is
    ``("log", engine, table_name, status, fields)``. ``load_table`` raises
    ``load_error`` when one is given.
    """
    calls = []

    def load(engine, table_name, df):
        calls.append(("load", engine, table_name, len(df)))
        if load_error is not None:
            raise load_error

    def write_log(engine, table_name, status, **fields):
        calls.append(("log", engine, table_name, status, fields))

    monkeypatch.setattr(loaders, "load_table", load)
    monkeypatch.setattr(loaders, "write_load_log", write_log)
    return calls


def test_success_is_logged_with_the_loaded_rows(monkeypatch):
    """A load that works leaves one SUCCESS row with the row count."""
    calls = use_fakes(monkeypatch)
    load_and_log(ENGINE, TABLE, FRAME)
    assert calls == [
        ("load", ENGINE, TABLE, 3),
        ("log", ENGINE, TABLE, STATUS_SUCCESS, {"rows_loaded": 3}),
    ]


def test_failure_is_logged_with_type_and_message_then_raised(monkeypatch):
    """A failed load leaves one FAILED row and the error is not swallowed."""
    calls = use_fakes(monkeypatch, RuntimeError("disk full"))
    with pytest.raises(RuntimeError, match="disk full"):
        load_and_log(ENGINE, TABLE, FRAME)
    assert calls == [
        ("load", ENGINE, TABLE, 3),
        ("log", ENGINE, TABLE, STATUS_FAILED,
         {"error_message": "RuntimeError: disk full"}),
    ]
