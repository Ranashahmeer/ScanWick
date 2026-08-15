from decimal import Decimal

from app.utils.numeric import parse_decimal


def test_parse_decimal_strips_thousands_separator_commas():
    assert parse_decimal("4,000") == 400000


def test_parse_decimal_strips_naira_symbol():
    assert parse_decimal("₦5,000") == 500000


def test_parse_decimal_strips_dollar_symbol():
    assert parse_decimal("$1,234.50") == 123450


def test_parse_decimal_strips_leading_naira_shorthand_letter():
    """"N5,000" -- a common Naira-shorthand cash-book convention (Data
    Mapping Layer spec Part 2.3)."""
    assert parse_decimal("N5,000") == 500000


def test_parse_decimal_does_not_strip_a_bare_leading_n_without_a_following_digit():
    """Guards against over-eager stripping eating something that isn't
    actually the Naira shorthand."""
    assert parse_decimal("Nil") is None


def test_parse_decimal_k_suffix():
    assert parse_decimal("5k") == 500000
    assert parse_decimal("2.5k") == 250000


def test_parse_decimal_m_suffix():
    assert parse_decimal("1.2m") == 120000000


def test_parse_decimal_negative_numbers_still_work():
    """A leading '-' must never be mistaken for the "N" Naira-shorthand
    stripping -- these are unrelated characters, but worth a regression
    test given both transformations touch the start of the string."""
    assert parse_decimal("-5,000") == -500000


def test_parse_decimal_blank_and_none_and_unparseable():
    assert parse_decimal("") is None
    assert parse_decimal(None) is None
    assert parse_decimal("nil") is None
    assert parse_decimal("-") is None
