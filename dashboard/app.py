"""
Syn Bank Share of Wallet Intelligence Engine - interactive front-end (Team ROOT3).

Single dashboard page. "Ask a Question" opens as a pop-up dialog wrapping
scripts/nl_query_assistant.py (rule-based, zero-cost, no API key - see that
module's docstring for why this design was chosen for the demo).

Run: streamlit run dashboard/app.py
"""

import re
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED_DIR = ROOT / "hackathon-finreports" / "_extracted"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "machine_learning"))

from nl_query_assistant import QueryAssistant  # noqa: E402
from predict_wallet import MLWalletPredictor  # noqa: E402
import nl_query_llm  # noqa: E402

TIER1_DECLINE_PREFIX = "I couldn't confidently match this question"

# Brand palette - dark theme. Main content is deliberately darker than the sidebar.
SIDEBAR_BG = "#0B2545"
PAGE_BG = "#060A12"
CARD_TOP = "#15263D"
CARD_BOTTOM = "#0B1626"
CARD_BORDER = "rgba(79,163,199,0.28)"
CARD_BORDER_HOVER = "rgba(79,163,199,0.55)"
TEXT = "#F2F5FA"
MUTED = "#93A4BD"
TEAL = "#33B8DE"
GOLD = "#D8B44A"
SLATE = "#5B6B82"
GRID = "rgba(255,255,255,0.08)"
TIER_COLORS = {"moderate": TEAL, "low": GOLD, "insufficient": SLATE}
KPI_ACCENTS = [TEAL, GOLD, TEAL, SLATE, GOLD]
PLOTLY_TEMPLATE = "plotly_dark"

