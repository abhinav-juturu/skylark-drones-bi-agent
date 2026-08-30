"""
Skylark Drones - Business Intelligence & Executive Agent
Streamlit Web Application
"""

import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime

from src.config import validate_config, DEALS_BOARD_ID, WORK_ORDERS_BOARD_ID
from src.connectors.monday_api import MondayAPIClient
from src.data.normalizer import DataNormalizer
from src.data.quality_reporter import DataQualityReporter
from src.analytics.metrics import BusinessMetricsCalculator
from src.analytics.query_engine import BusinessQueryEngine
from src.agent.llm import GroqLLMClient
from src.agent.orchestrator import BIAgentOrchestrator
from src.leadership.executive_brief import LeadershipBriefGenerator, BriefType

# Page Configuration
st.set_page_config(
    page_title="Skylark Drones BI Agent",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .badge-success {
        background-color: #DEF7EC;
        color: #03543F;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
    }
    .badge-warning {
        background-color: #FEF08A;
        color: #713F12;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
    }
    .badge-info {
        background-color: #E1EFFE;
        color: #1E429F;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource(show_spinner="Connecting to Monday.com & initializing BI Agent...")
def load_orchestrator():
    """Initialize Monday client, LLM, and load initial data."""
    api_client = MondayAPIClient()
    llm_client = GroqLLMClient()
    orchestrator = BIAgentOrchestrator(api_client=api_client, llm_client=llm_client)
    return orchestrator


# Load backend
try:
    orchestrator = load_orchestrator()
except Exception as e:
    st.error(f"⚠️ Initialization Error: {e}")
    st.info("Please verify your `.env` configuration file contains valid MONDAY_API_TOKEN and GROQ_API_KEY.")
    st.stop()

# Session State for Chat History
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "👋 Hello! I am your **Skylark Drones Business Intelligence Agent**.\n\n"
                "I am actively connected to your Monday.com **Deals** and **Work Orders** boards. "
                "Ask me any strategic question about pipeline health, sector performance, cash collection, or operational bottlenecks!"
            ),
        }
    ]

# Sidebar
with st.sidebar:
    st.image("https://raw.githubusercontent.com/feathericons/feather/master/icons/activity.svg", width=45)
    st.title("Skylark BI Agent")
    st.caption("Founder & Executive Intelligence System")
    st.divider()

    st.subheader("🔌 Connection & Integrations")
    st.markdown('<span class="badge-success">🟢 Monday.com Connected</span>', unsafe_allow_html=True)
    st.markdown('<span class="badge-info">⚡ Mode: MCP Tool Protocol + GraphQL API</span>', unsafe_allow_html=True)
    
    st.caption(f"Deals Board ID: `{DEALS_BOARD_ID}`")
    st.caption(f"Work Orders Board ID: `{WORK_ORDERS_BOARD_ID}`")

    if st.button("🔄 Force Sync Monday Data", use_container_width=True):
        with st.spinner("Refreshing live data from Monday.com..."):
            orchestrator.refresh_data(force=True)
            st.success("Data synced with Monday.com boards!")
            st.rerun()

    st.divider()

    st.subheader("🤖 Agent Settings")
    model_choice = st.selectbox(
        "Groq LLM Model",
        ["qwen/qwen3.8-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b"],
        index=0,
    )
    orchestrator.llm_client.model = model_choice

    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Chat history cleared. How can I assist you with Skylark Drones business intelligence today?",
            }
        ]
        st.rerun()

    st.divider()
    st.caption("Built for Skylark Drones • Technical Assessment")


# Header Area
col_title, col_health = st.columns([3, 1])
with col_title:
    st.markdown('<div class="main-header">🦅 Skylark Drones Executive Intelligence</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Real-time Cross-Board Analytics & Strategic Decision Support</div>', unsafe_allow_html=True)

with col_health:
    health_score = orchestrator.quality_report.data_health_score
    badge_class = "badge-success" if health_score >= 80 else ("badge-warning" if health_score >= 60 else "badge-info")
    st.markdown(f'<div style="text-align: right; margin-top: 10px;"><span class="{badge_class}">🛡️ Data Health: {health_score}%</span></div>', unsafe_allow_html=True)

# Top KPI Metric Cards
deals = orchestrator.deals
wos = orchestrator.work_orders
pipe_kpi = BusinessMetricsCalculator.compute_pipeline_health(deals)
rev_kpi = BusinessMetricsCalculator.compute_revenue_realization(wos)

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric(
        label="Active Pipeline Value",
        value=f"₹{pipe_kpi.total_pipeline_value:,.0f}",
        delta=f"Weighted: ₹{pipe_kpi.weighted_pipeline_value:,.0f}",
    )
