#!/usr/bin/env python3
"""Regenerate eight-axis strategy routes from v2 signatures and simulated induction."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
AXES = tuple("EPCLDHAS")


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    signatures = load(ROOT / "corpus/researchstudio-paper-signatures.v2.json")
    induction = load(ROOT / "corpus/researchstudio-pattern-induction.v2.json")
    baseline = load(ROOT / "corpus/robotics-axis-strategy-analysis.v1.json")
    baseline_by_axis = {row["axis_id"]: row for row in baseline["axes"]}
    route_by_axis = {row["primary_axis"]: row for row in induction["cluster_capability_routes"]}

    axes: list[dict[str, Any]] = []
    for axis in AXES:
        old = baseline_by_axis[axis]
        route = route_by_axis[axis]
        rows = [
            row
            for row in signatures["records"]
            if row.get("primary_axis") == axis
            or int(row.get("submanifold_axes", {}).get(axis, 0)) >= 2
        ]
        fidelity = Counter(row["extraction_fidelity"] for row in rows)
        strategy = dict(old["best_posting_strategy"])
        strategy["model_simulated_capability_route"] = {
            "cluster_id": route["cluster_id"],
            "runtime_question_id": route["runtime_question_id"],
            "runtime_question": route["runtime_question"],
            "contribution_center": route["contribution_center"],
            "preferred_parent_pattern_ids": route["preferred_parent_pattern_ids"],
            "preferred_subpattern_ids": route["preferred_subpattern_ids"],
            "workflow_translation": route["workflow_translation"],
        }
        axes.append(
            {
                "axis_id": axis,
                "axis_name": old["axis_name"],
                "axis_name_zh": old["axis_name_zh"],
                "corpus_sample_count": len(rows),
                "signature_fidelity_counts": dict(sorted(fidelity.items())),
                "best_posting_strategy": strategy,
                "source_paper_ids": [row["paper_id"] for row in rows],
                "venue_scope_candidates": old["venue_scope_candidates"],
                "official_scope_status": "REFRESH_REQUIRED",
                "routing_boundary": old["routing_boundary"],
            }
        )

    output = {
        "schema_version": "robotics-axis-strategy-analysis.v2",
        "status": "MODEL_SIMULATED_CAPABILITY_REGENERATION_COMPLETE",
        "analysis_id": "ROBOTICS-AXIS-STRATEGY-SIMULATED-V2-100",
        "input": {
            "signature_schema": signatures["schema_version"],
            "signature_record_count": signatures["record_count"],
            "signature_fidelity_counts": signatures["fidelity_counts"],
            "pattern_induction_schema": induction["schema_version"],
            "pattern_library_schema": "researchstudio-robotics-pattern-cards.v1",
            "venue_catalog_schema": "robotics-venue-catalog-v2",
        },
        "method": {
            "route": "axis -> simulated capability question -> 15/31 card mapping -> evidence recipe -> venue scope candidates",
            "purpose": "reasonable reusable Skill injection",
            "statistical_claim": False,
            "real_umap_hdbscan_claim": False
        },
        "axes": axes,
        "acceptance_probability": "NOT_ESTIMABLE",
        "non_claims": [
            "The simulated cluster ID is not a discovered scientific class.",
            "Venue scope candidates are not rankings and require current official-source refresh.",
            "Awards, presentations, counts, and factor fit are not decision outcomes.",
            "Mixed-fidelity model extraction is a capability substrate, not a paper-quality estimate."
        ]
    }
    path = ROOT / "corpus/robotics-axis-strategy-analysis.v2.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"ROBOTICS_AXIS_STRATEGY_V2: PASS axes={len(axes)} output={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
