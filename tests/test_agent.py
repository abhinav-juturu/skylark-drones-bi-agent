"""
Unit and integration tests for the AI Agent Orchestrator and Groq LLM.
"""

import pytest
from src.agent.llm import GroqLLMClient
from src.agent.tools import AgentTools
from src.agent.orchestrator import BIAgentOrchestrator
from src.connectors.monday_api import MondayAPIClient
from src.data.normalizer import DataNormalizer
from src.analytics.query_engine import BusinessQueryEngine


def test_groq_llm_client():
    """Verify Groq LLM connection and generation."""
    llm = GroqLLMClient()
    res = llm.generate([{"role": "user", "content": "Respond with the single word: ACKNOWLEDGED"}], max_tokens=15)
    assert len(res) > 0


def test_agent_tools_execution():
    """Verify agent tools dispatcher."""
    client = MondayAPIClient()
    deals = DataNormalizer.normalize_deals_batch(client.get_deals_raw())
    wos = DataNormalizer.normalize_work_orders_batch(client.get_work_orders_raw())
    engine = BusinessQueryEngine(deals, wos)
    tools = AgentTools(engine)

    overview = tools.execute_tool("get_executive_overview")
    assert "pipeline" in overview
    assert "revenue" in overview

    pipe = tools.execute_tool("get_pipeline_analysis")
    assert "kpis" in pipe

    ar = tools.execute_tool("get_revenue_and_ar_analysis")
    assert "total_contracted_excl_gst" in ar


def test_bi_agent_orchestrator_ask():
    """Verify end-to-end question answering by the BI Agent Orchestrator."""
    orchestrator = BIAgentOrchestrator()
    
    # Founder query 1: Sector pipeline
    res = orchestrator.ask("How is our pipeline looking for the energy sector this quarter?")
    assert "response" in res
    assert len(res["response"]) > 50
    assert len(res["suggested_followups"]) > 0
    assert res["data_health_score"] > 0

    # Founder query 2: AR exposure
    res_ar = orchestrator.ask("What is our current cash collection and AR risk?")
    assert "response" in res_ar
    assert len(res_ar["response"]) > 50
