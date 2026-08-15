import re
import pandas as pd
import numpy as np
from app.utils.numeric import parse_kobo
from datetime import datetime

def parse_palmpay(text: str) -> pd.DataFrame:
    """
    Parses a PalmPay statement.
    """
    rows = []
    lines = text.splitlines()
    
    current_date = None
    current_narration_parts = []
    
    # regex for MM/DD/YYYY hh:mm:ss AM/PM
    date_regex = re.compile(r"^(\d{2}/\d{2}/\d{4})\s+\d{2}:\d{2}:\d{2}\s+[AP]M$")
    phone_regex = re.compile(r"(0[789][01]\s?\d{3}\s?\d{4})")
    
    account_number = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Try to find the phone number for account identity
        if not account_number:
            match = phone_regex.search(line)
            if match:
                account_number = match.group(1).replace(" ", "")
            
        date_match = date_regex.match(line)
        if date_match:
            current_date = date_match.group(1)
            current_narration_parts = []
            continue
            
        if current_date is not None:
            # Check if it's an amount line (+123.45 or -123.45)
            if re.match(r"^[+-]\d+(,\d{3})*(\.\d+)?$", line):
                amount = 0 if line == "--" else parse_kobo(line)
                
                is_credit = line.startswith("+")
                debit = abs(amount) if not is_credit else 0
                credit = abs(amount) if is_credit else 0
                
                narration = " ".join(current_narration_parts).strip()
                
                # Normalize date to YYYY-MM-DD
                parsed_date = datetime.strptime(current_date, "%m/%d/%Y").strftime("%Y-%m-%d")
                
                rows.append({
                    "date": parsed_date,
                    "narration": narration,
                    "debit": debit,
                    "credit": credit,
                    "balance": np.nan,
                    "account_number": account_number
                })
                
                # We stop collecting narration.
                current_date = None
                continue
                
            # Otherwise, collect narration
            current_narration_parts.append(line)
            
    df = pd.DataFrame(rows, columns=["date", "narration", "debit", "credit", "balance", "account_number"])
    if len(df) == 0:
        raise ValueError("Could not extract any transactions. The file format does not match PalmPay. Did you select the correct bank?")
    return df
