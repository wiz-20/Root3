"""
Shared helpers for the internal-dataset profiling scripts (Step: pre-modeling
data profiling, per docs/superpowers/specs/2026-08-09-internal-data-profiling-design.md).

Each of profile_transactional_banking.py, profile_cross_border_payments.py, and
profile_trade_finance.py imports this module so entity cross-checking and the
markdown table format stay identical across all three reports.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FINANCIALS_EXTRACTED = ROOT / "hackathon-finreports" / "_extracted" / "financials_extracted_v2.csv"

DATE_WINDOW_START = "2023-07-01"
DATE_WINDOW_END = "2026-06-30"


def load_confirmed_entities() -> set[str]:
    """The 20 entity_name values from the external financials extraction — the
    ground truth this profiling cross-checks internal entity names against."""
    with open(FINANCIALS_EXTRACTED, encoding="utf-8") as f:
        return {row["entity_name"] for row in csv.DictReader(f)}


def normalize_name(name: str) -> str:
    """Loose form for near-match detection only (casefold, strip, collapse
    whitespace) — never used for the actual join, which must be exact-match."""
    return " ".join(name.casefold().split())


def entity_coverage_report(internal_names: set[str]) -> dict:
    confirmed = load_confirmed_entities()

    missing_from_internal = confirmed - internal_names
    extra_in_internal = internal_names - confirmed

    normalized_confirmed = {normalize_name(n): n for n in confirmed}
    near_matches = []
    for extra in sorted(extra_in_internal):
        norm = normalize_name(extra)
        if norm in normalized_confirmed:
            near_matches.append((extra, normalized_confirmed[norm]))

    return {
        "confirmed_count": len(confirmed),
        "internal_count": len(internal_names),
        "exact_match_count": len(confirmed & internal_names),
        "missing_from_internal": sorted(missing_from_internal),
        "extra_in_internal": sorted(extra_in_internal),
        "near_matches": near_matches,
    }


def md_table(headers: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def entity_coverage_section(internal_names: set[str], id_name_pairs_are_1to1: bool | None = None) -> str:
    report = entity_coverage_report(internal_names)
    lines = ["### Entity coverage", ""]
    lines.append(
        f"Confirmed entities (from `financials_extracted_v2.csv`): {report['confirmed_count']} | "
        f"Distinct entities in this dataset: {report['internal_count']} | "
        f"Exact-string matches: {report['exact_match_count']}"
    )
    lines.append("")

    if not report["missing_from_internal"] and not report["extra_in_internal"]:
        lines.append("**MATCH** — entity_name set is identical to the confirmed 20. No join-blocking name issues.")
    else:
        if report["missing_from_internal"]:
            lines.append(f"**Missing from this dataset** ({len(report['missing_from_internal'])}): " + ", ".join(report["missing_from_internal"]))
        if report["extra_in_internal"]:
            lines.append(f"**Present here but not in the confirmed 20** ({len(report['extra_in_internal'])}): " + ", ".join(report["extra_in_internal"]))
        if report["near_matches"]:
            lines.append("")
            lines.append("**Near-match candidates** (would silently break an exact-string join):")
            for extra, confirmed in report["near_matches"]:
                lines.append(f"- `{extra}` vs confirmed `{confirmed}`")

    if id_name_pairs_are_1to1 is not None:
        lines.append("")
        if id_name_pairs_are_1to1:
            lines.append("`entity_id` <-> `entity_name` is a clean 1:1 mapping (no entity_id maps to >1 name or vice versa).")
        else:
            lines.append("**`entity_id` <-> `entity_name` is NOT a clean 1:1 mapping** — see outliers section, this would break a join on either key.")

    return "\n".join(lines)
