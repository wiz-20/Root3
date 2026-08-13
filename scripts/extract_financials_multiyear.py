"""
Financial report extraction pipeline - multi-year extension.

Faten curated three single-file-per-company folders (hackathon-finreports-2024,
-2025, -2026) so the ML model has more than 20 samples (one row per company) to
train on - up to 3 fiscal years per company instead of 1. This script reuses the
Step 2 page-narrowing logic from extract_financials.py (no file-selection step
needed here since each folder already has exactly one PDF per company) and
produces one excerpt file per (company, year) pair for agent-assisted Step 3
extraction.

Outputs:
  hackathon-finreports/_extracted/multi_year/<canonical>_<year>_excerpt.txt
  hackathon-finreports/_extracted/multi_year_audit.csv
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_financials import narrow_pages, select_file  # noqa: E402

import pymupdf as fitz  # noqa: E402

# Below this many narrowed pages, assume the keyword/marker narrowing missed real
# content because the source is a results presentation / press release (short deck,
# financial tables as headline numbers rather than notes-style disclosure) rather than
# a full AFS - dump the whole doc instead of risking silently losing the only summary
# financial page it has. These are short enough (<100pp) that a full dump is cheap.
FULL_DUMP_THRESHOLD = 15

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "hackathon-finreports" / "_extracted" / "multi_year"
YEAR_DIRS = {
    2024: ROOT / "hackathon-finreports-2024",
    2025: ROOT / "hackathon-finreports-2025",
    2026: ROOT / "hackathon-finreports-2026",
}

# Canonicalize each year-folder's naming to the same entity keys used in
# merge_extraction.py's ENTITY_NAMES, since folder names vary release to release
# (e.g. "anglo" in 2024, "angloamerican" in 2025; "bidcorp" in 2024, "bid" in 2025).
FOLDER_TO_CANONICAL = {
    "anglo": "angloamerican",
    "angloamerican": "angloamerican",
    "ashanti": "angloashanti",
    "angloashanti": "angloashanti",
    "aspen": "aspen",
    "bhp": "bhp",
    "bidcorp": "bid",
    "bid": "bid",
    "bidvest": "bidvest group",
    "bidvest group": "bidvest group",
    "clicks": "clicks",
    "glencore": "glencore",
    "gold fields": "gold fields",
    "mtn": "mtn",
    "naspers": "naspe",
    "naspe": "naspe",
    "nepi": "nepi",
    "outsurance": "out",
    "out": "out",
    "pepkor": "pepkor",
    "prosus": "prosus",
    "sanlam": "sanlam",
    "shaftesbury": "shaftesbury",
    "shoprite": "shoprite",
    "valterra": "valterra",
    "vodacom": "vodacom",
}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    audit_rows = []

    for year, year_dir in YEAR_DIRS.items():
        if not year_dir.exists():
            continue
        folders = sorted(p for p in year_dir.iterdir() if p.is_dir())
        for folder in folders:
            canonical = FOLDER_TO_CANONICAL.get(folder.name.lower())
            if canonical is None:
                print(f"[WARN] unmapped folder name: {year}/{folder.name} - skipping")
                continue

            chosen, method, detected_year, flag = select_file(folder)
            tag = f"  FLAG: {flag}" if flag else ""
            print(f"[{year}/{canonical}] -> {chosen.name} ({method}){tag}")

            pages = narrow_pages(chosen)
            full_dump = len(pages) < FULL_DUMP_THRESHOLD
            excerpt_path = OUT_DIR / f"{canonical.replace(' ', '_')}_{year}_excerpt.txt"
            with open(excerpt_path, "w", encoding="utf-8") as f:
                f.write(f"Source: {chosen.name}\n")
                f.write(f"Target fiscal year: {year}\n")
                if full_dump:
                    doc = fitz.open(chosen)
                    f.write(f"Narrowing found only {len(pages)} pages - dumping FULL document ({len(doc)} pages) instead, likely a results presentation/press release rather than a full AFS.\n")
                    f.write("=" * 80 + "\n\n")
                    for i in range(len(doc)):
                        f.write(f"--- PAGE {i + 1} (full dump) ---\n")
                        f.write(doc[i].get_text().strip() + "\n\n")
                    doc.close()
                else:
                    f.write(f"Total relevant pages extracted: {len(pages)}\n")
                    f.write("=" * 80 + "\n\n")
                    for page_num, text, groups in pages:
                        matched = ", ".join(groups) if groups else "context"
                        f.write(f"--- PAGE {page_num} (matched: {matched}) ---\n")
                        f.write(text.strip() + "\n\n")
            print(f"    excerpt: {excerpt_path.name} ({len(pages)} narrowed pages{', FULL DUMP used' if full_dump else ''})")

            audit_rows.append(
                {
                    "canonical": canonical,
                    "target_year": year,
                    "source_folder": f"hackathon-finreports-{year}/{folder.name}",
                    "chosen_file": chosen.name,
                    "flag": flag,
                    "excerpt_file": excerpt_path.name,
                    "excerpt_pages": len(pages),
                }
            )

    audit_path = ROOT / "hackathon-finreports" / "_extracted" / "multi_year_audit.csv"
    with open(audit_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(audit_rows[0].keys()))
        writer.writeheader()
        writer.writerows(audit_rows)

    print(f"\n{len(audit_rows)} company-year excerpts written. Audit: {audit_path}")


if __name__ == "__main__":
    main()
