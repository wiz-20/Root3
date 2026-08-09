"""
Cross-dataset consistency check across all 3 internal Syn Bank datasets — do
they agree with each other on entity_id, entity_name, and sector per client?
Each individual profiling script already checks its own dataset against
financials_extracted_v2.csv; this checks the three internal datasets against
EACH OTHER, which none of them can do alone.

Run: py scripts/check_cross_dataset_consistency.py
Writes: docs/reports/sections/cross_dataset_consistency.md (also prints to stdout)
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCAL_JDK = ROOT / ".tools" / "jdk-17.0.20+8"
if "JAVA_HOME" not in os.environ and LOCAL_JDK.exists():
    os.environ["JAVA_HOME"] = str(LOCAL_JDK)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from profiling_common import md_table

import pandas as pd
from pyspark.sql import SparkSession

OUT_PATH = ROOT / "docs" / "reports" / "sections" / "cross_dataset_consistency.md"


def main() -> None:
    spark = SparkSession.builder.appName("check_cross_dataset_consistency").config("spark.driver.memory", "4g").getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")

    txn = spark.read.csv(str(ROOT / "transactional_banking.csv"), header=True, inferSchema=True)
    txn_pairs = {(r["entity_id"], r["entity_name"], r["sector"]) for r in txn.select("entity_id", "entity_name", "sector").distinct().collect()}
    spark.stop()

    xborder = pd.read_csv(ROOT / "cross_border_payments.csv", usecols=["entity_id", "entity_name", "sector"])
    xborder_pairs = set(xborder.drop_duplicates().itertuples(index=False, name=None))

    trade = pd.read_csv(ROOT / "trade_finance.csv", usecols=["entity_id", "entity_name", "sector"])
    trade_pairs = set(trade.drop_duplicates().itertuples(index=False, name=None))

    datasets = {
        "transactional_banking": txn_pairs,
        "cross_border_payments": xborder_pairs,
        "trade_finance": trade_pairs,
    }

    lines = ["# Cross-dataset entity/sector consistency", "", "One row per (entity_id, entity_name, sector) triple found in each dataset. All three should agree exactly per entity_id.", ""]

    all_ids = set()
    per_dataset_by_id = {}
    for name, pairs in datasets.items():
        by_id = {}
        for eid, ename, sector in pairs:
            by_id.setdefault(eid, set()).add((ename, sector))
        per_dataset_by_id[name] = by_id
        all_ids |= set(by_id.keys())

    mismatches = []
    for eid in sorted(all_ids):
        seen = {name: per_dataset_by_id[name].get(eid) for name in datasets}
        present_in = [n for n, v in seen.items() if v is not None]
        if len(present_in) < 3:
            missing_from = [n for n in datasets if n not in present_in]
            mismatches.append((eid, f"missing from: {', '.join(missing_from)}"))
            continue
        values = list(seen.values())
        if not all(v == values[0] for v in values):
            mismatches.append((eid, f"entity_name/sector differ across datasets: {seen}"))

    lines.append(f"Distinct `entity_id` values across all 3 datasets combined: {len(all_ids)}")
    lines.append("")
    if not mismatches:
        lines.append("**MATCH** — every `entity_id` maps to the identical `(entity_name, sector)` pair in all 3 internal datasets. Safe to join on `entity_id` alone across all 3.")
    else:
        lines.append(f"**{len(mismatches)} entity_id(s) with cross-dataset inconsistency:**")
        lines.append(md_table(["entity_id", "Issue"], mismatches))

    report = "\n".join(lines)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(report, encoding="utf-8")
    print(report)
    print(f"\n\nWrote {OUT_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
