#!/usr/bin/env python3
"""校验独立投稿适配快照。 / Validate a separate target-fit snapshot."""

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common.canonical_json import load_json


POLICY_FIELDS = (
    "scope",
    "page_limit",
    "anonymity",
    "template",
    "pdf_preflight",
    "supplementary_video",
    "artifact_links",
    "concurrent_submission",
    "conflicts",
)
STATUSES = {"VERIFIED", "UNVERIFIED", "NOT_APPLICABLE", "STALE"}
REFRESH_STATES = {"NOT_NEEDED", "REFRESHED", "NETWORK_BLOCKED", "OFFICIAL_SOURCE_MISSING"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot")
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()
    x = load_json(args.snapshot)
    errors = []
    if x.get("schema_version") != "robotics-target-fit.v2":
        errors.append("wrong schema")
    sources = x.get("sources")
    if not isinstance(sources, list):
        errors.append("sources must be an array")
        sources = []
    source_ids = {item.get("source_id") for item in sources if isinstance(item, dict) and item.get("source_id")}
    source_records = {item.get("source_id"): item for item in sources if isinstance(item, dict) and item.get("source_id")}
    coverage = x.get("policy_coverage")
    if not isinstance(coverage, dict) or set(coverage) != set(POLICY_FIELDS):
        errors.append("policy_coverage must contain the complete current-policy matrix")
        coverage = {}
    for field in POLICY_FIELDS:
        item = coverage.get(field)
        if not isinstance(item, dict) or set(item) != {"status", "source_ids"}:
            errors.append(f"policy_coverage.{field} must contain status and source_ids")
            continue
        if item.get("status") not in STATUSES:
            errors.append(f"policy_coverage.{field}.status unsupported")
        if not isinstance(item.get("source_ids"), list):
            errors.append(f"policy_coverage.{field}.source_ids must be an array")
        elif item.get("status") == "VERIFIED":
            if not item["source_ids"]:
                errors.append(f"verified policy field lacks official source: {field}")
            for source_id in item["source_ids"]:
                if source_id not in source_ids:
                    errors.append(f"unknown source_id {source_id!r} for policy field {field}")
                else:
                    source = source_records[source_id]
                    if source.get("official") is not True or not source.get("url") or not source.get("checked_at"):
                        errors.append(f"verified policy source {source_id!r} must include official=true, url, and checked_at")
    refresh_state = x.get("refresh_state")
    if refresh_state not in REFRESH_STATES:
        errors.append("invalid refresh_state")
    if args.fresh:
        try:
            expiry = dt.datetime.fromisoformat(str(x["expires_at"]).replace("Z", "+00:00"))
            now = dt.datetime.now(dt.timezone.utc)
            if expiry < now:
                errors.append("snapshot expired")
        except Exception:
            errors.append("invalid expires_at")
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    raise SystemExit(bool(errors))


if __name__ == "__main__":
    main()
