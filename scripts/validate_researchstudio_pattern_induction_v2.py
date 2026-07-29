#!/usr/bin/env python3
"""Validate the model-simulated 15/31 pattern-card induction receipt."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    artifact = json.loads(
        (ROOT / "corpus/researchstudio-pattern-induction.v2.json").read_text(encoding="utf-8")
    )
    library = json.loads(
        (ROOT / "corpus/researchstudio-pattern-cards.v1.json").read_text(encoding="utf-8")
    )
    parent_ids = {row["pattern_id"] for row in library["main_patterns"]}
    sub_ids = {row["subpattern_id"] for row in library["subpatterns"]}
    cluster_ids = {f"C{index:02d}" for index in range(1, 9)}

    assert artifact["schema_version"] == "researchstudio-pattern-induction.v2"
    assert artifact["status"] == "MODEL_SIMULATED_CAPABILITY_INDUCTION_COMPLETE"
    assert artifact["simulation_boundary"]["real_clustering_claim"] is False
    assert artifact["coverage"]["cluster_count"] == 8
    assert artifact["coverage"]["parent_cards"] == 15
    assert artifact["coverage"]["subpattern_cards"] == 31

    cluster_rows = artifact["cluster_capability_routes"]
    assert {row["cluster_id"] for row in cluster_rows} == cluster_ids
    assert {row["primary_axis"] for row in cluster_rows} == set("EPCLDHAS")
    assert {row["runtime_question_id"] for row in cluster_rows} == {
        f"Q{index}" for index in range(1, 9)
    }

    parents = artifact["parent_card_induction"]
    subs = artifact["subpattern_card_induction"]
    assert {row["pattern_id"] for row in parents} == parent_ids
    assert {row["subpattern_id"] for row in subs} == sub_ids
    assert all(set(row["mapped_cluster_ids"]) <= cluster_ids and row["mapped_cluster_ids"] for row in parents)
    assert all(set(row["mapped_cluster_ids"]) <= cluster_ids and row["mapped_cluster_ids"] for row in subs)
    assert all(row["parent_pattern_id"] in parent_ids for row in subs)
    assert all(isinstance(row["reusable_capability"], str) and row["reusable_capability"].strip() for row in parents)
    assert all(isinstance(row["failure_boundary"], str) and row["failure_boundary"].strip() for row in parents)
    assert artifact["acceptance_probability"] == "NOT_ESTIMABLE"
    print("RESEARCHSTUDIO_PATTERN_INDUCTION_V2: PASS clusters=8 parents=15 subpatterns=31")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
