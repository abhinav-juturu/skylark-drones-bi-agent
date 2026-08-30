"""
Agent tool execution layer connecting LLM queries to analytical engines.
"""

import json
from typing import Any, Optional
from ..analytics.query_engine import BusinessQueryEngine
from ..data.quality_reporter import DataQualityReporter


class AgentTools:
    """Tool execution dispatcher for the BI Agent."""

    def __init__(self, query_engine: BusinessQueryEngine):
        self.query_engine = query_engine

    def execute_tool(self, tool_name: str, arguments: Optional[dict[str, Any]] = None) -> str:
        """Dispatch and execute an analytical tool, returning JSON string result."""
        args = arguments or {}
        try:
            if tool_name == "get_executive_overview":
                data = self.query_engine.get_executive_summary()
                return json.dumps(data, indent=2)

            elif tool_name == "get_pipeline_analysis":
                sector = args.get("sector")
                if sector:
                    deals = self.query_engine.filter_deals(sector=sector)
                    pipe_kpi = self.query_engine.query_pipeline_health()
                    sec_kpis = self.query_engine.query_sector_performance(sector)
                    return json.dumps({"sector": sector, "sector_kpis": sec_kpis, "open_deals_count": len(deals)}, indent=2)
                return json.dumps(self.query_engine.query_pipeline_health(), indent=2)

            elif tool_name == "get_revenue_and_ar_analysis":
                return json.dumps(self.query_engine.query_cash_and_ar_risks(), indent=2)

            elif tool_name == "get_sector_deep_dive":
                sector_name = args.get("sector_name")
                data = self.query_engine.query_sector_performance(sector_name)
                return json.dumps(data, indent=2)

            elif tool_name == "get_operational_kpis":
                return json.dumps(self.query_engine.query_operational_status(), indent=2)

            elif tool_name == "search_records":
                query_str = args.get("query", "")
                data = self.query_engine.search_items(query_str)
                return json.dumps(data, indent=2)

            elif tool_name == "get_data_quality_report":
                report = self.query_engine.quality_report
                return json.dumps(report.model_dump(), indent=2)

            else:
                return json.dumps({"error": f"Unknown tool: {tool_name}"})

        except Exception as e:
            return json.dumps({"error": f"Tool execution failed: {str(e)}"})
