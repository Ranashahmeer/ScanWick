from datetime import date

from app.utils.locale_dates import parse_locale_date


def test_unambiguous_day_over_12_parses_regardless_of_locale():
    """"25/12/2026" can only be day=25/month=12 under either reading --
    parses the same with no locale confirmed."""
    parsed, warning = parse_locale_date("25/12/2026", None)
    assert warning is None
    assert parsed.date() == date(2026, 12, 25)


def test_ambiguous_date_with_no_locale_confirmed_is_rejected():
    """"03/04/2026" is genuinely ambiguous (day=3/month=4 vs day=4/month=3)
    -- must not be silently guessed when no date_locale was ever confirmed
    for this mapping."""
    parsed, warning = parse_locale_date("03/04/2026", None)
    assert parsed is None
    assert warning["code"] == "AMBIGUOUS_DATE"
    assert warning["raw_value"] == "03/04/2026"
    assert "remediation" in warning


def test_ambiguous_date_resolves_once_locale_is_confirmed_day_first():
    parsed, warning = parse_locale_date("03/04/2026", "day_first")
    assert warning is None
    assert parsed.date() == date(2026, 4, 3)


def test_ambiguous_date_resolves_once_locale_is_confirmed_month_first():
    parsed, warning = parse_locale_date("03/04/2026", "month_first")
    assert warning is None
    assert parsed.date() == date(2026, 3, 4)


def test_default_locale_is_day_first_when_unconfirmed_and_unambiguous():
    """"13/02/2026" isn't ambiguous (13 can't be a month), so it parses
    under the day-first default without needing a confirmed locale --
    proves the default really is day-first, not pandas' own month-first
    default."""
    parsed, warning = parse_locale_date("13/02/2026", None)
    assert warning is None
    assert parsed.date() == date(2026, 2, 13)


def test_iso_year_first_date_is_never_treated_as_ambiguous():
    """Regression: `pd.to_datetime("2026-01-05", dayfirst=True)` has a real
    pandas/dateutil quirk where it silently swaps the trailing month/day
    pair (returns 2026-05-01) even though the leading 4-digit year already
    fixes the field order unambiguously. Year-first values must always
    parse correctly regardless of the effective locale."""
    parsed, warning = parse_locale_date("2026-01-05", None)
    assert warning is None
    assert parsed.date() == date(2026, 1, 5)

    parsed_day_first, warning_day_first = parse_locale_date("2026-01-05", "day_first")
    assert warning_day_first is None
    assert parsed_day_first.date() == date(2026, 1, 5)


def test_invalid_date_string_returns_invalid_date_warning():
    parsed, warning = parse_locale_date("not-a-date", None)
    assert parsed is None
    assert warning["code"] == "INVALID_DATE"
    assert warning["raw_value"] == "not-a-date"


def test_missing_value_returns_no_warning():
    """A blank/NaN cell isn't a locale problem -- just a missing value,
    left to the caller's own missing-required-field handling."""
    parsed, warning = parse_locale_date(None, None)
    assert parsed is None
    assert warning is None

    parsed_empty, warning_empty = parse_locale_date("   ", None)
    assert parsed_empty is None
    assert warning_empty is None


def test_unrecognized_date_locale_falls_back_to_default():
    """A garbage/unrecognized date_locale value is treated the same as
    unconfirmed -- falls back to the documented day-first default rather
    than erroring or silently using pandas' month-first default."""
    parsed, warning = parse_locale_date("03/04/2026", "not-a-real-locale")
    assert parsed is None
    assert warning["code"] == "AMBIGUOUS_DATE"
