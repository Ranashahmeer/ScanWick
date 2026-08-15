import re
import pandas as pd
from datetime import datetime
from app.utils.numeric import parse_kobo

def parse_opay(text: str) -> pd.DataFrame:
    """
    Parses an OPay statement.
    """
    rows = []
    lines = text.splitlines()
    
    date_regex = re.compile(r"^(\d{2}\s[A-Za-z]{3}\s\d{4})\s\d{2}:\d{2}:\d{2}$")
    
    current_date = None
    current_narration = []
    amounts_collected = []
    header_count = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line == "Trans. Time":
            header_count += 1
            if header_count > 1:
                break
            continue
            
        date_match = date_regex.match(line)
        if date_match:
            current_date = date_match.group(1)
            current_narration = []
            amounts_collected = []
            continue
            
        if current_date is not None:
            # Skip the redundant "Value Date" which looks like "01 Jun 2026"
            if re.match(r"^\d{2}\s[A-Za-z]{3}\s\d{4}$", line):
                continue
                
            # If line is an amount or "--"
            is_amount = re.match(r"^\d{1,3}(,\d{3})*\.\d{2}$", line)
            if line == "--" or is_amount:
                # We expect exactly 3 amount lines: Debit, Credit, Balance After
                val = 0 if line == "--" else parse_kobo(line)
                amounts_collected.append(val)
                
                if len(amounts_collected) == 3:
                    debit, credit, balance = amounts_collected
                    narration = " ".join(current_narration).strip()
                    parsed_date = datetime.strptime(current_date, "%d %b %Y").strftime("%Y-%m-%d")
                    
                    rows.append({
                        "date": parsed_date,
                        "narration": narration,
                        "debit": debit,
                        "credit": credit,
                        "balance": balance
                    })
                    current_date = None  # reset for next block
                continue
            
            # If we haven't collected any amounts yet, it's narration
            if len(amounts_collected) == 0:
                current_narration.append(line)
                
    df = pd.DataFrame(rows, columns=["date", "narration", "debit", "credit", "balance"])
    if len(df) == 0:
        raise ValueError("Could not extract any transactions. The file format does not match OPay. Did you select the correct bank?")
    return df
