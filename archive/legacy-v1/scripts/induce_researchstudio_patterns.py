"""Run the embedding -> UMAP -> HDBSCAN pattern-discovery infrastructure.

The script uses the ResearchStudio production defaults when optional
dependencies and supplied vectors are available.  Otherwise it runs a
deterministic, clearly labelled smoke backend so the data contract remains
executable in the bundled runtime.  A fallback result is never described as a
real UMAP/HDBSCAN induction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter, deque
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common.researchstudio_patterns import DEFAULT_LIBRARY, load_pattern_library, validate_pattern_library  # noqa: E402
from common.robotics_submanifold import load_json  # noqa: E402


DEFAULT_INPUT = ROOT / "corpus" / "researchstudio-paper-signatures.v1.json"
DEFAULT_OUTPUT = ROOT / "corpus" / "researchstudio-cluster-analysis.v1.json"


def _text(record: dict[str, Any]) -> str:
    fields = record.get("stage2_domain_agnostic_fields", {})
    if isinstance(fields, dict):
        return " ".join(f"{key}: {value}" for key, value in fields.items() if value)
    return str(record.get("strategy_signature", ""))


def _tokens(text: str) -> list[str]:
    return [token.casefold() for token in text.replace("_", " ").split() if token.strip()]


def _hash_embedding(text: str, dimensions: int = 256) -> list[float]:
    vector = [0.0] * dimensions
    tokens = _tokens(text)
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 else -1.0
        vector[index] += sign * (1.0 + (digest[5] / 255.0))
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def _load_vectors(records: list[dict[str, Any]], dimensions: int = 256) -> tuple[list[list[float]], str, str]:
    supplied = [record.get("embedding") for record in records]
    if supplied and all(isinstance(item, list) and item for item in supplied):
        dims = len(supplied[0])
        if all(len(item) == dims and all(isinstance(x, (int, float)) for x in item) for item in supplied):
            return [[float(x) for x in item] for item in supplied], "provided_vectors", f"provided:{dims}"
    return [_hash_embedding(_text(record), dimensions) for record in records], "hash_smoke", f"hash:{dimensions}"


def _project(vectors: list[list[float]], *, strict_real: bool = False) -> tuple[list[list[float]], dict[str, Any]]:
    try:
        import numpy as np  # type: ignore
    except Exception:
        if strict_real:
            raise RuntimeError("strict real projection requested but numpy/umap is unavailable")
        return [vector[:10] for vector in vectors], {
            "backend": "deterministic_hash_slice",
            "status": "FALLBACK_NOT_UMAP",
            "dimensions": min(10, len(vectors[0]) if vectors else 0),
        }
    try:
        import umap  # type: ignore

        reducer = umap.UMAP(n_components=10, n_neighbors=15, min_dist=0.0, metric="cosine", random_state=42)
        projected = reducer.fit_transform(np.asarray(vectors, dtype=float)).tolist()
        return projected, {"backend": "umap", "status": "REAL_UMAP", "n_components": 10, "n_neighbors": 15, "min_dist": 0.0, "metric": "cosine", "seed": 42}
    except Exception as exc:
        if strict_real:
            raise RuntimeError(f"strict real UMAP requested but unavailable: {exc}") from exc
        matrix = np.asarray(vectors, dtype=float)
        matrix = matrix - matrix.mean(axis=0, keepdims=True)
        _, _, vt = np.linalg.svd(matrix, full_matrices=False)
        dims = min(10, vt.shape[0])
        projected = (matrix @ vt[:dims].T).tolist()
        return projected, {"backend": "numpy_svd", "status": "FALLBACK_NOT_UMAP", "dimensions": dims, "reason": str(exc)}


def _fallback_clusters(projected: list[list[float]], min_cluster_size: int = 10) -> list[int]:
    """Deterministic density-component fallback, not HDBSCAN."""

    n = len(projected)
    threshold = 0.86
    adjacency = [[] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if _cosine(projected[i], projected[j]) >= threshold:
                adjacency[i].append(j)
                adjacency[j].append(i)
    labels = [-1] * n
    cluster_id = 0
    for start in range(n):
        if labels[start] != -1:
            continue
        queue: deque[int] = deque([start])
        seen = {start}
        while queue:
            current = queue.popleft()
            for neighbor in adjacency[current]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)
        if len(seen) >= min_cluster_size:
            for member in seen:
                labels[member] = cluster_id
            cluster_id += 1
    return labels


def _cluster(projected: list[list[float]], *, min_cluster_size: int = 10, strict_real: bool = False) -> tuple[list[int], dict[str, Any]]:
    try:
        import hdbscan  # type: ignore

        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=math.ceil(min_cluster_size / 3),
            cluster_selection_method="eom",
            metric="euclidean",
        )
        labels = [int(item) for item in clusterer.fit_predict(projected)]
        return labels, {
            "backend": "hdbscan",
            "status": "REAL_HDBSCAN",
            "min_cluster_size": min_cluster_size,
            "min_samples": math.ceil(min_cluster_size / 3),
            "cluster_selection_method": "eom",
        }
    except Exception as exc:
        if strict_real:
            raise RuntimeError(f"strict real HDBSCAN requested but unavailable: {exc}") from exc
        return _fallback_clusters(projected, min_cluster_size), {
            "backend": "density_components",
            "status": "FALLBACK_NOT_HDBSCAN",
            "min_cluster_size": min_cluster_size,
            "threshold": 0.86,
            "reason": str(exc),
        }


def _silhouette(projected: list[list[float]], labels: list[int]) -> float | None:
    clusters = sorted({label for label in labels if label >= 0})
    if len(clusters) < 2:
        return None
    values: list[float] = []
    for index, label in enumerate(labels):
        if label < 0:
            continue
        same = [j for j, other in enumerate(labels) if other == label and j != index]
        if not same:
            continue
        a = sum(1.0 - _cosine(projected[index], projected[j]) for j in same) / len(same)
        other_means = []
        for other_label in clusters:
            if other_label == label:
                continue
            other = [j for j, candidate in enumerate(labels) if candidate == other_label]
            other_means.append(sum(1.0 - _cosine(projected[index], projected[j]) for j in other) / len(other))
        b = min(other_means) if other_means else a
        values.append((b - a) / max(a, b, 1e-12))
    return round(sum(values) / len(values), 4) if values else None


def build(input_path: str | Path = DEFAULT_INPUT, library_path: str | Path = DEFAULT_LIBRARY, *, strict_real: bool = False) -> dict[str, Any]:
    signatures = load_json(input_path)
    library = load_pattern_library(library_path)
    errors = validate_pattern_library(library)
    if errors:
        raise ValueError("invalid pattern library: " + "; ".join(errors))
    records = [item for item in signatures.get("records", []) if isinstance(item, dict)]
    vectors, embedding_backend, embedding_manifest = _load_vectors(records)
    projected, projection_meta = _project(vectors, strict_real=strict_real)
    labels, cluster_meta = _cluster(projected, min_cluster_size=10, strict_real=strict_real)
    clusters: list[dict[str, Any]] = []
    for label in sorted({item for item in labels if item >= 0}):
        indexes = [index for index, item in enumerate(labels) if item == label]
        axis_counts = Counter(str(records[index].get("primary_axis")) for index in indexes)
        tag_counts = Counter(tag for index in indexes for tag in records[index].get("pattern_tags", []))
        clusters.append({
            "cluster_id": f"C{label:02d}",
            "label": label,
            "size": len(indexes),
            "member_paper_ids": [records[index].get("paper_id") for index in indexes],
            "dominant_axes": [item[0] for item in axis_counts.most_common()],
            "top_metadata_terms": [item[0] for item in tag_counts.most_common(8)],
            "card_induction_status": "LLM_INDUCTION_REQUIRED",
        })
    unclustered = [records[index].get("paper_id") for index, label in enumerate(labels) if label < 0]
    return {
        "schema_version": "researchstudio-cluster-analysis.v1",
        "method": {
            "embedding_input": "field-prefixed four-field domain-agnostic Stage-2 signature",
            "embedding_backend": embedding_backend,
            "embedding_manifest": embedding_manifest,
            "projection": projection_meta,
            "clustering": cluster_meta,
            "upstream_defaults": {"umap_dimensions": 10, "umap_neighbors": 15, "umap_min_dist": 0.0, "seed": 42, "hdbscan_min_cluster_size": 10, "hdbscan_selection": "eom"},
        },
        "input": {"signature_schema": signatures.get("schema_version"), "record_count": len(records), "data_fidelity": signatures.get("data_fidelity")},
        "clusters": clusters,
        "unclustered": {"count": len(unclustered), "paper_ids": unclustered, "semantics": "geometric fallback/noise label only; not a substantive quality judgment"},
        "diagnostics": {"cluster_count": len(clusters), "silhouette": _silhouette(projected, labels), "label_counts": dict(Counter(labels))},
        "pattern_card_status": "SEED_LIBRARY_AVAILABLE; CLUSTER_TO_CARD_LLM_INDUCTION_NOT_RUN",
        "outcome_contrast": {"status": "DISABLED", "reason": "current corpus has no decision-aligned Oral/HC/Reject outcome table"},
        "honesty_boundary": "If projection or clustering uses a fallback backend, this artifact is infrastructure smoke output and must not be reported as a true UMAP/HDBSCAN result.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the ResearchStudio embedding/UMAP/HDBSCAN pattern pipeline.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--library", default=str(DEFAULT_LIBRARY))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--strict-real", action="store_true", help="fail unless real UMAP and HDBSCAN backends are importable")
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    result = build(args.input, args.library, strict_real=args.strict_real)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output.resolve())
    print(result["method"]["projection"]["status"], result["method"]["clustering"]["status"], result["diagnostics"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
