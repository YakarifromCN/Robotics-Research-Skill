"""Validate the constrained public robotics paper corpus.

The corpus is intentionally a hard-gated infrastructure artifact: it must
contain 100 records, an exact 50/50 journal/conference split, conference
presentation evidence at oral level or above, award evidence for more than
half of the records, and balanced primary-axis coverage across the eight
robotics submanifold axes.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


AXES = ("E", "P", "C", "L", "D", "H", "A", "S")
ORAL_OR_ABOVE = {"oral", "spotlight", "best_paper", "award"}
RECOGNIZED_AWARD_STATUSES = {"winner", "finalist", "nominee", "award"}


def load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("index must be a JSON object")
    return value


def validate(index: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if index.get("schema_version") != "robotics-public-corpus.v2":
        errors.append("schema_version must be robotics-public-corpus.v2")
    constraints = index.get("selection_constraints")
    if not isinstance(constraints, dict):
        errors.append("selection_constraints must be an object")
        constraints = {}
    expected = {
        "total": 100,
        "journal_count": 50,
        "conference_count": 50,
        "min_award_recognition_count": 51,
        "conference_min_presentation_rank": "oral",
        "primary_axis_max_imbalance": 1,
    }
    for key, value in expected.items():
        if constraints.get(key) != value:
            errors.append(f"selection_constraints.{key} must equal {value!r}")

    records = index.get("records")
    if not isinstance(records, list):
        errors.append("records must be an array")
        return errors
    if len(records) != 100:
        errors.append(f"records must contain exactly 100 items, got {len(records)}")

    ids: set[str] = set()
    kind_counts = {"journal": 0, "conference": 0}
    axis_counts = {axis: 0 for axis in AXES}
    award_count = 0
    for index_no, record in enumerate(records):
        prefix = f"records[{index_no}]"
        if not isinstance(record, dict):
            errors.append(f"{prefix} must be an object")
            continue
        paper_id = record.get("paper_id")
        if not isinstance(paper_id, str) or not paper_id:
            errors.append(f"{prefix}.paper_id must be nonempty")
        elif paper_id in ids:
            errors.append(f"duplicate paper_id: {paper_id}")
        else:
            ids.add(paper_id)
        for key in ("title", "venue", "year", "venue_kind", "primary_axis", "submanifold_axes"):
            if key not in record:
                errors.append(f"{prefix}.{key} is required")
        kind = record.get("venue_kind")
        if kind not in kind_counts:
            errors.append(f"{prefix}.venue_kind must be journal or conference")
        else:
            kind_counts[kind] += 1
        axis = record.get("primary_axis")
        if axis not in AXES:
            errors.append(f"{prefix}.primary_axis must be one of {AXES}")
        else:
            axis_counts[axis] += 1

        vector = record.get("submanifold_axes")
        if not isinstance(vector, dict) or set(vector) != set(AXES):
            errors.append(f"{prefix}.submanifold_axes must contain exactly {AXES}")
        elif any(
            isinstance(vector[axis], bool) or not isinstance(vector[axis], int) or not 0 <= vector[axis] <= 3
            for axis in AXES
        ):
            errors.append(f"{prefix}.submanifold_axes values must be integers in [0, 3]")
        elif vector.get(axis) != 3:
            errors.append(f"{prefix}.primary_axis must have loading 3")

        preprint = record.get("preprint")
        if not isinstance(preprint, dict) or not isinstance(preprint.get("url"), str) or not preprint["url"].startswith("http"):
            errors.append(f"{prefix}.preprint.url must be a public URL")
        final = record.get("final_publication")
        if not isinstance(final, dict) or not isinstance(final.get("url"), str) or not final["url"].startswith("http"):
            errors.append(f"{prefix}.final_publication.url must be a public URL")

        award = record.get("award")
        qualifies = isinstance(award, dict) and award.get("qualifies_for_quota") is True
        if qualifies:
            award_count += 1
            if award.get("status") not in RECOGNIZED_AWARD_STATUSES:
                errors.append(f"{prefix}.award.status is not recognized")
            if not isinstance(award.get("source_url"), str) or not award["source_url"].startswith("http"):
                errors.append(f"{prefix}.award.source_url must be a public URL")
        elif award is not None and not isinstance(award, dict):
            errors.append(f"{prefix}.award must be an object when present")

        if kind == "conference":
            presentation = record.get("presentation")
            if not isinstance(presentation, dict):
                errors.append(f"{prefix}.presentation is required for conferences")
            else:
                level = presentation.get("level")
                if level not in ORAL_OR_ABOVE:
                    errors.append(f"{prefix}.presentation.level must be oral or above")
                if not isinstance(presentation.get("source_url"), str) or not presentation["source_url"].startswith("http"):
                    errors.append(f"{prefix}.presentation.source_url must be a public URL")

    if kind_counts != {"journal": 50, "conference": 50}:
        errors.append(f"venue kind counts must be 50/50, got {kind_counts}")
    if award_count < 51:
        errors.append(f"award-recognized records must exceed 50, got {award_count}")
    if axis_counts and max(axis_counts.values()) - min(axis_counts.values()) > 1:
        errors.append(f"primary-axis coverage imbalance exceeds 1: {axis_counts}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "index",
        nargs="?",
        default=os.environ.get("ROBOTICS_CORPUS_PATH", "corpus/public-paper-index.json"),
        help="local-only corpus path; used by the explicit offline audit",
    )
    args = parser.parse_args()
    errors = validate(load(args.index))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    index = load(args.index)
    records = index["records"]
    counts = {kind: sum(item.get("venue_kind") == kind for item in records) for kind in ("journal", "conference")}
    axes = {axis: sum(item.get("primary_axis") == axis for item in records) for axis in AXES}
    awards = sum(item.get("award", {}).get("qualifies_for_quota") is True for item in records)
    print(f"PUBLIC_PAPER_INDEX: PASS total={len(records)} kinds={counts} awards={awards} primary_axes={axes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