with m2:
    st.metric(
        label="Total Contracted (PO)",
        value=f"₹{rev_kpi.total_contracted_excl_gst:,.0f}",
        delta=f"{len(wos)} Active Work Orders",
    )
with m3:
    st.metric(
        label="Billed vs Collected",
        value=f"₹{rev_kpi.total_billed_incl_gst:,.0f}",
        delta=f"Collected: ₹{rev_kpi.total_collected_incl_gst:,.0f} ({rev_kpi.collection_rate_pct}%)",
    )
with m4:
    st.metric(
        label="Outstanding AR Exposure",
        value=f"₹{rev_kpi.total_ar_outstanding:,.0f}",
        delta=f"{rev_kpi.high_risk_ar_count} Priority Accounts",
        delta_color="inverse",
    )

# Expandable Data Caveats
with st.expander(f"⚠️ Active Data Quality Caveats ({len(orchestrator.quality_report.caveats)} Notes)"):
    for c in orchestrator.quality_report.caveats:
        level_icon = "🚨" if c.level == "CRITICAL" else ("⚠️" if c.level == "WARNING" else "ℹ️")
        st.markdown(f"**{level_icon} [{c.category}]** {c.message}")

st.markdown("<br>", unsafe_allow_html=True)

# Main Application Tabs
tab_chat, tab_analytics, tab_briefs, tab_audit = st.tabs([
    "💬 Executive AI Agent",
    "📊 Visual Analytics & Funnel",
    "📋 Leadership Updates (Founder Flash)",
    "🛡️ Data Quality & Audit",
])


# ==========================================
# TAB 1: EXECUTIVE AI CHAT
# ==========================================
with tab_chat:
    st.subheader("💬 Ask Founder-Level Business Questions")
    
    # Prompt suggestions
    st.markdown("**Quick Prompts:**")
    prompt_cols = st.columns(4)
    sample_queries = [
        "How's our pipeline looking for energy sector this quarter?",
        "Which accounts represent our highest AR exposure?",
        "What is our win rate and stage distribution across deals?",
        "What are our key operational execution bottlenecks?",
    ]

    selected_sample = None
    for idx, (col, sq) in enumerate(zip(prompt_cols, sample_queries)):
        with col:
            if st.button(sq, key=f"sq_{idx}", use_container_width=True):
                selected_sample = sq

    # Render Conversation History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Handle user input (from chat input or sample prompt button)
    user_input = st.chat_input("Ask a business question across Deals and Work Orders...")
    query_to_run = selected_sample or user_input

    if query_to_run:
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": query_to_run})
        with st.chat_message("user"):
            st.markdown(query_to_run)

        # Generate Agent response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            with st.spinner("Analyzing cross-board records & synthesizing insights..."):
                try:
                    # Collect previous turns for context
                    history = [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.messages[:-1]
                        if m["role"] in ("user", "assistant")
                    ]
                    
                    stream_gen, followups = orchestrator.ask_stream(query_to_run, conversation_history=history)
                    for chunk in stream_gen:
                        full_response += chunk
                        message_placeholder.markdown(full_response + "▌")
                    
                    message_placeholder.markdown(full_response)

                    # Display Suggested Follow-ups
                    if followups:
                        st.markdown("**Suggested Follow-up Drilldowns:**")
                        f_cols = st.columns(len(followups))
                        for f_idx, (f_col, f_text) in enumerate(zip(f_cols, followups)):
                            with f_col:
                                st.button(f_text, key=f"fu_{len(st.session_state.messages)}_{f_idx}", on_click=lambda t=f_text: st.session_state.messages.append({"role": "user", "content": t}))

                except Exception as err:
                    full_response = f"⚠️ An error occurred while generating insight: {err}"
                    message_placeholder.markdown(full_response)

        # Save assistant message
        st.session_state.messages.append({"role": "assistant", "content": full_response})


