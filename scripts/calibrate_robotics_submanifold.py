"""Create a descriptive calibration report from the public paper corpus.

The report estimates axis coverage and venue-kind summaries from the curated
metadata vectors.  It is an infrastructure calibration artifact, not PCA,
maximum-likelihood factor analysis, a learned acceptance model, or a real
acceptance-probability estimate.  The corpus is intentionally balanced, so
means should be read as coverage diagnostics rather than prevalence claims.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common.robotics_submanifold import AXIS_ORDER, load_json, model_digest, validate_model  # noqa: E402


INDEX_PATH = ROOT / "corpus" / "public-paper-index.json"
MODEL_PATH = ROOT / "corpus" / "robotics-submanifold.v1.json"
CATALOG_V2 = ROOT / "corpus" / "venue-catalog.v2.json"
CATALOG_V1 = ROOT / "corpus" / "venue-catalog.v1.json"
OUTPUT_PATH = ROOT / "corpus" / "robotics-submanifold-calibration.v1.json"


def load_index() -> dict[str, Any]:
    value = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("public paper index must be an object")
    records = value.get("records")
    if not isinstance(records, list) or len(records) != 100:
        raise ValueError("calibration requires the validated 100-record corpus")
    return value


def axis_counts(records: list[dict[str, Any]], kind: str | None = None) -> dict[str, int]:
    selected = [record for record in records if kind is None or record.get("venue_kind") == kind]
    return {
        axis: sum(record.get("primary_axis") == axis for record in selected)
        for axis in AXIS_ORDER
    }


def mean_vectors(records: list[dict[str, Any]], kind: str | None = None) -> dict[str, float]:
    selected = [record for record in records if kind is None or record.get("venue_kind") == kind]
    if not selected:
        return {axis: 0.0 for axis in AXIS_ORDER}
    return {
        axis: round(mean(int(record["submanifold_axes"][axis]) for record in selected), 4)
        for axis in AXIS_ORDER
    }


def active_coverage(records: list[dict[str, Any]], kind: str | None = None) -> dict[str, int]:
    selected = [record for record in records if kind is None or record.get("venue_kind") == kind]
    return {
        axis: sum(int(record["submanifold_axes"][axis]) >= 2 for record in selected)
        for axis in AXIS_ORDER
    }


def calibrate() -> dict[str, Any]:
    index = load_index()
    records = [record for record in index["records"] if isinstance(record, dict)]
    model = load_json(MODEL_PATH)
    model_errors = validate_model(model)
    if model_errors:
        raise ValueError("invalid submanifold model: " + "; ".join(model_errors))
    catalog_path = CATALOG_V2 if CATALOG_V2.exists() else CATALOG_V1
    catalog = load_json(catalog_path)

    primary = axis_counts(records)
    journal_primary = axis_counts(records, "journal")
    conference_primary = axis_counts(records, "conference")
    award_statuses = Counter(
        record.get("award", {}).get("status")
        for record in records
        if record.get("award", {}).get("qualifies_for_quota") is True
    )
    venue_counts = Counter(str(record.get("venue")) for record in records)
    imbalance = max(primary.values()) - min(primary.values())
    kind_imbalances = {
        kind: max(counts.values()) - min(counts.values())
        for kind, counts in (("journal", journal_primary), ("conference", conference_primary))
    }

    return {
        "schema_version": "robotics-submanifold-calibration.v1",
        "generated_from": {
            "corpus": str(INDEX_PATH.relative_to(ROOT)).replace("\\", "/"),
            "corpus_schema": index.get("schema_version"),
            "model": str(MODEL_PATH.relative_to(ROOT)).replace("\\", "/"),
            "catalog": str(catalog_path.relative_to(ROOT)).replace("\\", "/"),
            "model_digest": model_digest(model),
        },
        "interpretation": {
            "status": "DESCRIPTIVE_BALANCED_CALIBRATION",
            "method": "semantic axis coding plus stratified corpus summaries",
            "not_claimed": [
                "statistical PCA",
                "statistical latent-factor fit",
                "venue acceptance probability",
                "causal effect of a venue label or award",
            ],
            "balance_note": "Because the corpus is sampled evenly across axes, vector means diagnose coding coverage and evidence patterns; they are not field prevalence estimates.",
        },
        "corpus_summary": {
            "records": len(records),
            "journal_count": sum(record.get("venue_kind") == "journal" for record in records),
            "conference_count": sum(record.get("venue_kind") == "conference" for record in records),
            "award_recognition_count": sum(record.get("award", {}).get("qualifies_for_quota") is True for record in records),
            "strict_winner_count": award_statuses.get("winner", 0),
            "award_status_counts": dict(sorted(award_statuses.items())),
        },
        "primary_axis_counts": primary,
        "primary_axis_uniformity": {
            "max_minus_min": imbalance,
            "required_max_minus_min": 1,
            "status": "PASS" if imbalance <= 1 else "FAIL",
        },
        "primary_axis_counts_by_kind": {"journal": journal_primary, "conference": conference_primary},
        "primary_axis_uniformity_by_kind": {
            "journal": {"max_minus_min": kind_imbalances["journal"], "status": "PASS" if kind_imbalances["journal"] <= 1 else "FAIL"},
            "conference": {"max_minus_min": kind_imbalances["conference"], "status": "PASS" if kind_imbalances["conference"] <= 1 else "FAIL"},
        },
        "mean_axis_loading": mean_vectors(records),
        "mean_axis_loading_by_kind": {"journal": mean_vectors(records, "journal"), "conference": mean_vectors(records, "conference")},
        "active_axis_coverage": active_coverage(records),
        "active_axis_coverage_by_kind": {"journal": active_coverage(records, "journal"), "conference": active_coverage(records, "conference")},
        "venue_record_counts": dict(sorted(venue_counts.items())),
        "axis_order": list(AXIS_ORDER),
        "next_use": [
            "Use axis means to inspect whether an evidence rule is underrepresented in the corpus.",
            "Use project vectors and venue vectors for routing; preserve claim and design locks.",
            "Recalibrate only after adding a new, auditable corpus version; do not convert the report into an acceptance model.",
        ],
    }


def main() -> int:
    report = calibrate()
    OUTPUT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "CALIBRATION: PASS "
        f"records={report['corpus_summary']['records']} "
        f"awards={report['corpus_summary']['award_recognition_count']} "
        f"axis_imbalance={report['primary_axis_uniformity']['max_minus_min']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
