"""Tests for the validators: each one must flag exactly what it promises."""

import pandas as pd
import pytest

from ingestion.validators import (
    find_containing,
    find_date_order_violations,
    find_duplicates,
    find_future_dates,
    find_invalid_dates,
    find_invalid_values,
    find_non_positive,
    find_not_uppercase,
    find_nulls,
    find_prefixed,
    find_total_mismatches,
    find_untrimmed,
)

DATE = "%Y-%m-%d"
AS_OF = pd.Timestamp("2025-01-01")


def make_frame(**columns):
    """Build a text DataFrame like the one ``read_raw`` returns.

    Every column is a string and ``None`` becomes a missing value.
    """
    return pd.DataFrame(columns, dtype=str)


def flagged(result):
    """Return the row numbers a validator flagged."""
    return result.index.tolist()


# A table where every validator below must flag nothing. The row numbers of
# the other tests refer to the position of each value in its own list.
CLEAN = make_frame(
    id=["1", "2"],
    name=["ana", "luis"],
    gender=["F", "M"],
    amount=["5", "10"],
    code=["AB", "CD"],
    date=["2024-01-01", "2024-02-01"],
    later=["2024-01-02", "2024-02-01"],
    quantity=["1", "2"],
    price=["5", "5"],
    total=["5", "10"],
)

CLEAN_CASES = [
    (find_nulls, {"column": "id"}),
    (find_duplicates, {"column": "id"}),
    (find_untrimmed, {"column": "name"}),
    (find_invalid_values, {"column": "gender", "allowed": ["F", "M"]}),
    (find_non_positive, {"column": "amount"}),
    (find_invalid_dates, {"column": "date", "date_format": DATE}),
    (find_prefixed, {"column": "code", "prefix": "NAS"}),
    (find_containing, {"column": "code", "text": "-"}),
    (find_not_uppercase, {"column": "code"}),
    (find_future_dates, {
        "column": "date", "date_format": DATE, "as_of": AS_OF,
    }),
    (find_date_order_violations, {
        "earlier": "date", "later": "later", "date_format": DATE,
    }),
    (find_total_mismatches, {
        "total": "total", "quantity": "quantity", "unit_price": "price",
    }),
]


@pytest.mark.parametrize(
    "check, params",
    [pytest.param(check, params, id=check.__name__)
     for check, params in CLEAN_CASES],
)
def test_clean_data_flags_nothing(check, params):
    """Valid data gives an empty result that keeps all the columns."""
    result = check(CLEAN, **params)
    assert result.empty
    assert result.columns.tolist() == CLEAN.columns.tolist()


def test_validators_return_the_original_rows():
    """A flagged row comes back whole and with its original index."""
    df = make_frame(id=["1", None, "3"], name=["a", "b", "c"])
    result = find_nulls(df, "id")
    assert flagged(result) == [1]
    assert result.loc[1, "name"] == "b"


def test_validators_do_not_modify_the_input():
    """Running a validator leaves the table it received untouched."""
    df = make_frame(name=[" a", "b"])
    before = df.copy()
    find_untrimmed(df, "name")
    pd.testing.assert_frame_equal(df, before)


def test_find_nulls():
    """Only missing values are flagged; an empty string is not missing."""
    df = make_frame(id=["1", None, "", "4", None])
    assert flagged(find_nulls(df, "id")) == [1, 4]


def test_find_duplicates_flags_every_copy():
    """Both rows of a repeated value are flagged, not just the second."""
    df = make_frame(id=["1", "2", "1", "3", "2"])
    assert flagged(find_duplicates(df, "id")) == [0, 1, 2, 4]


def test_find_duplicates_ignores_nulls():
    """Two missing values are not duplicates of each other."""
    df = make_frame(id=["1", None, None, "2"])
    assert find_duplicates(df, "id").empty


def test_find_untrimmed():
    """Leading and trailing whitespace is flagged; inner spaces are not."""
    df = make_frame(name=[" ana", "luis ", "ana maria", None, "\tx", "ok"])
    assert flagged(find_untrimmed(df, "name")) == [0, 1, 4]


def test_find_invalid_values_ignores_case_and_spaces():
    """`` m `` matches ``M``; anything outside the list is flagged."""
    df = make_frame(gender=[" m ", "f", "X", "Male", "M"])
    result = find_invalid_values(df, "gender", ["M", "F"])
    assert flagged(result) == [2, 3]


def test_find_invalid_values_ignores_nulls():
    """A missing value is the job of ``find_nulls``, not of this check."""
    df = make_frame(gender=["M", None])
    assert find_invalid_values(df, "gender", ["M", "F"]).empty


def test_find_non_positive():
    """Zero and negative numbers are flagged, decimals included."""
    df = make_frame(amount=["5", "0", "-3", "0.5", "-0.1", "0.0"])
    assert flagged(find_non_positive(df, "amount")) == [1, 2, 4, 5]


def test_find_non_positive_ignores_nulls_and_text():
    """A missing or non-numeric value is not 'non positive'."""
    df = make_frame(amount=[None, "abc", "", "-1"])
    assert flagged(find_non_positive(df, "amount")) == [3]


