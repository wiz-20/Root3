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

    /* ---- Animated background (subtle aurora glow, purely decorative) ----
       Painted as .stApp's own background layers - by spec this is always the
       bottom-most paint layer of the element, so it can never sit above real
       content the way a separate positioned/z-indexed div unpredictably can. */
    .stApp {{
        background:
            radial-gradient(650px circle at 12% -8%, rgba(51,184,222,0.16), transparent 60%),
            radial-gradient(560px circle at 96% 22%, rgba(216,180,74,0.13), transparent 60%),
            radial-gradient(600px circle at 38% 112%, rgba(51,184,222,0.11), transparent 60%),
            {PAGE_BG};
        background-repeat: no-repeat;
        animation: auroraShift 30s ease-in-out infinite;
    }}
    @keyframes auroraShift {{
        0%, 100% {{ background-position: 12% -8%, 96% 22%, 38% 112%, 0 0; }}
        50% {{ background-position: 20% 6%, 86% 12%, 44% 96%, 0 0; }}
    }}
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


def load_ml_predictor():
    # Do not cache the predictor: it loads the current Gold-layer CSVs in __init__.
    # A fresh dashboard run should always reflect the latest Step 4 outputs.
    return MLWalletPredictor()


def load_assistant(_ml_predictor):
    # Rebuild the assistant from the current ML portfolio each dashboard run.
    return QueryAssistant(ml_predictor=_ml_predictor)


def build_live_ml_portfolio(predictions: pd.DataFrame) -> pd.DataFrame:
    """Collapse target-level ML predictions into one row per current client."""
    if predictions.empty:
        return pd.DataFrame()

    df = predictions.copy()
    df["internal_zar_m"] = df["internal_zar"] / 1_000_000

    clients = pd.DataFrame(
        {"entity_name": sorted(df["entity_name"].dropna().unique())}
    )

    valid = df[
        df["predicted_total_wallet_zar_m"].notna()
        & (df["predicted_total_wallet_zar_m"] > 0)
        & df["predicted_gap_zar_m"].notna()
    ].copy()

    if valid.empty:
        return clients

    overall = (
        valid.groupby("entity_name", as_index=False)
        .agg(
            internal_zar_m=("internal_zar_m", "sum"),
            predicted_total_wallet_zar_m=(
                "predicted_total_wallet_zar_m",
                "sum",
            ),
            total_gap_zar_m=("predicted_gap_zar_m", "sum"),
        )
    )
    overall["blended_share_pct"] = (
        overall["internal_zar_m"]
        / overall["predicted_total_wallet_zar_m"]
        * 100
    )

    portfolio = clients.merge(overall, on="entity_name", how="left")

    pillar_map = {
        "Transactional Banking": 1,
        "Trade & Working Capital": 2,
        "Foreign/Cross-Border": 3,
    }

    pillar_summary = (
        valid.groupby(["entity_name", "pillar"], as_index=False)
        .agg(
            internal_zar_m=("internal_zar_m", "sum"),
            wallet_zar_m=("predicted_total_wallet_zar_m", "sum"),
            gap_zar_m=("predicted_gap_zar_m", "sum"),
        )
    )
    pillar_summary["share_pct"] = (
        pillar_summary["internal_zar_m"]
        / pillar_summary["wallet_zar_m"]
        * 100
    )

    for pillar_name, pillar_number in pillar_map.items():
        subset = (
            pillar_summary[
                pillar_summary["pillar"] == pillar_name
            ][["entity_name", "share_pct", "gap_zar_m"]]
            .rename(
                columns={
                    "share_pct": f"share_pct_pillar{pillar_number}",
                    "gap_zar_m": f"gap_zar_m_pillar{pillar_number}",
                }
            )
        )
        portfolio = portfolio.merge(
            subset,
            on="entity_name",
            how="left",
        )

    return portfolio


# Historical/external top-down benchmark data.
wallet_model, ranking, anomalies = load_data()
briefing_notes = load_briefing_notes()

# Current operational portfolio from the latest Gold-layer internal data.
ml_predictor = load_ml_predictor()
ml_predictions = ml_predictor.predict_all_clients()
live_portfolio = build_live_ml_portfolio(ml_predictions)

qa = load_assistant(ml_predictor)

_example_clients = live_portfolio["entity_name"].dropna().tolist()

if _example_clients:
    _example_a = _example_clients[0]
    _example_b = _example_clients[min(1, len(_example_clients) - 1)]
    EXAMPLE_QUESTIONS = [
        f"What is {_example_a}'s wallet?",
        "What are the top 3 opportunities?",
        f"Which pillar should we lead with for {_example_a}?",
        f"What does the ML model predict for {_example_b}?",
        f"Is there a top-down benchmark for {_example_a}?",
    ]
