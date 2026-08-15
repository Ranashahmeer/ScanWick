import io
import uuid

import pandas as pd

from app.services.upload_staging import (
    delete_staged_upload,
    read_csv_bytes,
    read_staged_bytes,
    read_staged_csv,
    read_staged_upload,
    stage_upload,
)


def _csv_bytes(data: dict) -> bytes:
    buf = io.BytesIO()
    pd.DataFrame(data).to_csv(buf, index=False)
    return buf.getvalue()


def _xlsx_bytes(data: dict) -> bytes:
    buf = io.BytesIO()
    pd.DataFrame(data).to_excel(buf, index=False)
    return buf.getvalue()


def test_stage_and_read_staged_csv_roundtrip():
    """Proves the API-side write and worker-side read go through the same
    storage.py abstraction (audit #12's Railway-compatible fix) rather than
    a path only the same container filesystem could see."""
    upload_id = str(uuid.uuid4())
    stage_upload(upload_id, _csv_bytes({"a": [1, 2], "b": ["x", "y"]}), "csv")

    df = read_staged_csv(upload_id)

    assert list(df.columns) == ["a", "b"]
    assert len(df) == 2


def test_read_staged_upload_falls_back_to_csv_when_no_xlsx_staged():
    """Existing CSV-only callers never stage an .xlsx file -- must resolve
    to the exact same data read_staged_csv always has, zero behavior
    change for them."""
    upload_id = str(uuid.uuid4())
    stage_upload(upload_id, _csv_bytes({"a": [1], "b": ["x"]}), "csv")

    df = read_staged_upload(upload_id)

    assert list(df.columns) == ["a", "b"]
    assert len(df) == 1


def test_read_staged_upload_prefers_xlsx_when_staged():
    upload_id = str(uuid.uuid4())
    stage_upload(upload_id, _xlsx_bytes({"a": [1, 2], "b": ["x", "y"]}), "xlsx")

    df = read_staged_upload(upload_id)

    assert list(df.columns) == ["a", "b"]
    assert len(df) == 2


def test_read_staged_upload_csv_and_xlsx_produce_identical_frames():
    """Same data, both formats -- proves the dispatch doesn't silently lose
    or reshape anything format-specific."""
    data = {"order_id": ["1001", "1002"], "gross_revenue": [200.5, 15.0]}
    csv_id = str(uuid.uuid4())
    xlsx_id = str(uuid.uuid4())
    stage_upload(csv_id, _csv_bytes(data), "csv")
    stage_upload(xlsx_id, _xlsx_bytes(data), "xlsx")

    csv_df = read_staged_upload(csv_id)
    xlsx_df = read_staged_upload(xlsx_id)

    assert csv_df.to_dict() == xlsx_df.to_dict()


def test_read_csv_bytes_falls_back_to_cp1252_for_a_non_utf8_csv():
    """Audit #18 regression: a CSV isn't guaranteed to be UTF-8 -- a common
    real-world case is Excel's "CSV" export on Windows, which is actually
    Windows-1252/cp1252. This used to raise an unhandled UnicodeDecodeError
    deep inside a Celery task instead of being read correctly."""
    # "café" encoded as cp1252 -- 0xe9 for "é" is invalid as a UTF-8
    # continuation byte here, so a naive utf-8 read raises.
    raw = "name,note\ncaf\xe9,ok\n".encode("cp1252")

    df = read_csv_bytes(raw)

    assert df.iloc[0]["name"] == "caf\xe9"


def test_read_staged_bytes_reads_raw_pdf():
    upload_id = str(uuid.uuid4())
    stage_upload(upload_id, b"%PDF-1.4 not a real pdf, just raw bytes", "pdf")

    assert read_staged_bytes(upload_id, "pdf") == b"%PDF-1.4 not a real pdf, just raw bytes"


def test_delete_staged_upload_removes_every_extension():
    upload_id = str(uuid.uuid4())
    stage_upload(upload_id, _csv_bytes({"a": [1]}), "csv")

    delete_staged_upload(upload_id)

    try:
        read_staged_csv(upload_id)
        assert False, "expected the staged file to be gone after delete_staged_upload"
    except Exception:
        pass
