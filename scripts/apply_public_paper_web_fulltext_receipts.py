#!/usr/bin/env python3
"""Apply manually verified public-web full-text receipts to the source manifest."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
manifest_path = ROOT / "corpus/public-paper-fulltext-manifest.v1.json"
receipt_path = ROOT / "corpus/public-paper-web-fulltext-receipts.v1.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
by_id = {row["paper_id"]: row for row in receipt["records"]}

for row in manifest["records"]:
    web = by_id.get(row["paper_id"])
    if not web or row.get("status") == "DOWNLOADED":
        continue
    row["status"] = "WEB_FULLTEXT_VERIFIED"
    row["source_url"] = web["url"]
    row["web_receipt"] = "corpus/public-paper-web-fulltext-receipts.v1.json"
    row["web_access"] = web["access"]
    row["resolution_note"] = (
        "Public full text verified through an interactive/indexed web source; "
        "host blocks or does not support unattended local PDF caching."
    )

statuses = sorted({row["status"] for row in manifest["records"]})
manifest["status_counts"] = {
    status: sum(row["status"] == status for row in manifest["records"])
    for status in statuses
}
manifest["usable_fulltext_count"] = sum(
    row["status"] in {"DOWNLOADED", "WEB_FULLTEXT_VERIFIED"}
    for row in manifest["records"]
)
manifest["usable_fulltext_contract"] = (
    "DOWNLOADED is locally hash-verified; WEB_FULLTEXT_VERIFIED is publicly "
    "readable but not represented as a cached PDF."
)
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"PUBLIC_FULLTEXT_RECEIPTS_APPLIED: usable={manifest['usable_fulltext_count']}")
