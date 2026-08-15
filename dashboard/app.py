"""
Syn Bank Share of Wallet Intelligence Engine - interactive front-end (Team ROOT3).

Two pages, navigated from the sidebar:
  1. Dashboard - portfolio KPIs, reliability tiers, top opportunities, per-client drill-down.
  2. Ask a Question - live chat wrapping scripts/nl_query_assistant.py (rule-based, zero-cost,
     no API key - see that module's docstring for why this design was chosen for the demo).

Run: streamlit run dashboard/app.py
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED_DIR = ROOT / "hackathon-finreports" / "_extracted"
sys.path.insert(0, str(ROOT / "scripts"))

from nl_query_assistant import QueryAssistant  # noqa: E402

# Brand palette - identical to docs/deliverables/ROOT3_one_pager.pdf and docs/genai/genai_snapshot.png.
NAVY = "#0B2545"
TEAL = "#2E86AB"
GOLD = "#C9A227"
BG = "#F3F5F9"
CARD_BG = "#FFFFFF"
CARD_BORDER = "#E3E8F0"
TEXT = "#1A2233"
MUTED = "#6B7688"
TRACK = "#E6EAF1"
TIER_COLORS = {"moderate": TEAL, "low": GOLD, "insufficient": "#A7AEBB"}
KPI_COLORS = [NAVY, "#123A66", "#1B5C7A", "#1F7A82", TEAL]
PLOTLY_TEMPLATE = "plotly_white"

st.set_page_config(page_title="Syn Bank Share of Wallet Engine", layout="wide")

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
    .stApp {{ background: {BG}; }}
    .block-container {{ padding-top: 2rem; max-width: 1300px; }}

    /* ---- Sidebar (nav) ---- */
    section[data-testid="stSidebar"] {{
        background: {NAVY}; padding-top: 0;
    }}
    section[data-testid="stSidebar"] * {{ color: #E8EEF5; }}
    .sidebar-logo {{
        display: flex; align-items: center; gap: 10px; padding: 22px 18px 18px 18px;
        border-bottom: 1px solid rgba(255,255,255,0.12); margin-bottom: 14px;
    }}
    .sidebar-logo .mark {{
        width: 36px; height: 36px; border-radius: 9px; background: linear-gradient(135deg, {TEAL}, {GOLD});
        display: flex; align-items: center; justify-content: center; font-weight: 800; color: {NAVY};
        font-size: 0.95rem; flex-shrink: 0;
    }}
    .sidebar-logo .title {{ font-weight: 700; font-size: 0.95rem; line-height: 1.2; color: #fff; }}
    .sidebar-logo .subtitle {{ font-size: 0.72rem; color: rgba(255,255,255,0.55); }}
    .sidebar-footer {{
        position: fixed; bottom: 0; padding: 16px 18px; width: inherit;
        border-top: 1px solid rgba(255,255,255,0.12); font-size: 0.72rem; color: rgba(255,255,255,0.5);
    }}
    .sidebar-footer b {{ color: rgba(255,255,255,0.8); display: block; margin-bottom: 3px; font-size: 0.78rem; }}

    section[data-testid="stSidebar"] div[role="radiogroup"] {{ padding: 0 10px; gap: 4px; display: flex; flex-direction: column; }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label {{
        background: transparent; border-radius: 8px; padding: 9px 12px; margin: 0;
        transition: background 0.15s ease; cursor: pointer;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {{ background: rgba(255,255,255,0.06); }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label div:first-child {{ display: none; }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label p {{ font-size: 0.88rem; font-weight: 500; }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] {{
        background: rgba(46,134,171,0.35); border-left: 3px solid {TEAL};
    }}

    /* ---- Page header ---- */
    .page-title {{ font-size: 1.55rem; font-weight: 800; color: {NAVY}; margin-bottom: 2px; }}
    .page-subtitle {{ font-size: 0.9rem; color: {MUTED}; margin-bottom: 6px; }}

    /* ---- Section headers ---- */
    .section-header {{
        font-size: 1.02rem; font-weight: 700; color: {TEXT}; margin: 0 0 2px 0;
        padding-left: 10px; border-left: 4px solid {TEAL};
    }}
    .section-caption {{ font-size: 0.76rem; color: {MUTED}; text-transform: uppercase; letter-spacing: 0.04em; margin: 0 0 10px 12px; }}

    /* ---- KPI tiles ---- */
    .kpi-tile {{
        border-radius: 12px; padding: 16px 16px 14px 16px; color: white; height: 100%;
        box-shadow: 0 4px 14px rgba(11,37,69,0.16);
    }}
    .kpi-tile .kpi-value {{ font-size: 1.55rem; font-weight: 800; line-height: 1.15; }}
    .kpi-tile .kpi-label {{ font-size: 0.72rem; opacity: 0.85; margin-top: 4px; font-weight: 500; }}

    /* ---- Bordered containers (cards) ---- */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: {CARD_BG}; border-radius: 12px !important; border: 1px solid {CARD_BORDER} !important;
        box-shadow: 0 2px 12px rgba(16,24,40,0.05);
    }}
    div[data-testid="stVerticalBlockBorderWrapper"] > div {{ padding: 4px; }}

    /* ---- Metrics inside cards ---- */
    div[data-testid="stMetric"] {{ background: transparent; }}
    div[data-testid="stMetricLabel"] {{ color: {MUTED} !important; font-size: 0.75rem !important; font-weight: 600 !important; }}
    div[data-testid="stMetricValue"] {{ color: {NAVY} !important; font-weight: 800 !important; }}

    /* ---- Buttons (example question chips) ---- */
    .stButton > button {{
        background: {CARD_BG}; border: 1px solid {CARD_BORDER}; color: {TEXT};
        border-radius: 18px; font-size: 0.82rem; transition: all 0.15s ease;
    }}
    .stButton > button:hover {{ border-color: {TEAL}; color: {TEAL}; }}

    /* ---- Reliability badge ---- */
    .tier-badge {{
        display: inline-block; padding: 3px 12px; border-radius: 20px; font-size: 0.8rem;
        font-weight: 700; letter-spacing: 0.02em;
    }}

    /* ---- Chat bubbles ---- */
    div[data-testid="stChatMessage"] {{ background: {CARD_BG}; border: 1px solid {CARD_BORDER}; border-radius: 12px; }}

    hr {{ border-color: {CARD_BORDER} !important; }}
    #MainMenu, footer {{ visibility: hidden; }}
    </style>
    """,
    unsafe_allow_html=True,
)


