"""
AI Business Intelligence Agent Orchestrator.
Coordinates data retrieval, query intent routing, contextual prompt preparation, and LLM response generation.
"""

import re
import logging
from typing import Any, Generator, Optional
from .prompts import SYSTEM_PROMPT
from .llm import GroqLLMClient
from .tools import AgentTools
from ..connectors.monday_api import MondayAPIClient
from ..data.normalizer import DataNormalizer
from ..data.quality_reporter import DataQualityReporter
from ..analytics.query_engine import BusinessQueryEngine

logger = logging.getLogger(__name__)


class BIAgentOrchestrator:
    """Orchestrates end-to-end question answering for Skylark Drones executive leadership."""

    def __init__(
        self,
        api_client: Optional[MondayAPIClient] = None,
        llm_client: Optional[GroqLLMClient] = None,
    ):
        self.api_client = api_client or MondayAPIClient()
        self.llm_client = llm_client or GroqLLMClient()
        
        self.deals = []
        self.work_orders = []
        self.unified_records = []
        self.quality_report = None
        self.query_engine: Optional[BusinessQueryEngine] = None
        self.tools: Optional[AgentTools] = None
        
        # Load initial data
        self.refresh_data()

    def refresh_data(self, force: bool = False) -> None:
        """Fetch and normalize latest data from Monday.com boards."""
        raw_deals = self.api_client.get_deals_raw(force_refresh=force)
        raw_wos = self.api_client.get_work_orders_raw(force_refresh=force)

        self.deals = DataNormalizer.normalize_deals_batch(raw_deals)
        self.work_orders = DataNormalizer.normalize_work_orders_batch(raw_wos)
        self.unified_records = DataNormalizer.reconcile_and_unify(self.deals, self.work_orders)
        self.quality_report = DataQualityReporter.generate_report(self.deals, self.work_orders, self.unified_records)

        self.query_engine = BusinessQueryEngine(
            self.deals,
            self.work_orders,
            self.unified_records,
            self.quality_report,
        )
        self.tools = AgentTools(self.query_engine)

    def route_intent_and_collect_context(self, user_query: str) -> tuple[str, list[str]]:
        """Identify query intent and gather relevant structured data and follow-up prompts."""
        q = user_query.lower()
        context_parts: list[str] = []
        suggested_followups: list[str] = []

        # Check for sector mention
        found_sectors = [
            s for s in [
                "energy", "renewables", "renewable", "solar", "wind", "powerline", "power",
                "mining", "infrastructure", "infra", "railways", "railway", "construction",
                "enterprise", "telecom", "agriculture", "aviation", "dsp"
            ]
            if s in q
        ]

        if found_sectors:
            sec = found_sectors[0]
            sec_data = self.query_engine.query_sector_performance(sec)
            deals_in_sec = self.query_engine.filter_deals(sector=sec)
            wos_in_sec = self.query_engine.filter_work_orders(sector=sec)
            
            top_sec_deals = [
                {
                    "name": d.name,
                    "stage": d.deal_stage,
                    "value": d.masked_deal_value,
                    "probability": d.closure_probability,
                    "close_date": str(d.close_date_actual or d.tentative_close_date or "")
                }
                for d in sorted(deals_in_sec, key=lambda x: x.masked_deal_value or 0.0, reverse=True)[:5]
            ]

            context_parts.append(f"### SECTOR PERFORMANCE DEEP-DIVE: {sec.upper()}\n{sec_data}")
            context_parts.append(f"Top Open Deals in {sec.capitalize()}:\n{top_sec_deals}")
            context_parts.append(f"Total Sector Deals Count: {len(deals_in_sec)} | Work Orders Count: {len(wos_in_sec)}")
            
            display_sec = "Energy (Renewables & Powerline)" if sec in ("energy", "renewables", "powerline") else sec.capitalize()
            suggested_followups = [
                f"What are the highest value open deals in {display_sec}?",
                f"What is our collection efficiency and AR risk for {display_sec}?",
                f"How does {display_sec} compare to overall company revenue?",
            ]

        elif any(w in q for w in ["ar", "receivable", "aging", "overdue", "collection", "collected", "unbilled", "cash"]):
            ar_data = self.query_engine.query_cash_and_ar_risks()
            context_parts.append(f"### REVENUE REALIZATION & AR RISK ANALYSIS\n{ar_data}")
            suggested_followups = [
                "Which accounts represent our highest AR exposure?",
                "What is our total unbilled backlog across active projects?",
                "Which sectors have the highest collection turnaround?",
            ]

        elif any(w in q for w in ["pipeline", "funnel", "win rate", "stage", "deals", "close rate"]):
            pipe_data = self.query_engine.query_pipeline_health()
            context_parts.append(f"### SALES PIPELINE & FUNNEL METRICS\n{pipe_data}")
            suggested_followups = [
                "Show pipeline breakdown by industry sector.",
                "What deals are expected to close this quarter?",
                "What is our win rate on closed deals?",
            ]

        elif any(w in q for w in ["operation", "execution", "turnaround", "delivery", "po", "quantity", "fulfillment"]):
            ops_data = self.query_engine.query_operational_status()
            context_parts.append(f"### OPERATIONAL EXECUTION & FULFILLMENT\n{ops_data}")
            suggested_followups = [
                "How many work orders require billing updates?",
                "What is our PO quantity fulfillment rate?",
                "What are the bottlenecks in project execution?",
            ]

        elif any(w in q for w in ["quality", "health", "missing", "incomplete", "caveat", "data audit"]):
            report_data = self.quality_report.model_dump()
            context_parts.append(f"### DATA QUALITY & HEALTH REPORT\n{report_data}")
            suggested_followups = [
                "How many deals are missing value figures?",
                "How does data incompleteness impact pipeline forecasting?",
                "What percentage of work orders are reconciled with CRM deals?",
            ]

        else:
            # General / executive query (e.g. "How is business doing?", "Leadership update summary")
            summary_data = self.query_engine.get_executive_summary()
            context_parts.append(f"### FULL EXECUTIVE BUSINESS SNAPSHOT\n{summary_data}")
            suggested_followups = [
                "How is our pipeline looking for the energy sector?",
                "What is our current AR risk and collection rate?",
                "Generate a leadership summary for this week's review.",
            ]

        # Add Data Quality Health & Active Caveats into context
        quality_summary = DataQualityReporter.format_caveats_for_prompt(self.quality_report)
        context_parts.append(f"### DATA QUALITY CONTEXT & CAVEATS\n{quality_summary}")

        full_context = "\n\n".join(context_parts)
        return full_context, suggested_followups

    def build_prompt_messages(
        self,
        user_query: str,
        context: str,
        conversation_history: Optional[list[dict[str, str]]] = None,
    ) -> list[dict[str, str]]:
        """Construct prompt messages including system instructions and context."""
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Append past conversation turns if provided
        if conversation_history:
            for turn in conversation_history[-6:]:  # Keep recent turns
                messages.append(turn)

        user_content = f"""USER QUERY: "{user_query}"

LIVE BUSINESS DATA & ANALYTICAL METRICS:
{context}

Please provide a strategic, executive-level response following your directives:
1. Executive Takeaway (1-2 sentences summarizing the core finding)
2. Detailed Metrics & Drivers (bulleted breakdown with numbers, conversion/realization rates)
3. Strategic Implications & Recommendations (bottlenecks, upside opportunities, actions needed)
4. Data Health Caveat (if relevant to the query's underlying data completeness)
"""
        messages.append({"role": "user", "content": user_content})
        return messages

    def ask(
        self,
        user_query: str,
        conversation_history: Optional[list[dict[str, str]]] = None,
    ) -> dict[str, Any]:
        """Process user question and return complete structured answer."""
        context, followups = self.route_intent_and_collect_context(user_query)
        messages = self.build_prompt_messages(user_query, context, conversation_history)
        
        response_text = self.llm_client.generate(messages)

        return {
            "query": user_query,
            "response": response_text,
            "suggested_followups": followups,
            "data_health_score": self.quality_report.data_health_score,
            "caveats": [c.message for c in self.quality_report.caveats],
        }

    def ask_stream(
        self,
        user_query: str,
        conversation_history: Optional[list[dict[str, str]]] = None,
    ) -> tuple[Generator[str, None, None], list[str]]:
        """Stream answer tokens for real-time conversational UI."""
        context, followups = self.route_intent_and_collect_context(user_query)
        messages = self.build_prompt_messages(user_query, context, conversation_history)
        
        stream_gen = self.llm_client.stream(messages)
        return stream_gen, followups