else:
    EXAMPLE_QUESTIONS = [
        "What are the top 3 opportunities?",
        "What can you help me with?",
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
                    print(f"[Tier 2 escalation error] {type(e).__name__}: {e}")  # console only - keep the chat reply clean
                    try:
                        import anthropic
                        reason = "the configured Claude API key isn't valid" if isinstance(e, anthropic.AuthenticationError) else "the live Claude call didn't go through"
                    except Exception:
                        reason = "the live Claude call didn't go through"
                    answer = (
                        f"{tier1_answer}\n\n"
                        f"_Tier 2 live escalation is enabled, but {reason} right now - falling back to the Tier 1 answer above._"
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
      <div class="hero-title">Syn Bank Share of Wallet Intelligence Engine</div>
      <div class="hero-subtitle">Live ElasticNet wallet inference &times; optional external benchmark &times; GenAI synthesis,
      across the current Syn Bank client portfolio</div>
    </div>
    """,
    unsafe_allow_html=True,
)

computable = live_portfolio[
    live_portfolio.get("blended_share_pct", pd.Series(dtype=float)).notna()
].copy()

benchmark_clients = set(wallet_model["entity_name"]) if not wallet_model.empty else set()
benchmark_count = int(
    live_portfolio["entity_name"].isin(benchmark_clients).sum()
) if not live_portfolio.empty else 0

avg_share = (
    computable["blended_share_pct"].mean()
    if not computable.empty
    else float("nan")
)
total_gap = (
    computable["total_gap_zar_m"].sum()
    if not computable.empty
    else 0.0
)

kpis = [
    (str(len(live_portfolio)), "Current clients analyzed"),
    (
        f"{avg_share:.1f}%" if pd.notna(avg_share) else "n/a",
        "Avg. predicted Syn Bank share",
    ),
    (f"R{total_gap / 1000:.1f}bn", "Combined predicted wallet gap"),
    (str(benchmark_count), "Top-down benchmarks available"),
    (str(len(ml_predictions)), "ML wallet components predicted"),
]
kpi_cols = st.columns(5)
for col, (value, label), accent in zip(kpi_cols, kpis, KPI_ACCENTS):
    kpi_tile(col, value, label, accent)

st.markdown(
    f'<p style="font-size:0.82rem;color:{MUTED};margin:14px 0 4px 0;">'
    f'The live dashboard is driven by the trained ElasticNet models using the latest Syn Bank internal activity. '
    f'Where a client also exists in the external-financials top-down model, that benchmark is shown separately '
    f'and is never treated as the source of the current client list.</p>',
    unsafe_allow_html=True,
)


st.write("")
with st.container(border=True):
    section("Opportunity heatmap", "White-space view - unclaimed share of wallet, by client and pillar")
    heat_pillars = [
        ("share_pct_pillar2", "gap_zar_m_pillar2", "Trade & Working Capital"),
        ("share_pct_pillar1", "gap_zar_m_pillar1", "Transactional Banking"),
        ("share_pct_pillar3", "gap_zar_m_pillar3", "Foreign/Cross-Border"),
    ]
    heat_df = live_portfolio.sort_values("total_gap_zar_m", ascending=False, na_position="last")
    heat_clients = heat_df["entity_name"].tolist()

    # Median share captured across this portfolio is under 1% - on a flat 0-100 scale nearly every
    # cell would pin near 100% unclaimed and the map would read as a single gold block. The color
    # axis is instead stretched to COLOR_FLOOR-100, the band where the real variation actually lives,
    # so differences between clients are visible; the true % is always shown as the on-cell label.
    COLOR_FLOOR = 75

    z, labels, hover = [], [], []
    for share_col, gap_col, _ in heat_pillars:
        z_row, label_row, hover_row = [], [], []
        for _, r in heat_df.iterrows():
            share, gap = r[share_col], r[gap_col]
            if pd.isna(share):
                z_row.append(None)
                label_row.append("")
                hover_row.append(f"<b>{r['entity_name']}</b><br>Not estimated for this pillar")
            elif share >= 100:
                z_row.append(COLOR_FLOOR)
                label_row.append("full")
                hover_row.append(
                    f"<b>{r['entity_name']}</b><br>Predicted share: {share:.0f}%"
                    f"<br>Treated as fully captured - no gap shown<br>Source: ElasticNet ML model"
                )
            else:
                z_row.append(max(COLOR_FLOOR, 100 - share))
                label_row.append(f"{share:.1f}%")
                gap_str = f"R{gap / 1000:,.1f}bn" if abs(gap) >= 1000 else f"R{gap:,.1f}m"
                hover_row.append(
                    f"<b>{r['entity_name']}</b><br>Share captured: {share:.1f}%"
                    f"<br>Predicted gap: {gap_str}<br>Source: ElasticNet ML model"
                )
        z.append(z_row)
        labels.append(label_row)
        hover.append(hover_row)

    heat_fig = go.Figure(
        data=go.Heatmap(
            z=z, x=heat_clients, y=[p[2] for p in heat_pillars],
            text=labels, texttemplate="%{text}", textfont=dict(color=PAGE_BG, size=10, family="Inter, sans-serif"),
            hovertext=hover, hoverinfo="text",
            colorscale=[[0, TEAL], [1, GOLD]],
            colorbar=dict(
                title="Unclaimed<br>share (%)", tickfont=dict(color=MUTED),
                tickvals=[COLOR_FLOOR, 100], ticktext=[f"≤{COLOR_FLOOR}%", "100%"],
            ),
            xgap=3, ygap=6, zmin=COLOR_FLOOR, zmax=100,
        )
    )
    plotly_dark_layout(heat_fig, height=300)
    heat_fig.update_xaxes(tickangle=-45, tickfont=dict(size=10))
    heat_fig.update_yaxes(tickfont=dict(size=12))
    st.plotly_chart(heat_fig, width="stretch")
    st.markdown(
        f'<p style="font-size:0.78rem;color:{MUTED};margin-top:-8px;">'
        f'Each cell shows the ElasticNet-predicted Syn Bank share for the current client portfolio. '
        f'Gold indicates more unclaimed share; teal indicates comparatively better penetration. '
        f'Blank cells mean that target was not computable from the model output.</p>',
        unsafe_allow_html=True,
    )

st.write("")
col_left, col_right = st.columns([3, 2])

with col_left:
    with st.container(border=True):
        section("Top opportunities", "Ranked by ElasticNet-predicted wallet gap")
        top_n = st.slider("Show top N", min_value=5, max_value=20, value=10)

        chart_df = live_portfolio.copy()
        chart_df = chart_df.dropna(subset=["total_gap_zar_m"]).sort_values(
            "total_gap_zar_m", ascending=False
        ).head(top_n)
        chart_df["gap_rbn"] = chart_df["total_gap_zar_m"] / 1000

        fig = px.bar(
            chart_df.sort_values("gap_rbn"), x="gap_rbn", y="entity_name", orientation="h",
            labels={"gap_rbn": "Predicted gap (R billions)", "entity_name": ""},
            hover_data={"blended_share_pct": ":.2f", "gap_rbn": ":.2f"},
        )
        plotly_dark_layout(fig, height=max(320, 32 * len(chart_df)), legend=dict(orientation="h", y=-0.15))
        fig.update_traces(marker_line_width=0)
        st.plotly_chart(fig, width="stretch")

with col_right:
    with st.container(border=True):
        section("External benchmark coverage", "Current portfolio")
        coverage_df = pd.DataFrame(
            {
                "status": ["Top-down benchmark available", "ML-only"],
                "count": [
                    benchmark_count,
                    max(0, len(live_portfolio) - benchmark_count),
                ],
            }
        )
        fig2 = px.pie(
            coverage_df,
            names="status",
            values="count",
            hole=0.6,
        )
        plotly_dark_layout(
            fig2,
            height=260,
            showlegend=True,
            legend=dict(orientation="h", y=-0.1),
        )
        fig2.update_traces(
            marker=dict(line=dict(color=CARD_BOTTOM, width=3)),
            textfont=dict(color=TEXT),
        )
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
    client = st.selectbox(
        "Select a client",
        sorted(live_portfolio["entity_name"].dropna().unique().tolist()),
    )
    row = live_portfolio[live_portfolio["entity_name"] == client].iloc[0]
    top_down_match = wallet_model[
        wallet_model["entity_name"] == client
    ] if not wallet_model.empty else pd.DataFrame()

    c1, c2 = st.columns([2, 3])
    with c1:
        st.markdown(
            f'<span style="color:{TEXT};font-weight:600;">{client}</span>'
            f'<span style="color:{MUTED};"> &mdash; current ElasticNet portfolio</span>',
            unsafe_allow_html=True,
        )

        st.write("")
        if pd.notna(row["blended_share_pct"]):
            m1, m2 = st.columns(2)
            m1.metric("Blended share", f"{row['blended_share_pct']:.1f}%")
            m2.metric("Blended gap", f"R{row['total_gap_zar_m'] / 1000:,.1f}bn" if abs(row['total_gap_zar_m']) >= 1000 else f"R{row['total_gap_zar_m']:.1f}m")
        else:
            st.info("Blended total not computed (insufficient data)")

        client_anomalies = anomalies[anomalies["entity_name"] == client] if (not anomalies.empty and not top_down_match.empty) else pd.DataFrame()
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
    section("Client intelligence note", "Live ML estimate + optional external benchmark")

    if not top_down_match.empty:
        benchmark_row = top_down_match.iloc[0]
        st.markdown(
            f"**External top-down benchmark available.** "
            f"Blended share: {benchmark_row['blended_share_pct']:.1f}% "
            f"| Reliability: {benchmark_row['top_down_reliability'].split(' - ')[0]}"
        )

        note = briefing_notes.get(client)
        if note:
            st.markdown(note)
        else:
            st.info(
                "A top-down benchmark exists for this client, but no static briefing "
                "note was found."
            )
    else:
        st.info(
            "No external top-down benchmark is available for this current client. "
            "The live view below is driven by the ElasticNet model."
        )

st.write("")
with st.container(border=True):
    section("Live wallet estimate (ElasticNet)", "Current share, total wallet & gap from internal activity")
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
        st.markdown(
            f'<p style="font-size:0.85rem;color:{TEXT};background:rgba(51,184,222,0.08);'
            f'border-left:3px solid {TEAL};padding:10px 14px;border-radius:6px;margin-bottom:12px;">'
            f"{ml_predictor.describe(client)}</p>",
            unsafe_allow_html=True,
        )
        st.dataframe(pd.DataFrame(ml_rows), width="stretch", hide_index=True)
    else:
        st.info("No current internal-activity data is available for this client.")

st.write("")
with st.container(border=True):
    section("Ad-hoc what-if prediction", "Feed internal activity directly without changing the current portfolio")
    st.markdown(
        f'<p style="font-size:0.8rem;color:{MUTED};margin-top:-6px;">For a quick what-if, enter Syn Bank '
        "internal activity directly below. This does not add the client to the current portfolio; "
        "to onboard a client into the reusable pipeline, add the raw CSV data plus fiscal-year metadata "
        "and rerun Steps 4, 6 and 7. No model retraining is required.</p>",
        unsafe_allow_html=True,
    )

    with st.form("new_client_predict_form"):
        new_client_name = st.text_input("Client name (for display only)", value="New client")
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            st.markdown("**Trade & Working Capital**")
            in_trade_receivables = st.number_input("Trade receivables (ZAR)", min_value=0.0, value=0.0, step=1_000_000.0, format="%.0f")
            in_trade_payables = st.number_input("Trade payables (ZAR)", min_value=0.0, value=0.0, step=1_000_000.0, format="%.0f")
        with fc2:
            st.markdown("**Transactional Banking**")
            in_collections = st.number_input("Collections (ZAR)", min_value=0.0, value=0.0, step=1_000_000.0, format="%.0f")
            in_supplier_payments = st.number_input("Supplier payments (ZAR)", min_value=0.0, value=0.0, step=1_000_000.0, format="%.0f")
        with fc3:
            st.markdown("**Foreign/Cross-Border**")
            in_cross_border = st.number_input("Cross-border inflows (ZAR)", min_value=0.0, value=0.0, step=1_000_000.0, format="%.0f")
        predict_clicked = st.form_submit_button("Predict")

    if predict_clicked:
        inputs = dict(
            trade_receivables=in_trade_receivables or None,
            trade_payables=in_trade_payables or None,
            collections=in_collections or None,
            supplier_payments=in_supplier_payments or None,
            cross_border_inflows=in_cross_border or None,
        )
        if not any(inputs.values()):
            st.warning("Enter at least one pillar's figures (both fields for Trade or Transactional, or Cross-border inflows alone) to get a prediction.")
        else:
            st.session_state.new_client_prediction = (new_client_name, ml_predictor.predict_from_inputs(**inputs))

    if "new_client_prediction" in st.session_state:
        pred_name, pred_by_pillar = st.session_state.new_client_prediction
        pred_rows = [
            {
                "Pillar": pillar,
                "Target": t["target"],
                "Predicted share": f"{t['predicted_share_pct']:.1f}%",
                "Predicted total wallet": f"R{t['predicted_total_wallet_zar_m']:,.0f}m" if pd.notna(t["predicted_total_wallet_zar_m"]) else "not computable",
                "Predicted gap": f"R{t['predicted_gap_zar_m']:,.0f}m" if pd.notna(t["predicted_gap_zar_m"]) else "not computable",
            }
            for pillar, targets in pred_by_pillar.items() for t in targets
        ]
        if pred_rows:
            st.markdown(
                f'<p style="font-size:0.85rem;color:{TEXT};background:rgba(51,184,222,0.08);'
                f'border-left:3px solid {TEAL};padding:10px 14px;border-radius:6px;margin-bottom:12px;">'
                f"{ml_predictor.describe_predictions(pred_by_pillar, pred_name)}</p>",
                unsafe_allow_html=True,
            )
            st.dataframe(pd.DataFrame(pred_rows), width="stretch", hide_index=True)