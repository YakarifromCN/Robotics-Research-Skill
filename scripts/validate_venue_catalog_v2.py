"""Validate the canonical venue catalog and its directness prior."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate(catalog: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if catalog.get("schema_version") != "robotics-venue-catalog.v2":
        errors.append("schema_version must be robotics-venue-catalog.v2")
    records = catalog.get("records")
    if not isinstance(records, list) or not records:
        return ["records must be a nonempty list"]
    ids: set[str] = set()
    for index, record in enumerate(records):
        prefix = f"records[{index}]"
        if not isinstance(record, dict):
            errors.append(f"{prefix} must be an object")
            continue
        venue_id = record.get("venue_id")
        if not isinstance(venue_id, str) or not venue_id:
            errors.append(f"{prefix}.venue_id must be nonempty")
        elif venue_id in ids:
            errors.append(f"duplicate venue_id: {venue_id}")
        else:
            ids.add(venue_id)
        if "ratings" in record:
            errors.append(f"{prefix} must not contain ratings")
        if record.get("layer") not in {"direct_robotics", "robotics_strong_related"}:
            errors.append(f"{prefix}.layer unsupported")
        expected_weight = 1.0 if record.get("layer") == "direct_robotics" else 0.65
        if record.get("directness_weight") != expected_weight:
            errors.append(f"{prefix}.directness_weight must equal {expected_weight}")
        if not isinstance(record.get("topic_tags"), list) or not record["topic_tags"]:
            errors.append(f"{prefix}.topic_tags must be nonempty")
        if not isinstance(record.get("contribution_gate"), list):
            errors.append(f"{prefix}.contribution_gate must be a list")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog", nargs="?", default=str(ROOT / "corpus" / "venue-catalog.v2.json"))
    args = parser.parse_args()
    value = json.loads(Path(args.catalog).read_text(encoding="utf-8"))
    errors = validate(value)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    records = value["records"]
    direct = sum(record["layer"] == "direct_robotics" for record in records)
    related = sum(record["layer"] == "robotics_strong_related" for record in records)
    print(f"VENUE_CATALOG_V2: PASS total={len(records)} direct={direct} strong_related={related} ratings=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