def test_find_invalid_dates():
    """Impossible dates and loose formats are flagged; valid ones are not."""
    df = make_frame(date=[
        "2024-01-05",   # valid
        "2024-02-30",   # impossible day
        "2024-1-5",     # loose format, not zero-padded
        "05/01/2024",   # different format
        "hello",        # not a date
        None,           # missing, a different problem
    ])
    assert flagged(find_invalid_dates(df, "date", DATE)) == [1, 2, 3, 4]


def test_find_invalid_dates_uses_the_given_format():
    """The same text is valid in one format and invalid in another."""
    df = make_frame(date=["20240105"])
    assert find_invalid_dates(df, "date", "%Y%m%d").empty
    assert flagged(find_invalid_dates(df, "date", DATE)) == [0]


def test_find_prefixed_is_case_sensitive_by_default():
    """``nas1`` does not start with ``NAS`` unless ``ignore_case`` is set."""
    df = make_frame(code=["NAS1", "nas2", "XNAS3", None, "NA"])
    assert flagged(find_prefixed(df, "code", "NAS")) == [0]
    result = find_prefixed(df, "code", "NAS", ignore_case=True)
    assert flagged(result) == [0, 1]


def test_find_prefixed_null_never_matches_with_object_column():
    """Missing values are skipped even in a column of ``object`` type."""
    df = pd.DataFrame({"code": pd.Series(["NAS1", None, "X"], dtype=object)})
    assert flagged(find_prefixed(df, "code", "NAS")) == [0]


def test_find_containing_is_a_literal_match():
    """``.`` is a plain dot, not a regular expression that matches any."""
    df = make_frame(code=["a.b", "axb", "AB-1", None])
    assert flagged(find_containing(df, "code", ".")) == [0]
    assert flagged(find_containing(df, "code", "-")) == [2]


def test_find_containing_ignore_case():
    """``ignore_case`` makes the search insensitive to upper/lower case."""
    df = make_frame(code=["Abc", "xyz", None])
    assert find_containing(df, "code", "ab").empty
    assert flagged(find_containing(df, "code", "ab", ignore_case=True)) == [0]


def test_find_containing_null_never_matches_with_object_column():
    """Missing values are skipped even in a column of ``object`` type."""
    df = pd.DataFrame({"code": pd.Series(["a-b", None, "ab"], dtype=object)})
    assert flagged(find_containing(df, "code", "-")) == [0]


def test_find_not_uppercase():
    """Any lower-case letter is flagged; digits and symbols are fine."""
    df = make_frame(code=["AB", "Ab", "ab", "AB-12", "", None])
    assert flagged(find_not_uppercase(df, "code")) == [1, 2]


def test_find_future_dates_compares_with_as_of():
    """Only dates after ``as_of`` are flagged; the same day is not."""
    df = make_frame(date=[
        "2025-01-02",   # after
        "2025-01-01",   # same day as as_of
        "2024-12-31",   # before
        "2024-02-30",   # invalid, ignored
        None,           # missing, ignored
    ])
    result = find_future_dates(df, "date", DATE, as_of=AS_OF)
    assert flagged(result) == [0]


def test_find_future_dates_defaults_to_now():
    """Without ``as_of`` the check uses today's date."""
    df = make_frame(date=["2000-01-01", "9999-12-31"])
    assert flagged(find_future_dates(df, "date", DATE)) == [1]


def test_find_date_order_violations():
    """Only a row whose earlier date is after the later one is flagged."""
    df = make_frame(
        start=["2024-01-02", "2024-01-01", "2024-01-01", "2024-01-01"],
        end=["2024-01-01", "2024-01-01", "2024-01-02", "2024-02-30"],
    )
    result = find_date_order_violations(df, "start", "end", DATE)
    assert flagged(result) == [0]


def test_find_date_order_violations_ignores_missing_dates():
    """A null date in either column cannot be out of order."""
    df = make_frame(
        start=[None, "2024-01-02", None],
        end=["2024-01-01", None, None],
    )
    assert find_date_order_violations(df, "start", "end", DATE).empty


def test_find_total_mismatches():
    """A total that is not quantity times price is flagged."""
    df = make_frame(
        total=["10", "11", "0", "7"],
        quantity=["2", "2", "3", "7"],
        price=["5", "5", "0", "1"],
    )
    result = find_total_mismatches(df, "total", "quantity", "price")
    assert flagged(result) == [1]


def test_find_total_mismatches_ignores_missing_and_text():
    """A row with a missing or non-numeric value is skipped."""
    df = make_frame(
        total=[None, "x", "10", "10"],
        quantity=["2", "2", None, "2"],
        price=["5", "5", "5", "abc"],
    )
    assert find_total_mismatches(df, "total", "quantity", "price").empty


def test_find_total_mismatches_is_exact():
    """There is no tolerance: ``0.1 * 3`` is not ``0.3`` in floating point."""
    df = make_frame(total=["0.3"], quantity=["3"], price=["0.1"])
    result = find_total_mismatches(df, "total", "quantity", "price")
    assert flagged(result) == [0]
