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

Guidelines:
- Maintain a clean, professional, and humanized executive tone.
- Do NOT use emojis anywhere in the output.
- Format strictly as follows:

# Skylark Drones - Weekly Founder Flash

## 1. Executive Snapshot & Core KPIs
- **Active Sales Pipeline**: Value, Deal count, Weighted pipeline
- **Booked Contract Value**: Total contracted PO amount (Excl/Incl GST)
- **Revenue Billed vs Collected**: Billed Value, Collected Amount, Collection Efficiency %
- **Outstanding Accounts Receivable**: Total AR exposure and Priority AR exposure

## 2. Top Business Highlights
- Highlight 2-3 positive commercial and operational milestones.

## 3. Critical Risks & Bottlenecks
- Identify 2-3 risks (such as overdue receivables, unbilled backlog, or CRM pipeline gaps).

## 4. Priority Action Items for the Week
- Specific, actionable recommendations for Commercial, Operations, and Finance leadership.

## 5. Data Health & Audit Notes
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

Guidelines:
- Maintain a clean, professional, and humanized executive tone.
- Do NOT use emojis anywhere in the output.
- Format strictly as follows:

# Skylark Drones - Sector Performance Scorecard

## 1. Executive Sector Ranking
- Rank sectors by total contracted value, pipeline strength, and win conversion rates.

## 2. Sector Deep Dives
- **Mining**: Contracted Value, Billed Amount, Pipeline, Conversion Rate, Strategic Summary
- **Powerline**: Contracted Value, Billed Amount, Pipeline, Conversion Rate, Strategic Summary
- **Renewables / Solar**: Contracted Value, Billed Amount, Pipeline, Strategic Summary
- **Infrastructure & Other**: Performance summary

## 3. Growth Opportunities & Bottlenecks
- Specific insights on where commercial teams should accelerate and where execution is stalling.

## 4. Data Health Notes
- Note sector classification caveats or unassigned records.
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
        
        prompt = f"""You are the Head of Financial Operations at Skylark Drones. Generate a 'Cash Flow & Accounts Receivable (AR) Risk Matrix'.

LIVE FINANCIAL & AR DATA:
{ar_data}

Guidelines:
- Maintain a clean, professional, and humanized executive tone.
- Do NOT use emojis anywhere in the output.
- Format strictly as follows:

# Skylark Drones - AR & Cash Flow Risk Matrix

## 1. Cash Realization Overview
- **Total Billed Value (Incl. GST)**
- **Total Collected Amount (Incl. GST)**
- **Total Outstanding AR Exposure**
- **Collection Efficiency Ratio (%)**

## 2. Priority Accounts Receivable Exposure
- List top customer accounts with outstanding receivables, priority status, and billing notes.

## 3. Unbilled Project Backlog
- Summary of executed work orders currently awaiting invoice generation.

## 4. Collections Action Plan
- Concrete steps for Finance and Account Management teams to accelerate cash inflow.
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

Guidelines:
- Maintain a clean, professional, and humanized executive tone.
- Do NOT use emojis anywhere in the output.
- Format strictly as follows:

# Skylark Drones - Operational Execution Brief

## 1. Work Order Execution Pipeline
- Breakdown of active work orders across execution statuses (Completed, In Progress, Pending).

## 2. Quantity Fulfillment vs PO Commitments
- Total PO quantity vs quantity billed vs balance remaining.

## 3. Operational Bottlenecks & Turnaround Actions
- Specific work orders requiring billing updates, data delivery timeline improvements, and ops coordination.
"""
        response_text = self.llm_client.generate([{"role": "user", "content": prompt}], temperature=0.15)
        return {
            "type": BriefType.OPERATIONAL_FULFILLMENT.value,
            "title": "Operational Execution Brief",
            "content": response_text,
            "raw_metrics": ops_data,
        }
