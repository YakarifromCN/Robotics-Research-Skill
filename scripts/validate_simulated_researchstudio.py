#!/usr/bin/env python3
"""Validate internal model-simulated ResearchStudio artifacts without upgrading them to real results."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--embedding", type=Path, default=ROOT / "agent/internal/researchstudio-simulated-embedding.v1.json")
    parser.add_argument("--clusters", type=Path, default=ROOT / "agent/internal/researchstudio-simulated-clusters.v1.json")
    parser.add_argument("--contract", type=Path, default=ROOT / "agent/internal/researchstudio-simulated-audit-contract.v1.json")
    parser.add_argument("--allow-missing-clusters", action="store_true")
    args = parser.parse_args()

    corpus = load(ROOT / "corpus/public-paper-index.json")["records"]
    corpus_ids = [record["paper_id"] for record in corpus]
    embedding = load(args.embedding)
    assert embedding["status"] == "SIMULATED_NOT_REAL_UMAP_HDBSCAN"
    assert embedding["embedding_status"] == "SIMULATED_NOT_MODEL_EMBEDDING"
    assert embedding["input_fidelity"] == "METADATA_ONLY"
    assert embedding["record_count"] == len(corpus_ids) == 100
    embedding_records = embedding["records"]
    assert [record["paper_id"] for record in embedding_records] == corpus_ids
    dimensions = embedding["vector_dimension"]
    assert all(len(record["vector"]) == dimensions for record in embedding_records)
    assert all(math.isfinite(float(value)) for record in embedding_records for value in record["vector"])
    assert all("feature_summary" in record and "input_record_digest" in record for record in embedding_records)

    contract = load(args.contract)
    assert contract["schema_version"] == "researchstudio-simulated-audit-contract.v1"
    assert any(
        "SIMULATED_NOT_REAL_UMAP_HDBSCAN" in invariant
        for invariant in contract["simulation_contract"]["global_invariants"]
    )

    if not args.clusters.exists():
        if not args.allow_missing_clusters:
            raise SystemExit(f"missing cluster artifact: {args.clusters}")
        print("SIMULATED_RESEARCHSTUDIO: EMBEDDING_AND_CONTRACT_PASS CLUSTERS_PENDING")
        return 0

    clusters = load(args.clusters)
    assert clusters["status"] == "SIMULATED_NOT_REAL_UMAP_HDBSCAN"
    assert clusters["input_fidelity"] == "METADATA_ONLY"
    assert clusters["record_count"] == 100
    labels = clusters.get("paper_labels", clusters.get("records"))
    assert isinstance(labels, list), "cluster artifact must expose paper_labels or records"
    clustered_ids = [record["paper_id"] for record in labels]
    assert clustered_ids == corpus_ids
    assert len(clustered_ids) == len(set(clustered_ids))
    assert clusters["projection_status"] == "SIMULATED_NOT_UMAP"
    assert clusters["clustering_status"] == "SIMULATED_NOT_HDBSCAN"
    assert clusters["clustered_count"] + clusters["noise_count"] == clusters["record_count"]
    assert sum(cluster["member_count"] for cluster in clusters["clusters"]) == clusters["clustered_count"]
    assert clusters["cluster_count"] == len(clusters["clusters"])
    neighbors = clusters["nearest_neighbors"]["per_paper_top_k"]
    assert set(neighbors) == set(corpus_ids)
    assert all(len(items) == clusters["nearest_neighbors"]["k"] for items in neighbors.values())
    assert clusters["audit_verdict"] in {"INCONCLUSIVE", "INTERNAL_SIMULATION_ONLY"}
    print(
        "SIMULATED_RESEARCHSTUDIO: PASS "
        f"records=100 dimensions={dimensions} clusters={clusters['cluster_count']} noise={clusters['noise_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
