"""Tests for the rule catalog: every rule must be well formed and runnable."""

import inspect

import pandas as pd
import pytest

from ingestion import validators
from ingestion.report import run_validations
from ingestion.rules import RULES


def rule_id(rule):
    """Return a readable name for a rule, used by the test report."""
    table, check, params = rule
    return f"{table}-{check.__name__}-{params.get('column', 'columns')}"


@pytest.mark.parametrize("rule", RULES, ids=rule_id)
def test_rule_arguments_match_the_validator(rule):
    """A typo in a parameter name must fail here, not in a production run."""
    _table, check, params = rule
    signature = inspect.signature(check)
    # ``bind`` raises TypeError if a parameter is missing or unknown.
    signature.bind(pd.DataFrame(), **params)


def test_rules_only_use_functions_from_validators():
    """Every rule uses a ``find_*`` function defined in ``validators``."""
    for _table, check, _params in RULES:
        assert getattr(validators, check.__name__) is check
        assert check.__name__.startswith("find_")


def test_every_rule_runs_on_the_included_sample_data():
    """No rule fails to run against the real CSV files in ``datasets/``."""
    report = run_validations(RULES)
    assert len(report) == len(RULES)
    assert report["error"].isna().all(), report[report["error"].notna()]