def plotly_light_layout(fig, height=None, **kwargs):
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, family="Inter, sans-serif"),
        margin=dict(l=0, r=0, t=10, b=0),
        **({"height": height} if height else {}),
        **kwargs,
    )
    fig.update_xaxes(gridcolor=TRACK, zerolinecolor=CARD_BORDER)
    fig.update_yaxes(gridcolor=TRACK, zerolinecolor=CARD_BORDER)
    return fig


def kpi_tile(col, value, label, color):
    col.markdown(
        f"""<div class="kpi-tile" style="background:{color};">
              <div class="kpi-value">{value}</div>
              <div class="kpi-label">{label}</div>
            </div>""",
        unsafe_allow_html=True,
    )


def section(title, caption=None):
    st.markdown(f'<p class="section-header">{title}</p>', unsafe_allow_html=True)
    if caption:
        st.markdown(f'<p class="section-caption">{caption}</p>', unsafe_allow_html=True)


@st.cache_data
def load_data():
    wallet_model = pd.read_csv(EXTRACTED_DIR / "wallet_model.csv")
    ranking = pd.read_csv(EXTRACTED_DIR / "opportunity_ranking.csv")
    anomalies_path = EXTRACTED_DIR / "anomalies_detected.csv"
    anomalies = pd.read_csv(anomalies_path) if anomalies_path.exists() else pd.DataFrame()
    wallet_model["reliability_tier"] = wallet_model["top_down_reliability"].str.split(" - ").str[0]
    ranking["reliability_tier"] = ranking["top_down_reliability"].str.split(" - ").str[0]
    return wallet_model, ranking, anomalies


@st.cache_resource
def load_assistant():
    return QueryAssistant()


wallet_model, ranking, anomalies = load_data()
qa = load_assistant()

# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-logo">
          <div class="mark">SW</div>
          <div>
            <div class="title">Syn Bank</div>
            <div class="subtitle">Share of Wallet Engine</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    page = st.radio("Navigate", ["Dashboard", "Ask a Question"], label_visibility="collapsed")
    st.markdown(
        """
        <div class="sidebar-footer">
          <b>Team ROOT3</b>
          Luke Naidoo &middot; Wisdom Ejiro Peru &middot; Fatan Saud<br>
          Standard Bank Data School Hackathon 2026
        </div>
        """,
        unsafe_allow_html=True,
    )

