"""
Configuration settings and environment management.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Search and load .env file from root
BASE_DIR = Path(__file__).resolve().parent.parent
dotenv_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=dotenv_path)

# Monday.com Configuration
MONDAY_API_TOKEN = os.getenv("MONDAY_API_TOKEN", "").strip()
MONDAY_API_URL = os.getenv("MONDAY_API_URL", "https://api.monday.com/v2")
MONDAY_API_VERSION = os.getenv("MONDAY_API_VERSION", "2024-01")

WORK_ORDERS_BOARD_ID = os.getenv("WORK_ORDERS_BOARD_ID", "").strip()
DEALS_BOARD_ID = os.getenv("DEALS_BOARD_ID", "").strip()

# Groq LLM Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "qwen/qwen3.8-27b")
FALLBACK_LLM_MODEL = os.getenv("FALLBACK_LLM_MODEL", "openai/gpt-oss-120b")

# Cache Configuration
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))  # 5 minutes cache

def validate_config() -> dict[str, bool]:
    """Validate presence of critical environment variables."""
    return {
        "monday_api_token": bool(MONDAY_API_TOKEN),
        "work_orders_board_id": bool(WORK_ORDERS_BOARD_ID),
        "deals_board_id": bool(DEALS_BOARD_ID),
        "groq_api_key": bool(GROQ_API_KEY),
    }
