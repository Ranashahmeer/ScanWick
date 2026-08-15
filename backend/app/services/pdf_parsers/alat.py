import re
import pandas as pd
from datetime import datetime
from app.utils.numeric import parse_kobo

def parse_alat(text: str) -> pd.DataFrame:
    """
    Parses an ALAT (Wema) Bank statement.
    Trap: Dates wrap across two physical lines (e.g. '04-Aug-' \\n '2025').
    Trap: Only one amount column is extracted, must infer Debit/Credit via balance delta.
    """
    rows = []
    lines = text.splitlines()
    
    # 1. Find the Opening Balance
    opening_balance = 0
    for i, line in enumerate(lines):
        if line.strip() == "Opening Balance":
            # The next line is the balance (e.g. ₦80,898.94)
            if i + 1 < len(lines):
                val = parse_kobo(lines[i+1])
                if val is not None:
                    opening_balance = val
            break
            
    # 2. Parse transactions
    date_part1_regex = re.compile(r"^(\d{2}-[A-Za-z]{3}-)$")
    date_part2_regex = re.compile(r"^(\d{4})$")
    
    current_date_str = None
    current_reference = None
    current_narration = []
    current_amount = None
    
    state = "SEEK_DATE" # SEEK_DATE, SEEK_YEAR, SEEK_REF, SEEK_NARRATION, SEEK_AMOUNT, SEEK_BALANCE
    
    prev_balance = opening_balance
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if state == "SEEK_DATE":
            match = date_part1_regex.match(line)
            if match:
                current_date_str = match.group(1)
                state = "SEEK_YEAR"
                
        elif state == "SEEK_YEAR":
            match = date_part2_regex.match(line)
            if match:
                current_date_str += match.group(1)
                state = "SEEK_REF"
            else:
                # false alarm
                state = "SEEK_DATE"
                
        elif state == "SEEK_REF":
            current_reference = line
            current_narration = []
            state = "SEEK_NARRATION"
            
        elif state == "SEEK_NARRATION":
            # Narration continues until we hit an amount
            is_amount = re.match(r"^\d{1,3}(,\d{3})*(\.\d{2})$", line)
            if is_amount:
                current_amount = parse_kobo(line)
                state = "SEEK_BALANCE"
            else:
                current_narration.append(line)
                
        elif state == "SEEK_BALANCE":
            is_amount = re.match(r"^\d{1,3}(,\d{3})*(\.\d{2})$", line)
            if is_amount:
                balance = parse_kobo(line)
                
                # Determine credit/debit
                debit = 0
                credit = 0
                
                # Exact integer math
                if prev_balance + current_amount == balance:
                    credit = current_amount
                elif prev_balance - current_amount == balance:
                    debit = current_amount
                else:
                    # Fallback if math doesn't perfectly align (shouldn't happen)
                    narration_lower = " ".join(current_narration).lower()
                    if "transfer to" in narration_lower or "vat" in narration_lower or "comm" in narration_lower or "levy" in narration_lower or "charges" in narration_lower:
                        debit = current_amount
                    else:
                        credit = current_amount

                narration = " ".join(current_narration).strip()
                parsed_date = datetime.strptime(current_date_str, "%d-%b-%Y").strftime("%Y-%m-%d")
                
                rows.append({
                    "date": parsed_date,
                    "narration": narration,
                    "debit": debit,
                    "credit": credit,
                    "balance": balance
                })
                
                prev_balance = balance
                state = "SEEK_DATE"
            else:
                # If we didn't find a balance, maybe the previous amount was actually part of narration
                # (unlikely, but reset to seek date just in case)
                state = "SEEK_DATE"

    df = pd.DataFrame(rows, columns=["date", "narration", "debit", "credit", "balance"])
    if len(df) == 0:
        raise ValueError("Could not extract any transactions. The file format does not match ALAT. Did you select the correct bank?")
    return df
