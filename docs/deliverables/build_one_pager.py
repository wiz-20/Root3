"""
Builds the 1-page PDF solution summary required by PLAN.md's deliverables checklist.

Run: python docs/deliverables/build_one_pager.py
Output: docs/deliverables/ROOT3_one_pager.pdf
"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)

OUT_DIR = Path(__file__).resolve().parent
OUT_PATH = OUT_DIR / "ROOT3_one_pager.pdf"

# ============================================================
# COLOUR PALETTE
# ============================================================

# Core Root3 palette
NAVY = colors.HexColor("#2A2223")        # dark charcoal/brown - main header
TEAL = colors.HexColor("#E30A60")        # vivid pink - primary accent
GOLD = colors.HexColor("#64CC0F")        # lime green - secondary accent

# Neutral supporting colours
LIGHT_GREY = colors.HexColor("#EFEDEE")  # very light warm grey/pink
DARK_TEXT = colors.HexColor("#211C1D")   # softer black
MUTED = colors.HexColor("#6F6467")       # readable muted grey

styles = {
    "title": ParagraphStyle(
        "title",
        fontName="Helvetica-Bold",
        fontSize=17,
        textColor=colors.white,
        leading=20
    ),

    "subtitle": ParagraphStyle(
        "subtitle",
        fontName="Helvetica",
        fontSize=9.5,
        textColor=colors.HexColor("#F4ECEF"),
        leading=12
    ),

    "h2": ParagraphStyle(
        "h2",
        fontName="Helvetica-Bold",
        fontSize=10.5,
        textColor=TEAL,
        spaceBefore=0,
        spaceAfter=3,
        leading=13
    ),

    "body": ParagraphStyle(
        "body",
        fontName="Helvetica",
        fontSize=8.3,
        textColor=DARK_TEXT,
        leading=10.8,
        spaceAfter=2
    ),

    "bullet": ParagraphStyle(
        "bullet",
        fontName="Helvetica",
        fontSize=8.3,
        textColor=DARK_TEXT,
        leading=10.6,
        leftIndent=8,
        bulletIndent=0,
        spaceAfter=2.2
    ),

    "stat_num": ParagraphStyle(
        "stat_num",
        fontName="Helvetica-Bold",
        fontSize=15,
        textColor=TEAL,
        leading=17,
        alignment=1
    ),

    "stat_label": ParagraphStyle(
        "stat_label",
        fontName="Helvetica",
        fontSize=6.6,
        textColor=MUTED,
        leading=8,
        alignment=1
    ),

    "footer": ParagraphStyle(
        "footer",
        fontName="Helvetica",
        fontSize=7,
        textColor=MUTED,
        leading=9
    ),

    "footer_b": ParagraphStyle(
        "footer_b",
        fontName="Helvetica-Bold",
        fontSize=7,
        textColor=TEAL,
        leading=9
    ),

    "foot_info": ParagraphStyle(
        "foot_info",
        fontName="Helvetica",
        fontSize=8.3,
        textColor=DARK_TEXT,
        leading=10.8,
        spaceAfter=2
    ),
}

def header_band():
    title = Paragraph(
        "Syn Bank Share of Wallet Intelligence Engine",
        styles["title"]
    )

    team = Paragraph(
        "<b>Team: Root3</b>",
        styles["subtitle"]
    )

    members = Paragraph(
        "Luke Naidoo &nbsp;&bull;&nbsp; Wisdom Ejiro Peru &nbsp;&bull;&nbsp; Faten Saud",
        styles["subtitle"]
    )

    event = Paragraph(
        "Standard Bank Data School Hackathon 2026",
        styles["subtitle"]
    )

    band = Table(
        [
            [title],
            [team],
            [members],
            [event]
        ],
        colWidths=[180 * mm]
    )

    band.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),

        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 3),

        ("TOPPADDING", (0, 1), (-1, 1), 1),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 1),

        ("TOPPADDING", (0, 2), (-1, 2), 1),
        ("BOTTOMPADDING", (0, 2), (-1, 2), 1),

        ("TOPPADDING", (0, 3), (-1, 3), 1),
        ("BOTTOMPADDING", (0, 3), (-1, 3), 7),
    ]))

    return band


def stat_strip():
    stats = [
        ("20", "JSE-listed clients\nanalyzed (43 company-years)"),
        ("3.6%", "predicted avg. blended Share of\nWallet"),
        ("R3.4tn", "predicted combined addressable gap"),
        ("0.24\u20130.39", "ElasticNet R\u00b2, 4/5 targets\n(honest LOGO cross-validation)"),
        ("3/3", "GenAI use cases built:\nbriefing notes, NL query, anomalies"),
    ]
    cells = []
    for num, label in stats:
        label_html = label.replace("\n", "<br/>")
        cells.append([Paragraph(num, styles["stat_num"]), Paragraph(label_html, styles["stat_label"])])
    col_w = 180 * mm / 5
    table = Table([[c[0] for c in cells], [c[1] for c in cells]], colWidths=[col_w] * 5)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 0),
        ("TOPPADDING", (0, 1), (-1, 1), 0),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
        ("LINEAFTER", (0, 0), (-2, -1), 0.5, colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return table


def section(title, flowables, width=None):
    head = Paragraph(title.upper(), styles["h2"])
    rule = HRFlowable(width="100%",thickness=1.3,color=GOLD,spaceBefore=1,spaceAfter=4
)
    return [head, rule] + flowables


def bullets(items):
    return [Paragraph(f"&#8226;&nbsp; {t}", styles["bullet"]) for t in items]


def build():
    doc = SimpleDocTemplate(
        str(OUT_PATH), pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm, topMargin=10 * mm, bottomMargin=10 * mm,
        title="ROOT3 - Syn Bank Share of Wallet Intelligence Engine",
    )

    story = []
    story.append(header_band())
    story.append(Spacer(1, 5))
    story.append(stat_strip())
    story.append(Spacer(1, 7))

    problem = Paragraph(
        "Syn Bank is never a client's <b>sole</b> banking partner. Our team built an engine that estimates each client's "
        "<b>Total Wallet</b> across three product pillars, quantifies Syn Bank's <b>current Share</b> from internal "
        "data, and ranks the <b>Rand Gap</b> to prioritize which clients SynBank should chase next, "
        "for the 20 JSE-listed corporates in Syn Bank's synthetic transactional, trade finance, and cross-border datasets.",
        styles["body"],
    )
    story += section("The Problem", [problem])
    story.append(Spacer(1, 5))

    left_col = section("Our Approach", [
        Paragraph(
            "<b>Numerator (Share):</b> Internal transactional, trade finance and cross-border data, split into "
            "3 pillars: Transactional Banking, Trade &amp; Working Capital, Foreign/Cross-Border.",
            styles["body"],
        ),
        Paragraph(
            "<b>Denominator (Wallet):</b> top-down proxy built from each client's own disclosed annual-report "
            "financials (revenue, cost of sales, receivables/payables, foreign-revenue %), extracted from 43 "
            "company-year filings (FY2024\u20132026) and normalized to ZAR at live SARB rates.",
            styles["body"],
        ),
        Paragraph(
            "<b>Learned angle:</b> ElasticNet regression (5 targets, Leave-One-Group-Out CV) predicts share % "
            "directly from the internal activity volume; useful precisely where the top-down external "
            "benchmark is thin or missing (when the company's public financial statements do not disclose "
            "enough reliable information to construct the external top-down wallet estimate). ",
            styles["body"],
        ),
    ])

    right_col = section("GenAI Layer (3/3 use cases)", [
        Paragraph(
            "<b>Client briefing notes</b> \u2014 Converts each client’s Share of Wallet, estimated wallet "
            "gaps, reliability indicators and model signals into a concise briefing, helping relationship managers "
            "quickly understand where the biggest opportunities lie and what to discuss with the client.",
            styles["body"],
        ),
        Paragraph(
            "<b>Anomaly explanations</b> \u2014 Automatically identifies unusual or high-opportunity "
            "wallet signals and uses GenAI to explain why they matter, while keeping the underlying "
            "detection and calculations deterministic to reduce hallucination risk.",
            styles["body"],
        ),
        Paragraph(
            "<b>NL query assistant</b> — Lets bankers interrogate the portfolio in plain English, "
            "asking questions such as “Which three clients should we prioritise?” or "
            "“Where do the ML and financial-statement estimates disagree?” The assistant grounds "
            "its answers in both the top-down financial benchmark and the latest ElasticNet predictions.",
            styles["body"],
        ),
    ])

    two_col = Table([[left_col, right_col]], colWidths=[88 * mm, 88 * mm])
    two_col.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), 6),
        ("LEFTPADDING", (1, 0), (1, 0), 6),
        ("RIGHTPADDING", (1, 0), (1, 0), 0),
    ]))
    story.append(two_col)
    story.append(Spacer(1, 6))

    findings = bullets([
        "<b>Top ML opportunities:</b> Naspers leads the current ElasticNet portfolio with a R468.3bn predicted gap at 0.4% predicted Syn Bank share, followed by Prosus (R294.7bn), The Bidvest Group (R253.4bn), Aspen Pharmacare (R253.1bn), and MTN Group (R242.4bn).",

        "<b>Portfolio-wide white space:</b> across 20 current clients, the ElasticNet models estimate an average Syn Bank share of 3.6% and a combined predicted wallet gap of R3,423.4bn, highlighting substantial cross-sell potential across the portfolio.",

        "<b>Pillar-level signal:</b> the ML opportunity heatmap shows consistently low predicted penetration across Trade &amp; Working Capital, while Transactional Banking varies more meaningfully by client, helping bankers identify both the client and product pillar to prioritise.",

        "<b>FX limitation remains visible:</b> the current FX model produces a uniform 12.7% predicted share across clients, consistent with its weak out-of-sample performance; FX should therefore be treated as directional until additional training data improves the signal.",
    ])
    story += section("Key Findings", findings)
    story.append(Spacer(1, 5))

    limitations = bullets([
    "<b>Limited ML training sample:</b> only 43 company-year observations were available across 20 corporates. The original FY2025-only scope (~20 observations) was therefore expanded to FY2024–2026 where available, more than doubling the training data.",

    "<b>FX remains the weakest target:</b> only 17 usable FX observations remained after filtering, resulting in weak out-of-sample performance (R² = −0.264). FX estimates are therefore treated as directional rather than precise.",

    "<b>Designed around the constraint:</b> ElasticNet regularisation, company-level Leave-One-Group-Out cross-validation and target-specific hyperparameter tuning were used to reduce overfitting and improve generalisation within the available sample."
    ])
    story += section("Limitations, Stated Plainly", limitations)
    story.append(Spacer(1, 5))

    next_steps = bullets([
        "Layer in bottom-up competitor evidence (SENS facility announcements, BA900) to tighten/validate the top-down proxy.",
        "Expand the multi-year training dataset, particularly Foreign/Cross-Border observations, to improve model generalisation and strengthen the currently weak FX prediction.",
        "Automate the GenAI briefing-note pipeline via API to scale from 20 to the full 43-row multi-year panel.",
    ])
    story += section("Next Steps", next_steps)
    story.append(Spacer(1, 6))

    tier_row = Table([[
        Paragraph("<b>Reliability tiers, stated on every figure:</b>", styles["foot_info"]),
        Paragraph("<b>10</b> moderate (ZAR reporter, literal Rand gap)", styles["foot_info"]),
        Paragraph("<b>9</b> low (foreign currency, directional % only)", styles["foot_info"]),
        Paragraph("<b>1</b> insufficient (Group AFS not disclosed)", styles["foot_info"]),
    ]], colWidths=[52 * mm, 46 * mm, 48 * mm, 42 * mm])
    tier_row.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (0, 0), 8),
        ("LINEAFTER", (0, 0), (-2, -1), 0.5, colors.white),
    ]))
    story.append(tier_row)
    story.append(Spacer(1, 8))

    story.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#CCCCCC")))
    story.append(Spacer(1, 3))
    footer = Table([[
        Paragraph("<b>Code &amp; full notebook:</b> github.com/wiz-20/Root3 (private \u2013 access on request)", styles["footer"]),
        Paragraph("Team ROOT3 &nbsp;|&nbsp; Submission: 16 Aug 2026", styles["footer_b"]),
    ]], colWidths=[130 * mm, 46 * mm])
    footer.setStyle(TableStyle([("ALIGN", (1, 0), (1, 0), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.append(footer)

    doc.build(story)
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    build()