from __future__ import annotations
from pathlib import Path
from collections import Counter, defaultdict
import json
import pandas as pd
from ..parser import load_bib_entries
from ..pipeline import VerificationPipeline
from ..llm.judge import MockJudge
from ..normalize import normalize_title
from .provider import build_benchmark_provider

STATUS_OK = {
    "tier1_basic_sanity": {"exact_verified", "high_confidence_corrected"},
    "tier2_common_errors": {"exact_verified", "high_confidence_corrected", "llm_adjudicated", "review_needed", "unresolved"},
    "tier3_hard_cases": {"review_needed", "unresolved", "exact_verified", "high_confidence_corrected", "llm_adjudicated"},
    "tier4_adversarial": {"review_needed", "unresolved"},
    "tier5_format_edge": {"review_needed", "unresolved", "exact_verified", "high_confidence_corrected", "llm_adjudicated"},
}

ENTRY_EXPECTATIONS = {
    # Tier 1: no unsafe changes on clean records
    "wiles1995modular": "safe_accept",
    "tao2006perelman": "safe_accept",
    "tao2006additive": "safe_accept",
    "andrews2025glaisher": "safe_accept",
    "tao2025sumdiff": "safe_accept",
    "apostol1974mathematical": "safe_accept",
    "guillera2018ramanujan": "safe_accept",
    "tao2007goodmath": "safe_accept",
    "lacey2006small": "safe_accept",
    "barany2023tverberg": "safe_accept",
    # Tier2 fixable
    "wiles1995modular_t2a": "safe_accept",
    "tao2006perelman_t2b": "safe_accept",
    "tao2006additive_t2c": "safe_accept",
    "andrews2025glaisher_t2d": "safe_accept",
    "tao2025sumdiff_t2e": "safe_accept",
    "wiles1995modular_t2f": "safe_accept",
    "guillera2018ramanujan_t2g": "safe_accept",
    "apostol1974mathematical_t2h": "safe_accept",
    "tao2007goodmath_t2i": "safe_accept",
    "lacey2006small_t2j": "safe_accept",
    "barany2023tverberg_t2k": "safe_accept",
    "tao2006perelman_t2l": "safe_accept",
    "wiles1995modular_t2m": "safe_accept",
    "tao2006additive_t2n": "safe_accept",
    "tao2025sumdiff_t2o": "safe_accept",
    # Tier3 should mostly review; exact safe acceptable for exact names
    "deeplearning_goodfellow_fake_collision": "review_or_safe",
    "wiles1995modular_t3a": "review_or_safe",
    "tao_perelman_notes": "review_or_safe",
    "tao_namevar_t3b": "safe_accept",
    "perelman_original_t3c": "review_or_safe",
    "taoVu2006additive_t3d": "safe_accept",
    "ramanujan_many_titles": "review_or_safe",
    "wiles_taylor_collaborative": "review_or_safe",
    "tao_analysis_paper": "safe_accept",
    "andrews_partition_many": "review_or_safe",
    # Tier4: must not auto-correct dangerous cases except duplicates may safe_accept
    "fake_plausible_t4a": "must_flag",
    "hybrid_corrupt_t4b": "must_flag",
    "near_miss_t4c": "must_flag",
    "duplicate_same_t4d": "safe_accept",
    "duplicate_same_t4e": "safe_accept",
    "fake_title_t4f": "must_flag",
    "wiles_near_miss_journal": "review_or_safe",
    "tao_fake_collaborator": "must_flag",
    "hybrid_multi_error_t4i": "review_or_safe",
    "perelman_tao_mix_t4j": "must_flag",
    # Tier5: parser robustness first
    "broken_missing_comma": "parse_only",
    "tao2006perelman_unicode": "safe_accept",
    "mathheavy": "review_or_safe",
    "mixed_content": "parse_only",
    "no_braces_title": "safe_accept",
    "extra_braces": "safe_accept",
    "unicode_german": "must_flag",
    "broken_brace": "parse_only",
    "extra_field": "review_or_safe",
    "eol_comment": "review_or_safe",
}

SAFE_STATUSES = {"exact_verified", "high_confidence_corrected", "llm_adjudicated"}
FLAG_STATUSES = {"review_needed", "unresolved"}


