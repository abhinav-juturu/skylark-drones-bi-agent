"""
Unit tests for Business Intelligence analytics metrics and query engine.
"""

import pytest
from src.connectors.monday_api import MondayAPIClient
from src.data.normalizer import DataNormalizer
from src.analytics.metrics import BusinessMetricsCalculator
from src.analytics.query_engine import BusinessQueryEngine


@pytest.fixture(scope="module")
def live_data():
    client = MondayAPIClient()
    raw_deals = client.get_deals_raw()
    raw_wos = client.get_work_orders_raw()
    deals = DataNormalizer.normalize_deals_batch(raw_deals)
    wos = DataNormalizer.normalize_work_orders_batch(raw_wos)
    unified = DataNormalizer.reconcile_and_unify(deals, wos)
    return deals, wos, unified


def test_pipeline_health_calculation(live_data):
    deals, _, _ = live_data
    kpis = BusinessMetricsCalculator.compute_pipeline_health(deals)

    assert kpis.total_deals > 0
    assert kpis.total_pipeline_value >= 0.0
    assert 0.0 <= kpis.win_rate_pct <= 100.0
    assert len(kpis.stage_breakdown) > 0
    assert len(kpis.sector_breakdown) > 0


def test_revenue_realization_calculation(live_data):
    _, wos, _ = live_data
    kpis = BusinessMetricsCalculator.compute_revenue_realization(wos)

    assert kpis.total_contracted_excl_gst > 0.0
    assert kpis.total_billed_excl_gst >= 0.0
    assert kpis.total_ar_outstanding >= 0.0
    assert 0.0 <= kpis.billing_rate_pct <= 100.0


def test_sector_kpis_calculation(live_data):
    deals, wos, _ = live_data
    sectors = BusinessMetricsCalculator.compute_sector_kpis(deals, wos)

    assert len(sectors) > 0
    sector_names = [s.sector_name for s in sectors]
    assert "Mining" in sector_names or "Powerline" in sector_names


def test_query_engine_queries(live_data):
    deals, wos, unified = live_data
    engine = BusinessQueryEngine(deals, wos, unified)

    # Executive summary
    summary = engine.get_executive_summary()
    assert "pipeline" in summary
    assert "revenue" in summary
    assert "top_sectors" in summary
    assert "data_health_score" in summary

    # Sector query
    mining_data = engine.query_sector_performance("Mining")
    assert isinstance(mining_data, list)

    # Pipeline health query
    pipe_health = engine.query_pipeline_health()
    assert "kpis" in pipe_health
    assert "top_open_deals" in pipe_health

    # Search
    search_res = engine.search_items("Mining")
    assert search_res["deals_count"] >= 0
