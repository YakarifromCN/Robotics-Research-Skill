"""Build the compact runtime artifact from a local-only paper corpus.

The input corpus is intentionally an offline build/audit dependency.  The
output is the only paper-derived artifact consumed by the normal Skill route.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common.robotics_research_runtime import AXES, validate_runtime  # noqa: E402
from scripts.validate_public_paper_index import load as load_corpus, validate as validate_corpus  # noqa: E402


DEFAULT_OUTPUT = ROOT / "corpus" / "robotics-research-runtime.v1.json"


def _default_input() -> Path:
    configured = os.environ.get("ROBOTICS_CORPUS_PATH")
    return Path(configured) if configured else ROOT / "corpus" / "public-paper-index.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _compact_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "paper_id": record.get("paper_id"),
        "title": record.get("title"),
        "year": record.get("year"),
        "venue": record.get("venue"),
        "venue_kind": record.get("venue_kind"),
        "primary_axis": record.get("primary_axis"),
        "submanifold_axes": record.get("submanifold_axes", {}),
        "pattern_tags": record.get("pattern_tags", []),
        "extract": record.get("extract", []),
        "do_not_infer": record.get("do_not_infer", []),
        "preprint_url": record.get("preprint", {}).get("url"),
        "final_publication_url": record.get("final_publication", {}).get("url"),
        "award_status": record.get("award", {}).get("status") if isinstance(record.get("award"), dict) else None,
    }


def _select_exemplars(records: list[dict[str, Any]], catalog: dict[str, Any], axis: str, limit: int) -> list[dict[str, Any]]:
    venue_weights = {
        str(row.get("name")): float(row.get("directness_weight", 0.65))
        for row in catalog.get("records", [])
        if isinstance(row, dict) and row.get("name")
    }
    ranked = sorted(
        records,
        key=lambda record: (
            0 if record.get("primary_axis") == axis else 1,
            -int(record.get("submanifold_axes", {}).get(axis, 0)),
            -venue_weights.get(str(record.get("venue")), 0.65),
            str(record.get("paper_id")),
        ),
    )
    return [_compact_record(record) for record in ranked[:limit]]


def build(input_path: str | Path, *, exemplar_count: int = 4) -> dict[str, Any]:
    source_path = Path(input_path)
    if not source_path.exists():
        raise FileNotFoundError(
            f"local corpus not found: {source_path}; set ROBOTICS_CORPUS_PATH or pass --input"
        )
    corpus = load_corpus(source_path)
    errors = validate_corpus(corpus)
    if errors:
        raise ValueError("local corpus failed validation: " + "; ".join(errors))
    records = [row for row in corpus["records"] if isinstance(row, dict)]
    catalog = json.loads((ROOT / "corpus" / "venue-catalog.v2.json").read_text(encoding="utf-8"))
    axis_report = json.loads((ROOT / "corpus" / "robotics-axis-strategy-analysis.v2.json").read_text(encoding="utf-8"))
    induction = json.loads((ROOT / "corpus" / "researchstudio-pattern-induction.v2.json").read_text(encoding="utf-8"))
    outcome = json.loads((ROOT / "corpus" / "researchstudio-outcome-contrast.v1.json").read_text(encoding="utf-8"))

    rows_by_axis = {row["axis_id"]: row for row in axis_report.get("axes", []) if isinstance(row, dict)}
    if set(rows_by_axis) != set(AXES):
        raise ValueError("axis strategy report must contain exactly E/P/C/L/D/H/A/S")

    axis_strategy: dict[str, dict[str, Any]] = {}
    for axis in AXES:
        row = rows_by_axis[axis]
        axis_strategy[axis] = {
            "axis_id": axis,
            "axis_name": row.get("axis_name"),
            "axis_name_zh": row.get("axis_name_zh"),
            "corpus_sample_count": row.get("corpus_sample_count"),
            "signature_fidelity_counts": row.get("signature_fidelity_counts", {}),
            "best_posting_strategy": row.get("best_posting_strategy", {}),
            "source_paper_ids": row.get("source_paper_ids", []),
            "venue_scope_candidates": row.get("venue_scope_candidates", []),
            "official_scope_status": row.get("official_scope_status", "REFRESH_REQUIRED"),
        }

    result = {
        "schema_version": "robotics-research-runtime.v1",
        "artifact_status": "DERIVED_RUNTIME_ONLY",
        "source": {
            "corpus_schema": corpus.get("schema_version"),
            "record_count": len(records),
            "journal_count": corpus.get("selection_constraints", {}).get("journal_count"),
            "conference_count": corpus.get("selection_constraints", {}).get("conference_count"),
            "award_recognition_count": sum(
                record.get("award", {}).get("qualifies_for_quota") is True
                for record in records
                if isinstance(record.get("award"), dict)
            ),
            "primary_axis_counts": {
                axis: sum(record.get("primary_axis") == axis for record in records) for axis in AXES
            },
            "corpus_sha256": _sha256(source_path),
            "source_path_policy": "local_only_not_committed",
            "raw_corpus_loaded_at_runtime": False,
        },
        "runtime_contract": {
            "purpose": "compact paper-derived context for normal Idea/Experiment/Writing/Review routing",
            "paper_record_policy": "compact exemplars only; never the complete 100-record corpus",
            "exemplar_count_per_axis": exemplar_count,
            "offline_build": "python scripts/build_robotics_research_runtime.py --input <local-corpus>",
            "offline_audit": "python scripts/validate_public_paper_index.py <local-corpus>",
            "raw_corpus_required_for_runtime": False,
        },
        "paper_exemplars_by_axis": {
            axis: _select_exemplars(records, catalog, axis, exemplar_count) for axis in AXES
        },
        "axis_strategy_by_axis": axis_strategy,
        "pattern_system": {
            "parent_cards": induction.get("coverage", {}).get("parent_cards"),
            "subpattern_cards": induction.get("coverage", {}).get("subpattern_cards"),
            "cluster_count": induction.get("coverage", {}).get("cluster_count"),
            "status": induction.get("status"),
            "real_clustering_claim": induction.get("simulation_boundary", {}).get("real_clustering_claim"),
        },
        "outcome_contract": {
            "status": outcome.get("status"),
            "contrast_enabled": outcome.get("runtime_behavior", {}).get("contrast_enabled"),
            "acceptance_probability": outcome.get("runtime_behavior", {}).get("acceptance_probability"),
        },
        "non_claims": [
            "The source corpus was not loaded by the runtime route.",
            "This artifact is not a prevalence estimate, PCA/factor-analysis fit, or acceptance model.",
            "Exemplar selection is an audit reference, not a ranking of paper quality.",
        ],
    }
    errors = validate_runtime(result)
    if errors:
        raise ValueError("generated runtime artifact is invalid: " + "; ".join(errors))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the compact robotics runtime artifact from a local corpus.")
    parser.add_argument("--input", default=str(_default_input()))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--exemplar-count", type=int, default=4)
    args = parser.parse_args()
    if args.exemplar_count < 1:
        parser.error("--exemplar-count must be positive")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    result = build(args.input, exemplar_count=args.exemplar_count)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"ROBOTICS_RUNTIME: PASS output={output} source_records={result['source']['record_count']} exemplars_per_axis={args.exemplar_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
