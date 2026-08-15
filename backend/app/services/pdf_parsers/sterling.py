import re
from datetime import datetime

import pandas as pd

from app.utils.numeric import parse_kobo


DATE_RE = re.compile(
    r"^\d{2}/[A-Za-z]{3}/\d{4}$"
)

MONEY_RE = re.compile(
    r"^(?:-|(?:\d{1,3}(?:,\d{3})*|\d+)\.\d{2})$"
)

PLAIN_MONEY_RE = re.compile(
    r"^(?:\d{1,3}(?:,\d{3})*|\d+)\.\d{2}$"
)

TOTAL_RE = re.compile(
    r"^Total\s+(Credit|Debit)\s+\(\d+\):\s+"
    r"([\d,]+\.\d{2})\s+NGN$",
    flags=re.IGNORECASE,
)


def _parse_money(value: str) -> int:
    """
    Sterling uses "-" for blank Money In / Money Out cells.
    """

    if value == "-":
        return 0

    parsed = parse_kobo(value)

    if parsed is None:
        raise ValueError(
            f"Invalid Sterling monetary value: {value}"
        )

    return parsed


def _extract_labeled_amount(
    lines: list[str],
    label: str,
) -> int:
    """
    Example:

        Opening balance:
        21.88
    """

    for i, line in enumerate(lines):

        if line.lower() != label.lower():
            continue

        for j in range(
            i + 1,
            min(i + 4, len(lines)),
        ):
            if PLAIN_MONEY_RE.fullmatch(lines[j]):
                return _parse_money(lines[j])

    raise ValueError(
        f"Could not find Sterling {label}"
    )


def parse_sterling(text: str) -> pd.DataFrame:
    """
    Parse a Sterling Bank statement.

    Expected table:

        Trans Date
        Value Date
        Reference/Session ID
        Channel
        Narration
        Money In
        Money Out
        Balance

    Transaction dates use:

        DD/Mon/YYYY

    Example:

        01/Jul/2026

    The statement-period header uses a different format and must not
    be used to infer transaction dates.

    Money In  -> credit
    Money Out -> debit
    """

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    opening_balance = _extract_labeled_amount(
        lines,
        "Opening balance:",
    )

    closing_balance = _extract_labeled_amount(
        lines,
        "Closing balance:",
    )

    expected_credit = None
    expected_debit = None

    for line in lines:

        match = TOTAL_RE.fullmatch(line)

        if not match:
            continue

        direction = match.group(1).lower()
        amount = _parse_money(
            match.group(2)
        )

        if direction == "credit":
            expected_credit = amount

        elif direction == "debit":
            expected_debit = amount

    rows = []
    previous_balance = opening_balance

    i = 0

    while i < len(lines):

        # ---------------------------------
        # Transaction date
        # ---------------------------------

        if not DATE_RE.fullmatch(lines[i]):
            i += 1
            continue

        trans_date = lines[i]

        # Sterling puts Value Date immediately after
        # transaction date.
        if (
            i + 1 >= len(lines)
            or not DATE_RE.fullmatch(lines[i + 1])
        ):
            i += 1
            continue

        value_date = lines[i + 1]

        # ---------------------------------
        # Locate:
        #
        # Money In
        # Money Out
        # Balance
        #
        # They appear as three consecutive
        # monetary tokens.
        # ---------------------------------

        j = i + 2
        money_index = None

        while j + 2 < len(lines):

            if (
                MONEY_RE.fullmatch(lines[j])
                and MONEY_RE.fullmatch(lines[j + 1])
                and MONEY_RE.fullmatch(lines[j + 2])
            ):
                money_index = j
                break

            # Don't accidentally consume the next
            # transaction if this row is malformed.
            if (
                j > i + 2
                and DATE_RE.fullmatch(lines[j])
            ):
                break

            j += 1

        if money_index is None:
            i += 1
            continue

        money_in_raw = lines[money_index]
        money_out_raw = lines[money_index + 1]
        balance_raw = lines[money_index + 2]

        credit = _parse_money(
            money_in_raw
        )

        debit = _parse_money(
            money_out_raw
        )

        balance = _parse_money(
            balance_raw
        )

        # ---------------------------------
        # Metadata / narration
        # ---------------------------------

        metadata = lines[
            i + 2:money_index
        ]

        # First two fields are normally:
        #
        # Reference/Session ID
        # Channel
        #
        # Everything after them is narration.
        if len(metadata) >= 2:
            narration_parts = metadata[2:]
        else:
            narration_parts = metadata

        narration = " ".join(
            narration_parts
        ).strip()

        if not narration:
            narration = "UNKNOWN"

        # ---------------------------------
        # Financial integrity
        # ---------------------------------

        if debit and credit:
            raise ValueError(
                f"Sterling transaction has both "
                f"Money In and Money Out on "
                f"{trans_date}"
            )

        expected_balance = (
            previous_balance
            - debit
            + credit
        )

        if expected_balance != balance:
            raise ValueError(
                f"Sterling balance mismatch on "
                f"{trans_date}: "
                f"previous={previous_balance}, "
                f"debit={debit}, "
                f"credit={credit}, "
                f"expected={expected_balance}, "
                f"actual={balance}"
            )

        parsed_date = datetime.strptime(
            trans_date,
            "%d/%b/%Y",
        ).strftime("%Y-%m-%d")

        rows.append(
            {
                "date": parsed_date,
                "narration": narration,
                "debit": debit,
                "credit": credit,
                "balance": balance,
            }
        )

        previous_balance = balance

        i = money_index + 3

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
            "The file format does not match Sterling Bank."
        )

    # ---------------------------------
    # Full-statement reconciliation
    # ---------------------------------

    if df.iloc[-1]["balance"] != closing_balance:
        raise ValueError(
            "Sterling closing balance mismatch: "
            f"parsed={df.iloc[-1]['balance']}, "
            f"statement={closing_balance}"
        )

    if expected_credit is not None:
        actual_credit = int(
            df["credit"].sum()
        )

        if actual_credit != expected_credit:
            raise ValueError(
                "Sterling total credit mismatch: "
                f"parsed={actual_credit}, "
                f"statement={expected_credit}"
            )

    if expected_debit is not None:
        actual_debit = int(
            df["debit"].sum()
        )

        if actual_debit != expected_debit:
            raise ValueError(
                "Sterling total debit mismatch: "
                f"parsed={actual_debit}, "
                f"statement={expected_debit}"
            )

    return df