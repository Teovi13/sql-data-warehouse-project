"""Tests for validate_table: flagged rows inform, crashed rules stop."""

import logging

import pandas as pd
import pytest

from ingestion import pipeline, report
from ingestion.validators import find_nulls

TABLE = "test.table"
OTHER = "test.other"


def use_rows(monkeypatch, rows):
    """Make ``run_validations`` read ``rows`` instead of a CSV file."""
    frame = pd.DataFrame(rows, dtype=str)
    monkeypatch.setattr(report, "read_table", lambda _table: frame)


def test_table_without_rules_raises():
    """A table with no rules is a configuration hole, not a clean table."""
    rules = [(OTHER, find_nulls, {"column": "id"})]
    with pytest.raises(ValueError) as error:
        pipeline.validate_table(TABLE, rules)
    assert TABLE in str(error.value)


def test_crashed_rule_raises(monkeypatch):
    """A rule that could not run means the table was not really checked."""
    use_rows(monkeypatch, {"id": ["1", "2"]})
    rules = [(TABLE, find_nulls, {"column": "missing"})]
    with pytest.raises(ValueError) as error:
        pipeline.validate_table(TABLE, rules)
    assert "find_nulls" in str(error.value)
    assert "missing" in str(error.value)


def test_flagged_rows_do_not_stop(monkeypatch):
    """Bronze keeps raw data: rows flagged by a rule are reported only."""
    use_rows(monkeypatch, {"id": ["1", None, None]})
    rules = [(TABLE, find_nulls, {"column": "id"})]
    result = pipeline.validate_table(TABLE, rules)
    assert result["rows"].tolist() == [2]


def test_only_rules_of_the_table_run(monkeypatch):
    """Rules of other tables are ignored."""
    use_rows(monkeypatch, {"id": ["1"]})
    rules = [
        (TABLE, find_nulls, {"column": "id"}),
        (OTHER, find_nulls, {"column": "nope"}),
    ]
    result = pipeline.validate_table(TABLE, rules)
    assert result["table"].tolist() == [TABLE]


def test_log_flagged_rules_logs_only_rules_with_rows(caplog):
    """A rule that flagged nothing is not worth a line in the log."""
    report_frame = pd.DataFrame({
        "rule": ["find_nulls", "find_duplicates"],
        "params": [{"column": "id"}, {"column": "key"}],
        "rows": [0, 3],
    })
    with caplog.at_level(logging.INFO, logger="ingestion.pipeline"):
        pipeline.log_flagged_rules(TABLE, report_frame)
    assert [record.levelname for record in caplog.records] == ["INFO"]
    assert TABLE in caplog.messages[0]
    assert "find_duplicates" in caplog.messages[0]
    assert "3" in caplog.messages[0]
