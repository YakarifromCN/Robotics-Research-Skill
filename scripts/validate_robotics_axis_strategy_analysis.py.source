"""Validate ResearchStudio pattern, signature and per-axis strategy artifacts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from common.researchstudio_patterns import DEFAULT_LIBRARY, load_pattern_library, validate_pattern_library
from scripts.validate_public_paper_index import validate as validate_public_corpus


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SIGNATURES = ROOT / "corpus" / "researchstudio-paper-signatures.v1.json"
DEFAULT_REPORT = ROOT / "corpus" / "robotics-axis-strategy-analysis.v1.json"
_DRIVE_ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def validate(
    report: dict[str, Any],
    signatures: dict[str, Any],
    library: dict[str, Any],
    public_corpus: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    errors.extend(validate_public_corpus(public_corpus))
    errors.extend(validate_pattern_library(library))
    if report.get("schema_version") != "robotics-axis-strategy-analysis.v1":
        errors.append("wrong axis strategy report schema")
    if signatures.get("schema_version") != "researchstudio-paper-signatures.v1":
        errors.append("wrong signature index schema")
    source_corpus = signatures.get("source_corpus")
    if not isinstance(source_corpus, str) or source_corpus.startswith("/") or _DRIVE_ABSOLUTE.match(source_corpus):
        errors.append("signature source_corpus must be repository-portable and non-absolute")
    source_digest = signatures.get("source_corpus_sha256")
    if not isinstance(source_digest, str) or not _SHA256.fullmatch(source_digest):
        errors.append("signature source_corpus_sha256 must be a lowercase SHA-256 digest")
    if signatures.get("record_count") != 100 or len(signatures.get("records", [])) != 100:
        errors.append("signature index must contain exactly 100 records")
    if signatures.get("data_fidelity") != "METADATA_ONLY":
        errors.append("current baseline must disclose METADATA_ONLY fidelity")
    rows = report.get("axes")
    if not isinstance(rows, list) or len(rows) != 8:
        errors.append("report must contain exactly 8 axis rows")
        rows = []
    expected_counts = {"E": 13, "P": 13, "C": 13, "L": 13, "D": 12, "H": 12, "A": 12, "S": 12}
    parent_ids = {item.get("pattern_id") for item in library.get("main_patterns", []) if isinstance(item, dict)}
    sub_ids = {item.get("subpattern_id") for item in library.get("subpatterns", []) if isinstance(item, dict)}
    seen_axes: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            errors.append("axis row must be an object")
            continue
        axis = row.get("axis_id")
        if axis in seen_axes:
            errors.append(f"duplicate axis row: {axis}")
        seen_axes.add(axis)
        if axis not in expected_counts:
            errors.append(f"unsupported axis: {axis}")
            continue
        if row.get("corpus_sample_count") != expected_counts[axis]:
            errors.append(f"{axis} sample count must be {expected_counts[axis]}")
        strategy = row.get("best_posting_strategy", {})
        best = strategy.get("anchor_pattern") if isinstance(strategy, dict) else None
        if not isinstance(best, dict) or best.get("pattern_id") not in parent_ids:
            errors.append(f"{axis} has no valid anchor pattern")
        for item in strategy.get("supporting_patterns", []) if isinstance(strategy, dict) else []:
            if item.get("pattern_id") not in parent_ids:
                errors.append(f"{axis} has unknown supporting pattern")
        for item in strategy.get("tactical_subpatterns", []) if isinstance(strategy, dict) else []:
            if item.get("subpattern_id") not in sub_ids:
                errors.append(f"{axis} has unknown tactical subpattern")
        if row.get("data_fidelity") != "METADATA_ONLY":
            errors.append(f"{axis} must disclose metadata-only fidelity in baseline")
    if seen_axes != set(expected_counts):
        errors.append("report must cover E/P/C/L/D/H/A/S exactly")
    text = json.dumps(report, ensure_ascii=False)
    if "rating" in text.casefold() or "prestige" in text.casefold():
        errors.append("rating/prestige fields are forbidden in the axis strategy artifact")
    if report.get("non_claims") and not any("acceptance probability" in item for item in report["non_claims"]):
        errors.append("report must state the acceptance-probability non-claim")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the robotics ResearchStudio axis strategy baseline.")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--signatures", default=str(DEFAULT_SIGNATURES))
    parser.add_argument("--library", default=str(DEFAULT_LIBRARY))
    parser.add_argument("--public-corpus", default=str(ROOT / "corpus" / "public-paper-index.json"))
    args = parser.parse_args()
    errors = validate(_load(args.report), _load(args.signatures), _load(args.library), _load(args.public_corpus))
    if errors:
        for error in errors:
            print("ERROR:", error)
        return 1
    print("ROBOTICS_AXIS_STRATEGY_ANALYSIS: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
