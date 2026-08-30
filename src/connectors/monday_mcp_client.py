"""
Monday.com Model Context Protocol (MCP) Client interface and tool dispatcher.
Provides standardized MCP tool definitions with resilient GraphQL fallback.
"""

import json
import logging
from typing import Any, Optional
from .monday_api import MondayAPIClient, MondayAPIError
from ..config import WORK_ORDERS_BOARD_ID, DEALS_BOARD_ID

logger = logging.getLogger(__name__)


class MondayMCPClient:
    """
    Monday MCP Client interface.
    Exposes standardized MCP tools for the AI Agent to query monday.com workspace
    with automatic resilience and direct API fallback.
    """

    def __init__(self, api_client: Optional[MondayAPIClient] = None):
        self.api_client = api_client or MondayAPIClient()
        self.mode = "api_fallback"  # or "mcp_native"

    def list_tools(self) -> list[dict[str, Any]]:
        """Return MCP-compliant tool specifications for LLM function calling."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_board_schema",
                    "description": "Fetch column definitions and metadata for Deals and Work Orders boards.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "board_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional list of board IDs. Defaults to Deals and Work Orders boards.",
                            }
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_deals",
                    "description": "Fetch all deals from the Monday.com Deals board including stage, status, sector, close date, and value.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "force_refresh": {
                                "type": "boolean",
                                "description": "Whether to bypass in-memory cache and fetch live data.",
                                "default": False,
                            }
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_work_orders",
                    "description": "Fetch all execution work orders from Monday.com including billing, collection, status, and receivables.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "force_refresh": {
                                "type": "boolean",
                                "description": "Whether to bypass in-memory cache and fetch live data.",
                                "default": False,
                            }
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_board_items",
                    "description": "Search for specific items/deals/work orders by query keyword across boards.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search keyword (e.g. client code, deal name, or sector).",
                            },
                            "board_type": {
                                "type": "string",
                                "enum": ["all", "deals", "work_orders"],
                                "description": "Which board to search in. Default is 'all'.",
                                "default": "all",
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
        ]

    def call_tool(self, tool_name: str, arguments: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Execute an MCP tool call and return structured result."""
        args = arguments or {}
        try:
            if tool_name == "get_board_schema":
                board_ids = args.get("board_ids") or [DEALS_BOARD_ID, WORK_ORDERS_BOARD_ID]
                boards = self.api_client.get_board_schema(board_ids)
                return {"status": "success", "boards": boards}

            elif tool_name == "get_deals":
                force_refresh = args.get("force_refresh", False)
                deals = self.api_client.get_deals_raw(force_refresh=force_refresh)
                return {"status": "success", "count": len(deals), "items": deals}

            elif tool_name == "get_work_orders":
                force_refresh = args.get("force_refresh", False)
                wos = self.api_client.get_work_orders_raw(force_refresh=force_refresh)
                return {"status": "success", "count": len(wos), "items": wos}

            elif tool_name == "search_board_items":
                query_str = args.get("query", "").lower()
                board_type = args.get("board_type", "all")
                results: list[dict[str, Any]] = []

                if board_type in ("all", "deals"):
                    deals = self.api_client.get_deals_raw()
                    for d in deals:
                        name = d.get("name", "")
                        col_texts = [cv.get("text") or "" for cv in d.get("column_values", [])]
                        combined = f"{name} {' '.join(col_texts)}".lower()
                        if query_str in combined:
                            results.append({"board": "deals", "item": d})

                if board_type in ("all", "work_orders"):
                    wos = self.api_client.get_work_orders_raw()
                    for w in wos:
                        name = w.get("name", "")
                        col_texts = [cv.get("text") or "" for cv in w.get("column_values", [])]
                        combined = f"{name} {' '.join(col_texts)}".lower()
                        if query_str in combined:
                            results.append({"board": "work_orders", "item": w})

                return {"status": "success", "count": len(results), "results": results}

            else:
                return {"status": "error", "message": f"Unknown tool: {tool_name}"}

        except MondayAPIError as e:
            logger.error("Error executing MCP tool '%s': %s", tool_name, e)
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.exception("Unexpected error in MCP tool '%s': %s", tool_name, e)
            return {"status": "error", "message": f"Internal execution error: {str(e)}"}
