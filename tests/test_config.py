"""Tests that the table catalogs agree with each other."""

from ingestion.config import COLUMN_TYPES, SOURCES
from ingestion.rules import RULES


def test_sources_and_column_types_cover_the_same_tables():
    """A table with a CSV but no types (or the reverse) is a config hole."""
    assert set(SOURCES) == set(COLUMN_TYPES)


def test_rules_cover_exactly_the_source_tables():
    """Every table has rules, and no rule names a table that does not exist.

    A rule with a misspelled table is never selected by ``validate_table``,
    so without this test it would silently never run.
    """
    tables_with_rules = {rule[0] for rule in RULES}
    assert tables_with_rules == set(SOURCES)
