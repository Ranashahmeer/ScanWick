import pytest
import os
import fitz
import numpy as np
import pandas as pd

from app.services.pdf_parsers import get_parser_for_bank

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures", "statements")

def get_pdf_text(filename: str) -> str:
    path = os.path.join(FIXTURE_DIR, filename)
    if not os.path.exists(path):
        pytest.skip(f"Fixture {filename} not found")
    
    doc = fitz.open(path)
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text

def test_kuda_parser():
    text = get_pdf_text("kuda.pdf")
    parser = get_parser_for_bank("kuda")
    df = parser(text)
    
    assert len(df) > 0, "Should parse at least 1 transaction"
    # Ensure standard columns are present
    for col in ["date", "narration", "debit", "credit", "balance"]:
        assert col in df.columns
        
    # Verify date is formatted properly (YYYY-MM-DD)
    assert len(df.iloc[0]["date"].split("-")) == 3

def test_opay_parser():
    text = get_pdf_text("opay.pdf")
    parser = get_parser_for_bank("opay")
    df = parser(text)
    
    assert len(df) > 0, "Should parse at least 1 transaction"
    
    # OPay has a balance column
    assert "balance" in df.columns
    assert not pd.isna(df.iloc[0]["balance"])
    
    # Verify date formatting
    assert len(df.iloc[0]["date"].split("-")) == 3

def test_palmpay_parser():
    text = get_pdf_text("palmpay.pdf")
    parser = get_parser_for_bank("palmpay")
    df = parser(text)
    
    assert len(df) > 0, "Should parse at least 1 transaction"
    
    # PalmPay has no balance column, ensure it's NaN
    assert pd.isna(df.iloc[0]["balance"]) or np.isnan(df.iloc[0]["balance"])

def test_alat_parser():
    text = get_pdf_text("alat.pdf")
    parser = get_parser_for_bank("alat")
    df = parser(text)
    
    assert len(df) > 0, "Should parse at least 1 transaction"
    
    # Check that credit or debit are correctly assigned from single amount column
    for _, row in df.iterrows():
        assert (row["debit"] > 0) != (row["credit"] > 0) or (row["debit"] == 0 and row["credit"] == 0), \
               "A transaction must be either debit or credit, not both or neither unless amount is 0"

def test_gtbank_parser():
    path = os.path.join(FIXTURE_DIR, "gtbank.txt")

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    parser = get_parser_for_bank("GTBank")
    df = parser(text)

    assert len(df) == 2

    for col in ["date", "narration", "debit", "credit", "balance"]:
        assert col in df.columns

    first = df.iloc[0]

    assert first["date"] == "2026-07-31"
    assert first["debit"] == 10
    assert first["credit"] == 0
    assert first["balance"] == 14336
    assert "WITHHOLDING TAX" in first["narration"]

    second = df.iloc[1]

    assert second["date"] == "2026-07-31"
    assert second["debit"] == 0
    assert second["credit"] == 97
    assert second["balance"] == 14433
    assert "INTEREST CAPITALISED" in second["narration"]
    
def test_alpha_morgan_parser():
    path = os.path.join(FIXTURE_DIR, "alphamorgan.txt")

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    parser = get_parser_for_bank("Alpha Morgan")
    df = parser(text)

    assert len(df) == 3

    for col in ["date", "narration", "debit", "credit", "balance"]:
        assert col in df.columns

    first = df.iloc[0]

    assert first["date"] == "2026-08-05"
    assert first["debit"] == 0
    assert first["credit"] == 520000
    assert first["balance"] == 520000
    assert "From Opay Digit" in first["narration"]

    second = df.iloc[1]

    assert second["date"] == "2026-08-09"
    assert second["debit"] == 10000
    assert second["credit"] == 0
    assert second["balance"] == 510000
    assert "NIP/RIB" in second["narration"]

    third = df.iloc[2]

    assert third["date"] == "2026-08-09"
    assert third["debit"] == 1075
    assert third["credit"] == 0
    assert third["balance"] == 508925
    assert "NIP/RIB" in third["narration"]
    
    
def test_stanbic_parser():
    path = os.path.join(FIXTURE_DIR, "stanbic.txt")

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    parser = get_parser_for_bank("Stanbic IBTC")
    df = parser(text)

    assert not df.empty

    for col in ["date", "narration", "debit", "credit", "balance"]:
        assert col in df.columns

    first = df.iloc[0]

    assert first["date"] == "2026-05-01"
    assert first["debit"] == 0
    assert first["credit"] == 355500
    assert first["balance"] == 974015
    assert "PiggyVest" in first["narration"]

    second = df.iloc[1]

    assert second["date"] == "2026-05-01"
    assert second["debit"] == 340000
    assert second["credit"] == 0
    assert second["balance"] == 634015
    
def test_moniepoint_parser():
    path = os.path.join(
        FIXTURE_DIR,
        "moniepoint.txt",
    )

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    parser = get_parser_for_bank(
        "Moniepoint MFB"
    )

    df = parser(text)

    # Full supplied fixture
    assert len(df) == 442

    for col in [
        "date",
        "narration",
        "debit",
        "credit",
        "balance",
    ]:
        assert col in df.columns

    # ---------------------------------
    # First transaction
    # ---------------------------------

    first = df.iloc[0]

    assert first["date"] == "2025-08-13"

    # 9,900 transaction + 10 charge
    # = 9,910 settlement debit
    assert first["debit"] == 991000
    assert first["credit"] == 0

    assert first["balance"] == 6507572

    # ---------------------------------
    # First incoming transfer
    # ---------------------------------

    second = df.iloc[1]

    assert second["date"] == "2025-08-14"
    assert second["debit"] == 0
    assert second["credit"] == 1000000
    assert second["balance"] == 7507572

    # ---------------------------------
    # Full-statement reconciliation
    # ---------------------------------

    assert int(df["debit"].sum()) == 261893350
    assert int(df["credit"].sum()) == 255905487

    # Statement closes at NGN 15,107.09
    assert df.iloc[-1]["balance"] == 1510709
    assert df.iloc[-1]["date"] == "2026-08-09"
    
def test_sterling_parser():
    path = os.path.join(
        FIXTURE_DIR,
        "sterling.txt",
    )

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    parser = get_parser_for_bank(
        "Sterling Bank"
    )

    df = parser(text)

    assert len(df) == 1

    for col in [
        "date",
        "narration",
        "debit",
        "credit",
        "balance",
    ]:
        assert col in df.columns

    first = df.iloc[0]

    assert first["date"] == "2026-07-01"

    assert first["debit"] == 0
    assert first["credit"] == 14
    assert first["balance"] == 2202

    assert (
        "Credit Interest Capitalise"
        in first["narration"]
    )

    assert int(df["debit"].sum()) == 0
    assert int(df["credit"].sum()) == 14