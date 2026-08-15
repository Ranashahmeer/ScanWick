from typing import Callable
import pandas as pd

from app.services.pdf_parsers.kuda import parse_kuda
from app.services.pdf_parsers.alat import parse_alat
from app.services.pdf_parsers.opay import parse_opay
from app.services.pdf_parsers.palmpay import parse_palmpay
from app.services.pdf_parsers.gtbank import parse_gtbank
from app.services.pdf_parsers.alpha_morgan import parse_alpha_morgan
from app.services.pdf_parsers.stanbic import parse_stanbic
from app.services.pdf_parsers.moniepoint import parse_moniepoint
from app.services.pdf_parsers.sterling import parse_sterling

def get_parser_for_bank(bank_name: str) -> Callable[[str], pd.DataFrame]:
    """
    Returns the specific parser function for a given bank name.
    Strictly forbids falling through to a generic parser.
    """
    bank_name_normalized = bank_name.lower().replace(" ", "") if bank_name else ""
    
    if "opay" in bank_name_normalized or "paycom" in bank_name_normalized:
        return parse_opay
    elif "palmpay" in bank_name_normalized:
        return parse_palmpay
    elif "alat" in bank_name_normalized or "wema" in bank_name_normalized:
        return parse_alat
    elif "kuda" in bank_name_normalized:
        return parse_kuda
    elif "gtbank" in bank_name_normalized or "gtco" in bank_name_normalized or "guarantytrust" in bank_name_normalized:
        return parse_gtbank
    elif "alpha" in bank_name_normalized or "morgan" in bank_name_normalized or "alphamorgan" in bank_name_normalized or "alpha-morgan" in bank_name_normalized:
        return parse_alpha_morgan
    elif "stanbic" in bank_name_normalized or "stanbicibtc" in bank_name_normalized or "ibtc" in bank_name_normalized:
        return parse_stanbic
    elif "moniepoint" in bank_name_normalized or "monie" in bank_name_normalized or "microfinance" in bank_name_normalized or "micro" in bank_name_normalized:
        return parse_moniepoint
    elif "sterling" in bank_name_normalized:
        return parse_sterling
    else:
        raise NotImplementedError(
            f"Unsupported bank: '{bank_name}'. "
            "No generic parser is allowed. Please build a specific parser for this bank."
        )
