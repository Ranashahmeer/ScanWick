import re
import pandas as pd
from datetime import datetime
from app.utils.numeric import parse_kobo


def parse_alpha_morgan(text: str) -> pd.DataFrame:
    """
    Parses an Alpha Morgan Bank statement.

    Source-specific behavior:
    - Transaction dates use DD MMM YYYY, e.g. "05 Aug 2026".
    - Statement header/period may use ordinal dates like "August 1st, 2026".
      We do NOT use the header to infer transaction date format.
    - Columns are:
      Trans Date, Reference, Value Date, Debit, Credit, Balance, Narration.
    - Debit/Credit may be blank, so transaction direction is verified
      against the running balance.
    """

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    rows = []

    # Find opening balance
    opening_balance = None

    for i, line in enumerate(lines):
        if line.lower() == "opening balance":
            if i + 1 < len(lines):
                opening_balance = parse_kobo(lines[i + 1])
            break

    if opening_balance is None:
        raise ValueError(
            "Could not find Alpha Morgan opening balance. "
            "The file format may not match Alpha Morgan."
        )

    prev_balance = opening_balance

    date_regex = re.compile(
        r"^\d{2}\s+[A-Za-z]{3}\s+\d{4}$"
    )

    # Start after the transaction-table header if possible
    try:
        start_index = lines.index("Trans Date") + 1
    except ValueError:
        start_index = 0

    i = start_index

    while i < len(lines):

        # Transaction must begin with a row date
        if not date_regex.match(lines[i]):
            i += 1
            continue

        trans_date = lines[i]

        # Expected:
        # date
        # reference
        # value date
        if i + 2 >= len(lines):
            break

        reference = lines[i + 1]
        value_date = lines[i + 2]

        if not date_regex.match(value_date):
            i += 1
            continue

        j = i + 3

        # Collect numeric values before narration begins.
        #
        # Alpha Morgan visually has:
        # Debit | Credit | Balance
        #
        # but blank debit/credit cells disappear in text extraction.
        numeric_values = []

        while j < len(lines):

            if date_regex.match(lines[j]):
                break

            value = parse_kobo(lines[j])

            if value is not None:
                numeric_values.append((j, value))

                # At most:
                # debit + credit + balance
                #
                # Usually only 2 values survive because one
                # of debit/credit is blank.
                if len(numeric_values) >= 3:
                    break
            else:
                # Once we've collected at least two money values,
                # the next non-number is narration.
                if len(numeric_values) >= 2:
                    break

            j += 1

        if len(numeric_values) < 2:
            i += 1
            continue

        # Balance is always the final monetary value.
        balance_index, balance = numeric_values[-1]

        transaction_values = [
            value for _, value in numeric_values[:-1]
        ]

        if not transaction_values:
            i += 1
            continue

        debit = 0
        credit = 0

        #
        # Determine direction from balance arithmetic instead of
        # relying on blank columns surviving PDF extraction.
        #
        matched = False

        for amount in transaction_values:

            if prev_balance - amount == balance:
                debit = amount
                matched = True
                break

            if prev_balance + amount == balance:
                credit = amount
                matched = True
                break

        if not matched:
            raise ValueError(
                f"Alpha Morgan balance mismatch on {trans_date}: "
                f"previous={prev_balance}, "
                f"values={transaction_values}, "
                f"balance={balance}"
            )

        # Everything after balance until the next transaction date
        # is narration.
        narration_lines = []

        k = balance_index + 1

        while k < len(lines):

            if date_regex.match(lines[k]):
                break

            # Stop once statement footer begins
            if lines[k].upper().startswith(
                "PLEASE DIRECT ALL ENQUIRIES"
            ):
                break

            narration_lines.append(lines[k])
            k += 1

        narration = " ".join(narration_lines).strip()

        parsed_date = datetime.strptime(
            trans_date,
            "%d %b %Y",
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
            "The file format does not match Alpha Morgan. "
            "Did you select the correct bank?"
        )

    return df