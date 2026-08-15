from pathlib import Path

import pandas as pd

from app.models.orders import OrderDataSource
from app.services.dataset_detection import detect_dataset_type

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> pd.DataFrame:
    return pd.read_csv(FIXTURES_DIR / name)


def test_detects_a_bank_statement():
    result = detect_dataset_type(_load("generic_bank_sample.csv"))
    assert result.analyzer_type == "bank"
    assert result.source is None
    assert result.confidence == 1.0


def test_detects_shopify_ecommerce_export():
    result = detect_dataset_type(_load("shopify_sample.csv"))
    assert result.analyzer_type == "ecommerce"
    assert result.source == OrderDataSource.shopify_csv.value


def test_detects_woocommerce_ecommerce_export():
    result = detect_dataset_type(_load("woocommerce_sample.csv"))
    assert result.analyzer_type == "ecommerce"
    assert result.source == OrderDataSource.woocommerce_csv.value


def test_detects_generic_ecommerce_export():
    result = detect_dataset_type(_load("generic_ecommerce_sample.csv"))
    assert result.analyzer_type == "ecommerce"
    assert result.source == OrderDataSource.generic_csv.value


def test_low_confidence_on_an_unrecognizable_file():
    df = pd.DataFrame({"random_column_a": [1, 2], "random_column_b": ["x", "y"]})

    result = detect_dataset_type(df)

    assert result.analyzer_type is None
    assert result.source is None
    assert result.confidence < 0.4
