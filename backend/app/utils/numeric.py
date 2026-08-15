import re
from decimal import Decimal, InvalidOperation
from typing import Optional

import pandas as pd

# Data Mapping Layer (Scanwick_Mapping_Layer_Guide.pdf Part 2.3): real cash-
# book/spreadsheet cells routinely carry a currency symbol or a leading
# alpha shorthand ("N5,000" for Naira) -- strip these before parsing rather
# than letting them fall through to InvalidOperation -> silently None, the
# same failure mode the comma-stripping fix below already existed for.
_CURRENCY_SYMBOLS_PATTERN = re.compile(r"[₦$€£]")
# A bare leading "N"/"n" (Naira shorthand, e.g. "N5000") -- deliberately only
# stripped when immediately followed by a digit, so it never eats a real
# negative-number minus sign or a plain numeric string that happens to
# already parse fine.
_LEADING_NAIRA_LETTER_PATTERN = re.compile(r"^[Nn](?=\d)")
_K_SUFFIX_PATTERN = re.compile(r"^(-?\d+(?:\.\d+)?)\s*[kK]$")
_M_SUFFIX_PATTERN = re.compile(r"^(-?\d+(?:\.\d+)?)\s*[mM]$")


def parse_decimal(value) -> Optional[Decimal]:
    """Parses a raw CSV/spreadsheet cell into a Decimal.

    Strips thousands-separator commas (e.g. "4,000"), currency symbols
    (₦/$/€/£), a leading Naira-shorthand "N" (e.g. "N5,000"), and k/m
    magnitude suffixes ("5k" -> 5000, "1.2m" -> 1200000) before parsing --
    plain `Decimal(str(value))` raises InvalidOperation on all of these,
    which every ingestion pipeline here already caught and silently mapped
    to None. That's fine for genuinely unparseable text, but these are
    extremely common real-world spreadsheet/cash-book conventions and were
    being dropped as null instead of read correctly.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text:
        return None
    text = _CURRENCY_SYMBOLS_PATTERN.sub("", text).strip()
    text = _LEADING_NAIRA_LETTER_PATTERN.sub("", text)
    text = text.replace(",", "")
    if not text:
        return None

    k_match = _K_SUFFIX_PATTERN.match(text)
    if k_match:
        try:
            return Decimal(k_match.group(1)) * 1000
        except InvalidOperation:
            return None
    m_match = _M_SUFFIX_PATTERN.match(text)
    if m_match:
        try:
            return Decimal(m_match.group(1)) * 1_000_000
        except InvalidOperation:
            return None

    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None
import re
import pandas as pd
from typing import Optional
from decimal import Decimal, InvalidOperation

_CURRENCY_SYMBOLS_PATTERN = re.compile(r"[\$\€\£\¥\₹\₦]")
_LEADING_NAIRA_LETTER_PATTERN = re.compile(r"^[Nn](?=\d)")
_K_SUFFIX_PATTERN = re.compile(r"^([\d\.]+)[Kk]$")
_M_SUFFIX_PATTERN = re.compile(r"^([\d\.]+)[Mm]$")

def parse_kobo(value) -> Optional[int]:
    """Strictly parses a string amount directly into integer minor units (Kobo)
    without ever passing through float() or Decimal-from-string roundtripping,
    preventing floating point binary imprecision."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text:
        return None
    
    # Strip symbols and commas
    text = _CURRENCY_SYMBOLS_PATTERN.sub("", text).strip()
    text = _LEADING_NAIRA_LETTER_PATTERN.sub("", text)
    text = text.replace(",", "")
    if not text:
        return None

    # Handle k/m magnitude suffixes
    k_match = _K_SUFFIX_PATTERN.match(text)
    if k_match:
        try:
            # 5k -> 500000 kobo
            num = Decimal(k_match.group(1)) * 1000 * 100
            return int(num)
        except InvalidOperation:
            return None
    m_match = _M_SUFFIX_PATTERN.match(text)
    if m_match:
        try:
            # 1.2m -> 120000000 kobo
            num = Decimal(m_match.group(1)) * 1_000_000 * 100
            return int(num)
        except InvalidOperation:
            return None

    # Handle standard numbers (e.g. 5000.50 -> 500050, 5000 -> 500000)
    # No float() used. We split on decimal point.
    sign = 1
    if text.startswith("-"):
        sign = -1
        text = text[1:]
    elif text.startswith("+"):
        text = text[1:]

    parts = text.split(".")
    try:
        if len(parts) == 1:
            return int(parts[0]) * 100 * sign
        elif len(parts) == 2:
            whole = parts[0] or "0"
            frac = parts[1].ljust(2, "0")[:2]
            return int(whole + frac) * sign
        else:
            return None
    except ValueError:
        return None
