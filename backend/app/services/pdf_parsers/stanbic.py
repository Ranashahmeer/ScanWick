import re
from datetime import datetime

import pandas as pd

from app.utils.numeric import parse_kobo


PARTIAL_DATE_RE = re.compile(r"^\d{2}\s+[A-Za-z]{3}$")
FULL_DATE_RE = re.compile(r"^\d{2}\s+[A-Za-z]{3}\s+\d{4}$")
YEAR_RE = re.compile(r"^\d{4}$")

MONEY_RE = re.compile(r"^(?:-|\d[\d,]*\.\d{2})$")

PAGE_RE = re.compile(
    r"^Page\s+\d+\s+of\s+\d+$",
    flags=re.IGNORECASE,
)

HEADER_LINES = {
    "POSTED",
    "DATE",
    "CREATE",
    "NARRATION",
    "DEBIT",
    "CREDIT",
    "BALANCE",
    "NARRATION DEBIT CREDIT BALANCE",
}


def _parse_money(value: str) -> int:
    """
    Convert a Stanbic monetary value to integer minor units.

    Examples:
        "-"        -> 0
        "10.00"    -> 1000
        "3,555.00" -> 355500
    """

    if value == "-":
        return 0

    parsed = parse_kobo(value)

    if parsed is None:
        raise ValueError(
            f"Invalid Stanbic monetary value: {value}"
        )

    return parsed


def _read_date(lines, index):
    """
    Read a Stanbic date.

    PyMuPDF may extract a date as either:

        01 May
        2026

    or:

        01 May 2026

    Returns:
        (iso_date, next_index)

    If no date exists at index:
        (None, index)
    """

    if index >= len(lines):
        return None, index

    line = lines[index]

    # Full date on one line.
    if FULL_DATE_RE.fullmatch(line):
        parsed = datetime.strptime(
            line,
            "%d %b %Y",
        ).strftime("%Y-%m-%d")

        return parsed, index + 1

    # Split date:
    #
    # 01 May
    # 2026
    if (
        PARTIAL_DATE_RE.fullmatch(line)
        and index + 1 < len(lines)
        and YEAR_RE.fullmatch(lines[index + 1])
    ):
        combined = f"{line} {lines[index + 1]}"

        parsed = datetime.strptime(
            combined,
            "%d %b %Y",
        ).strftime("%Y-%m-%d")

        return parsed, index + 2

    return None, index


def _is_page_marker(line: str) -> bool:
    return PAGE_RE.fullmatch(line) is not None


def _is_header(line: str) -> bool:
    return line.upper() in HEADER_LINES


def _find_transaction_start(lines):
    """
    Locate the first transaction table.

    We look for the table's BALANCE header with DEBIT/CREDIT
    appearing shortly before it.
    """

    for i, line in enumerate(lines):

        if line.upper() != "BALANCE":
            continue

        previous = " ".join(
            item.upper()
            for item in lines[max(0, i - 8):i]
        )

        if "DEBIT" in previous and "CREDIT" in previous:
            return i + 1

    return 0


