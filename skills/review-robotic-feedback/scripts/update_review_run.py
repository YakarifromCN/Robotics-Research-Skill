#!/usr/bin/env python3
"""更新评审运行清单，不参与科学判断。

Update the review-run manifest without making scientific decisions.  This keeps
agent heartbeats, one repair attempt, report hashes, and terminal state visible
to the orchestrator.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
try:
    from common.canonical_json import load_json, sha256_file, write_json
except ModuleNotFoundError:  # 独立安装兼容 / standalone installed Skill
    from review_runtime import load_json, sha256_file, write_json


STATUSES = {"PENDING", "RUNNING", "VALIDATING", "RETRYING", "COMPLETE", "FAILED"}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_state")
    parser.add_argument("reviewer")
    parser.add_argument("status", choices=sorted(STATUSES))
    parser.add_argument("--report")
    parser.add_argument("--validation", choices=("PENDING", "PASS", "FAIL"), default=None)
    parser.add_argument("--error")
    args = parser.parse_args()
    path = Path(args.run_state)
    resolved = path.resolve()
    if resolved.name != "run-state.json" or resolved.parent.name != "jsons" or not resolved.parent.parent.name.startswith("review-"):
        raise SystemExit("run state must be reviews/review-<timestamp>/jsons/run-state.json")
    state = load_json(path)
    if state.get("schema_version") != "robotics-review-run.v1":
        raise SystemExit("wrong run-state schema")
    agents = state.get("agents")
    if not isinstance(agents, dict) or args.reviewer not in agents:
        raise SystemExit(f"unknown reviewer: {args.reviewer}")
    item = agents[args.reviewer]
    previous = item.get("status")
    if previous == "COMPLETE" and args.status not in {"COMPLETE"}:
        raise SystemExit("completed reviewer cannot move back without a new run")
    if args.status == "RETRYING":
        attempt = int(item.get("attempt") or 0) + 1
        if attempt > 2:
            raise SystemExit("only one automatic schema-repair retry is allowed")
        item["attempt"] = attempt
    elif args.status in {"RUNNING", "VALIDATING"} and not item.get("attempt"):
        item["attempt"] = 1
    item["status"] = args.status
    item["updated_at"] = now_iso()
    if args.validation:
        item["validation"] = args.validation
    if args.report:
        report_path = Path(args.report).resolve()
        item["report_path"] = str(report_path)
        item["report_sha256"] = sha256_file(report_path)
    if args.error:
        item["error"] = args.error
    state["updated_at"] = now_iso()
    write_json(path, state)


if __name__ == "__main__":
    main()
