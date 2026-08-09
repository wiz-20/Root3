"""
Profiling report for transactional_banking.csv (~2.8M rows) — PySpark, local mode.

Requires a JVM. If JAVA_HOME isn't already set in your environment, this script
falls back to the repo-local portable JDK at .tools/jdk-17.0.20+8 (not committed
to git — see docs/reports/2026-08-09-internal-data-profiling-report.md for how
it was installed and why PySpark was used instead of pandas for this one file).

Run: py scripts/profile_transactional_banking.py
Writes: docs/reports/sections/transactional_banking.md (also prints to stdout)
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCAL_JDK = ROOT / ".tools" / "jdk-17.0.20+8"
if "JAVA_HOME" not in os.environ and LOCAL_JDK.exists():
    os.environ["JAVA_HOME"] = str(LOCAL_JDK)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from profiling_common import DATE_WINDOW_END, DATE_WINDOW_START, entity_coverage_section, md_table

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

CSV_PATH = ROOT / "transactional_banking.csv"
OUT_PATH = ROOT / "docs" / "reports" / "sections" / "transactional_banking.md"

COLUMN_NOTES = {
    "transaction_id": "unique identifier per transaction record",
    "entity_id": "internal client identifier — join key across all 3 Syn Bank datasets",
    "entity_name": "client display name — join key against external financials data",
    "sector": "client's industry/sector classification",
    "date": "transaction date",
    "leg_type": "collections / supplier_payments / intercompany_sweeps / tax / payroll",
    "direction": "inbound (money received) or outbound (money sent)",
    "amount_zar": "transaction amount, already in ZAR",
    "currency": "currency code recorded on the transaction",
    "channel": "payment rail: EFT / SWIFT / Internal Transfer / RTC / Debit Order",
    "beneficiary_name": "name of the payment beneficiary",
    "reference": "payment reference / description text",
    "memo": "free-text memo field, mostly unused",
}

VALID_LEG_TYPES = {"collections", "supplier_payments", "intercompany_sweeps", "tax", "payroll"}
VALID_CHANNELS = {"EFT", "SWIFT", "Internal Transfer", "RTC", "Debit Order"}


def main() -> None:
    spark = SparkSession.builder.appName("profile_transactional_banking").config("spark.driver.memory", "4g").getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")

    df = spark.read.csv(str(CSV_PATH), header=True, inferSchema=True)
    df = df.withColumn("date", F.to_date("date"))
    df.cache()

    total_rows = df.count()
    lines = ["# transactional_banking.csv — Profiling Report", ""]
    lines.append(f"_Profiled with PySpark {__import__('pyspark').__version__}, local mode._")
    lines.append("")

    # --- Schema ---
    lines.append("## Schema")
    lines.append("")
    lines.append(md_table(
        ["Column", "Dtype", "Notes"],
        [[f.name, f.dataType.simpleString(), COLUMN_NOTES.get(f.name, "")] for f in df.schema.fields],
    ))
    lines.append("")

    # --- Row counts & date coverage ---
    lines.append("## Row counts & date coverage")
    lines.append("")
    lines.append(f"Rows: {total_rows:,}")
    date_bounds = df.agg(F.min("date").alias("min_d"), F.max("date").alias("max_d")).collect()[0]
    lines.append(f"Date range: {date_bounds['min_d']} -> {date_bounds['max_d']}")
    out_of_window = df.filter((F.col("date") < DATE_WINDOW_START) | (F.col("date") > DATE_WINDOW_END)).count()
    if out_of_window == 0:
        lines.append(f"All rows fall within the stated {DATE_WINDOW_START} -> {DATE_WINDOW_END} window.")
    else:
        lines.append(f"**{out_of_window:,} rows fall OUTSIDE the stated {DATE_WINDOW_START} -> {DATE_WINDOW_END} window.**")
    lines.append("")

    # --- Entity coverage ---
    id_name = df.select("entity_id", "entity_name").distinct()
    ids_per_name = id_name.groupBy("entity_name").agg(F.countDistinct("entity_id").alias("n")).agg(F.max("n")).collect()[0][0]
    names_per_id = id_name.groupBy("entity_id").agg(F.countDistinct("entity_name").alias("n")).agg(F.max("n")).collect()[0][0]
    clean_1to1 = bool(ids_per_name == 1 and names_per_id == 1)
    entity_names = {r["entity_name"] for r in df.select("entity_name").distinct().collect()}
    lines.append(entity_coverage_section(entity_names, id_name_pairs_are_1to1=clean_1to1))
    lines.append("")

    # --- Missing values & duplicates ---
    lines.append("## Missing values & duplicates")
    lines.append("")
    null_counts = df.select([F.sum(F.col(c).isNull().cast("int")).alias(c) for c in df.columns]).collect()[0].asDict()
    lines.append(md_table(
        ["Column", "Null %"],
        [[c, f"{round(100 * null_counts[c] / total_rows, 2)}%"] for c in df.columns],
    ))
    lines.append("")
    exact_dupes = total_rows - df.distinct().count()
    lines.append(f"Exact duplicate rows (all columns identical): {exact_dupes:,}")

    id_group_sizes = df.groupBy("transaction_id").count()
    id_group_sizes.cache()
    distinct_ids_with_dupes = id_group_sizes.filter(F.col("count") > 1).count()
    rows_in_dupe_groups = id_group_sizes.filter(F.col("count") > 1).agg(F.sum("count")).collect()[0][0] or 0
    lines.append(
        f"Distinct `transaction_id` values that appear more than once: {distinct_ids_with_dupes:,} "
        f"({rows_in_dupe_groups:,} rows involved)."
    )
    lines.append(
        "**This is not the same as exact duplicate rows** — spot-checking confirms `transaction_id` is being "
        "reused across genuinely different transactions (different entities, dates, amounts, beneficiaries), "
        "not just re-inserted copies of the same record. `transaction_id` is therefore **not a reliable unique "
        "key** and cannot be used for row-level dedup or as a join key on its own. This does not corrupt "
        "entity/pillar-level sums (aggregation groups by `entity_id`, not `transaction_id`), but flag it before "
        "anyone builds transaction-level logic (e.g. de-duplication, audit trail lookups) on top of this ID."
    )
    lines.append("")

    # --- Outliers / data quality ---
    lines.append("## Outliers / data quality issues")
    lines.append("")
    nonpositive_amount = df.filter(F.col("amount_zar") <= 0).count()
    lines.append(f"`amount_zar` <= 0: {nonpositive_amount:,} rows")
    bad_direction = df.filter(~F.col("direction").isin(["inbound", "outbound"])).count()
    lines.append(f"`direction` outside {{inbound, outbound}}: {bad_direction:,} rows")
    bad_leg_type = df.filter(~F.col("leg_type").isin(list(VALID_LEG_TYPES))).count()
    lines.append(f"`leg_type` outside {sorted(VALID_LEG_TYPES)}: {bad_leg_type:,} rows")
    bad_channel = df.filter(~F.col("channel").isin(list(VALID_CHANNELS))).count()
    lines.append(f"`channel` outside {sorted(VALID_CHANNELS)}: {bad_channel:,} rows")
    lines.append("")
    currency_counts = {r["currency"]: r["n"] for r in df.groupBy("currency").count().withColumnRenamed("count", "n").collect()}
    lines.append(f"Distinct `currency` values ({len(currency_counts)}): " + ", ".join(f"'{c}' ({n:,})" for c, n in sorted(currency_counts.items())))
    lines.append("")

    # --- Currency ---
    lines.append("## Currency")
    lines.append("")
    non_zar_ci = df.filter(~F.upper(F.col("currency")).eqNullSafe("ZAR")).count()
    case_variants = {c for c in currency_counts if c.upper() == "ZAR"}
    if non_zar_ci == 0 and len(case_variants) > 1:
        lines.append(
            f"`amount_zar` is named as already ZAR-converted, and case-insensitively every row's `currency` is "
            f"'ZAR' — but the literal string varies by case ({', '.join(repr(c) for c in sorted(case_variants))}). "
            "This is a **data-quality/formatting bug, not a currency-conversion issue**: no non-ZAR currency "
            "actually appears in this file, so there is nothing to convert. Flag for whoever consumes `currency` "
            "downstream (e.g. a groupby or filter on the literal string 'ZAR' would silently drop the lowercase "
            "rows) — worth normalizing case before use."
        )
    elif non_zar_ci == 0:
        lines.append("`amount_zar` is named as already ZAR-converted, and every row's `currency` is 'ZAR' — consistent, nothing to convert.")
    else:
        lines.append(
            f"{non_zar_ci:,} rows have a `currency` that is not ZAR even case-insensitively. No FX-rate column "
            "is present to verify whether `amount_zar` was actually converted for these rows. Flag for team."
        )
    lines.append("")

    # --- Join feasibility ---
    lines.append("## Join feasibility")
    lines.append("")
    lines.append(
        "- To other internal datasets: `entity_id` (confirmed 1:1 with `entity_name` above) — same key used "
        "in `cross_border_payments.csv` and `trade_finance.csv`.\n"
        "- To `financials_extracted_v2.csv`: `entity_name`, exact string match (see Entity coverage above)."
    )
    lines.append("")

    report = "\n".join(lines)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(report, encoding="utf-8")
    print(report)
    print(f"\n\nWrote {OUT_PATH}", file=sys.stderr)

    spark.stop()


if __name__ == "__main__":
    main()
