"""
Monday.com GraphQL API Client with resilient pagination, retries, and caching.
"""

import time
import logging
from typing import Any, Optional
import requests
from ..config import (
    MONDAY_API_TOKEN,
    MONDAY_API_URL,
    MONDAY_API_VERSION,
    WORK_ORDERS_BOARD_ID,
    DEALS_BOARD_ID,
    CACHE_TTL_SECONDS,
)

logger = logging.getLogger(__name__)


class MondayAPIError(Exception):
    """Custom exception for Monday.com API errors."""
    pass


class MondayAPIClient:
    """Robust client for interacting with Monday.com GraphQL API."""

    def __init__(
        self,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
        api_version: Optional[str] = None,
        cache_ttl: int = CACHE_TTL_SECONDS,
    ):
        self.token = token or MONDAY_API_TOKEN
        self.api_url = api_url or MONDAY_API_URL
        self.api_version = api_version or MONDAY_API_VERSION
        self.cache_ttl = cache_ttl

        self._cache: dict[str, tuple[float, Any]] = {}

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": self.token,
            "API-Version": self.api_version,
            "Content-Type": "application/json",
        }

    def execute_query(
        self,
        query: str,
        variables: Optional[dict[str, Any]] = None,
        retries: int = 3,
        backoff_factor: float = 1.5,
    ) -> dict[str, Any]:
        """Execute a GraphQL query against Monday.com API with retry and backoff."""
        if not self.token:
            raise MondayAPIError("Monday API Token is not configured.")

        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        last_error = None
        for attempt in range(1, retries + 1):
            try:
                response = requests.post(
                    self.api_url,
                    json=payload,
                    headers=self.headers,
                    timeout=30,
                )

                if response.status_code == 429:
                    # Rate limited
                    sleep_time = backoff_factor ** attempt
                    logger.warning("Monday API rate limit reached (429). Retrying in %.2fs...", sleep_time)
                    time.sleep(sleep_time)
                    continue

                if response.status_code >= 500:
                    sleep_time = backoff_factor ** attempt
                    logger.warning("Monday API server error (%d). Retrying in %.2fs...", response.status_code, sleep_time)
                    time.sleep(sleep_time)
                    continue

                if response.status_code != 200:
                    raise MondayAPIError(f"HTTP {response.status_code}: {response.text}")

                data = response.json()
                if "errors" in data and data["errors"]:
                    error_msg = "; ".join(
                        err.get("message", str(err)) if isinstance(err, dict) else str(err)
                        for err in data["errors"]
                    )
                    raise MondayAPIError(f"Monday API GraphQL Error: {error_msg}")

                return data.get("data", {})

            except (requests.RequestException, MondayAPIError) as e:
                last_error = e
                if attempt == retries:
                    break
                sleep_time = backoff_factor ** attempt
                time.sleep(sleep_time)

        raise MondayAPIError(f"Failed after {retries} attempts: {last_error}")

    def test_connection(self) -> dict[str, Any]:
        """Verify API token authentication and return user details."""
        query = """
        query {
            me {
                id
                name
                email
                is_admin
            }
        }
        """
        data = self.execute_query(query)
        return data.get("me", {})

    def get_board_schema(self, board_ids: list[str]) -> list[dict[str, Any]]:
        """Fetch board schema including column ids, titles, and types."""
        cache_key = f"schema_{','.join(sorted(board_ids))}"
        if cache_key in self._cache:
            ts, val = self._cache[cache_key]
            if time.time() - ts < self.cache_ttl:
                return val

        query = """
        query GetBoardSchema($boardIds: [ID!]) {
            boards(ids: $boardIds) {
                id
                name
                description
                state
                columns {
                    id
                    title
                    type
                    settings_str
                }
            }
        }
        """
        data = self.execute_query(query, variables={"boardIds": board_ids})
        boards = data.get("boards", [])
        self._cache[cache_key] = (time.time(), boards)
        return boards

    def get_all_board_items(
        self,
        board_id: str,
        page_size: int = 250,
        force_refresh: bool = False,
    ) -> list[dict[str, Any]]:
        """Fetch all items from a board using cursor-based pagination."""
        cache_key = f"items_{board_id}"
        if not force_refresh and cache_key in self._cache:
            ts, val = self._cache[cache_key]
            if time.time() - ts < self.cache_ttl:
                return val

        items: list[dict[str, Any]] = []
        cursor: Optional[str] = None
        has_more = True

        query_initial = """
        query GetInitialItems($boardId: [ID!], $limit: Int!) {
            boards(ids: $boardId) {
                id
                name
                items_page(limit: $limit) {
                    cursor
                    items {
                        id
                        name
                        created_at
                        updated_at
                        column_values {
                            id
                            text
                            value
                            type
                        }
                    }
                }
            }
        }
        """

        query_next = """
        query GetNextItems($limit: Int!, $cursor: String!) {
            next_items_page(limit: $limit, cursor: $cursor) {
                cursor
                items {
                    id
                    name
                    created_at
                    updated_at
                    column_values {
                        id
                        text
                        value
                        type
                    }
                }
            }
        }
        """

        # First page
        data = self.execute_query(query_initial, variables={"boardId": [board_id], "limit": page_size})
        boards = data.get("boards", [])
        if not boards:
            return []

        items_page = boards[0].get("items_page", {})
        page_items = items_page.get("items", [])
        items.extend(page_items)
        cursor = items_page.get("cursor")

        # Subsequent pages
        while cursor and has_more:
            next_data = self.execute_query(query_next, variables={"limit": page_size, "cursor": cursor})
            next_page = next_data.get("next_items_page", {})
            next_items = next_page.get("items", [])
            if not next_items:
                break
            items.extend(next_items)
            cursor = next_page.get("cursor")
            if not cursor:
                has_more = False

        self._cache[cache_key] = (time.time(), items)
        return items

    def get_deals_raw(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        """Fetch raw items from Deals board."""
        if not DEALS_BOARD_ID:
            raise MondayAPIError("DEALS_BOARD_ID is not configured.")
        return self.get_all_board_items(DEALS_BOARD_ID, force_refresh=force_refresh)

    def get_work_orders_raw(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        """Fetch raw items from Work Orders board."""
        if not WORK_ORDERS_BOARD_ID:
            raise MondayAPIError("WORK_ORDERS_BOARD_ID is not configured.")
        return self.get_all_board_items(WORK_ORDERS_BOARD_ID, force_refresh=force_refresh)

    def clear_cache(self) -> None:
        """Clear all cached query results."""
        self._cache.clear()
