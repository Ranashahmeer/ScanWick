import re
import pandas as pd
from datetime import datetime
from app.utils.numeric import parse_kobo

def parse_kuda(text: str) -> pd.DataFrame:
    """
    Parses a Kuda Bank statement.
    Trap 1: Dates are DD/MM/YY
    Trap 2: Internal transfers ("Savings Pockets") look like expenses.
    """
    rows = []
    lines = text.splitlines()
    
    # State machine variables
    current_date = None
    current_narration_parts = []
    current_amount = None
    
    # regex for DD/MM/YY
    date_regex = re.compile(r"^(\d{2}/\d{2}/\d{2})$")
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        date_match = date_regex.match(line)
        if date_match:
            # We found a new transaction date block.
            current_date = date_match.group(1)
            current_narration_parts = []
            current_amount = None
            continue
            
        if current_date is not None:
            # If line is a time, skip it
            if re.match(r"^\d{2}:\d{2}:\d{2}$", line):
                continue
                
            # If line is an amount starting with ₦
            if line.startswith("₦") and current_amount is None:
                current_amount = parse_kobo(line)
                continue
                
            # If line is another ₦, it's the balance (end of block)
            if line.startswith("₦") and current_amount is not None:
                balance = parse_kobo(line)
                narration = " ".join(current_narration_parts).strip()
                
                # Determine debit or credit based on previous balance if possible
                # Wait, without a running previous balance, we can just look at the word "inward transfer" vs "outward transfer"
                # in the narration. Kuda prints "inward transfer" or "outward transfer" or "web payment" or "spend and save"
                is_credit = "inward transfer" in narration.lower() or "cashback" in narration.lower()
                is_debit = "outward transfer" in narration.lower() or "web payment" in narration.lower() or "spend and save" in narration.lower() or "card payment" in narration.lower()
                
                # But sometimes it's "reversal". A reversal of web payment is a credit.
                if "reversal" in narration.lower():
                    is_credit, is_debit = True, False
                    
                # The most foolproof way: calculate from previous balance
                prev_balance = rows[-1]["balance"] if rows else None
                if prev_balance is not None:
                    # Integer math exactly
                    if prev_balance + current_amount == balance:
                        is_credit, is_debit = True, False
                    elif prev_balance - current_amount == balance:
                        is_credit, is_debit = False, True
                
                # Fallback to narration keyword if prev_balance didn't help (e.g., first row)
                debit = current_amount if is_debit else 0
                credit = current_amount if is_credit else 0
                
                # Normalize date to YYYY-MM-DD
                parsed_date = datetime.strptime(current_date, "%d/%m/%y").strftime("%Y-%m-%d")
                
                rows.append({
                    "date": parsed_date,
                    "narration": narration,
                    "debit": debit,
                    "credit": credit,
                    "balance": balance
                })
                
                # Reset for next possible transaction on the same date, or wait for next date
                current_date = None
                continue
                
            # Otherwise it's part of the narration
            current_narration_parts.append(line)
            
    df = pd.DataFrame(rows, columns=["date", "narration", "debit", "credit", "balance"])
    if len(df) == 0:
        raise ValueError("Could not extract any transactions. The file format does not match Kuda. Did you select the correct bank?")
    return df