def parse_stanbic(text: str) -> pd.DataFrame:
    """
    Parse a Stanbic IBTC statement.

    Logical transaction layout:

        POSTED DATE
        CREATE DATE
        NARRATION
        DEBIT
        CREDIT
        BALANCE

    Important extraction behavior:

    1. Dates may be:

           01 May
           2026

       or:

           01 May 2026

    2. Empty debit/credit cells are represented by "-".

    3. Narration may span multiple lines.

    4. PDF page boundaries may cause narration to appear
       before its transaction dates.

    5. Repeated table headers may appear between transactions.

    Monetary values are returned as integer minor units.
    """

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    rows = []

    # Some Stanbic PDF rows are extracted in an unusual order.
    # Text belonging to the next transaction can appear before
    # that transaction's dates.
    pending_narration = []

    i = _find_transaction_start(lines)

    while i < len(lines):

        line = lines[i]

        # -------------------------------------------
        # Ignore PDF/table structural noise
        # -------------------------------------------

        if _is_page_marker(line):
            i += 1
            continue

        if _is_header(line):
            i += 1
            continue

        # -------------------------------------------
        # 1. POSTED DATE
        # -------------------------------------------

        posted_date, after_posted = _read_date(
            lines,
            i,
        )

        if posted_date is None:

            # This may be narration emitted before the row's
            # actual date because of PDF extraction ordering.
            #
            # Do not buffer monetary values or partial dates.

            if (
                not MONEY_RE.fullmatch(line)
                and not FULL_DATE_RE.fullmatch(line)
                and not PARTIAL_DATE_RE.fullmatch(line)
                and not YEAR_RE.fullmatch(line)
            ):
                pending_narration.append(line)

            i += 1
            continue

        # -------------------------------------------
        # 2. CREATE DATE
        # -------------------------------------------

        create_date, after_created = _read_date(
            lines,
            after_posted,
        )

        if create_date is None:

            # False-positive date.
            i += 1
            continue

        j = after_created

        # -------------------------------------------
        # 3. NARRATION AFTER DATES
        # -------------------------------------------

        narration_lines = []

        while j < len(lines):

            current = lines[j]

            # Skip page boundaries.
            if _is_page_marker(current):
                j += 1
                continue

            # Skip repeated table headers.
            if _is_header(current):
                j += 1
                continue

            # First monetary value indicates that the
            # debit/credit/balance section has started.
            if MONEY_RE.fullmatch(current):
                break

            narration_lines.append(current)
            j += 1

        # -------------------------------------------
        # 4. DEBIT / CREDIT / BALANCE
        # -------------------------------------------

        if j + 2 >= len(lines):
            break

        debit_raw = lines[j]
        credit_raw = lines[j + 1]
        balance_raw = lines[j + 2]

        if not (
            MONEY_RE.fullmatch(debit_raw)
            and MONEY_RE.fullmatch(credit_raw)
            and MONEY_RE.fullmatch(balance_raw)
        ):

            # This looked like a transaction date but wasn't
            # followed by the expected monetary structure.
            i += 1
            continue

        debit = _parse_money(debit_raw)
        credit = _parse_money(credit_raw)
        balance = _parse_money(balance_raw)

        # -------------------------------------------
        # 5. NARRATION
        # -------------------------------------------

        all_narration = []

        if pending_narration:
            all_narration.extend(
                pending_narration
            )

        all_narration.extend(
            narration_lines
        )

        narration = " ".join(
            all_narration
        ).strip()

        # The buffered text has now been consumed.
        pending_narration = []

        # -------------------------------------------
        # 6. SANITY CHECKS
        # -------------------------------------------

        if debit and credit:
            raise ValueError(
                f"Stanbic transaction has both debit "
                f"and credit on {posted_date}: "
                f"debit={debit}, credit={credit}"
            )

        # Do not fail just because narration is empty.
        #
        # Some Stanbic rows can be reordered across PDF
        # page boundaries. Monetary correctness is more
        # important than inventing narration.
        if not narration:
            narration = "UNKNOWN"

        # -------------------------------------------
        # 7. SAVE TRANSACTION
        # -------------------------------------------

        rows.append(
            {
                "date": posted_date,
                "narration": narration,
                "debit": debit,
                "credit": credit,
                "balance": balance,
            }
        )

        i = j + 3

    # -----------------------------------------------
    # DataFrame
    # -----------------------------------------------

    df = pd.DataFrame(
        rows,
        columns=[
            "date",
            "narration",
            "debit",
            "credit",
            "balance",
        ],
    )

    if df.empty:
        raise ValueError(
            "Could not extract any transactions. "
            "The file format does not match Stanbic IBTC. "
            "Did you select the correct bank?"
        )

    return df