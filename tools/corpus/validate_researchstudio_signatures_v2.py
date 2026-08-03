#!/usr/bin/env python3
"""Validate the mixed-fidelity model-simulated ResearchStudio signature index."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    path = ROOT / "corpus/researchstudio-paper-signatures.v2.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    index = json.loads((ROOT / "corpus/public-paper-index.json").read_text(encoding="utf-8"))
    manifest = json.loads(
        (ROOT / "corpus/public-paper-fulltext-manifest.v1.json").read_text(encoding="utf-8")
    )
    assert data["schema_version"] == "researchstudio-paper-signatures.v2"
    assert data["record_count"] == len(data["records"]) == 100
    expected_ids = [row["paper_id"] for row in index["records"]]
    observed_ids = [row["paper_id"] for row in data["records"]]
    assert observed_ids == expected_ids
    assert len(set(observed_ids)) == 100
    manifest_fidelity = {
        row["paper_id"]: (
            "FULLTEXT_EXTRACTED" if row.get("text_status") == "EXTRACTED"
            else "FULLTEXT_WEB_VERIFIED" if row.get("status") == "WEB_FULLTEXT_VERIFIED"
            else "METADATA_FALLBACK"
        )
        for row in manifest["records"]
    }
    counts: Counter[str] = Counter()
    for row in data["records"]:
        fidelity = row["extraction_fidelity"]
        assert fidelity == manifest_fidelity[row["paper_id"]]
        counts[fidelity] += 1
        stage1 = row["stage1_base_fields"]
        stage2 = row["stage2_domain_agnostic_fields"]
        assert stage1["reviewer_praise"] == []
        assert stage1["reviewer_concern"] == []
        assert stage1["acceptance_signal"] is None
        assert all(isinstance(value, str) and value.strip() for key, value in stage1.items() if key not in {"reviewer_praise", "reviewer_concern", "acceptance_signal"})
        assert all(isinstance(value, str) and value.strip() for value in stage2.values())
        assert row["model_simulation_status"] == "MODEL_SIMULATED_NO_EXTERNAL_API"
        assert len(row["record_digest"]) == 64
    assert dict(counts) == data["fidelity_counts"]
    assert set(counts) <= {"FULLTEXT_EXTRACTED", "FULLTEXT_WEB_VERIFIED"}
    print(f"RESEARCHSTUDIO_SIGNATURES_V2: PASS records=100 fidelity={dict(counts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