def classify_row(row):
    expected = ENTRY_EXPECTATIONS.get(row["entry_key"], "review_or_safe")
    status = row["status"]
    n_changes = int(row.get("n_changes", 0))
    if expected == "must_flag":
        ok = status in FLAG_STATUSES
    elif expected == "safe_accept":
        ok = status in SAFE_STATUSES or (status == "review_needed" and n_changes == 0)
    elif expected == "parse_only":
        ok = True
    else:
        ok = status in SAFE_STATUSES | FLAG_STATUSES
    return expected, ok


def detect_duplicates(entries):
    groups = defaultdict(list)
    for e in entries:
        title = normalize_title(e.fields.get("title", ""))
        eprint = (e.fields.get("eprint", "") or "").strip()
        doi = (e.fields.get("doi", "") or "").strip().lower()
        key = doi or eprint or title
        if key:
            groups[key].append(e.entry_key)
    return {k: v for k, v in groups.items() if len(v) > 1}


def run_benchmark(input_files, output_dir, judge=None):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    pipeline = VerificationPipeline(
        providers=[build_benchmark_provider()],
        judge=judge or MockJudge(),
        auto_accept_threshold=0.93,
        llm_threshold=0.82,
        ambiguity_margin=0.04,
        min_title_similarity=0.90,
        min_safe_title_similarity=0.95,
    )

    tier_rows = []
    entry_rows = []
    duplicate_rows = []
    total_parse_failures = 0

    for file_path in input_files:
        path = Path(file_path)
        tier_name = path.stem
        entries = load_bib_entries(str(path))
        duplicates = detect_duplicates(entries)
        for group, keys in duplicates.items():
            duplicate_rows.append({"tier": tier_name, "group_key": group, "entry_keys": " | ".join(keys), "count": len(keys)})
        bench_out = output_dir / tier_name
        result = pipeline.verify_file(str(path), str(bench_out))
        report = pd.read_csv(result["report_csv"])
        parsed_n = len(entries)
        # rough parse failure estimate by counting apparent entry starts
        apparent = path.read_text(encoding="utf-8", errors="ignore").count("@")
        parse_failures = max(apparent - parsed_n, 0)
        total_parse_failures += parse_failures
        status_counts = report["status"].value_counts().to_dict() if not report.empty else {}
        safe_accept = int(report["status"].isin(list(SAFE_STATUSES)).sum()) if not report.empty else 0
        flagged = int(report["status"].isin(list(FLAG_STATUSES)).sum()) if not report.empty else 0
        changed = int((report["n_changes"] > 0).sum()) if not report.empty else 0
        unchanged = int((report["n_changes"] == 0).sum()) if not report.empty else 0
        tier_rows.append({
            "tier": tier_name,
            "entries_parsed": parsed_n,
            "apparent_entries": apparent,
            "parse_failures_est": parse_failures,
            "safe_accept": safe_accept,
            "flagged": flagged,
            "changed": changed,
            "unchanged": unchanged,
            "duplicates_found": sum(len(v) for v in duplicates.values()),
            **{f"status_{k}": v for k, v in status_counts.items()},
        })
        for _, row in report.iterrows():
            expected, ok = classify_row(row)
            entry_rows.append({
                "tier": tier_name,
                "entry_key": row["entry_key"],
                "status": row["status"],
                "confidence": row["confidence"],
                "n_changes": int(row["n_changes"]),
                "selected_title": row.get("selected_title", ""),
                "expected_behavior": expected,
                "benchmark_ok": ok,
            })

    tier_df = pd.DataFrame(tier_rows).fillna(0)
    entry_df = pd.DataFrame(entry_rows)
    dup_df = pd.DataFrame(duplicate_rows)
    summary = {
        "tiers": tier_df.to_dict(orient="records"),
        "benchmark_ok_rate": float(entry_df["benchmark_ok"].mean()) if not entry_df.empty else 0.0,
        "total_entries": int(len(entry_df)),
        "total_parse_failures_est": int(total_parse_failures),
        "false_autocorrections_est": int(((entry_df["expected_behavior"] == "must_flag") & (entry_df["status"].isin(list(SAFE_STATUSES)))).sum()) if not entry_df.empty else 0,
    }

    tier_df.to_csv(output_dir / "benchmark_summary.csv", index=False)
    entry_df.to_csv(output_dir / "benchmark_detailed.csv", index=False)
    if not dup_df.empty:
        dup_df.to_csv(output_dir / "benchmark_duplicates.csv", index=False)
    with open(output_dir / "benchmark_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    return summary
