import re

import pandas as pd

from app.utils.numeric import parse_kobo


YEAR_START_RE = re.compile(r"^20\d{2}-$")
MONTH_RE = re.compile(r"^\d{2}-$")
DAY_TIME_RE = re.compile(r"^(?P<day>\d{2})T")

MONEY_RE = re.compile(
    r"^\d[\d,]*\.\d{2}$"
)

TRANSACTION_REF_RE = re.compile(
    r"_(?:DEBIT|CREDIT)_\d"
)


def _parse_money(value: str) -> int:
    parsed = parse_kobo(value)

    if parsed is None:
        raise ValueError(
            f"Invalid Moniepoint monetary value: {value}"
        )

    return parsed


def _extract_date(segment: list[str]) -> str:
    """
    Moniepoint timestamps are commonly extracted as:

        2025-
        08-
        13T19:
        47:36

    Some page boundaries reorder the time fragments, so we only
    depend on year, month, and the DD portion of DDThh:.

    Returns YYYY-MM-DD.
    """

    if len(segment) < 3:
        raise ValueError(
            "Incomplete Moniepoint transaction timestamp."
        )

    year_line = segment[0]
    month_line = segment[1]

    if not YEAR_START_RE.fullmatch(year_line):
        raise ValueError(
            f"Invalid Moniepoint year fragment: {year_line}"
        )

    if not MONTH_RE.fullmatch(month_line):
        raise ValueError(
            f"Invalid Moniepoint month fragment: {month_line}"
        )

    day = None

    # A few rows are reordered around PDF page boundaries,
    # so search the beginning of the transaction rather than
    # assuming DDThh: is always segment[2].
    for line in segment[:12]:
        match = DAY_TIME_RE.match(line)

        if match:
            day = match.group("day")
            break

    if day is None:
        raise ValueError(
            "Could not determine Moniepoint transaction day."
        )

    year = year_line[:-1]
    month = month_line[:-1]

    return f"{year}-{month}-{day}"

def _extract_summary_balance(lines, label: str) -> int:
    """
    Extract a balance from the statement summary.

    Example:
        Opening Balance
        74,985.72
    """

    for i, line in enumerate(lines):
        if line.strip().lower() == label.lower():

            # Search a few lines ahead because PDF extraction
            # can occasionally insert whitespace/header fragments.
            for j in range(i + 1, min(i + 5, len(lines))):
                if MONEY_RE.fullmatch(lines[j]):
                    return _parse_money(lines[j])

    raise ValueError(
        f"Could not find Moniepoint {label}."
    )


def _order_by_balance_chain(
    rows: list[dict],
    opening_balance: int,
) -> list[dict]:
    """
    Reconstruct ledger order using exact balance continuity.

    This is necessary because Moniepoint PDF extraction can emit
    multiple transactions with the same timestamp out of order.

    Rule:
        next.balance_before == previous.balance_after
    """

    remaining = list(rows)
    ordered = []

    current_balance = opening_balance

    while remaining:

        candidates = [
            row
            for row in remaining
            if row["_balance_before"] == current_balance
        ]

        if not candidates:
            raise ValueError(
                "Could not reconstruct Moniepoint transaction "
                f"order after balance {current_balance}. "
                f"{len(remaining)} transaction(s) remain."
            )

        # Identical balances can legitimately appear at different
        # points in a long statement. When multiple rows qualify,
        # preserve the earliest PDF extraction position.
        row = min(
            candidates,
            key=lambda item: item["_source_index"],
        )

        ordered.append(row)
        remaining.remove(row)

        current_balance = row["balance"]

    return ordered

