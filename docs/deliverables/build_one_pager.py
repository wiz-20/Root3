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

NAVY = colors.HexColor("#0B2545")
TEAL = colors.HexColor("#2E86AB")
GOLD = colors.HexColor("#C9A227")
LIGHT_GREY = colors.HexColor("#F2F4F7")
DARK_TEXT = colors.HexColor("#1A1A1A")
MUTED = colors.HexColor("#555555")

styles = {
    "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=17, textColor=colors.white, leading=20),
    "subtitle": ParagraphStyle("subtitle", fontName="Helvetica", fontSize=9.5, textColor=colors.white, leading=12),
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=10.5, textColor=NAVY, spaceBefore=0, spaceAfter=3, leading=13),
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=8.3, textColor=DARK_TEXT, leading=10.8, spaceAfter=2),
    "bullet": ParagraphStyle("bullet", fontName="Helvetica", fontSize=8.3, textColor=DARK_TEXT, leading=10.6, leftIndent=8, bulletIndent=0, spaceAfter=2.2),
    "stat_num": ParagraphStyle("stat_num", fontName="Helvetica-Bold", fontSize=15, textColor=TEAL, leading=17, alignment=1),
    "stat_label": ParagraphStyle("stat_label", fontName="Helvetica", fontSize=6.6, textColor=MUTED, leading=8, alignment=1),
    "footer": ParagraphStyle("footer", fontName="Helvetica", fontSize=7, textColor=MUTED, leading=9),
    "footer_b": ParagraphStyle("footer_b", fontName="Helvetica-Bold", fontSize=7, textColor=NAVY, leading=9),
}


def header_band():
    title = Paragraph("Syn Bank Share of Wallet Intelligence Engine", styles["title"])
    subtitle = Paragraph(
        "Standard Bank Data School Hackathon 2026 &nbsp;&bull;&nbsp; Team ROOT3 &nbsp;&bull;&nbsp; "
        "Luke Naidoo &middot; Wisdom Ejiro Peru &middot; Fatan Saud",
        styles["subtitle"],
    )
    band = Table([[title], [subtitle]], colWidths=[180 * mm])
    band.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 1),
        ("TOPPADDING", (0, 1), (-1, 1), 1),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
    ]))
    return band


def stat_strip():
    stats = [
        ("20", "JSE-listed clients\nanalyzed (43 company-years)"),
        ("5.8%", "avg. blended Share of\nWallet, actionable-tier clients"),
        ("R2.4tn", "combined addressable gap,\n10 highest-confidence clients"),
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
    rule = HRFlowable(width="100%", thickness=1, color=GOLD, spaceBefore=1, spaceAfter=4)
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
        "Syn Bank is never a client's <b>sole</b> banking partner. We built an engine that estimates each client's "
        "<b>Total Wallet</b> across three product pillars, quantifies Syn Bank's <b>current Share</b> from internal "
        "data, and ranks the <b>Rand Gap</b> to prioritize which clients a coverage banker should chase next \u2014 "
        "for the 20 JSE-listed corporates in Syn Bank's synthetic transactional, trade finance, and cross-border datasets.",
        styles["body"],
    )
    story += section("The Problem", [problem])
    story.append(Spacer(1, 5))

    left_col = section("Our Approach", [
        Paragraph(
            "<b>Numerator (Share):</b> internal transactional, trade finance and cross-border data, split into "
            "3 pillars \u2014 Transactional Banking, Trade &amp; Working Capital, Foreign/Cross-Border.",
            styles["body"],
        ),
        Paragraph(
            "<b>Denominator (Wallet):</b> top-down proxy built from each client's own disclosed annual-report "
            "financials (revenue, cost of sales, receivables/payables, foreign-revenue %), extracted from 43 "
            "company-year filings (FY2024\u20132026) and normalized to ZAR at live SARB rates.",
            styles["body"],
        ),
        Paragraph(
            "<b>Learned angle:</b> ElasticNet regression (5 targets, Leave-One-Group-Out CV) predicts Share % "
            "directly from internal activity volume \u2014 useful precisely where the top-down external "
            "benchmark is thin or missing.",
            styles["body"],
        ),
    ])

    right_col = section("GenAI Layer (3/3 use cases)", [
        Paragraph(
            "<b>Client briefing notes</b> \u2014 all 20/20 clients, machine-verified against source data "
            "(142/143 numeric claims auto-confirmed; caught one real stale-data error before it shipped).",
            styles["body"],
        ),
        Paragraph(
            "<b>Anomaly explanations</b> \u2014 code detects (60 client\u00d7pillar cells, fixed rules), GenAI "
            "explains only what code already found (27 anomalies, 6 patterns) \u2014 hallucination-resistant by design.",
            styles["body"],
        ),
        Paragraph(
            "<b>NL query assistant</b> \u2014 live, zero-cost, deterministic layer for common lookups; LLM "
            "reserved only for genuinely open-ended synthesis questions.",
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
        "<b>Top opportunity:</b> Shoprite Holdings \u2014 2.4% transactional share, R437bn gap on a R448bn wallet (literal, ZAR-reporter).",
        "<b>Sharpest anomaly:</b> Valterra Platinum \u2014 near-zero share (0.0\u20130.2%) despite being a <i>domestic</i> reporter, not a scale artifact \u2014 flagged for immediate relationship review.",
        "<b>Model self-awareness as a finding:</b> reliability tiering catches the naive-model trap before it reaches a banker \u2014 a raw calculation would report Glencore's global consolidated revenue as a fictional R9.5 trillion \"gap\"; explicitly flagged low-reliability/directional-only instead.",
    ])
    story += section("Key Findings", findings)
    story.append(Spacer(1, 5))

    limitations = bullets([
        "<b>Stated scope cut:</b> top-down financials-based Total Wallet only \u2014 bottom-up competitor evidence (SARB BA900, JSE SENS) was descoped for the solo/time-constrained build; documented as the top next step, not hidden.",
        "Foreign/Cross-Border wallet is estimated for only 4/20 clients (numeric foreign-revenue disclosure required) \u2014 flagged \"external estimate unavailable\" for the rest, never silently zeroed.",
    ])
    story += section("Limitations, Stated Plainly", limitations)
    story.append(Spacer(1, 5))

    next_steps = bullets([
        "Layer in bottom-up competitor evidence (SENS facility announcements, BA900) to tighten/validate the top-down proxy.",
        "Extend Pillar 3 (cross-border) external benchmark coverage beyond the current 4/20 clients.",
        "Automate the GenAI briefing-note pipeline via API to scale from 20 to the full 43-row multi-year panel.",
    ])
    story += section("Next Steps", next_steps)
    story.append(Spacer(1, 6))

    tier_row = Table([[
        Paragraph("<b>Reliability tiers, stated on every figure:</b>", styles["body"]),
        Paragraph("<b>10</b> moderate (ZAR reporter, literal Rand gap)", styles["body"]),
        Paragraph("<b>9</b> low (foreign currency, directional % only)", styles["body"]),
        Paragraph("<b>1</b> insufficient (Group AFS not disclosed)", styles["body"]),
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
        Paragraph("<b>Code &amp; full notebook:</b> github.com/wiz-20/Root3 (private \u2014 access on request)", styles["footer"]),
        Paragraph("Team ROOT3 &nbsp;|&nbsp; Submission: 16 Aug 2026", styles["footer_b"]),
    ]], colWidths=[130 * mm, 46 * mm])
    footer.setStyle(TableStyle([("ALIGN", (1, 0), (1, 0), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.append(footer)

    doc.build(story)
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    build()
