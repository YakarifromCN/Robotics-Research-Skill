#!/usr/bin/env python3
"""Validate the model-simulated eight-axis strategy v2 artifact."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AXES = set("EPCLDHAS")


def main() -> int:
    data = json.loads(
        (ROOT / "corpus/robotics-axis-strategy-analysis.v2.json").read_text(encoding="utf-8")
    )
    assert data["schema_version"] == "robotics-axis-strategy-analysis.v2"
    assert data["status"] == "MODEL_SIMULATED_CAPABILITY_REGENERATION_COMPLETE"
    assert data["input"]["signature_record_count"] == 100
    assert data["method"]["statistical_claim"] is False
    assert data["method"]["real_umap_hdbscan_claim"] is False
    assert data["acceptance_probability"] == "NOT_ESTIMABLE"
    rows = data["axes"]
    assert len(rows) == 8
    assert {row["axis_id"] for row in rows} == AXES
    question_ids = set()
    cluster_ids = set()
    for row in rows:
        route = row["best_posting_strategy"]["model_simulated_capability_route"]
        question_ids.add(route["runtime_question_id"])
        cluster_ids.add(route["cluster_id"])
        assert route["preferred_parent_pattern_ids"]
        assert route["preferred_subpattern_ids"]
        assert isinstance(route["workflow_translation"], str) and route["workflow_translation"].strip()
        assert row["official_scope_status"] == "REFRESH_REQUIRED"
        assert row["source_paper_ids"]
        assert sum(row["signature_fidelity_counts"].values()) == row["corpus_sample_count"]
        assert all(
            candidate["official_scope_status"] == "REFRESH_REQUIRED"
            for candidate in row["venue_scope_candidates"]
        )
    assert question_ids == {f"Q{index}" for index in range(1, 9)}
    assert cluster_ids == {f"C{index:02d}" for index in range(1, 9)}
    print("ROBOTICS_AXIS_STRATEGY_V2: PASS axes=8 questions=8 clusters=8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
