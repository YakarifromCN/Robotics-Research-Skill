"""Canonical v2 router for project strength, evidence pressure, and venue fit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common.robotics_submanifold import analyze, load_json  # noqa: E402


def find_target(candidates: list[dict[str, object]], catalog: dict[str, object], target: str) -> dict[str, object] | None:
    target_lower = target.casefold()
    for record in catalog.get("records", []):
        if not isinstance(record, dict):
            continue
        if str(record.get("venue_id", "")).casefold() == target_lower or str(record.get("name", "")).casefold() == target_lower:
            venue_id = record.get("venue_id")
            for candidate in candidates:
                if candidate.get("venue_id") == venue_id:
                    return candidate
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Route a robotics project through the v2 submanifold and venue catalog.")
    parser.add_argument("profile", help="project profile or V2 research-card JSON")
    parser.add_argument("--venue", help="optional exact venue name or venue_id")
    parser.add_argument("--catalog", default=str(ROOT / "corpus" / "venue-catalog.v2.json"))
    parser.add_argument("--model", default=str(ROOT / "corpus" / "robotics-submanifold.v1.json"))
    parser.add_argument("--top-k", type=int, default=12)
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.top_k < 1:
        parser.error("--top-k must be positive")

    profile = load_json(args.profile)
    catalog = load_json(args.catalog)
    model = load_json(args.model)
    # Keep every catalog record available when a user asks for a fixed venue;
    # the displayed ranking is trimmed only after the target lookup.
    full = analyze(profile, catalog, model, top_k=len(catalog.get("records", [])))
    ranking = full["candidates"][: args.top_k]
    target_fit = find_target(full["candidates"], catalog, args.venue) if args.venue else None
    official_snapshot = profile.get("official_scope_snapshot")
    output = {
        "schema_version": "robotics-submanifold-route.v1",
        "project_vector": full["project_vector"],
        "research_intensity": full["research_intensity"],
        "fixed_venue_fit": target_fit,
        "factor_fit_ranking": ranking,
        "official_scope_status": "PROVIDED" if isinstance(official_snapshot, dict) else "REFRESH_REQUIRED",
        "official_scope_snapshot": official_snapshot if isinstance(official_snapshot, dict) else None,
        "acceptance_probability": {
            "status": "NOT_ESTIMABLE",
            "reason": "A semantic factor vector and venue catalog do not identify review outcomes or a calibrated acceptance probability.",
            "available_proxies": ["factor_fit", "evidence_pressure_coverage", "official_scope_status", "submission_process_completeness"],
        },
        "catalog_id": full["catalog_id"],
        "model_id": full["model_id"],
        "limitations": full["limitations"],
    }
    payload = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        path = Path(args.output)
        path.write_text(payload, encoding="utf-8")
        print(path.resolve())
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
