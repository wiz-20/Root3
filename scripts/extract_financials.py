"""
Financial report extraction pipeline - Step 1 & 2.

Step 1: Select the best AFS (Annual Financial Statements) PDF per company folder.
Step 2: Extract text and narrow down to pages relevant to the 12 target fields
        defined in docs/superpowers/specs/2026-08-08-pillar-spend-split-design.md.

Design doc: docs/superpowers/specs/2026-08-08-financial-report-extraction-design.md

Outputs:
  hackathon-finreports/_extracted/file_selection_audit.csv
  hackathon-finreports/_extracted/<folder>_excerpt.txt   (one per company)

Step 3 (structured field extraction from the excerpts) is done separately by an
agent reading the excerpt files - this script only prepares the inputs for that.
"""

import re
import csv
from pathlib import Path

import pymupdf as fitz

ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT / "hackathon-finreports"
OUT_DIR = REPORTS_DIR / "_extracted"

AFS_PATTERN = re.compile(r"\bafs\b|\bafr\b|annual financial statement", re.IGNORECASE)
REPORT_PATTERN = re.compile(r"annual report|integrated report|\biar\b", re.IGNORECASE)
YEAR_PATTERN = re.compile(r"(20[1-2][0-9])")
EXCLUDE_PATTERN = re.compile(r"circular|1h[a-z]*\d|interim|half.?year", re.IGNORECASE)
DUP_MARKER_PATTERN = re.compile(r"\(\d+\)")

KEYWORD_GROUPS = {
    "revenue_cos_opex": [
        "cost of sales",
        "revenue from contracts with customers",
        "disaggregation of revenue",
        "revenue by category",
    ],
    "receivables_payables": [
        "trade and other receivables",
        "trade and other payables",
        "trade receivables",
        "trade payables",
    ],
    "inventory_working_capital": [
        "inventories",
        "net working capital",
        "movement in working capital",
    ],
    "trade_imports_exports": [
        "letters of credit",
        "letter of credit",
        "documentary credit",
        "trade finance facilit",
        "guarantees and letters of credit",
        "import duties",
        "export sales",
    ],
    "geographic_foreign_revenue": [
        "geographical segment",
        "revenue by geography",
        "revenue by region",
        "revenue by geographic",
        "segmental information",
        "segment information",
    ],
    "fx_exposure": [
        "foreign currency risk",
        "currency risk management",
        "sensitivity to foreign currency",
        "foreign exchange gain",
        "foreign exchange loss",
        "net foreign exchange",
        "foreign currency translation",
    ],
}

# A page must also show at least one of these financial-statement markers to count -
# filters out narrative/marketing pages that happen to mention a keyword in passing.
FINANCIAL_MARKER_PATTERN = re.compile(
    r"r['\u2019]?000|r million|rm\b|note \d|notes to the|for the year ended|consolidated statement",
    re.IGNORECASE,
)

KNOWN_FLAGS = {
    "bidvest group": "Bidvest FY2025 AFS available is Company-level only; Group FY2025 AFS not in folder (only Group FY2024 present).",
    "sanlam": "Latest AFS-labeled file is 2023; FY2025 only available as Integrated Report / unclear 'FY24.pdf'.",
    "angloamerican": "Folder contains a file referencing 'AGA' (AngloGold Ashanti's ticker) - verify this isn't misfiled.",
}


def detect_year(filename: str) -> int | None:
    years = [int(y) for y in YEAR_PATTERN.findall(filename)]
    return max(years) if years else None


def sort_key(path: Path) -> tuple:
    """Highest year first, then prefer filenames without a '(1)'-style duplicate marker."""
    year = detect_year(path.name)
    return (-(year if year is not None else -1), bool(DUP_MARKER_PATTERN.search(path.name)))


def normalize(filename: str) -> str:
    """Turn separators into spaces so word-boundary regexes work across Foo_AFS.pdf, Foo-AFS.pdf, AFR2025.pdf, etc.

    Two passes: explicit separators (-, _) become spaces, then a letter/digit boundary
    (e.g. "AFR2025" -> "AFR 2025") is inserted - \\b alone doesn't split these since digits
    and letters are both \\w characters, so "AFR2025" has no regex word boundary at all
    between "R" and "2". Without this, AFR2025.pdf silently fails to match \\bafr\\b.
    """
    spaced = re.sub(r"[-_]+", " ", filename)
    return re.sub(r"(?<=[A-Za-z])(?=[0-9])|(?<=[0-9])(?=[A-Za-z])", " ", spaced)


