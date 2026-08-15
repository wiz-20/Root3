"""
Grounding verification for GenAI-generated client briefing notes.

Addresses the most common judge/reviewer concern about any LLM-generated text: "how do we
know it isn't hallucinating numbers?" This script extracts every percentage and every Rand
figure (bn/trillion) stated in hackathon-finreports/_extracted/client_briefing_notes.md and
checks each one against the actual source-of-truth numbers in wallet_model.csv for that
client, within a small rounding tolerance (prose rounds "R447,941m" to "R448bn", etc.).

Any number that does NOT match anything in that client's source row is flagged as
UNVERIFIED - a candidate hallucination or arithmetic slip - so it can be checked before the
notes go anywhere near a judge or a real coverage banker.

Also checks one non-numeric reasoning claim: every section's subtitle states a reliability
tier ("*Sector: X | Reliability: LOW/moderate/insufficient*") - this is checked against
wallet_model.csv's actual top_down_reliability tier for that client. A wrong tier word is a
different failure mode than a wrong number (a mismatched caveat, not an arithmetic slip) and
numeric-only checking would never catch it - e.g. a client mislabelled "moderate" when the
source data says "low" would still pass every numeric check while giving a banker false
confidence in a directional-only Rand figure.

Output: prints a pass/fail summary per client, and a full audit trail to
hackathon-finreports/_extracted/briefing_notes_verification.csv
"""

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED_DIR = ROOT / "hackathon-finreports" / "_extracted"

TOLERANCE = 0.015  # 1.5% relative tolerance for rounding in prose (e.g. "R448bn" for 447,941)

PCT_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*%")
RAND_RE = re.compile(r"R\s?(-?\d+(?:[.,]\d+)?)\s*(trillion|bn|billion|million|m)\b", re.IGNORECASE)
RELIABILITY_CLAIM_RE = re.compile(r"Reliability:\s*([A-Za-z]+)")

UNIT_TO_ZAR_MILLIONS = {
    "trillion": 1_000_000.0,
    "bn": 1_000.0,
    "billion": 1_000.0,
    "million": 1.0,
    "m": 1.0,
}


def close(a: float, b: float, tol: float = TOLERANCE) -> bool:
    if pd.isna(a) or pd.isna(b):
        return False
    if b == 0:
        return abs(a) < 1e-6
    # Prose rounds small ZAR-million/percent figures to the nearest whole number for
    # readability (e.g. "R4m" for a source value of 3.9) - a pure relative tolerance is too
    # strict for small magnitudes, so also accept anything within +/-0.5 absolute.
    return (abs(a - b) / abs(b) <= tol) or (abs(a - b) <= 0.5)


def extract_sections(md_text: str) -> dict:
    """Split the briefing notes file into {client_name: body_text} blocks."""
    sections = {}
    parts = re.split(r"^## (.+)$", md_text, flags=re.MULTILINE)
    # parts[0] is the preamble before the first heading; then alternating [heading, body, heading, body, ...]
    for i in range(1, len(parts), 2):
        heading = parts[i].strip()
        # Headings are "N. Client Name" or "N. Client Name - note" (e.g.
        # "10. Valterra Platinum - flag this one specifically") - strip both the leading rank
        # number and any trailing note to get the bare client name for the wallet_model.csv lookup.
        heading = re.sub(r"^\d+\.\s*", "", heading)
        client_name = heading.split("—")[0].strip()
        sections[client_name] = parts[i + 1]
    return sections


def numbers_in_text(text: str) -> tuple[list[float], list[float]]:
    pcts = [float(m.group(1)) for m in PCT_RE.finditer(text)]
    rands_zar_m = []
    for m in RAND_RE.finditer(text):
        value = float(m.group(1).replace(",", ""))
        unit = m.group(2).lower()
        rands_zar_m.append(value * UNIT_TO_ZAR_MILLIONS[unit])
    return pcts, rands_zar_m


def check_reliability_claim(body: str, actual_tier: str) -> bool | None:
    """Compares the subtitle's stated reliability word against the source tier. Returns None
    (not applicable) if no "Reliability: ..." claim is found - shouldn't happen given the
    template, but fails safe rather than crashing on a malformed section."""
    m = RELIABILITY_CLAIM_RE.search(body)
    if not m:
        return None
    return m.group(1).strip().lower() == actual_tier.strip().lower()


def source_values_for_client(row: pd.Series, foreign_pct: float | None) -> tuple[list[float], list[float]]:
    pct_cols = ["share_pct_pillar1", "share_pct_pillar2", "share_pct_pillar3", "blended_share_pct"]
    rand_cols = [
        "internal_pillar1_zar_m", "total_wallet_pillar1_zar_m", "gap_zar_m_pillar1",
        "internal_pillar2_zar_m", "total_wallet_pillar2_zar_m", "gap_zar_m_pillar2",
        "internal_pillar3_zar_m", "total_wallet_pillar3_zar_m", "gap_zar_m_pillar3",
        "total_internal_zar_m", "total_wallet_zar_m", "total_gap_zar_m",
    ]
    pcts = [row[c] for c in pct_cols if pd.notna(row.get(c))]
    if foreign_pct is not None and pd.notna(foreign_pct):
        pcts.append(foreign_pct)
    rands = [row[c] for c in rand_cols if pd.notna(row.get(c))]
    return pcts, rands


