"""Analyze the balanced robotics corpus with the ResearchStudio pattern substrate.

The result answers: for each robotics research axis, which reusable reasoning
operator best matches the observed mechanism signatures, what supporting
operator composes with it, what evidence is needed, and which venue scopes are
semantically compatible.  It does not rank venues by prestige or predict
acceptance.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common.researchstudio_patterns import (  # noqa: E402
    DEFAULT_LIBRARY,
    fit_patterns_for_axis,
    load_pattern_library,
    validate_pattern_library,
)
from common.robotics_submanifold import AXIS_ORDER, load_json  # noqa: E402


DEFAULT_SIGNATURES = ROOT / "corpus" / "researchstudio-paper-signatures.v1.json"
DEFAULT_CATALOG = ROOT / "corpus" / "venue-catalog.v2.json"
DEFAULT_MODEL = ROOT / "corpus" / "robotics-submanifold.v1.json"
DEFAULT_OUTPUT = ROOT / "corpus" / "robotics-axis-strategy-analysis.v1.json"


def _axis_records(records: list[dict[str, Any]], axis: str) -> list[dict[str, Any]]:
    return [
        record
        for record in records
        if record.get("primary_axis") == axis or int(record.get("submanifold_axes", {}).get(axis, 0)) >= 2
    ]


def _normalise(text: str) -> str:
    return text.casefold().replace("_", " ").replace("-", " ")


def _scope_candidates(axis_profile: dict[str, Any], catalog: dict[str, Any]) -> list[dict[str, Any]]:
    wanted = [_normalise(str(item)) for item in axis_profile.get("venue_scope_tags", [])]
    rows: list[dict[str, Any]] = []
    for venue in catalog.get("records", []):
        if not isinstance(venue, dict):
            continue
        tags = [_normalise(str(item)) for item in venue.get("topic_tags", [])]
        hits = sorted({tag for tag in wanted if tag in tags})
        overlap = len(hits) / max(1, len(wanted))
        directness = float(venue.get("directness_weight", 0.65))
        scope_fit = 0.75 * overlap + 0.25 * directness
        if hits:
            rows.append({
                "venue_id": venue.get("venue_id"),
                "name": venue.get("name"),
                "kind": venue.get("kind"),
                "layer": venue.get("layer"),
                "directness_weight": directness,
                "matched_scope_tags": hits,
                "scope_fit": round(scope_fit, 4),
                "official_scope_status": "REFRESH_REQUIRED",
            })
    rows.sort(key=lambda item: (-item["scope_fit"], -item["directness_weight"], str(item["name"])))
    return rows[:8]


def _corpus_venue_context(axis_rows: list[dict[str, Any]], catalog: dict[str, Any]) -> dict[str, Any]:
    weights = {
        str(row.get("name")): float(row.get("directness_weight", 0.65))
        for row in catalog.get("records", [])
        if isinstance(row, dict) and row.get("name")
    }
    counts = Counter(str(row.get("venue")) for row in axis_rows if row.get("venue"))
    direct = [weights.get(name, 0.65) for name in counts]
    return {
        "observed_venue_counts": dict(sorted(counts.items(), key=lambda item: (-item[1], item[0]))),
        "observed_directness_weight_mean": round(sum(direct) / len(direct), 4) if direct else 0.0,
        "semantics": "coverage context only; not a venue quality or acceptance measure",
    }


def build_report(
    signatures_path: str | Path = DEFAULT_SIGNATURES,
    library_path: str | Path = DEFAULT_LIBRARY,
    catalog_path: str | Path = DEFAULT_CATALOG,
    model_path: str | Path = DEFAULT_MODEL,
) -> dict[str, Any]:
    signatures = load_json(signatures_path)
    library = load_pattern_library(library_path)
    catalog = load_json(catalog_path)
    model = load_json(model_path)
    errors = validate_pattern_library(library)
    if errors:
        raise ValueError("invalid pattern library: " + "; ".join(errors))
    records = signatures.get("records", [])
    axes: list[dict[str, Any]] = []
    for axis in AXIS_ORDER:
        rows = _axis_records(records, axis)
        fit = fit_patterns_for_axis(axis, rows, library, catalog=catalog, top_k=5)
        profile = library["axis_profiles"][axis]
        ranked = fit["ranked_patterns"]
        best = ranked[0] if ranked else None
        supporting = ranked[1:3] if len(ranked) >= 3 else ranked[1:]
        subpatterns = fit["recommended_subpatterns"]
        axes.append({
            "axis_id": axis,
            "axis_name": profile["axis_name"],
            "axis_name_zh": profile["axis_name_zh"],
            "corpus_sample_count": len(rows),
            "data_fidelity": fit["data_fidelity"],
            "best_posting_strategy": {
                "anchor_pattern": best,
                "supporting_patterns": supporting,
                "composition_default": [item["pattern_id"] for item in ([best] if best else []) + supporting[:1]],
                "tactical_subpatterns": [
                    {"subpattern_id": item["subpattern_id"], "parent_pattern_id": item["parent_pattern_id"], "name": item["name"], "when_to_apply": item["when_to_apply"]}
                    for item in subpatterns
                ],
                "strategy_signature": profile["strategy_signature_template"],
                "evidence_recipe": profile["evidence_recipe"],
                "failure_guard": profile["failure_guard"],
                "claim_altitude": profile["claim_altitude"],
            },
            "corpus_support": {
                "paper_ids": [str(row.get("paper_id")) for row in rows],
                "observed_venue_context": _corpus_venue_context(rows, catalog),
                "recognition_and_outcome_status": "DESCRIPTIVE_RECOGNITION_ONLY; NO_DECISION_ALIGNED_ORAL_HC_REJECT_TABLE",
            },
            "venue_scope_candidates": _scope_candidates(profile, catalog),
            "routing_boundary": "Use these venues only as scope candidates; refresh each target's official scope, format, ethics, artifact and submission policy before drafting.",
        })
    return {
        "schema_version": "robotics-axis-strategy-analysis.v1",
        "analysis_id": "ROBOTICS-AXIS-STRATEGY-BASELINE-100",
        "method": {
            "source": "ResearchStudio.pdf",
            "chain": "paper metadata/full text + outcome -> Stage-1 fields -> domain-agnostic Stage-2 strategy signature -> embedding/UMAP/HDBSCAN infrastructure -> pattern-card fit -> axis-level posting strategy",
            "current_run": "metadata adapter + transparent expert structural fit; not full-text LLM extraction and not an upstream PCA/factor-analysis result",
            "selection_unit": "research-axis bottleneck",
            "pattern_composition": {"min": 1, "max": 3, "default": 2},
        },
        "input": {
            "signature_schema": signatures.get("schema_version"),
            "signature_record_count": len(records),
            "signature_fidelity": signatures.get("data_fidelity"),
            "pattern_library_schema": library.get("schema_version"),
            "axis_model_schema": model.get("schema_version"),
            "venue_catalog_schema": catalog.get("schema_version"),
        },
        "axes": axes,
        "non_claims": [
            "No acceptance probability is estimated.",
            "No rating or prestige field is used.",
            "Directness weight is a scope-routing prior only.",
            "Recognition and presentation fields are not treated as reviewer decisions.",
            "Metadata-only signatures do not establish true semantic clusters or outcome-conditioned pattern effects.",
        ],
        "upgrade_gate": {
            "next_required_input": "full-text or abstract-backed Stage-1/Stage-2 signatures for every selected paper",
            "then_run": ["scripts/induce_researchstudio_patterns.py", "scripts/analyze_robotics_axis_strategies.py", "scripts/validate_robotics_axis_strategy_analysis.py"],
            "outcome_comparison_requires": "decision-aligned Oral/Reject labels plus independently sourced High-Cited labels with denominator provenance",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze per-axis robotics posting strategy patterns.")
    parser.add_argument("--signatures", default=str(DEFAULT_SIGNATURES))
    parser.add_argument("--library", default=str(DEFAULT_LIBRARY))
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    parser.add_argument("--model", default=str(DEFAULT_MODEL))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    report = build_report(args.signatures, args.library, args.catalog, args.model)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output.resolve())
    for row in report["axes"]:
        print(f"{row['axis_id']} {row['axis_name']}: {row['best_posting_strategy']['anchor_pattern']['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
