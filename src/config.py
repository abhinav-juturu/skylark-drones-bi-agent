"""
Configuration settings and environment management.
Supports both .env files (local) and Streamlit Secrets (cloud deployments).
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Search and load .env file from root
BASE_DIR = Path(__file__).resolve().parent.parent
dotenv_path = BASE_DIR / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)


def get_config_var(key: str, default: str = "") -> str:
    """Retrieve config from environment variable, falling back to Streamlit secrets if available."""
    val = os.getenv(key)
    if val:
        return val.strip()

    # Try Streamlit secrets if running inside Streamlit Cloud
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key]).strip()
    except Exception:
        pass

    return default


# Monday.com Configuration
MONDAY_API_TOKEN = get_config_var("MONDAY_API_TOKEN")
MONDAY_API_URL = get_config_var("MONDAY_API_URL", "https://api.monday.com/v2")
MONDAY_API_VERSION = get_config_var("MONDAY_API_VERSION", "2024-01")

WORK_ORDERS_BOARD_ID = get_config_var("WORK_ORDERS_BOARD_ID")
DEALS_BOARD_ID = get_config_var("DEALS_BOARD_ID")

# Groq LLM Configuration
GROQ_API_KEY = get_config_var("GROQ_API_KEY")
DEFAULT_LLM_MODEL = get_config_var("DEFAULT_LLM_MODEL", "qwen/qwen3.8-27b")
FALLBACK_LLM_MODEL = get_config_var("FALLBACK_LLM_MODEL", "openai/gpt-oss-120b")

# Cache Configuration
CACHE_TTL_SECONDS = int(get_config_var("CACHE_TTL_SECONDS", "300"))


def validate_config() -> dict[str, bool]:
    """Validate presence of critical environment variables."""
    return {
        "monday_api_token": bool(MONDAY_API_TOKEN),
        "work_orders_board_id": bool(WORK_ORDERS_BOARD_ID),
        "deals_board_id": bool(DEALS_BOARD_ID),
        "groq_api_key": bool(GROQ_API_KEY),
    }