st.set_page_config(page_title="Syn Bank Share of Wallet Engine", layout="wide")

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;700&display=swap');

    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
    .stApp {{ background: {PAGE_BG}; }}
    .block-container {{ padding-top: 2rem; max-width: 1300px; }}

    @keyframes fadeInUp {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    /* ---- Sidebar ---- */
    section[data-testid="stSidebar"] {{ background: {SIDEBAR_BG}; padding-top: 0; }}
    section[data-testid="stSidebar"] * {{ color: #E8EEF5; }}
    .sidebar-logo {{
        display: flex; align-items: center; gap: 10px; padding: 22px 18px 18px 18px;
        border-bottom: 1px solid rgba(255,255,255,0.12); margin-bottom: 16px;
    }}
    .sidebar-logo .mark {{
        width: 36px; height: 36px; border-radius: 9px; background: linear-gradient(135deg, {TEAL}, {GOLD});
        display: flex; align-items: center; justify-content: center; font-weight: 800; color: {SIDEBAR_BG};
        font-size: 0.95rem; flex-shrink: 0;
    }}
    .sidebar-logo .title {{ font-weight: 700; font-size: 0.95rem; line-height: 1.2; color: #fff; }}
    .sidebar-logo .subtitle {{ font-size: 0.72rem; color: rgba(255,255,255,0.55); }}
    .sidebar-footer {{
        position: fixed; bottom: 0; padding: 16px 18px; width: inherit;
        border-top: 1px solid rgba(255,255,255,0.12); font-size: 0.72rem; color: rgba(255,255,255,0.5);
    }}
    .sidebar-footer b {{ color: rgba(255,255,255,0.8); display: block; margin-bottom: 3px; font-size: 0.78rem; }}

    /* Sidebar "Ask a Question" button */
    section[data-testid="stSidebar"] div[data-testid="stButton"] {{ padding: 0 18px; }}
    section[data-testid="stSidebar"] div[data-testid="stButton"] > button {{
        width: 100%; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.16);
        border-radius: 10px; padding: 10px 14px; font-weight: 600; font-size: 0.88rem; color: #fff;
        text-align: left; transition: all 0.15s ease;
    }}
    section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover {{
        border-color: {TEAL}; background: rgba(51,184,222,0.12); color: {TEAL};
    }}

    /* ---- Hero header banner ---- */
    .hero-banner {{
        background: linear-gradient(160deg, #10233B 0%, #081420 100%);
        border: 1px solid rgba(51,184,222,0.30);
        box-shadow: 0 0 0 1px rgba(51,184,222,0.06), 0 10px 30px rgba(0,0,0,0.35);
        border-radius: 16px; padding: 20px 26px 22px 26px; margin-bottom: 22px;
        animation: fadeInUp 0.5s ease both;
    }}
    .hero-tag {{
        font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; font-weight: 700;
        letter-spacing: 0.08em; text-transform: uppercase; color: {TEAL}; margin-bottom: 10px;
    }}
    .hero-title {{ font-size: 1.65rem; font-weight: 800; color: {TEXT}; margin-bottom: 6px; line-height: 1.25; }}
    .hero-subtitle {{ font-size: 0.86rem; color: {MUTED}; }}

    /* ---- Section headers (eyebrow + title) ---- */
    .section-eyebrow {{
        font-size: 0.72rem; font-weight: 700; color: {TEAL}; text-transform: uppercase;
        letter-spacing: 0.06em; margin: 0 0 4px 0;
    }}
    .section-title {{ font-size: 1.05rem; font-weight: 700; color: {TEXT}; margin: 0 0 12px 0; }}

    /* ---- KPI tiles ---- */
    .kpi-tile {{
        border-radius: 12px; padding: 16px 16px 14px 16px; height: 100%;
        background: linear-gradient(160deg, {CARD_TOP} 0%, {CARD_BOTTOM} 100%);
        border: 1px solid {CARD_BORDER}; border-top: 3px solid var(--accent);
        box-shadow: 0 4px 14px rgba(0,0,0,0.25);
        transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
        animation: fadeInUp 0.5s ease both;
    }}
    .kpi-tile:hover {{
        transform: translateY(-3px); box-shadow: 0 10px 26px rgba(0,0,0,0.4); border-color: {CARD_BORDER_HOVER};
    }}
    .kpi-tile .kpi-value {{ font-size: 1.55rem; font-weight: 800; line-height: 1.15; color: {TEXT}; }}
    .kpi-tile .kpi-label {{ font-size: 0.72rem; color: {MUTED}; margin-top: 4px; font-weight: 500; }}

    /* ---- Bordered containers (cards) ---- */
    div[data-testid="stVerticalBlock"][data-test-scroll-behavior] {{
        background: linear-gradient(160deg, {CARD_TOP} 0%, {CARD_BOTTOM} 100%) !important;
        border-radius: 14px !important; border: 1px solid {CARD_BORDER} !important;
        box-shadow: 0 4px 18px rgba(0,0,0,0.3); padding: 16px 18px 14px 18px !important;
        transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
        animation: fadeInUp 0.55s ease both;
    }}
    div[data-testid="stVerticalBlock"][data-test-scroll-behavior]:hover {{
        transform: translateY(-2px); box-shadow: 0 12px 30px rgba(0,0,0,0.42); border-color: {CARD_BORDER_HOVER};
    }}

    /* ---- Metrics inside cards ---- */
    div[data-testid="stMetric"] {{ background: transparent; }}
    div[data-testid="stMetricLabel"] {{ color: {MUTED} !important; font-size: 0.75rem !important; font-weight: 600 !important; }}
    div[data-testid="stMetricValue"] {{ color: {TEXT} !important; font-weight: 800 !important; }}

    /* ---- General text on dark cards / page ---- */
    div[data-testid="stMarkdownContainer"] p {{ color: {MUTED}; }}
    .hero-banner p, .hero-banner div {{ color: inherit; }}
    label, .stSlider label p, .stSelectbox label p, .stToggle label p {{ color: {TEXT} !important; }}
    div[data-testid="stSelectbox"] div {{ color: {TEXT}; }}

    /* ---- Buttons (example question chips) ---- */
    .stButton > button {{
        background: rgba(255,255,255,0.03); border: 1px solid {CARD_BORDER}; color: {TEXT};
        border-radius: 18px; font-size: 0.82rem; transition: all 0.15s ease;
    }}
    .stButton > button:hover {{ border-color: {TEAL}; color: {TEAL}; background: rgba(51,184,222,0.08); }}

    /* ---- Reliability badge ---- */
    .tier-badge {{
        display: inline-block; padding: 3px 12px; border-radius: 20px; font-size: 0.8rem;
        font-weight: 700; letter-spacing: 0.02em; color: {PAGE_BG};
    }}

    /* ---- Chat bubbles ---- */
    div[data-testid="stChatMessage"] {{
        background: linear-gradient(160deg, {CARD_TOP} 0%, {CARD_BOTTOM} 100%);
        border: 1px solid {CARD_BORDER}; border-radius: 12px;
    }}
    div[data-testid="stChatMessage"] p {{ color: {TEXT}; }}

    /* ---- Alerts (info/warning boxes) ---- */
    div[data-testid="stAlertContainer"] {{
        background: linear-gradient(160deg, {CARD_TOP} 0%, {CARD_BOTTOM} 100%) !important;
        border: 1px solid {CARD_BORDER} !important; border-radius: 10px;
    }}
    div[data-testid="stAlertContainer"] p {{ color: {TEXT} !important; }}

    /* ---- Dialog (Ask a Question pop-up) ---- */
    div[data-testid="stDialog"] div[role="dialog"] {{
        background: {PAGE_BG}; border: 1px solid {CARD_BORDER}; border-radius: 16px;
    }}

    hr {{ border-color: {CARD_BORDER} !important; }}
    #MainMenu, footer {{ visibility: hidden; }}
    </style>
    """,
    unsafe_allow_html=True,
)


def plotly_dark_layout(fig, height=None, **kwargs):
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=MUTED, family="Inter, sans-serif"),
        margin=dict(l=0, r=0, t=10, b=0),
        **({"height": height} if height else {}),
        **kwargs,
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID)
    return fig


def kpi_tile(col, value, label, accent):
    col.markdown(
        f"""<div class="kpi-tile" style="--accent:{accent};">
              <div class="kpi-value">{value}</div>
              <div class="kpi-label">{label}</div>
            </div>""",
        unsafe_allow_html=True,
    )


def section(title, caption=None):
    if caption:
        st.markdown(f'<p class="section-eyebrow">{caption}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="section-title">{title}</p>', unsafe_allow_html=True)


@st.cache_data
def load_data():
    wallet_model = pd.read_csv(EXTRACTED_DIR / "wallet_model.csv")
    ranking = pd.read_csv(EXTRACTED_DIR / "opportunity_ranking.csv")
    anomalies_path = EXTRACTED_DIR / "anomalies_detected.csv"
    anomalies = pd.read_csv(anomalies_path) if anomalies_path.exists() else pd.DataFrame()
    wallet_model["reliability_tier"] = wallet_model["top_down_reliability"].str.split(" - ").str[0]
    ranking["reliability_tier"] = ranking["top_down_reliability"].str.split(" - ").str[0]
    return wallet_model, ranking, anomalies


@st.cache_data
def load_briefing_notes() -> dict:
    """{entity_name: markdown body} parsed from client_briefing_notes.md - same heading
    parsing as scripts/verify_briefing_notes.py so the keys line up with wallet_model.csv."""
    path = EXTRACTED_DIR / "client_briefing_notes.md"
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"^## (.+)$", text, flags=re.MULTILINE)
    notes = {}
    for i in range(1, len(parts), 2):
        heading = re.sub(r"^\d+\.\s*", "", parts[i].strip())
        client_name = re.split(r"[-—]", heading)[0].strip()
        notes[client_name] = parts[i + 1].strip()
    return notes


@st.cache_resource
def load_assistant():
    return QueryAssistant()


@st.cache_resource
def load_ml_predictor():
    return MLWalletPredictor()


wallet_model, ranking, anomalies = load_data()
briefing_notes = load_briefing_notes()
qa = load_assistant()
ml_predictor = load_ml_predictor()

EXAMPLE_QUESTIONS = [
    "What is Pepkor's share of the transactional wallet?",
    "What are the top 3 actionable opportunities?",
    "Why is Glencore's gap so large?",
    "Which pillar should we lead with for MTN?",
    "Are there any anomalies for Bidvest?",
]

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


@st.dialog("Ask a Question", width="large")
def ask_a_question_dialog():
    st.markdown('<p class="section-eyebrow">Tier 1 &middot; Live, zero-cost, deterministic</p>', unsafe_allow_html=True)
    if nl_query_llm.is_available():
        tier2_note = (
            "Genuinely open-ended questions automatically escalate to <b>Tier 2</b> - a live Claude Opus 5 "
            "call grounded in the same CSVs (see <code>docs/genai/nl_query_prompt.md</code>)."
        )
    else:
        tier2_note = (
            "Genuinely open-ended questions are explicitly declined (no <code>ANTHROPIC_API_KEY</code> "
            "configured for live Tier 2 - see <code>hackathon-finreports/_extracted/nl_query_examples.md</code> "
            "for static worked examples instead)."
        )
    st.markdown(
        f'<p style="font-size:0.82rem;color:{MUTED};margin-top:-6px;">Handles lookups, comparisons, rankings, '
        f"reliability checks, and anomaly questions - no API key, safe to demo live. {tier2_note}</p>",
        unsafe_allow_html=True,
    )
    st.write("")

    cols = st.columns(len(EXAMPLE_QUESTIONS))
    for col, q in zip(cols, EXAMPLE_QUESTIONS):
        if col.button(q, width="stretch", key=f"chip_{q}"):
            st.session_state.chat_history.append(("user", q))
            st.session_state.chat_history.append(("assistant", qa.answer(q)))

    user_input = st.chat_input("Ask about any client, opportunity, or anomaly...")
    if user_input:
        st.session_state.chat_history.append(("user", user_input))
        tier1_answer = qa.answer(user_input)
        if tier1_answer.startswith(TIER1_DECLINE_PREFIX) and nl_query_llm.is_available():
            with st.spinner("Escalating to Tier 2 (live Claude call)..."):
                try:
                    llm_answer = nl_query_llm.answer_open_ended(user_input)
                    answer = f"**Tier 2 &middot; live Claude Opus 5 call:**\n\n{llm_answer}"
                except Exception as e:
                    answer = (
                        f"{tier1_answer}\n\n(Tier 2 escalation attempted but failed - "
                        f"{type(e).__name__}: {e}. Showing the Tier 1 fallback above instead.)"
                    )
        else:
            answer = tier1_answer
        st.session_state.chat_history.append(("assistant", answer))

    st.write("")
    for role, msg in st.session_state.chat_history:
        with st.chat_message(role):
            st.markdown(msg.replace("\n", "  \n"))


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
    if st.button("Ask a Question", width="stretch"):
        ask_a_question_dialog()
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
# Dashboard
# ----------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero-banner">
      <div class="hero-tag">// Team ROOT3 &mdash; Standard Bank Data School Hackathon 2026</div>
      <div class="hero-title">Syn Bank Share of Wallet Intelligence Engine</div>
      <div class="hero-subtitle">Luke Naidoo &middot; Wisdom Ejiro Peru &middot; Fatan Saud &nbsp;|&nbsp;
      Numerator (internal share) &times; Denominator (top-down wallet) &times; GenAI synthesis,
      across 20 JSE-listed clients</div>
    </div>
    """,
    unsafe_allow_html=True,
)

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
for col, (value, label), accent in zip(kpi_cols, kpis, KPI_ACCENTS):
    kpi_tile(col, value, label, accent)

st.markdown(
    f'<p style="font-size:0.82rem;color:{MUTED};margin:14px 0 4px 0;">Reliability tiers matter: '
    f'<b style="color:{TEXT};">moderate</b> = ZAR reporter, literal Rand figures. '
    f'<b style="color:{TEXT};">low</b> = foreign-currency reporter, read the % as directional only - Rand gaps are '
    "consolidated GLOBAL figures, not SA-specific (e.g. Glencore's R9.5tn figure). "
    f'<b style="color:{TEXT};">insufficient</b> = Group financials not disclosed at all.</p>',
    unsafe_allow_html=True,
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
        plotly_dark_layout(fig, height=max(320, 32 * len(chart_df)), legend=dict(orientation="h", y=-0.15))
        fig.update_traces(marker_line_width=0)
        st.plotly_chart(fig, width="stretch")

with col_right:
    with st.container(border=True):
        section("Reliability tier mix", "Portfolio composition")
        tier_df = tier_counts.rename_axis("tier").reset_index(name="count")
        fig2 = px.pie(
            tier_df, names="tier", values="count", color="tier", color_discrete_map=TIER_COLORS, hole=0.6,
        )
        plotly_dark_layout(fig2, height=260, showlegend=True, legend=dict(orientation="h", y=-0.1))
        fig2.update_traces(marker=dict(line=dict(color=CARD_BOTTOM, width=3)), textfont=dict(color=TEXT))
        st.plotly_chart(fig2, width="stretch")

    if not anomalies.empty:
        with st.container(border=True):
            section("Anomalies by type", "Rule-based detection")
            rule_counts = anomalies["rule"].value_counts().rename_axis("rule").reset_index(name="count")
            fig3 = px.bar(rule_counts, x="count", y="rule", orientation="h", color_discrete_sequence=[TEAL])
            plotly_dark_layout(fig3, height=240, yaxis_title="", xaxis_title="Instances")
            fig3.update_traces(marker_line_width=0)
            st.plotly_chart(fig3, width="stretch")

st.write("")
with st.container(border=True):
    section("Client drill-down", "Per-client view")
    client = st.selectbox("Select a client", sorted(wallet_model["entity_name"].tolist()))
    row = wallet_model[wallet_model["entity_name"] == client].iloc[0]

    c1, c2 = st.columns([2, 3])
    with c1:
        st.markdown(
            f'<span style="color:{TEXT};font-weight:600;">{client}</span>'
            f'<span style="color:{MUTED};"> &mdash; {row["sector"]}, {row["currency"]} reporter, FY{int(row["fiscal_year"])}</span>',
            unsafe_allow_html=True,
        )
        tier = row["reliability_tier"]
        badge_color = TIER_COLORS.get(tier, SLATE)
        st.markdown(
            f"<span class='tier-badge' style='background-color:{badge_color};'>"
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
            st.warning(f"{len(client_anomalies)} anomaly(ies) flagged for this client - open Ask a Question for details")

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
            fig4.add_bar(y=pdf["pillar"], x=pdf["gap"], name="Gap to 100%", orientation="h", marker_color="rgba(255,255,255,0.08)")
            plotly_dark_layout(
                fig4, height=220, barmode="stack",
                xaxis_title="% of pillar wallet", legend=dict(orientation="h", y=-0.3),
            )
            fig4.update_traces(marker_line_width=0)
            st.plotly_chart(fig4, width="stretch")
        else:
            st.info("No pillar-level external wallet estimate available for this client.")

st.write("")
with st.container(border=True):
    section("AI briefing note", "GenAI-generated, grounding-verified")
    note = briefing_notes.get(client)
    if note:
        st.markdown(
            f'<p style="font-size:0.72rem;color:{MUTED};margin:-8px 0 10px 0;">Generated via '
            f'<code>docs/genai/briefing_note_prompt.md</code> - every numeric claim machine-checked '
            f"against <code>wallet_model.csv</code> by <code>scripts/verify_briefing_notes.py</code> "
            f'(see <code>hackathon-finreports/_extracted/briefing_notes_verification.csv</code>).</p>',
            unsafe_allow_html=True,
        )
        st.markdown(note)
    else:
        st.info("No briefing note found for this client in client_briefing_notes.md.")

st.write("")
with st.container(border=True):
    section("ML cross-check (ElasticNet)", "Share, total wallet & gap from internal activity alone")
    st.markdown(
        f'<p style="font-size:0.8rem;color:{MUTED};margin-top:-6px;">Predicts share from Syn Bank\'s own '
        "internal activity only - no client external total required - then derives total wallet and gap "
        "the same way the top-down model does (total wallet = internal / share). Useful precisely where "
        f'the top-down benchmark above is missing or low-reliability. <span style="color:{TEXT};">Not computable</span> '
        "means the model predicted a non-positive share for that row (no positivity constraint on ElasticNet) "
        "rather than showing an inverted or fabricated number.</p>",
        unsafe_allow_html=True,
    )
    ml_rows = []
    for pillar, targets in ml_predictor.predict_for_client(client).items():
        for t in targets:
            wallet_ok = pd.notna(t["predicted_total_wallet_zar_m"])
            ml_rows.append({
                "Pillar": pillar,
                "Target": t["target"],
                "Predicted share": f"{t['predicted_share_pct']:.1f}%",
                "Predicted total wallet": f"R{t['predicted_total_wallet_zar_m']:,.0f}m" if wallet_ok else "not computable",
                "Predicted gap": f"R{t['predicted_gap_zar_m']:,.0f}m" if wallet_ok else "not computable",
            })
    if ml_rows:
        st.dataframe(pd.DataFrame(ml_rows), width="stretch", hide_index=True)
    else:
        st.info("No internal-activity data available for this client in the ML training set.")