# ----------------------------------------------------------------------------
# Dashboard page
# ----------------------------------------------------------------------------
if page == "Dashboard":
    st.markdown('<p class="page-title">Share of Wallet Dashboard</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="page-subtitle">Numerator (internal share) &times; Denominator (top-down wallet) &times; GenAI synthesis, across 20 JSE-listed clients</p>',
        unsafe_allow_html=True,
    )
    st.write("")

    actionable = wallet_model[wallet_model["reliability_tier"] == "moderate"]
    tier_counts = wallet_model["reliability_tier"].value_counts()

    kpis = [
        (str(len(wallet_model)), "Clients analyzed"),
        (f"{actionable['blended_share_pct'].mean():.1f}%", "Avg. blended share (actionable tier)"),
        (f"R{actionable['total_gap_zar_m'].sum() / 1000:.0f}bn", "Combined addressable gap"),
        (str(len(anomalies) if not anomalies.empty else 0), "Anomalies flagged"),
        (f"{tier_counts.get('moderate', 0)} / {tier_counts.get('low', 0)} / {tier_counts.get('insufficient', 0)}", "Moderate / Low / Insufficient reliability"),
    ]
    kpi_cols = st.columns(5)
    for col, (value, label), color in zip(kpi_cols, kpis, KPI_COLORS):
        kpi_tile(col, value, label, color)

    st.caption(
        "Reliability tiers matter: **moderate** = ZAR reporter, literal Rand figures. "
        "**low** = foreign-currency reporter, read the % as directional only - Rand gaps are consolidated "
        "GLOBAL figures, not SA-specific (e.g. Glencore's R9.5tn figure). **insufficient** = Group financials "
        "not disclosed at all."
    )

    st.write("")
    col_left, col_right = st.columns([3, 2])

    with col_left:
        with st.container(border=True):
            section("Top opportunities", "Ranked by total Rand gap")
            actionable_only = st.toggle("Actionable tier only (ZAR reporters)", value=False)
            top_n = st.slider("Show top N", min_value=5, max_value=20, value=10)

            chart_df = ranking.copy()
            if actionable_only:
                chart_df = chart_df[chart_df["reliability_tier"] == "moderate"]
            chart_df = chart_df.dropna(subset=["total_gap_zar_m"]).sort_values("total_gap_zar_m", ascending=False).head(top_n)
            chart_df["gap_rbn"] = chart_df["total_gap_zar_m"] / 1000

            fig = px.bar(
                chart_df.sort_values("gap_rbn"), x="gap_rbn", y="entity_name", orientation="h",
                color="reliability_tier", color_discrete_map=TIER_COLORS,
                labels={"gap_rbn": "Total gap (R billions)", "entity_name": "", "reliability_tier": "Reliability"},
                hover_data={"blended_share_pct": True, "sector": True, "gap_rbn": ":.0f"},
            )
            plotly_light_layout(fig, height=max(320, 32 * len(chart_df)), legend=dict(orientation="h", y=-0.15))
            fig.update_traces(marker_line_width=0)
            st.plotly_chart(fig, width="stretch")

    with col_right:
        with st.container(border=True):
            section("Reliability tier mix", "Portfolio composition")
            tier_df = tier_counts.rename_axis("tier").reset_index(name="count")
            fig2 = px.pie(
                tier_df, names="tier", values="count", color="tier", color_discrete_map=TIER_COLORS, hole=0.6,
            )
            plotly_light_layout(fig2, height=260, showlegend=True, legend=dict(orientation="h", y=-0.1))
            fig2.update_traces(marker=dict(line=dict(color=CARD_BG, width=3)), textfont=dict(color=TEXT))
            st.plotly_chart(fig2, width="stretch")

        if not anomalies.empty:
            with st.container(border=True):
                section("Anomalies by type", "Rule-based detection")
                rule_counts = anomalies["rule"].value_counts().rename_axis("rule").reset_index(name="count")
                fig3 = px.bar(rule_counts, x="count", y="rule", orientation="h", color_discrete_sequence=[TEAL])
                plotly_light_layout(fig3, height=240, yaxis_title="", xaxis_title="Instances")
                fig3.update_traces(marker_line_width=0)
                st.plotly_chart(fig3, width="stretch")

    st.write("")
    with st.container(border=True):
        section("Client drill-down", "Per-client view")
        client = st.selectbox("Select a client", sorted(wallet_model["entity_name"].tolist()))
        row = wallet_model[wallet_model["entity_name"] == client].iloc[0]

        c1, c2 = st.columns([2, 3])
        with c1:
            st.markdown(f"**{client}** &mdash; {row['sector']}, {row['currency']} reporter, FY{int(row['fiscal_year'])}")
            tier = row["reliability_tier"]
            badge_color = TIER_COLORS.get(tier, "#888")
            st.markdown(
                f"<span class='tier-badge' style='background-color:{badge_color}; color:white;'>"
                f"{tier} reliability</span>",
                unsafe_allow_html=True,
            )
            st.write("")
            if pd.notna(row["blended_share_pct"]):
                m1, m2 = st.columns(2)
                m1.metric("Blended share", f"{row['blended_share_pct']:.1f}%")
                m2.metric("Blended gap", f"R{row['total_gap_zar_m'] / 1000:,.1f}bn" if abs(row['total_gap_zar_m']) >= 1000 else f"R{row['total_gap_zar_m']:.1f}m")
            else:
                st.info("Blended total not computed (insufficient data)")

            client_anomalies = anomalies[anomalies["entity_name"] == client] if not anomalies.empty else pd.DataFrame()
            if not client_anomalies.empty:
                st.warning(f"{len(client_anomalies)} anomaly(ies) flagged for this client - see the Ask a Question page for details")

        with c2:
            pillar_names = {1: "Transactional Banking", 2: "Trade & Working Capital", 3: "Foreign/Cross-Border"}
            pillar_data = []
            for i in [1, 2, 3]:
                share = row[f"share_pct_pillar{i}"]
                if pd.notna(share):
                    pillar_data.append({"pillar": pillar_names[i], "share_pct": share, "captured": share, "gap": max(0, 100 - share)})
            if pillar_data:
                pdf = pd.DataFrame(pillar_data)
                fig4 = go.Figure()
                fig4.add_bar(y=pdf["pillar"], x=pdf["captured"], name="Syn Bank share", orientation="h", marker_color=TEAL)
                fig4.add_bar(y=pdf["pillar"], x=pdf["gap"], name="Gap to 100%", orientation="h", marker_color=TRACK)
                plotly_light_layout(
                    fig4, height=220, barmode="stack",
                    xaxis_title="% of pillar wallet", legend=dict(orientation="h", y=-0.3),
                )
                fig4.update_traces(marker_line_width=0)
                st.plotly_chart(fig4, width="stretch")
            else:
                st.info("No pillar-level external wallet estimate available for this client.")

