"""
Tests for Data Normalizer, Schema, and Quality Reporter.
"""

from datetime import date
import pytest
from src.data.normalizer import DataNormalizer
from src.data.quality_reporter import DataQualityReporter
from src.connectors.monday_api import MondayAPIClient


def test_parse_float():
    """Verify resilient numeric parsing."""
    assert DataNormalizer.parse_float("1,234.50") == 1234.50
    assert DataNormalizer.parse_float("₹ 2,984,097.36") == 2984097.36
    assert DataNormalizer.parse_float("Rs. 5000") == 5000.0
    assert DataNormalizer.parse_float(None) == 0.0
    assert DataNormalizer.parse_float("-") == 0.0
    assert DataNormalizer.parse_float("NaN") == 0.0
    assert DataNormalizer.parse_float(1500) == 1500.0


def test_parse_date():
    """Verify resilient date parsing across multiple formats."""
    assert DataNormalizer.parse_date("2025-12-31") == date(2025, 12, 31)
    assert DataNormalizer.parse_date("31/12/2025") == date(2025, 12, 31)
    assert DataNormalizer.parse_date("15-05-2025") == date(2025, 5, 15)
    assert DataNormalizer.parse_date('{"date":"2025-05-16"}') == date(2025, 5, 16)
    assert DataNormalizer.parse_date("InvalidDate") is None
    assert DataNormalizer.parse_date(None) is None


def test_parse_probability():
    """Verify probability normalization."""
    assert DataNormalizer.parse_probability("80%") == 0.8
    assert DataNormalizer.parse_probability("0.75") == 0.75
    assert DataNormalizer.parse_probability("High") == 0.8
    assert DataNormalizer.parse_probability("Low") == 0.2
    assert DataNormalizer.parse_probability("Won") == 1.0
    assert DataNormalizer.parse_probability(None) is None


def test_normalize_sector():
    """Verify canonical sector naming."""
    assert DataNormalizer.normalize_sector("mining") == "Mining"
    assert DataNormalizer.normalize_sector("Powerline") == "Powerline"
    assert DataNormalizer.normalize_sector("Solar Energy") == "Solar"
    assert DataNormalizer.normalize_sector(None) == "Other"


def test_live_data_normalization_and_unification():
    """Verify end-to-end normalization on live Monday board data."""
    client = MondayAPIClient()
    raw_deals = client.get_deals_raw()
    raw_wos = client.get_work_orders_raw()

    assert len(raw_deals) > 0
    assert len(raw_wos) > 0

    deals = DataNormalizer.normalize_deals_batch(raw_deals)
    wos = DataNormalizer.normalize_work_orders_batch(raw_wos)

    assert len(deals) == len(raw_deals)
    assert len(wos) == len(raw_wos)

    # Check deal fields
    for d in deals[:10]:
        assert isinstance(d.name, str)
        assert d.masked_deal_value is not None

    # Check work order fields
    for w in wos[:10]:
        assert isinstance(w.name, str)
        assert isinstance(w.amount_excl_gst, float)

    # Reconcile cross-board
    unified = DataNormalizer.reconcile_and_unify(deals, wos)
    assert len(unified) >= len(deals)

    # Generate Quality Report
    report = DataQualityReporter.generate_report(deals, wos, unified)
    assert report.total_deals == len(deals)
    assert report.total_work_orders == len(wos)
    assert 0 <= report.data_health_score <= 100
    assert len(report.caveats) > 0
