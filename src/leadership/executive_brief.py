"""
Automated Executive Brief & Leadership Update Generator for Skylark Drones.
Prepares slide, email, and meeting-ready structured reports for founders and executives.
"""

from enum import Enum
import logging
from typing import Any, Optional
from ..analytics.query_engine import BusinessQueryEngine
from ..agent.llm import GroqLLMClient

logger = logging.getLogger(__name__)


class BriefType(str, Enum):
    FOUNDER_FLASH = "founder_flash"
    SECTOR_SCORECARD = "sector_scorecard"
    AR_RISK_MATRIX = "ar_risk_matrix"
    OPERATIONAL_FULFILLMENT = "operational_fulfillment"


class LeadershipBriefGenerator:
    """Generates structured leadership briefs using analytics and LLM synthesis."""

    def __init__(
        self,
        query_engine: BusinessQueryEngine,
        llm_client: Optional[GroqLLMClient] = None,
    ):
        self.query_engine = query_engine
        self.llm_client = llm_client or GroqLLMClient()

    def generate_brief(self, brief_type: BriefType = BriefType.FOUNDER_FLASH) -> dict[str, Any]:
        """Generate a complete leadership report based on the requested template."""
        if brief_type == BriefType.FOUNDER_FLASH:
            return self._generate_founder_flash()
        elif brief_type == BriefType.SECTOR_SCORECARD:
            return self._generate_sector_scorecard()
        elif brief_type == BriefType.AR_RISK_MATRIX:
            return self._generate_ar_risk_matrix()
        elif brief_type == BriefType.OPERATIONAL_FULFILLMENT:
            return self._generate_operational_fulfillment()
        else:
            raise ValueError(f"Unsupported brief type: {brief_type}")

    def _generate_founder_flash(self) -> dict[str, Any]:
        """Weekly Founder Flash with Macro KPIs, Highlights, and Bottlenecks."""
        summary = self.query_engine.get_executive_summary()
        
        prompt = f"""You are the Chief of Staff at Skylark Drones. Generate a 'Weekly Founder Flash' executive brief for the founders and board.

LIVE EXECUTIVE DATA:
{summary}

Format your output exactly as follows:
# 🦅 Skylark Drones - Weekly Founder Flash

## 1. Executive Snapshot & Core KPIs
- **Active Sales Pipeline**: Value, Deal count, Weighted pipeline
- **Booked Contract Value**: Total contracted PO amount (Excl/Incl GST)
- **Revenue Billed vs Collected**: Billed Value, Collected Amount, Collection Efficiency %
- **Outstanding Accounts Receivable**: Total AR exposure & Priority AR exposure

## 2. 🟢 Top Highlights & Wins
- Highlight 2-3 positive indicators (e.g. top sectors, high win rates, healthy stage conversions).

## 3. 🔴 Critical Red Flags & Bottlenecks
- Identify 2-3 risks (e.g. overdue receivables, unbilled project backlog, missing CRM values).

## 4. 🎯 Leadership Action Items for the Week
- Bulleted actionable decisions for Sales, Operations, and Finance leadership.

## 5. 🛡️ Data Quality & Caveats
- Note data completeness percentage and specific caveats.
"""
        response_text = self.llm_client.generate([{"role": "user", "content": prompt}], temperature=0.15)
        return {
            "type": BriefType.FOUNDER_FLASH.value,
            "title": "Weekly Founder Flash",
            "content": response_text,
            "raw_metrics": summary,
        }

    def _generate_sector_scorecard(self) -> dict[str, Any]:
        """Sector-by-sector performance scorecard."""
        sectors = self.query_engine.query_sector_performance()
        
        prompt = f"""You are the VP of Strategic Growth at Skylark Drones. Generate an in-depth 'Sector Performance Scorecard'.

LIVE SECTOR DATA:
{sectors}

Format your output as:
# 📊 Skylark Drones - Sector Performance Scorecard

## 1. Executive Sector Ranking
- Rank sectors by total contracted value, pipeline strength, and win conversion rates.

## 2. Sector-by-Sector Deep Dive
- **Mining**: Contracted, Billed, Pipeline, Conversion rate, Key Takeaway
- **Powerline**: Contracted, Billed, Pipeline, Conversion rate, Key Takeaway
- **Renewables / Solar**: Contracted, Billed, Pipeline, Key Takeaway
- **Infrastructure & Other**: Performance overview

## 3. Strategic Sector Growth Opportunities
- Where should BD/KAM leadership double down? Where are deals stalling?

## 4. Data Health Caveats
- Note sector mapping caveats or unrecorded values.
"""
        response_text = self.llm_client.generate([{"role": "user", "content": prompt}], temperature=0.15)
        return {
            "type": BriefType.SECTOR_SCORECARD.value,
            "title": "Sector Performance Scorecard",
            "content": response_text,
            "raw_metrics": sectors,
        }

    def _generate_ar_risk_matrix(self) -> dict[str, Any]:
        """Accounts Receivable and Cash Flow Risk Matrix."""
        ar_data = self.query_engine.query_cash_and_ar_risks()
        
        prompt = f"""You are the Head of Financial Planning & Operations at Skylark Drones. Generate a 'Cash Flow & Accounts Receivable (AR) Risk Matrix'.

LIVE FINANCIAL & AR DATA:
{ar_data}

Format your output as:
# 💰 Skylark Drones - AR & Cash Flow Risk Matrix

## 1. Cash Realization Overview
- **Total Billed Value (Incl. GST)**
- **Total Collected Amount (Incl. GST)**
- **Total Outstanding AR Exposure**
- **Collection Efficiency Ratio (%)**

## 2. 🚨 High-Priority AR Accounts Exposure
- Table or list of top accounts with outstanding receivables, priority status, and collection delays.

## 3. 📦 Unbilled Backlog Analysis
- Breakdown of work orders delivered or executed but awaiting billing generation.

## 4. 🛠️ Collections Action Plan
- Specific steps for Finance & KAM teams to accelerate cash conversion.
"""
        response_text = self.llm_client.generate([{"role": "user", "content": prompt}], temperature=0.15)
        return {
            "type": BriefType.AR_RISK_MATRIX.value,
            "title": "AR & Cash Flow Risk Matrix",
            "content": response_text,
            "raw_metrics": ar_data,
        }

    def _generate_operational_fulfillment(self) -> dict[str, Any]:
        """Operational execution, fulfillment, and billing turnaround brief."""
        ops_data = self.query_engine.query_operational_status()
        
        prompt = f"""You are the VP of Drone Operations at Skylark Drones. Generate an 'Operational Execution & Fulfillment Brief'.

LIVE OPERATIONS DATA:
{ops_data}

Format your output as:
# ⚙️ Skylark Drones - Operational Execution Brief

## 1. Work Order Execution Pipeline
- Breakdown of active work orders across execution statuses (Completed, In Progress, Pending).

## 2. Quantity Fulfillment vs PO Commitments
- Total PO quantity vs quantity billed vs balance remaining.

## 3. Operational Bottlenecks & Action Items
- Work orders requiring billing updates, data delivery delays, and turnaround improvements.
"""
        response_text = self.llm_client.generate([{"role": "user", "content": prompt}], temperature=0.15)
        return {
            "type": BriefType.OPERATIONAL_FULFILLMENT.value,
            "title": "Operational Execution Brief",
            "content": response_text,
            "raw_metrics": ops_data,
        }