# ==========================================
# TAB 2: VISUAL ANALYTICS & FUNNEL
# ==========================================
with tab_analytics:
    st.subheader("📊 Cross-Board Visual Business Intelligence")

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown("##### 🎯 Deals Pipeline Stage Breakdown")
        stages_data = []
        for stage, info in pipe_kpi.stage_breakdown.items():
            stages_data.append({"Stage": stage, "Count": info["count"], "Value": info["total_value"]})
        
        if stages_data:
            df_stages = pd.DataFrame(stages_data)
            chart_stage = alt.Chart(df_stages).mark_bar(color="#3B82F6", cornerRadiusEnd=4).encode(
                x=alt.X("Value:Q", title="Total Value (₹)"),
                y=alt.Y("Stage:N", sort="-x", title="Deal Stage"),
                tooltip=["Stage", "Count", alt.Tooltip("Value:Q", format=",.2f")],
            ).properties(height=320)
            st.altair_chart(chart_stage, use_container_width=True)

    with col_chart2:
        st.markdown("##### 🏢 Sector Performance Comparison")
        sectors_data = BusinessMetricsCalculator.compute_sector_kpis(deals, wos)
        df_sec = pd.DataFrame([s.model_dump() for s in sectors_data[:7]])
        
        if not df_sec.empty:
            chart_sec = alt.Chart(df_sec).mark_bar(color="#10B981", cornerRadiusEnd=4).encode(
                x=alt.X("total_contracted:Q", title="Total Contracted PO Value (₹)"),
                y=alt.Y("sector_name:N", sort="-x", title="Sector"),
                tooltip=["sector_name", "deals_count", "work_orders_count", alt.Tooltip("total_contracted:Q", format=",.2f"), alt.Tooltip("total_collected:Q", format=",.2f")],
            ).properties(height=320)
            st.altair_chart(chart_sec, use_container_width=True)

    st.divider()

    st.markdown("##### 🚨 Accounts Receivable (AR) & Priority Risk Matrix")
    if rev_kpi.ar_priority_accounts:
        df_ar = pd.DataFrame(rev_kpi.ar_priority_accounts)
        st.dataframe(
            df_ar.rename(columns={
                "deal_name": "Deal Name",
                "customer_code": "Customer",
                "sector": "Sector",
                "amount_receivable": "Amount Receivable (₹)",
                "billed_amount": "Billed Amount (₹)",
                "collected_amount": "Collected Amount (₹)",
                "is_priority": "Priority Flag",
                "billing_status": "Billing Status",
            }),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No outstanding AR priority accounts recorded.")


# ==========================================
# TAB 3: LEADERSHIP UPDATES (FOUNDER FLASH)
# ==========================================
with tab_briefs:
    st.subheader("📋 Leadership Update & Executive Brief Generator")
    st.markdown(
        "Generate comprehensive, slide-ready and board-ready briefs summarizing pipeline, revenue realization, and strategic operational health."
    )

    brief_choice = st.radio(
        "Select Brief Type",
        [
            ("Weekly Founder Flash", BriefType.FOUNDER_FLASH),
            ("Sector Performance Scorecard", BriefType.SECTOR_SCORECARD),
            ("Cash Flow & AR Risk Matrix", BriefType.AR_RISK_MATRIX),
            ("Operational Execution & Fulfillment", BriefType.OPERATIONAL_FULFILLMENT),
        ],
        format_func=lambda x: x[0],
        horizontal=True,
    )

    if st.button("🚀 Generate Executive Brief", type="primary"):
        with st.spinner(f"Compiling {brief_choice[0]}..."):
            generator = LeadershipBriefGenerator(orchestrator.query_engine, orchestrator.llm_client)
            brief_output = generator.generate_brief(brief_choice[1])
            
            st.markdown("---")
            st.markdown(brief_output["content"])
            
            st.download_button(
                label="📥 Download Brief (Markdown)",
                data=brief_output["content"],
                file_name=f"skylark_{brief_choice[1].value}_{datetime.now().strftime('%Y%m%d')}.md",
                mime="text/markdown",
            )


# ==========================================
# TAB 4: DATA QUALITY & AUDIT
# ==========================================
with tab_audit:
    st.subheader("🛡️ Data Resilience & Completeness Audit")
    
    q_rep = orchestrator.quality_report
    
    qcol1, qcol2, qcol3, qcol4 = st.columns(4)
    with qcol1:
        st.metric("Total Deals in CRM", q_rep.total_deals)
    with qcol2:
        st.metric("Total Work Orders", q_rep.total_work_orders)
    with qcol3:
        st.metric("Deals Missing Values", q_rep.deals_with_missing_value)
    with qcol4:
        st.metric("Work Orders with Pending AR", q_rep.work_orders_with_overdue_ar)

    st.markdown("#### Audit Notes & Caveats")
    for caveat in q_rep.caveats:
        alert_type = st.error if caveat.level == "CRITICAL" else (st.warning if caveat.level == "WARNING" else st.info)
        alert_type(f"**[{caveat.category}]** {caveat.message} (Impacts {caveat.impacted_records_count} records / {caveat.impacted_records_pct}%)")

    st.divider()
    st.markdown("#### Raw Deals Sample")
    df_deals_sample = pd.DataFrame([d.model_dump(exclude={"raw_columns"}) for d in deals[:10]])
    st.dataframe(df_deals_sample, use_container_width=True)

    st.markdown("#### Raw Work Orders Sample")
    df_wos_sample = pd.DataFrame([w.model_dump(exclude={"raw_columns"}) for w in wos[:10]])
    st.dataframe(df_wos_sample, use_container_width=True)
