import datetime
from pathlib import Path

import pandas as pd

from app.models.orders import OrderDataSource
from app.services.ecommerce_ingestion import compute_ecommerce_quality_report, extract_canonical_rows

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def _quality_report_for(csv_name: str) -> dict:
    df = pd.read_csv(FIXTURES_DIR / csv_name)
    rows = extract_canonical_rows(df, OrderDataSource.shopify_csv)
    return compute_ecommerce_quality_report(rows)


def test_cogs_missing_below_threshold_does_not_disable_features():
    report = _quality_report_for("shopify_cogs_below_threshold.csv")

    assert report["rows_parsed"] == 10
    assert report["rows_rejected"] == 0
    assert report["warnings"] == []


def test_cogs_missing_above_threshold_fires_warning_and_disables_features():
    report = _quality_report_for("shopify_cogs_above_threshold.csv")

    assert report["rows_parsed"] == 10
    assert len(report["warnings"]) == 1

    warning = report["warnings"][0]
    assert warning["field"] == "cogs"
    assert warning["severity"] == "high"
    assert warning["features_disabled"] == ["unit_margin", "profit_leak_detector"]
    assert "4 of 10 line items" in warning["message"]
    assert "40.0%" in warning["message"]
    assert "exceeds the 20% threshold" in warning["message"]


def test_date_range_and_days_of_history():
    report = _quality_report_for("shopify_cogs_below_threshold.csv")

    assert report["date_range_start"] == datetime.date(2026, 2, 1)
    assert report["date_range_end"] == datetime.date(2026, 2, 10)
    assert report["days_of_history"] == 10  # inclusive


def test_rows_missing_required_fields_are_rejected_not_silently_defaulted():
    df = pd.DataFrame(
        [
            {
                "Name": "#9001",
                "Financial Status": "paid",
                "Fulfillment Status": "fulfilled",
                "Currency": "NGN",
                "Total": 1000.00,
                "Created at": "2026-04-01 10:00:00",
                "Lineitem sku": "SKU-X",
                "Lineitem quantity": 1,
                "Lineitem price": 1000.00,
            },
            {
                # Missing Total (gross_revenue) entirely
                "Name": "#9002",
                "Financial Status": "paid",
                "Fulfillment Status": "fulfilled",
                "Currency": "NGN",
                "Total": None,
                "Created at": "2026-04-02 10:00:00",
                "Lineitem sku": "SKU-Y",
                "Lineitem quantity": 1,
                "Lineitem price": 1000.00,
            },
            {
                # Missing Created at (order_date) entirely
                "Name": "#9003",
                "Financial Status": "paid",
                "Fulfillment Status": "fulfilled",
                "Currency": "NGN",
                "Total": 1000.00,
                "Created at": None,
                "Lineitem sku": "SKU-Z",
                "Lineitem quantity": 1,
                "Lineitem price": 1000.00,
            },
        ]
    )
    rows = extract_canonical_rows(df, OrderDataSource.shopify_csv)
    report = compute_ecommerce_quality_report(rows)

    assert report["rows_parsed"] == 1
    assert report["rows_rejected"] == 2


def test_no_warning_when_there_are_no_line_items_at_all():
    df = pd.DataFrame(
        [
            {
                "Name": "#9101",
                "Financial Status": "paid",
                "Fulfillment Status": "fulfilled",
                "Currency": "NGN",
                "Total": 1000.00,
                "Created at": "2026-04-01 10:00:00",
            }
        ]
    )
    rows = extract_canonical_rows(df, OrderDataSource.shopify_csv)
    report = compute_ecommerce_quality_report(rows)

    assert report["rows_parsed"] == 1
    assert report["warnings"] == []
