#!/usr/bin/env python3
"""Validate that every core-corpus paper has a usable full-text receipt."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads(
    (ROOT / "corpus/public-paper-fulltext-manifest.v1.json").read_text(encoding="utf-8")
)
web = json.loads(
    (ROOT / "corpus/public-paper-web-fulltext-receipts.v1.json").read_text(encoding="utf-8")
)
records = manifest["records"]
web_ids = [row["paper_id"] for row in web["records"]]
assert len(records) == 100
assert len(web_ids) == len(set(web_ids)) == 19
assert manifest["usable_fulltext_count"] == 100
assert all(row["status"] in {"DOWNLOADED", "WEB_FULLTEXT_VERIFIED"} for row in records)
assert {row["paper_id"] for row in records if row["status"] == "WEB_FULLTEXT_VERIFIED"} == set(web_ids)
print(
    "PUBLIC_PAPER_FULLTEXT_RECEIPTS: PASS "
    f"local={manifest['status_counts'].get('DOWNLOADED', 0)} "
    f"web={manifest['status_counts'].get('WEB_FULLTEXT_VERIFIED', 0)} usable=100"
)
