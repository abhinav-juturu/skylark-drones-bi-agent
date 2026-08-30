# Skylark Drones - Business Intelligence & Executive AI Agent

A full-stack, conversational Business Intelligence (BI) agent developed for **Skylark Drones**. The system integrates dynamically with **Monday.com** boards (**Deals CRM** and **Execution Work Orders**), normalizes messy real-world operational data on the fly, and delivers founder-level strategic insights, visual KPI dashboards, and automated leadership briefings.

---

## Overview

Executive leaders frequently face challenges pulling timely, consolidated insights across disconnected business boards. Commercial pipeline opportunities and operational delivery records often reside in separate workflows with inconsistent naming conventions, incomplete values, and varied date formats.

This project delivers an end-to-end agentic solution that:
- Connects directly to Monday.com using MCP-compliant tool interfaces and resilient GraphQL querying.
- Cleans and reconciles messy CRM deals with post-sale execution work orders in real time.
- Computes core business metrics including weighted pipeline, collection efficiency, AR exposure, and sectoral conversion.
- Provides a conversational chat interface powered by Groq high-speed LLM inference.
- Generates structured, downloadable leadership updates (Founder Flash, Sector Scorecard, AR Risk Matrix, Operational Review).

---

## Core Capabilities

### 1. Dynamic Monday.com Integration
- Live schema introspection for both Deals and Work Orders boards.
- Robust cursor-based pagination handling large datasets seamlessly.
- Built-in retry mechanism with exponential backoff and rate-limit handling (HTTP 429).
- In-memory TTL caching with a one-click manual data refresh.

### 2. Data Resilience and Cross-Board Reconciliation
- **Date Normalization:** Robust parsing across ISO strings, standard regional dates (`DD/MM/YYYY`, `MM/DD/YYYY`), textual representations, and JSON date objects.
- **Financial Cleaning:** Strips currency symbols (`INR`, `Rs.`, `₹`, `$`), commas, and masked numerical noise.
- **Entity Linking:** Reconciles CRM Deals with Work Orders via canonical name matching and PO serial references.
- **Data Health and Audit Reporting:** Computes a real-time Data Health Score (0-100%) and attaches audit caveats to queries involving incomplete fields.

### 3. Conversational BI Agent
- Strategic insight generation powered by Groq (`qwen/qwen3.8-27b` with automatic fallback to `openai/gpt-oss-120b`).
- Executive-focused answer structure: Executive Takeaway, Key Metrics Breakdown, Strategic Implications, and Data Caveats.
- Dynamic intent routing and proactive follow-up suggestions for deeper exploration.

### 4. Leadership Update Generator
- **Weekly Founder Flash:** High-level summary of pipeline health, contracted values, cash collection rates, weekly wins, and operational bottlenecks.
- **Sector Performance Scorecard:** Comprehensive review of sector performance, pipeline distribution, and expansion recommendations.
- **AR and Cash Flow Risk Matrix:** Overview of overdue receivables, unbilled project backlogs, and prioritized high-risk accounts.
- **Operational Execution Review:** Work order progression, PO quantity fulfillment, and billing update requirements.

### 5. Interactive Web Interface
- Metric cards for Active Pipeline Value, Total Contracted PO Value, Billed vs. Collected Revenue, and Outstanding AR Exposure.
- Streaming conversation interface with pre-built founder prompts and suggested follow-ups.
- Visual charts for pipeline stage funnels and sector performance comparisons.
- Full data audit inspection tab showing raw records and active caveats.

---

## System Architecture

```
+-------------------------------------------------------------------------+
|                      Streamlit Web Interface (app.py)                   |
|   [Executive Chat]  [Visual Funnel]  [Leadership Briefs]  [Data Audit]   |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|               AI Agent Orchestrator (src/agent/orchestrator.py)         |
|     * Intent Classification     * Context Assembler    * Clarification  |
+-------------------+---------------------------------+-------------------+
                    |                                 |
                    v                                 v
+--------------------------------------+  +-------------------------------+
|   Groq LLM Engine (src/agent/llm.py) |  |  Business Analytics & Query   |
|   * Primary: qwen/qwen3.8-27b        |  |  Engine (src/analytics/)      |
|   * Fallback: openai/gpt-oss-120b    |  |  * Pipeline Health KPIs       |
|   * Sub-second Token Streaming       |  |  * Revenue Realization & AR   |
+--------------------------------------+  |  * Sector Deep-Dive           |
                                          +---------------+---------------+
                                                          |
                                                          v
+-------------------------------------------------------------------------+
|              Data Resilience & Normalizer (src/data/)                   |
|     * Date/Currency Normalization      * Cross-Board Linking            |
|     * Data Health Score (0-100%)       * Caveat & Audit Generator       |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|             Monday.com Connector Layer (src/connectors/)                |
|     * MCP Tool Schema Protocol         * Direct GraphQL API Client      |
|     * Cursor Pagination                * Retry & Rate-Limit Handling    |
+------------------------------------+------------------------------------+
                                     |
                                     v
                      +-----------------------------+
                      |    Monday.com Live Boards   |
                      |  * Deals (ID: 5030963292)   |
                      |  * Work Orders (5030963279) |
                      +-----------------------------+
```

