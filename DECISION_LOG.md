# Skylark Drones BI Agent - Decision Log

**Author:** Nagaabhinavasai Jutur  
**Role:** Full Stack AI Engineer Candidate  
**Project:** Monday.com Business Intelligence & Strategic Operations Agent  
**Date:** August 2026  

---

## 1. Context and Problem Understanding

Founders and executives at Skylark Drones need fast, reliable answers to strategic questions that span multiple operational systems. In practice, commercial sales data lives in a CRM Deals board, while operational delivery, billing status, and collections reside in an Execution Work Orders board. 

Answering a straightforward question—such as *"How does our Q4 energy pipeline compare against actual cash collections?"*—historically required manual data exports, formatting inconsistencies, manual cross-board joins, and ad-hoc spreadsheet calculations.

The objective of this project was to build a resilient, conversational Business Intelligence agent that connects dynamically to Monday.com, cleans real-world messy data on the fly, computes core business metrics, and surfaces actionable leadership insights with full transparency around data health.

---

## 2. Key Architectural Assumptions

### 2.1 Cross-Board Entity Linking
- **The Reality:** In real-world workflows, Deals CRM and Work Orders boards rarely share a single clean foreign key. Work orders reference deals either by client-deal codenames (for example, *Sakura*, *Scooby-Doo*, *Appa*) or by serial numbers (such as *SDPLDEAL-002*).
- **Our Approach:** We built a deterministic and fuzzy normalization layer that canonicalizes deal names (case-insensitive trimming, whitespace removal) and parses serial references. This joins commercial pipeline commitments with real execution milestones, enabling unified pipeline-to-cash analysis.

### 2.2 Handling Sparse Financial and Date Records
- **The Reality:** Real business data contains significant gaps. Approximately 52% of deal records in the raw pipeline did not have an explicit deal value assigned, and several records lacked projected close dates.
- **Our Approach:** Rather than silently discarding incomplete rows or imputing artificial averages, the system calculates pipeline aggregates strictly from recorded figures and transparently surfaces an audit caveat to the user. This ensures founders know the exact reliability and scope of the underlying figures.

### 2.3 Closure Probability Normalization
- **The Reality:** Probability was entered inconsistently across records as percentages (`80%`), decimals (`0.8`), text descriptors (`High`, `Medium`, `Low`), or stage names (`Won`, `Lost`).
- **Our Approach:** We implemented a multi-stage parser that maps qualitative tags (`High` to 0.8, `Medium` to 0.5, `Low` to 0.2, `Won` to 1.0) and percentages into clean floats between 0.0 and 1.0. This allows the system to compute both Raw Pipeline and Risk-Weighted Pipeline metrics.

### 2.4 Canonical Sector Taxonomy
- **The Reality:** Sector classifications contained casing and naming variations (such as `mining`, `Mining`, `powerline`, `Power line`, `Solar Energy`).
- **Our Approach:** We standardized entries into canonical verticals: *Mining*, *Powerline*, *Renewables/Solar*, *Infrastructure*, *Telecom*, *Agriculture*, and *Enterprise/Other*.

---

## 3. Engineering Decisions and Trade-offs

| Decision | Alternative Considered | Chosen Approach and Rationale |
| :--- | :--- | :--- |
| **Model Context Protocol (MCP) + GraphQL Fallback** | Pure GraphQL API or Pure MCP | We implemented an MCP-compatible tool schema interface for standardized agent function calling, backed by a high-throughput Monday.com GraphQL API client with retries, exponential backoff, and pagination. This provides standard tool interoperability alongside robust in-process execution. |
| **Streamlit Interface** | React + FastAPI | Selected Streamlit to deliver a responsive, production-ready web application with real-time streaming tokens, Altair visual funnels, and executive KPI cards without unnecessary frontend build overhead. |
| **Groq High-Speed Inference** | OpenAI / Anthropic Cloud API | Utilized Groq (`qwen/qwen3.8-27b` with automatic fallback to `openai/gpt-oss-120b`). This delivers sub-second time-to-first-token latency, critical for responsive executive conversational interaction. |
| **In-Memory TTL Caching with Manual Sync** | Uncached Live Calls or Database Sync | Implemented an in-memory cache with a 5-minute TTL to prevent API rate-limiting (HTTP 429), paired with a prominent "Force Sync Monday Data" trigger for instant updates on demand. |

---

## 4. Leadership Updates Interpretation and Design

### The Need
Founders and executive leaders do not only ask ad-hoc questions; they regularly need consolidated executive summaries for board meetings, leadership syncs, and operational standups.

### Implementation
We designed the **Leadership Brief Generator** (`src/leadership/executive_brief.py`), which automates four distinct executive reports:

1. **Weekly Founder Flash:** A macro view of active pipeline value, total contracted commitments, billed revenue vs. collected cash, top three business highlights, critical bottlenecks, and immediate weekly priorities.
2. **Sector Performance Scorecard:** A comparative ranking of sectors by total contracted value, win rates, and strategic growth opportunities.
3. **Accounts Receivable (AR) Risk Matrix:** Clear breakdown of overdue receivables, unbilled backlogs, and prioritized high-risk client accounts requiring immediate finance follow-up.
4. **Operational Fulfillment Review:** Execution status distribution, PO quantity fulfillment rates, and work orders requiring billing status updates.

Each brief is formatted in clean markdown, downloadable directly from the interface for slide decks or stakeholder memos.

---

## 5. Future Enhancements With More Time

1. **Real-Time Webhook Synchronization:** Transition from periodic polling and caching to Monday.com webhook listeners for instant event-driven updates.
2. **Predictive Cash Realization Models:** Train a lightweight statistical model on historical billing turnaround cycles to forecast monthly cash collections with confidence intervals.
3. **Controlled Write-Back Operations:** Add capability for authorized executives to flag priority accounts or trigger automated task updates back into Monday.com boards.
4. **Multi-Tenant OAuth Integration:** Package the connector as a multi-tenant Monday.com Marketplace app allowing any workspace to authenticate and map custom board columns dynamically.
