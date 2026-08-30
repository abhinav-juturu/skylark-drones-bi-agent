"""
Unit tests for the Leadership Brief Generator.
"""

import pytest
from src.connectors.monday_api import MondayAPIClient
from src.data.normalizer import DataNormalizer
from src.analytics.query_engine import BusinessQueryEngine
from src.leadership.executive_brief import LeadershipBriefGenerator, BriefType


@pytest.fixture(scope="module")
def generator():
    client = MondayAPIClient()
    deals = DataNormalizer.normalize_deals_batch(client.get_deals_raw())
    wos = DataNormalizer.normalize_work_orders_batch(client.get_work_orders_raw())
    engine = BusinessQueryEngine(deals, wos)
    return LeadershipBriefGenerator(engine)


def test_generate_founder_flash(generator):
    """Verify generation of Founder Flash brief."""
    brief = generator.generate_brief(BriefType.FOUNDER_FLASH)
    assert brief["type"] == BriefType.FOUNDER_FLASH.value
    assert "content" in brief
    assert len(brief["content"]) > 100
    assert "Skylark Drones" in brief["content"]
