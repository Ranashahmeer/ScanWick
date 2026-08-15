import re
import pandas as pd
from datetime import datetime
from app.utils.numeric import parse_kobo


def _normalize_gtbank_amount(value: str) -> str:
    """
    GTBank sometimes prints amounts without a leading zero:
    '.10' instead of '0.10'.
    """
    value = value.strip()

    if re.fullmatch(r"\.\d{2}", value):
        return "0" + value

    return value


def parse_gtbank(text: str) -> pd.DataFrame:
    """
    Parses a GTBank / GTCO bank statement.

    GTBank-specific traps:
    - Dates use DD-MMM-YYYY.
    - Account numbers may be masked.
    - Small monetary values may be printed without a leading zero,
      e.g. '.10' or '.97'.
    - Debit/Credit direction is verified against running balance.
    """

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    rows = []

    # Find opening balance.
    opening_balance = None

    for i, line in enumerate(lines):
        if line.lower() == "opening balance":
            if i + 1 < len(lines):
                value = _normalize_gtbank_amount(lines[i + 1])
                opening_balance = parse_kobo(value)
            break

    if opening_balance is None:
        raise ValueError(
            "Could not find GTBank opening balance. "
            "The file format may not match GTBank."
        )

    prev_balance = opening_balance

    date_regex = re.compile(r"^\d{2}-[A-Za-z]{3}-\d{4}$")

    i = 0

    while i < len(lines):
        # Transaction begins with transaction date.
        if not date_regex.match(lines[i]):
            i += 1
            continue

        transaction_date = lines[i]

        # GTBank prints Value Date immediately after Trans Date.
        if i + 1 >= len(lines) or not date_regex.match(lines[i + 1]):
            i += 1
            continue

        value_date = lines[i + 1]

        # Move past the two dates.
        j = i + 2

        # Skip reference noise / quote markers until we reach an amount.
        amounts = []

        while j < len(lines):
            line = lines[j]

            # Stop if another transaction starts unexpectedly.
            if date_regex.match(line):
                break

            normalized = _normalize_gtbank_amount(line)

            if re.fullmatch(r"(?:\d{1,3}(?:,\d{3})*|\d+)?\.\d{2}", normalized):
                amount = parse_kobo(normalized)

                if amount is not None:
                    amounts.append((j, amount))

                # GTBank transaction should contain:
                # debit/credit amount + resulting balance.
                if len(amounts) == 2:
                    break

            j += 1

        if len(amounts) < 2:
            i += 1
            continue

        amount_index, transaction_amount = amounts[0]
        balance_index, balance = amounts[1]

        debit = 0
        credit = 0

        # Determine direction using exact balance arithmetic.
        if prev_balance - transaction_amount == balance:
            debit = transaction_amount

        elif prev_balance + transaction_amount == balance:
            credit = transaction_amount

        else:
            raise ValueError(
                f"GTBank balance mismatch on {transaction_date}: "
                f"previous={prev_balance}, amount={transaction_amount}, "
                f"balance={balance}"
            )

        # After balance comes Originating Branch, then narration.
        narration_lines = []

        narration_start = balance_index + 1

        # Skip originating branch.
        if narration_start < len(lines):
            narration_start += 1

        k = narration_start

        while k < len(lines):
            if date_regex.match(lines[k]):
                break

            # Ignore obvious page/header fields if encountered.
            if lines[k] not in {
                "Trans. Date",
                "Value Date",
                "Reference",
                "Debits",
                "Credits",
                "Balance",
                "Originating Branch",
                "Remarks",
            }:
                narration_lines.append(lines[k])

            k += 1

        narration = " ".join(narration_lines).strip()

        parsed_date = datetime.strptime(
            transaction_date,
            "%d-%b-%Y",
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

        prev_balance = balance
        i = k

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

    if len(df) == 0:
        raise ValueError(
            "Could not extract any transactions. "
            "The file format does not match GTBank. "
            "Did you select the correct bank?"
        )

    return df