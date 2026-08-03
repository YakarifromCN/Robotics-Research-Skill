#!/usr/bin/env python3
"""Validate the robotics submanifold model and full venue coverage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common.robotics_submanifold import load_json, validate_model, venue_vector


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", default=str(ROOT / "corpus" / "venue-catalog.v2.json"))
    parser.add_argument("--model", default=str(ROOT / "corpus" / "robotics-submanifold.v1.json"))
    args = parser.parse_args()
    catalog = load_json(args.catalog)
    model = load_json(args.model)
    errors = validate_model(model, catalog)
    covered = []
    if not errors:
        for record in catalog["records"]:
            vector = venue_vector(record, model)["vector"]
            if sum(vector.values()) == 0:
                errors.append(f"venue has no factor loading: {record.get('venue_id')}")
            else:
                covered.append(record.get("venue_id"))
    result = {
        "valid": not errors,
        "model_id": model.get("model_id"),
        "catalog_id": catalog.get("catalog_id"),
        "venue_count": len(catalog.get("records", [])),
        "factorized_count": len(covered),
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(bool(errors))


if __name__ == "__main__":
    main()
