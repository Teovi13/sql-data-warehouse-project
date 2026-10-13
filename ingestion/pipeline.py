"""Run the ingestion of the Bronze tables: validate, prepare and load."""

import pandas as pd

from ingestion.report import run_validations


def validate_table(table: str, rules: list) -> pd.DataFrame:
    """Run the validation rules of one table and return their report.

    Only the rules whose table is ``table`` are run. A rule that flags rows
    does not stop anything: Bronze keeps the raw data, so those rows are only
    reported. A rule that could not run (it raised an error) does stop, since
    the table would be loaded without having been checked.

    The report is the one from ``run_validations``, with one row per rule.

    Raises:
        ValueError: If ``rules`` has no rule for ``table`` (nothing is run),
        or if any rule of the table could not run.
    """
    table_rules = [rule for rule in rules if rule[0] == table]
    if not table_rules:
        raise ValueError(f"{table}: no validation rules")
    report = run_validations(table_rules)
    crashed = report[report["error"].notna()]
    if not crashed.empty:
        details = [
            f"{row.rule}({row.params}): {row.error}"
            for row in crashed.itertuples()
        ]
        raise ValueError(f"{table}: rules that could not run: {details}")
    return report
