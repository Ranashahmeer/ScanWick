"""Locale-aware date parsing for ingestion (3.7).

Real bank/cash-book/ecommerce exports mix day-first (Nigeria/UK-style,
"03/04/2026" = 3 April) and month-first (US-style, "03/04/2026" = March 4)
numeric date formats. Plain `pd.to_datetime(..., errors="coerce")` silently
assumes month-first (`dayfirst=False`) regardless of which the source
actually used -- wrong more often than right for this product's primary
market, and never flags a value like "03/04/2026" as genuinely ambiguous
between the two even when nothing on record says which format the source
uses.
"""
from __future__ import annotations

import re
from typing import Optional

import pandas as pd

# Per spec: adopt the documented day-first default only when the mapping's
# persisted value_rules has no explicit date_locale.
DEFAULT_DATE_LOCALE = "day_first"
VALID_DATE_LOCALES = {"day_first", "month_first"}

# Matches a bare numeric D/M/Y-shaped value ("03/04/2026", "03-04-26",
# "03.04.2026"). A 4-digit YEAR-first value ("2026-01-05", ISO) never
# matches this (the first group is 1-2 digits), so ISO-formatted dates are
# never treated as ambiguous -- there's only one way to read them.
_NUMERIC_DATE_PATTERN = re.compile(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})$")

# A leading 4-digit year ("2026-01-05...", ISO 8601, with or without a time
# component) is unambiguous regardless of locale -- there's only one field
# order once the year is that clearly marked. Also works around a genuine
# pandas/dateutil bug: `pd.to_datetime("2026-01-05", dayfirst=True)` silently
# returns 2026-05-01 (it swaps the trailing M-D pair even though the leading
# 4-digit year already fixes the field order) -- confirmed against this
# pandas version. Year-first values are always parsed with dayfirst=False to
# avoid that swap.
_YEAR_FIRST_PATTERN = re.compile(r"^\d{4}[/\-.]")


def _is_ambiguous_numeric_date(raw_value) -> bool:
    """A D/M/Y-shaped value is a candidate for ambiguity only when BOTH
    components could plausibly be either the day or the month (both <=
    12) -- "25/12/2026" is unambiguous since 25 can't be a month under
    either reading."""
    match = _NUMERIC_DATE_PATTERN.match(str(raw_value).strip())
    if not match:
        return False
    first, second, _year = match.groups()
    return 1 <= int(first) <= 12 and 1 <= int(second) <= 12


def parse_locale_date(raw_value, date_locale: Optional[str]) -> tuple[Optional["pd.Timestamp"], Optional[dict]]:
    """Parses one raw date cell using `date_locale` ("day_first" or
    "month_first", read from the mapping's persisted value_rules) --
    falling back to `DEFAULT_DATE_LOCALE` only when the caller never
    confirmed one.

    Returns (parsed_timestamp_or_None, warning_or_None):
    - A value that fails to parse under the effective locale at all comes
      back as (None, {"code": "INVALID_DATE", ...}).
    - A value that IS parseable but is genuinely ambiguous under an
      UNCONFIRMED locale (e.g. "03/04/2026" could be 3 April or March 4,
      and nothing on record says which this source uses) comes back as
      (None, {"code": "AMBIGUOUS_DATE", ...}) rather than silently
      guessing. Once a locale has been explicitly confirmed for this
      mapping, that same numeric-slash format is no longer ambiguous --
      the confirmed locale IS the resolution -- and parses normally.
    - An unparseable/missing cell (None/NaN/empty) returns (None, None):
      not a locale problem, just a missing value, left to the caller's
      existing missing-required-field handling.
    """
    if raw_value is None or (isinstance(raw_value, float) and pd.isna(raw_value)):
        return None, None
    text = str(raw_value).strip()
    if not text:
        return None, None

    year_first = bool(_YEAR_FIRST_PATTERN.match(text))

    locale_confirmed = date_locale in VALID_DATE_LOCALES
    effective_locale = date_locale if locale_confirmed else DEFAULT_DATE_LOCALE
    dayfirst = False if year_first else effective_locale == "day_first"

    parsed = pd.to_datetime(text, dayfirst=dayfirst, errors="coerce")
    if pd.isna(parsed):
        return None, {
            "code": "INVALID_DATE",
            "message": f"'{text}' could not be parsed as a date.",
            "raw_value": text,
            "remediation": "Confirm the date column mapping and format for this upload.",
        }

    if not locale_confirmed and _is_ambiguous_numeric_date(text):
        alternate = pd.to_datetime(text, dayfirst=not dayfirst, errors="coerce")
        if not pd.isna(alternate) and alternate.date() != parsed.date():
            return None, {
                "code": "AMBIGUOUS_DATE",
                "message": (
                    f"'{text}' is ambiguous (could be {parsed.date().isoformat()} or "
                    f"{alternate.date().isoformat()}) and no date_locale was confirmed for this mapping."
                ),
                "raw_value": text,
                "remediation": "Confirm a date_locale ('day_first' or 'month_first') for this mapping and re-upload.",
            }

    return parsed, None
