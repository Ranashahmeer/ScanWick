import asyncio
import re
import uuid
from typing import Optional

import fitz  # PyMuPDF
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_app import celery_app
from app.database import async_session
from app.models.bank_transactions import BankTransactionDataSource
from app.models.reconciliation_reports import AnalyzerType
from app.services.bank_ingestion import ingest_bank_dataframe
from app.services.pdf_parsers import get_parser_for_bank
from app.services.upload_staging import delete_staged_upload, mark_upload_failed, read_staged_bytes

_MAX_PDF_PAGES = 100  # audit #20: cap rasterization/parsing cost on a pathological page count

# A text PDF can still have odd spacing around punctuation depending on the
# font/kerning it was produced with (e.g. "3216000. 00"), so the
# digit-grouping for amounts tolerates internal whitespace, normalized away
# in _clean_line before this pattern runs.
_LINE_PATTERN = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<narration>.+?)\s+"
    r"(?P<debit>\d+\.\d{2})\s+(?P<credit>\d+\.\d{2})\s+(?P<balance>\d+\.\d{2})\s*$"
)


class ScannedPdfNotSupportedError(ValueError):
    """Raised when a PDF has no extractable text layer at all — i.e. it's a
    scanned/image-only statement. By design (per product decision), this
    pipeline only reads a PDF's real text layer; it does not render pages to
    images or run OCR on them."""


class PasswordRequiredError(ValueError):
    """PDF is encrypted and no password was supplied."""


class WrongPasswordError(ValueError):
    """PDF is encrypted and the supplied password did not unlock it."""


def unlock_pdf_bytes(pdf_bytes: bytes, password: Optional[str] = None) -> bytes:
    """Returns plaintext PDF bytes. Password is used only in-memory to open an
    encrypted file — never written to staging/disk. Unencrypted PDFs are
    returned unchanged (password ignored)."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        if doc.is_encrypted:
            if not password:
                raise PasswordRequiredError(
                    "This statement is password-protected. Enter the password your bank uses."
                )
            # authenticate returns >0 on success; 0 means wrong password
            if not doc.authenticate(password):
                raise WrongPasswordError(
                    "That password did not open this statement. Check your bank's "
                    "password convention and try again."
                )
        # Re-save without encryption so Celery workers never need the password.
        unlocked = doc.tobytes()
    finally:
        doc.close()
    return unlocked


def extract_pdf_text(pdf_bytes: bytes, password: Optional[str] = None) -> str:
    """Extracts the embedded text layer directly from each page — no image
    rendering, no OCR. Raises ScannedPdfNotSupportedError if the PDF has no
    extractable text at all (a scanned/image-only statement), rather than
    silently producing zero rows."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        if doc.is_encrypted:
            if not password:
                raise PasswordRequiredError(
                    "This statement is password-protected. Enter the password your bank uses."
                )
            if not doc.authenticate(password):
                raise WrongPasswordError(
                    "That password did not open this statement. Check your bank's "
                    "password convention and try again."
                )
        if doc.page_count > _MAX_PDF_PAGES:
            raise ValueError(
                f"PDF has {doc.page_count} pages, exceeding the {_MAX_PDF_PAGES}-page limit."
            )
        text = "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()

    if not text.strip():
        raise ScannedPdfNotSupportedError(
            "This PDF has no extractable text layer — it appears to be a scanned/image-only "
            "statement, which isn't supported. Please upload a text-based PDF export or a CSV."
        )
    return text


def dataframe_for_bank_statement(text: str, bank_name: Optional[str]) -> pd.DataFrame:
    """Routes to the bank-specific PDF parser when one exists; otherwise the
    generic line parser (used for unlisted banks / fixtures)."""
    if bank_name:
        try:
            parser = get_parser_for_bank(bank_name)
        except NotImplementedError:
            parser = None
        else:
            df = parser(text)
            if df is None or df.empty:
                raise ValueError(
                    f"We recognised this as a {bank_name} statement but could not read any "
                    "transactions. Re-download a text PDF from your bank app, or try CSV."
                )
            return df

    return parse_bank_statement_text_to_dataframe(text)

def _clean_line(line: str) -> str:
    line = re.sub(r"[^\w\s.\-]", " ", line)  # strip stray punctuation noise (e.g. a stray "|")
    line = re.sub(r"(\d)\s*\.\s*(\d{2})\b", r"\1.\2", line)  # "3216000. 00" -> "3216000.00"
    return " ".join(line.split())


def parse_bank_statement_text_to_dataframe(text: str) -> pd.DataFrame:
    """Line-based parser for a PDF's extracted bank-statement text, producing
    a DataFrame with the same column *names* (date/narration/debit/credit/
    balance) the CSV fixture uses — so it feeds the exact same
    extract_canonical_bank_rows()/ingest_bank_dataframe() the CSV path uses
    (app/services/bank_ingestion.py), unmodified. Expects one transaction
    per line in a reasonably regular `DATE NARRATION DEBIT CREDIT BALANCE`
    layout; this is a stated limitation, not a general-purpose table-layout
    reconstructor.
    """
    rows = []
    for line in text.splitlines():
        cleaned = _clean_line(line)
        if not cleaned:
            continue
        match = _LINE_PATTERN.match(cleaned)
        if match:
            rows.append(match.groupdict())
    return pd.DataFrame(rows, columns=["date", "narration", "debit", "credit", "balance"])


async def ingest_bank_pdf_bytes(
    db: AsyncSession, pdf_bytes: bytes, user_id: uuid.UUID, bank_name: Optional[str], upload_id: str
) -> dict:
    """Extracts the PDF's text layer, routes through the bank-specific parser
    when one exists (else the generic line parser), then calls the *same*
    ingest_bank_dataframe() the CSV path calls."""
    text = extract_pdf_text(pdf_bytes)
    df = dataframe_for_bank_statement(text, bank_name)
    return await ingest_bank_dataframe(db, df, user_id, bank_name, BankTransactionDataSource.generic_pdf, upload_id)


@celery_app.task(name="ingest_bank_pdf")
def ingest_bank_pdf(upload_id: str, user_id: str, bank_name: Optional[str] = None) -> dict:
    return asyncio.run(_ingest_bank_pdf_async(upload_id, user_id, bank_name))


async def _ingest_bank_pdf_async(upload_id: str, user_id: str, bank_name: Optional[str]) -> dict:
    try:
        pdf_bytes = read_staged_bytes(upload_id, "pdf")
        async with async_session() as db:
            result = await ingest_bank_pdf_bytes(db, pdf_bytes, uuid.UUID(user_id), bank_name, upload_id)
    except Exception as exc:
        async with async_session() as db:
            await mark_upload_failed(db, upload_id, uuid.UUID(user_id), AnalyzerType.bank, exc)
        raise
    finally:
        delete_staged_upload(upload_id)
    return result
