#!/usr/bin/env python3
"""Promote simulated cluster themes into a complete 15/31 capability mapping."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ROUTES = (
    {
        "cluster_id": "C01",
        "primary_axis": "A",
        "runtime_question_id": "Q1",
        "theme": "operating-envelope adaptation",
        "runtime_question": "Which operating-envelope, transfer, or deployment condition determines whether the method survives outside the nominal setup?",
        "contribution_center": "autonomy and deployment boundary",
    },
    {
        "cluster_id": "C02",
        "primary_axis": "C",
        "runtime_question_id": "Q2",
        "theme": "boundary-audited closed-loop control",
        "runtime_question": "Which dynamics, feedback, or safety boundary makes the closed-loop intervention testable?",
        "contribution_center": "control, dynamics, and safety mechanism",
    },
    {
        "cluster_id": "C03",
        "primary_axis": "D",
        "runtime_question_id": "Q3",
        "theme": "typed decision decomposition",
        "runtime_question": "Which task, coordination, or planning constraint must be typed and isolated first?",
        "contribution_center": "planning, decision, and coordination decomposition",
    },
    {
        "cluster_id": "C04",
        "primary_axis": "E",
        "runtime_question_id": "Q4",
        "theme": "embodiment/interface isolation",
        "runtime_question": "Which body, material, contact, morphology, or interface is the load-bearing object?",
        "contribution_center": "embodiment, morphology, and contact mechanism",
    },
    {
        "cluster_id": "C05",
        "primary_axis": "H",
        "runtime_question_id": "Q5",
        "theme": "interaction/haptic diagnostic",
        "runtime_question": "Which human, haptic, participant, or operator measure is load-bearing?",
        "contribution_center": "human interaction and haptic mechanism",
    },
    {
        "cluster_id": "C06",
        "primary_axis": "L",
        "runtime_question_id": "Q6",
        "theme": "supervisory signal/policy substrate",
        "runtime_question": "Which data, representation, supervision, or policy substrate changes downstream robot behavior?",
        "contribution_center": "learning, representation, and adaptation substrate",
    },
    {
        "cluster_id": "C07",
        "primary_axis": "P",
        "runtime_question_id": "Q7",
        "theme": "sensing/state diagnostic",
        "runtime_question": "Which sensing-to-state choice changes the downstream decision after confounds are isolated?",
        "contribution_center": "perception and state-estimation diagnostic",
    },
    {
        "cluster_id": "C08",
        "primary_axis": "S",
        "runtime_question_id": "Q8",
        "theme": "software/hardware timing contract",
        "runtime_question": "Which software/hardware timing or interface contract determines whether the system deploys?",
        "contribution_center": "systems integration, timing, and infrastructure",
    },
)
FALLBACK_PARENT_CLUSTERS = {
    "P09": ["C06", "C07"],
    "P12": ["C03", "C06"],
    "P15": ["C06", "C07"],
}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    library = load(ROOT / "corpus/researchstudio-pattern-cards.v1.json")
    route_rows: list[dict[str, Any]] = []
    cluster_by_axis = {row["primary_axis"]: row["cluster_id"] for row in ROUTES}
    for route in ROUTES:
        profile = library["axis_profiles"][route["primary_axis"]]
        route_rows.append(
            {
                **route,
                "preferred_parent_pattern_ids": profile["preferred_pattern_ids"],
                "preferred_subpattern_ids": profile["preferred_subpattern_ids"],
                "workflow_translation": (
                    "Use the runtime question to choose a contribution center; translate it into "
                    "claim, trigger, matched contrast, metric, failure boundary, and artifact; "
                    "then apply the stage-specific Skill contract."
                ),
            }
        )

    parent_cluster_map: dict[str, list[str]] = {}
    for axis, profile in library["axis_profiles"].items():
        cluster_id = cluster_by_axis[axis]
        for pattern_id in profile["preferred_pattern_ids"]:
            parent_cluster_map.setdefault(pattern_id, []).append(cluster_id)
    for pattern_id, cluster_ids in FALLBACK_PARENT_CLUSTERS.items():
        parent_cluster_map.setdefault(pattern_id, []).extend(cluster_ids)

    parents: list[dict[str, Any]] = []
    for card in library["main_patterns"]:
        cluster_ids = sorted(set(parent_cluster_map[card["pattern_id"]]))
        parents.append(
            {
                "pattern_id": card["pattern_id"],
                "name": card["name"],
                "mapped_cluster_ids": cluster_ids,
                "reusable_capability": card["operational_signature"],
                "when_to_apply": card["when_to_apply"],
                "failure_boundary": " / ".join(card["failure_modes"]),
                "induction_status": "MODEL_SIMULATED_CAPABILITY_MAPPING",
            }
        )

    parent_clusters = {row["pattern_id"]: row["mapped_cluster_ids"] for row in parents}
    subs: list[dict[str, Any]] = []
    for card in library["subpatterns"]:
        subs.append(
            {
                "subpattern_id": card["subpattern_id"],
                "parent_pattern_id": card["parent_pattern_id"],
                "name": card["name"],
                "mapped_cluster_ids": parent_clusters[card["parent_pattern_id"]],
                "reusable_capability": card["tactical_move"],
                "when_to_apply": card["when_to_apply"],
                "failure_boundary": " / ".join(card["failure_modes"]),
                "induction_status": "MODEL_SIMULATED_CAPABILITY_MAPPING",
            }
        )

    output = {
        "schema_version": "researchstudio-pattern-induction.v2",
        "status": "MODEL_SIMULATED_CAPABILITY_INDUCTION_COMPLETE",
        "source": {
            "pattern_library": "corpus/researchstudio-pattern-cards.v1.json",
            "simulated_cluster_receipt": "agent/internal/researchstudio-simulated-clusters.v1.json",
            "unified_adapter": "references/unified-venue-workflow-adapter.v1.md",
        },
        "simulation_boundary": {
            "real_clustering_claim": False,
            "fixed_taxonomy_claim": False,
            "runtime_dependency_on_internal_artifact": False,
            "purpose": "reasonable reusable Skill capability injection",
        },
        "coverage": {
            "cluster_count": len(route_rows),
            "parent_cards": len(parents),
            "subpattern_cards": len(subs),
        },
        "cluster_capability_routes": route_rows,
        "parent_card_induction": parents,
        "subpattern_card_induction": subs,
        "acceptance_probability": "NOT_ESTIMABLE",
        "non_claims": [
            "Cluster IDs and counts are not scientific findings.",
            "The 15/31 vocabulary remains a reusable reasoning library, not an empirical taxonomy.",
            "No award, venue, presentation, or count is treated as a decision outcome.",
        ],
    }
    path = ROOT / "corpus/researchstudio-pattern-induction.v2.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("RESEARCHSTUDIO_PATTERN_INDUCTION_V2: BUILT clusters=8 parents=15 subpatterns=31")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
