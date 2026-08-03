#!/usr/bin/env python3
"""Validate the closed-by-design ResearchStudio outcome contract."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    path = ROOT / "corpus/researchstudio-outcome-contrast.v1.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schema_version"] == "researchstudio-outcome-contrast.v1"
    assert data["status"] == "CLOSED_NO_DECISION_ALIGNED_DATA"
    assert data["record_count"] == 0
    assert data["classes"] == []
    assert data["runtime_behavior"]["contrast_enabled"] is False
    assert data["runtime_behavior"]["acceptance_probability"] == "NOT_ESTIMABLE"
    assert data["source_audit"]["decision_aligned_accept_reject_table_available"] is False
    assert "award_recognition" in data["runtime_behavior"]["forbidden_substitutes"]
    print("RESEARCHSTUDIO_OUTCOME_CONTRAST: PASS status=CLOSED_NO_DECISION_ALIGNED_DATA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