def parse_moniepoint(text: str) -> pd.DataFrame:
    """
    Parse a Moniepoint account statement.

    Moniepoint's source table contains substantially more data than
    Scanwick's canonical transaction representation:

        Date
        Transaction Type
        Transaction Status
        Transaction Ref
        Transaction Amount
        Settlement Debit
        Settlement Credit
        Balance Before
        Balance After
        Charge
        Beneficiary
        Source
        Narration
        ...

    This parser intentionally uses Settlement Debit / Settlement Credit
    because those values represent the actual movement applied to the
    account balance.

    Two monetary layouts occur in the supplied Moniepoint format:

    6 monetary values:
        transaction_amount
        settlement_debit
        settlement_credit
        balance_before
        balance_after
        charge

    4 monetary values:
        settlement_debit
        settlement_credit
        balance_before
        balance_after

    Every row is validated using exact integer arithmetic:

        balance_before - debit + credit == balance_after
    """

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    # A transaction starts wherever the PDF extraction emits:
    #
    # 2025-
    # 08-
    # 13T19:
    # ...
    starts = [
        i
        for i, line in enumerate(lines)
        if YEAR_START_RE.fullmatch(line)
    ]

    if not starts:
        raise ValueError(
            "Could not find any Moniepoint transaction timestamps."
        )

    rows = []

    for position, start in enumerate(starts):
        end = (
            starts[position + 1]
            if position + 1 < len(starts)
            else len(lines)
        )

        segment = lines[start:end]

        transaction_date = _extract_date(
            segment
        )

        # --------------------------------------------------
        # Locate transaction reference
        # --------------------------------------------------

        references = [
            (i, line)
            for i, line in enumerate(segment)
            if TRANSACTION_REF_RE.search(line)
        ]

        if len(references) != 1:
            raise ValueError(
                f"Expected exactly one Moniepoint transaction "
                f"reference on {transaction_date}, "
                f"found {len(references)}."
            )

        ref_index, transaction_ref = references[0]

        # --------------------------------------------------
        # Monetary fields
        # --------------------------------------------------

        monetary_fields = [
            (i, line)
            for i, line in enumerate(
                segment[ref_index + 1:],
                start=ref_index + 1,
            )
            if MONEY_RE.fullmatch(line)
        ]

        if len(monetary_fields) not in (4, 6):
            raise ValueError(
                f"Unexpected Moniepoint monetary layout on "
                f"{transaction_date}: expected 4 or 6 values, "
                f"got {len(monetary_fields)} "
                f"for {transaction_ref}."
            )

        values = [
            _parse_money(value)
            for _, value in monetary_fields
        ]

        if len(values) == 6:
            # Transaction Amount is informational.
            # Charge is also already reflected in Settlement Debit.
            (
                transaction_amount,
                debit,
                credit,
                balance_before,
                balance_after,
                charge,
            ) = values

        else:
            (
                debit,
                credit,
                balance_before,
                balance_after,
            ) = values

        # --------------------------------------------------
        # Financial integrity checks
        # --------------------------------------------------

        if debit and credit:
            raise ValueError(
                f"Moniepoint transaction has both debit "
                f"and credit values on {transaction_date}: "
                f"{transaction_ref}"
            )

        expected_balance = (
            balance_before
            - debit
            + credit
        )

        if expected_balance != balance_after:
            raise ValueError(
                f"Moniepoint balance mismatch on "
                f"{transaction_date}: "
                f"before={balance_before}, "
                f"debit={debit}, "
                f"credit={credit}, "
                f"expected={expected_balance}, "
                f"actual={balance_after}, "
                f"ref={transaction_ref}"
            )

        # --------------------------------------------------
        # Narration
        # --------------------------------------------------

        # Everything after the final monetary field belongs to
        # beneficiary/source/narration metadata.
        last_money_index = monetary_fields[-1][0]

        narration_parts = [
            line
            for line in segment[last_money_index + 1:]
            if line
        ]

        narration = " ".join(
            narration_parts
        ).strip()

        # Some fee rows contain little/no explicit narration.
        # The transaction reference is safer than inventing text.
        if not narration:
            narration = transaction_ref

        # --------------------------------------------------
        # Canonical row
        # --------------------------------------------------

        rows.append(
            {
                "date": transaction_date,
                "narration": narration,
                "debit": debit,
                "credit": credit,
                "balance": balance_after,

                # Internal fields used only to reconstruct ledger order.
                "_balance_before": balance_before,
                "_source_index": position,
            }
        )
        
    opening_balance = _extract_summary_balance(
    lines,
    "Opening Balance",
)

    closing_balance = _extract_summary_balance(
        lines,
        "Closing Balance",
    )

    rows = _order_by_balance_chain(
        rows,
        opening_balance,
    )

    # Verify the reconstructed ledger actually reaches
    # the bank's stated closing balance.
    if rows[-1]["balance"] != closing_balance:
        raise ValueError(
            "Moniepoint closing balance mismatch: "
            f"parsed={rows[-1]['balance']}, "
            f"statement={closing_balance}"
        )

    df = pd.DataFrame(
        [
            {
                "date": row["date"],
                "narration": row["narration"],
                "debit": row["debit"],
                "credit": row["credit"],
                "balance": row["balance"],
            }
            for row in rows
        ],
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
            "The file format does not match Moniepoint."
        )

    return df