def select_file(folder: Path) -> tuple[Path, str, int | None, str]:
    """Return (chosen_path, method, year_detected, flag)."""
    candidates = list(folder.glob("*.pdf"))
    flag_parts = []

    usable = [p for p in candidates if not EXCLUDE_PATTERN.search(normalize(p.name))]
    if not usable:
        usable = candidates
        flag_parts.append("all files matched exclude pattern, exclusion relaxed")

    afs_matches = sorted([p for p in usable if AFS_PATTERN.search(normalize(p.name))], key=sort_key)
    if afs_matches:
        chosen = afs_matches[0]
        method = "afs_match"
    else:
        report_matches = sorted(
            [p for p in usable if REPORT_PATTERN.search(normalize(p.name))] or usable, key=sort_key
        )
        chosen = report_matches[0]
        method = "fallback_no_afs_label"
        flag_parts.append("no AFS-labeled file found; used newest annual/integrated report")

    known_flag = KNOWN_FLAGS.get(folder.name.lower())
    if known_flag:
        flag_parts.append(known_flag)

    return chosen, method, detect_year(chosen.name), "; ".join(flag_parts)


def narrow_pages(pdf_path: Path) -> list[tuple[int, str, list[str]]]:
    """Return list of (page_number, page_text, matched_group_names) for relevant pages, 1-indexed."""
    doc = fitz.open(pdf_path)
    page_texts = [doc[i].get_text() for i in range(len(doc))]
    doc.close()

    matched_pages: dict[int, set[str]] = {}
    for i, text in enumerate(page_texts):
        lower = text.lower()
        if not FINANCIAL_MARKER_PATTERN.search(lower):
            continue
        for group, keywords in KEYWORD_GROUPS.items():
            if any(kw in lower for kw in keywords):
                matched_pages.setdefault(i, set()).add(group)

    expanded = set()
    for i in matched_pages:
        expanded.update({i - 1, i, i + 1})
    expanded = {i for i in expanded if 0 <= i < len(page_texts)}

    result = []
    for i in sorted(expanded):
        groups = sorted(matched_pages.get(i, set()))
        result.append((i + 1, page_texts[i], groups))
    return result


def write_excerpt(folder_name: str, pdf_path: Path, pages: list[tuple[int, str, list[str]]]) -> Path:
    out_path = OUT_DIR / f"{folder_name.replace(' ', '_')}_excerpt.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"Source: {pdf_path.name}\n")
        f.write(f"Total relevant pages extracted: {len(pages)}\n")
        f.write("=" * 80 + "\n\n")
        for page_num, text, groups in pages:
            matched = ", ".join(groups) if groups else "context"
            f.write(f"--- PAGE {page_num} (matched: {matched}) ---\n")
            f.write(text.strip() + "\n\n")
    return out_path


def main():
    OUT_DIR.mkdir(exist_ok=True)
    folders = sorted(p for p in REPORTS_DIR.iterdir() if p.is_dir() and p.name != "_extracted")

    audit_rows = []
    for folder in folders:
        chosen, method, year, flag = select_file(folder)
        tag = f"  FLAG: {flag}" if flag else ""
        print(f"[{folder.name}] -> {chosen.name} ({method}, year={year}){tag}")

        pages = narrow_pages(chosen)
        excerpt_path = write_excerpt(folder.name, chosen, pages)
        print(f"    excerpt: {excerpt_path.name} ({len(pages)} pages)")

        audit_rows.append(
            {
                "folder": folder.name,
                "chosen_file": chosen.name,
                "method": method,
                "year_detected": year,
                "flag": flag,
                "excerpt_file": excerpt_path.name,
                "excerpt_pages": len(pages),
            }
        )

    audit_path = OUT_DIR / "file_selection_audit.csv"
    with open(audit_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(audit_rows[0].keys()))
        writer.writeheader()
        writer.writerows(audit_rows)

    print(f"\nAudit written to {audit_path}")


if __name__ == "__main__":
    main()