---

## Getting Started

### Prerequisites
- Python 3.10 or higher (virtual environment recommended)
- Monday.com API Token and Board IDs
- Groq API Key

### 1. Clone Repository and Set Up Environment
```bash
git clone https://github.com/abhinav-juturu/skylark-drones-bi-agent.git
cd skylark-drones-bi-agent

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create or verify the `.env` file in the root directory:
```env
MONDAY_API_TOKEN=your_monday_api_token
GROQ_API_KEY=your_groq_api_key
WORK_ORDERS_BOARD_ID=5030963279
DEALS_BOARD_ID=5030963292
DEFAULT_LLM_MODEL=qwen/qwen3.8-27b
FALLBACK_LLM_MODEL=openai/gpt-oss-120b
```

### 4. Launch the Web Application
```bash
streamlit run app.py
```
Access the application in your browser at `http://localhost:8501`.

---

## Test Suite Execution

The automated test suite validates Monday.com connectivity, schema validation, data cleaning edge cases, analytics calculations, agent workflows, and leadership report generation:

```bash
pytest -v
```

All 18 unit and integration tests validate the complete pipeline with live data:
```
tests/test_agent.py::test_groq_llm_client PASSED
tests/test_agent.py::test_agent_tools_execution PASSED
tests/test_agent.py::test_bi_agent_orchestrator_ask PASSED
tests/test_analytics.py::test_pipeline_health_calculation PASSED
tests/test_analytics.py::test_revenue_realization_calculation PASSED
tests/test_analytics.py::test_sector_kpis_calculation PASSED
tests/test_analytics.py::test_query_engine_queries PASSED
tests/test_leadership.py::test_generate_founder_flash PASSED
tests/test_monday_api.py::test_configuration PASSED
tests/test_monday_api.py::test_monday_api_connection PASSED
tests/test_monday_api.py::test_monday_get_board_schema PASSED
tests/test_monday_api.py::test_monday_get_items PASSED
tests/test_monday_api.py::test_mcp_client_tools PASSED
tests/test_normalizer.py::test_parse_float PASSED
tests/test_normalizer.py::test_parse_date PASSED
tests/test_normalizer.py::test_parse_probability PASSED
tests/test_normalizer.py::test_normalize_sector PASSED
tests/test_normalizer.py::test_live_data_normalization_and_unification PASSED

============================= 18 passed in 55s =============================
```

---

## Repository Structure

```
skylark-drones-bi-agent/
├── app.py                         # Streamlit Interactive Web Application
├── DECISION_LOG.md                # 2-Page Executive Decision Log
├── README.md                      # Comprehensive Documentation
├── requirements.txt               # Project Dependencies
├── .env                           # Environment Configuration
├── src/
│   ├── __init__.py
│   ├── config.py                  # Environment Settings & Validation
│   ├── connectors/
│   │   ├── __init__.py
│   │   ├── monday_api.py          # GraphQL API Client with Retry & Cache
│   │   └── monday_mcp_client.py   # MCP Tool Schema Client & Dispatcher
│   ├── data/
│   │   ├── __init__.py
│   │   ├── schema.py              # Pydantic Schemas for Business Records
│   │   ├── normalizer.py          # Data Resilience, Cleaning & Linking
│   │   └── quality_reporter.py    # Health Score & Audit Caveats
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── metrics.py             # Pipeline, Revenue, AR & Sector KPIs
│   │   └── query_engine.py        # Multi-Dimensional Query Engine
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── prompts.py             # Strategic Personas & Prompts
│   │   ├── llm.py                 # Groq Client Wrapper with Fallback
│   │   ├── tools.py               # Analytical Tool Dispatcher
│   │   └── orchestrator.py        # Conversational Intent Orchestrator
│   └── leadership/
│       ├── __init__.py
│       └── executive_brief.py     # Automated Leadership Brief Generator
└── tests/
    ├── __init__.py
    ├── test_monday_api.py         # Connector and API Tests
    ├── test_normalizer.py         # Data Normalization Tests
    ├── test_analytics.py          # Business Metrics Tests
    ├── test_agent.py              # Agent Workflow Tests
    └── test_leadership.py         # Leadership Generator Tests
```

---

## Deliverables Summary
- **Source Code Repository:** Structured, modular codebase with complete git history.
- **Decision Log:** [`DECISION_LOG.md`](file:///C:/Users/HP/OneDrive/Desktop/Skylark/skylark-drones-bi-agent/DECISION_LOG.md) detailing assumptions, trade-offs, and leadership updates interpretation.
- **Hosted Application:** Production-ready Streamlit application ready for local or cloud deployment.
