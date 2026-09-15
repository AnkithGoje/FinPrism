"""
streamlit_app.py — Human-facing chat interface for the Configurable Financial Agent.

Run with:
    streamlit run ui/streamlit_app.py

Features:
  - Persona and sector selectors in the sidebar
  - Chat history with message bubbles
  - Tool call transparency panel (expandable)
  - Companies referenced badge list
  - Confidence indicator
"""

import sys
from pathlib import Path

# Ensure project root is on path when running from ui/ directory
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from agent.agent import run_agent
from agent.personas import PERSONAS, VALID_SECTORS
from agent.schemas import QueryRequest

# ─────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="FinPrism | Financial Analyst Agent",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        margin-bottom: 1.5rem;
    }
    .persona-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 8px;
    }
    .mf-badge { background-color: #e3f2fd; color: #1565c0; }
    .eq-badge { background-color: #e8f5e9; color: #2e7d32; }
    .pe-badge { background-color: #fce4ec; color: #c62828; }

    .confidence-high { color: #2e7d32; font-weight: 600; }
    .confidence-medium { color: #f57f17; font-weight: 600; }
    .confidence-low { color: #c62828; font-weight: 600; }

    .company-chip {
        display: inline-block;
        background: #f0f4ff;
        border: 1px solid #c5d0f0;
        border-radius: 12px;
        padding: 2px 10px;
        font-size: 0.8rem;
        margin: 2px;
        color: #2c3e6b;
    }
    .tool-call-item {
        background: #f8f9fa;
        border-left: 3px solid #6c757d;
        padding: 6px 10px;
        margin: 4px 0;
        border-radius: 0 4px 4px 0;
        font-size: 0.85rem;
        font-family: monospace;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# Sidebar — Configuration
# ─────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 💎 FinPrism")
    st.caption("Configurable Financial Analyst Agent")
    st.markdown("---")

    persona_options = {
        "mutual_fund_analyst": "📈 Mutual Fund Analyst",
        "equity_analyst": "📊 Equity Analyst",
        "pe_analyst": "🏦 PE Analyst",
    }
    selected_persona = st.selectbox(
        "Analyst Persona",
        options=list(persona_options.keys()),
        format_func=lambda x: persona_options[x],
        key="persona_select",
    )

    sector_options = {
        "tech": "💻 Technology",
        "retail": "🛒 Retail",
        "manufacturing": "🏭 Manufacturing",
    }
    selected_sector = st.selectbox(
        "Sector",
        options=list(sector_options.keys()),
        format_func=lambda x: sector_options[x],
        key="sector_select",
    )

    st.markdown("---")

    # Persona description
    persona_desc = {
        "mutual_fund_analyst": "Long-only, benchmark-relative. Focuses on sustainable growth, valuation vs. index, portfolio fit.",
        "equity_analyst": "Fundamentals-driven — earnings, margins, competitive positioning, price targets.",
        "pe_analyst": "Deal/ops lens — cash flow, leverage capacity, operational levers, exit potential.",
    }
    st.info(persona_desc[selected_persona])

    st.markdown("---")
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.markdown("**Sample Questions:**")
    sample_questions = [
        "Is this sector a good place to be putting money to work right now?",
        "Walk me through the margin profile — who's improving and who's under pressure?",
        "Which company here looks like the most attractive target?",
        "What's the most recent hiring signal you have for [company name]?",
        "What do you think about Tesla?",  # out-of-scope test
    ]
    for q in sample_questions:
        if st.button(f"💬 {q[:50]}...", key=f"sample_{q[:20]}", use_container_width=True):
            st.session_state.pending_question = q

# ─────────────────────────────────────────────────────────────
# Main panel
# ─────────────────────────────────────────────────────────────

st.markdown('<div class="main-header">💎 FinPrism</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="sub-header">Multi-Lens Financial Research Agent &bull; Configured as: '
    f'<strong>{persona_options[selected_persona]}</strong> | '
    f'<strong>{sector_options[selected_sector]}</strong></div>',
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

# ─────────────────────────────────────────────────────────────
# Display chat history
# ─────────────────────────────────────────────────────────────

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            # Agent response — rich display
            response = msg.get("response_obj")

            if response:
                # Persona + sector badge
                badge_class = {"mutual_fund_analyst": "mf", "equity_analyst": "eq", "pe_analyst": "pe"}.get(
                    response.persona, "eq"
                )
                st.markdown(
                    f'<span class="persona-badge {badge_class}-badge">{response.persona_display}</span>'
                    f'<span class="persona-badge" style="background:#f5f5f5;color:#555;">{response.sector_display}</span>',
                    unsafe_allow_html=True,
                )

                st.markdown(response.answer)

                # Companies referenced
                if response.companies_referenced:
                    st.markdown("**Companies referenced:**")
                    chips_html = " ".join(
                        f'<span class="company-chip">{c}</span>'
                        for c in response.companies_referenced
                    )
                    st.markdown(chips_html, unsafe_allow_html=True)

                # Confidence
                conf_color = {"high": "confidence-high", "medium": "confidence-medium", "low": "confidence-low"}.get(
                    response.confidence, "confidence-medium"
                )
                st.markdown(
                    f'<span class="{conf_color}">Confidence: {response.confidence.upper()}</span>',
                    unsafe_allow_html=True,
                )

                # Tool calls transparency (expandable)
                if response.tool_calls_made:
                    with st.expander(f"🔧 MCP Tool Calls ({len(response.tool_calls_made)})", expanded=False):
                        for tc in response.tool_calls_made:
                            st.markdown(
                                f'<div class="tool-call-item">'
                                f'<strong>{tc.tool_name}</strong>({tc.arguments}) → {tc.result_summary}'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

                # Caveats
                if response.data_coverage_note:
                    st.warning(response.data_coverage_note)

                st.caption(response.caveats)
            else:
                st.markdown(msg["content"])


# ─────────────────────────────────────────────────────────────
# Input handling
# ─────────────────────────────────────────────────────────────

# Handle sample question buttons
user_input = st.session_state.pending_question
st.session_state.pending_question = None

# Chat input (overrides pending if user typed something)
typed_input = st.chat_input("Ask your analyst anything about this sector...")
if typed_input:
    user_input = typed_input

if user_input:
    # Display user message
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    # Run agent
    with st.chat_message("assistant"):
        with st.spinner(f"🔍 {persona_options[selected_persona]} analyzing..."):
            try:
                request = QueryRequest(
                    query=user_input,
                    persona=selected_persona,
                    sector=selected_sector,
                )
                result = run_agent(request)

                # Persona badge
                badge_class = {"mutual_fund_analyst": "mf", "equity_analyst": "eq", "pe_analyst": "pe"}.get(
                    selected_persona, "eq"
                )
                st.markdown(
                    f'<span class="persona-badge {badge_class}-badge">{result.persona_display}</span>'
                    f'<span class="persona-badge" style="background:#f5f5f5;color:#555;">{result.sector_display}</span>',
                    unsafe_allow_html=True,
                )

                st.markdown(result.answer)

                if result.companies_referenced:
                    st.markdown("**Companies referenced:**")
                    chips_html = " ".join(
                        f'<span class="company-chip">{c}</span>'
                        for c in result.companies_referenced
                    )
                    st.markdown(chips_html, unsafe_allow_html=True)

                conf_color = {"high": "confidence-high", "medium": "confidence-medium", "low": "confidence-low"}.get(
                    result.confidence, "confidence-medium"
                )
                st.markdown(
                    f'<span class="{conf_color}">Confidence: {result.confidence.upper()}</span>',
                    unsafe_allow_html=True,
                )

                if result.tool_calls_made:
                    with st.expander(f"🔧 MCP Tool Calls ({len(result.tool_calls_made)})", expanded=False):
                        for tc in result.tool_calls_made:
                            st.markdown(
                                f'<div class="tool-call-item">'
                                f'<strong>{tc.tool_name}</strong>({tc.arguments}) → {tc.result_summary}'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

                if result.data_coverage_note:
                    st.warning(result.data_coverage_note)

                st.caption(result.caveats)

                # Save to history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result.answer,
                    "response_obj": result,
                })

            except Exception as e:
                error_msg = f"❌ Error: {str(e)}\n\nMake sure the database is built: `python db/build_db.py`"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg,
                })