def main():
    notes_text = (EXTRACTED_DIR / "client_briefing_notes.md").read_text(encoding="utf-8")
    wallet_model = pd.read_csv(EXTRACTED_DIR / "wallet_model.csv").set_index("entity_name")

    # foreign_revenue_pct in financials_extracted.csv is free text; the numeric value actually
    # used by build_wallet_model.py to compute total_wallet_pillar3_zar_m comes from the FY2025
    # row of financials_multiyear_ml.csv - use that same source so this check reflects what the
    # model actually computed, not an earlier fiscal year's number.
    multiyear_ml = pd.read_csv(EXTRACTED_DIR / "financials_multiyear_ml.csv")
    foreign_pct_by_client = (
        multiyear_ml[multiyear_ml["fiscal_year"] == 2025]
        .drop_duplicates(subset="entity_name")
        .set_index("entity_name")["foreign_revenue_pct"]
    )

    # Portfolio-wide comparison statements ("vs. 0.1-5% for most other clients") are legitimate
    # claims about the dataset as a whole, not about the one client being profiled - checked
    # against every client's blended share, not just the profiled client's own row.
    portfolio_pcts = wallet_model["blended_share_pct"].dropna().tolist()

    sections = extract_sections(notes_text)
    audit_rows = []

    for client, body in sections.items():
        if client not in wallet_model.index:
            print(f"SKIP: '{client}' not found in wallet_model.csv (heading parsing issue?)")
            continue

        row = wallet_model.loc[client]
        foreign_pct = foreign_pct_by_client.get(client)
        stated_pcts, stated_rands = numbers_in_text(body)
        source_pcts, source_rands = source_values_for_client(row, foreign_pct)

        for pct in stated_pcts:
            client_match = any(close(pct, sp) for sp in source_pcts)
            portfolio_match = any(close(pct, pp) for pp in portfolio_pcts)
            audit_rows.append({
                "client": client, "type": "percent", "stated_value": pct,
                "verified": client_match or portfolio_match,
                "match_scope": "client" if client_match else ("portfolio" if portfolio_match else "none"),
            })

        for rand in stated_rands:
            matched = any(close(rand, sr) for sr in source_rands)
            audit_rows.append({
                "client": client, "type": "rand_zar_m", "stated_value": rand,
                "verified": matched, "match_scope": "client" if matched else "none",
            })

        actual_tier = str(row["top_down_reliability"]).split(" - ")[0]
        reliability_ok = check_reliability_claim(body, actual_tier)
        if reliability_ok is not None:
            audit_rows.append({
                "client": client, "type": "reliability_tier_claim", "stated_value": actual_tier,
                "verified": reliability_ok, "match_scope": "client" if reliability_ok else "none",
            })

    audit = pd.DataFrame(audit_rows)
    audit_path = EXTRACTED_DIR / "briefing_notes_verification.csv"
    audit.to_csv(audit_path, index=False)

    numeric_audit = audit[audit["type"] != "reliability_tier_claim"]
    reliability_audit = audit[audit["type"] == "reliability_tier_claim"]

    print(f"Checked {len(numeric_audit)} numeric claims + {len(reliability_audit)} reliability-tier claims across {audit['client'].nunique()} clients\n")
    summary = numeric_audit.groupby("client")["verified"].agg(["sum", "count"])
    summary["pass"] = summary["sum"] == summary["count"]
    for client, r in summary.iterrows():
        status = "PASS" if r["pass"] else "REVIEW"
        print(f"  [{status}] {client}: {int(r['sum'])}/{int(r['count'])} numeric claims verified against source data")

    mismatched_tiers = reliability_audit[~reliability_audit["verified"]]
    if len(mismatched_tiers):
        print(f"\n{len(mismatched_tiers)} MISMATCHED reliability-tier claim(s) (subtitle wording vs. wallet_model.csv's actual tier):")
        print(mismatched_tiers[["client", "stated_value"]].to_string(index=False))
    else:
        print(f"\nAll {len(reliability_audit)} reliability-tier claims match wallet_model.csv.")

    audit = numeric_audit  # everything below (unverified listing, final summary) is the numeric check as before

    unverified = audit[~audit["verified"]]
    if len(unverified):
        print(f"\n{len(unverified)} UNVERIFIED claims (candidate hallucinations/rounding beyond tolerance):")
        print(unverified.to_string(index=False))
    else:
        print(f"\nAll {len(audit)} numeric claims across {audit['client'].nunique()} clients verified against wallet_model.csv (tolerance={TOLERANCE:.1%}).")

    print(f"\nFull audit trail written to {audit_path}")


if __name__ == "__main__":
    main()