# ----------------------------------------------------------------------------
# Ask a Question page
# ----------------------------------------------------------------------------
else:
    st.markdown('<p class="page-title">Ask a Question</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="page-subtitle">Live, zero-cost, deterministic - no API key, safe to demo</p>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Handles lookups, comparisons, rankings, reliability checks, and anomaly questions. Genuinely "
        "open-ended questions are explicitly declined (see `docs/genai/nl_query_prompt.md` for how those "
        "are handled via LLM reasoning instead)."
    )
    st.write("")

    example_questions = [
        "What is Pepkor's share of the transactional wallet?",
        "What are the top 3 actionable opportunities?",
        "Why is Glencore's gap so large?",
        "Which pillar should we lead with for MTN?",
        "Are there any anomalies for Bidvest?",
    ]

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    cols = st.columns(len(example_questions))
    for col, q in zip(cols, example_questions):
        if col.button(q, width="stretch"):
            st.session_state.chat_history.append(("user", q))
            st.session_state.chat_history.append(("assistant", qa.answer(q)))

    st.write("")
    for role, msg in st.session_state.chat_history:
        with st.chat_message(role):
            st.markdown(msg.replace("\n", "  \n"))

    user_input = st.chat_input("Ask about any client, opportunity, or anomaly...")
    if user_input:
        st.session_state.chat_history.append(("user", user_input))
        answer = qa.answer(user_input)
        st.session_state.chat_history.append(("assistant", answer))
        st.rerun()
