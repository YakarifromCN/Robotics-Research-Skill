#!/usr/bin/env python3
"""Extract local public-paper PDFs into an ignored text cache and update manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=ROOT / "corpus/public-paper-fulltext-manifest.v1.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "corpus/extracted")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for record in manifest["records"]:
        if record.get("status") != "DOWNLOADED" or not record.get("local_path"):
            record["text_status"] = "NO_PDF"
            continue
        pdf = ROOT / record["local_path"]
        text_path = args.output_dir / f"{record['paper_id']}.txt"
        result = subprocess.run(
            ["pdftotext", "-layout", str(pdf), str(text_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode:
            record["text_status"] = "EXTRACTION_FAILED"
            record["text_error"] = (result.stderr or result.stdout).strip()[:500]
            continue
        record["text_status"] = "EXTRACTED"
        record["text_path"] = str(text_path.relative_to(ROOT))
        record["text_bytes"] = text_path.stat().st_size
        record["text_sha256"] = digest(text_path)
        record["extraction_tool"] = "pdftotext -layout"
        record["extracted_at"] = now()

    manifest["text_extraction"] = {
        "tool": "pdftotext -layout",
        "updated_at": now(),
        "status_counts": {
            status: sum(1 for record in manifest["records"] if record.get("text_status") == status)
            for status in sorted({record.get("text_status") for record in manifest["records"]})
        },
        "cache_policy": "Extracted text is local ignored cache; manifest contains hashes and paths only",
    }
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(args.manifest), "text_extraction": manifest["text_extraction"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
