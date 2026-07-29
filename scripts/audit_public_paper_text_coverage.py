#!/usr/bin/env python3
"""Audit extracted-paper coverage without copying paper text into tracked JSON."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "corpus/public-paper-fulltext-manifest.v1.json"
OUTPUT = ROOT / "corpus/public-paper-text-coverage.v1.json"
SECTION_PATTERNS = {
    "abstract": re.compile(r"\babstract\b", re.I),
    "introduction": re.compile(r"\b(?:i\.?\s*)?introduction\b", re.I),
    "method": re.compile(r"\b(?:method|approach|methodology|model)\b", re.I),
    "experiment": re.compile(r"\b(?:experiment|evaluation|results)\b", re.I),
    "conclusion": re.compile(r"\b(?:conclusion|discussion)\b", re.I),
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def audit_text(path: Path) -> dict:
    sha = hashlib.sha256()
    line_count = 0
    char_count = 0
    section_hits: dict[str, int] = {key: 0 for key in SECTION_PATTERNS}
    with path.open("rb") as raw:
        for raw_line in raw:
            sha.update(raw_line)
            line = raw_line.decode("utf-8", errors="ignore")
            line_count += 1
            char_count += len(line)
            for key, pattern in SECTION_PATTERNS.items():
                if pattern.search(line):
                    section_hits[key] += 1
    if char_count < 1000:
        status = "TEXT_TOO_SHORT"
    elif section_hits["abstract"] and (section_hits["method"] or section_hits["experiment"]):
        status = "TEXT_BACKED_WITH_SECTION_MARKERS"
    else:
        status = "TEXT_BACKED_SECTION_MARKERS_INCOMPLETE"
    return {
        "status": status,
        "line_count": line_count,
        "char_count": char_count,
        "text_sha256": sha.hexdigest(),
        "section_marker_counts": section_hits,
        "extraction_requirement": "LLM_STAGE1_STAGE2_WITH_FIELD_LEVEL_PROVENANCE",
    }


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    records = []
    for source in manifest["records"]:
        entry = {
            "paper_id": source["paper_id"],
            "title": source.get("title"),
            "source_status": source.get("status"),
            "source_url": source.get("source_url"),
            "local_path": source.get("text_path"),
            "source_sha256": source.get("sha256"),
            "text_status": source.get("text_status", "NO_TEXT"),
        }
        if source.get("text_path"):
            path = ROOT / source["text_path"]
            entry["coverage"] = audit_text(path) if path.exists() else {"status": "MISSING_CACHE"}
        else:
            entry["coverage"] = {"status": "NO_TEXT"}
        records.append(entry)
    records.sort(key=lambda item: item["paper_id"])
    statuses = sorted({item["coverage"]["status"] for item in records})
    output = {
        "schema_version": "robotics-public-paper-text-coverage.v1",
        "generated_at": now(),
        "source_manifest": "corpus/public-paper-fulltext-manifest.v1.json",
        "record_count": len(records),
        "status_counts": {status: sum(item["coverage"]["status"] == status for item in records) for status in statuses},
        "honesty_boundary": "Coverage and section markers do not equal semantic Stage-1/Stage-2 extraction; source locators remain required.",
        "records": records,
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "record_count": len(records), "status_counts": output["status_counts"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
