"""
Tests for Monday API client and MCP connector.
"""

import pytest
from src.config import validate_config, WORK_ORDERS_BOARD_ID, DEALS_BOARD_ID
from src.connectors.monday_api import MondayAPIClient, MondayAPIError
from src.connectors.monday_mcp_client import MondayMCPClient


def test_configuration():
    """Verify configuration presence."""
    status = validate_config()
    assert status["monday_api_token"] is True
    assert status["work_orders_board_id"] is True
    assert status["deals_board_id"] is True
    assert status["groq_api_key"] is True


def test_monday_api_connection():
    """Verify Monday.com API authentication and connectivity."""
    client = MondayAPIClient()
    me = client.test_connection()
    assert "id" in me
    assert "name" in me


def test_monday_get_board_schema():
    """Verify retrieval of board schema for both boards."""
    client = MondayAPIClient()
    boards = client.get_board_schema([WORK_ORDERS_BOARD_ID, DEALS_BOARD_ID])
    assert len(boards) == 2
    board_names = [b["name"] for b in boards]
    assert "Deals" in board_names
    assert "Work Orders" in board_names


def test_monday_get_items():
    """Verify pagination and item retrieval."""
    client = MondayAPIClient()
    deals = client.get_deals_raw()
    assert len(deals) > 0
    assert "id" in deals[0]
    assert "name" in deals[0]
    assert "column_values" in deals[0]

    wos = client.get_work_orders_raw()
    assert len(wos) > 0
    assert "id" in wos[0]


def test_mcp_client_tools():
    """Verify MCP tool list and tool invocation."""
    mcp_client = MondayMCPClient()
    tools = mcp_client.list_tools()
    tool_names = [t["function"]["name"] for t in tools]
    assert "get_board_schema" in tool_names
    assert "get_deals" in tool_names
    assert "get_work_orders" in tool_names
    assert "search_board_items" in tool_names

    res = mcp_client.call_tool("get_board_schema")
    assert res["status"] == "success"
    assert len(res["boards"]) == 2
