#!/usr/bin/env python3
"""校验结构化 Engineering Handoff 的恢复语义。

Validate recovery semantics in a structured Engineering Handoff.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from validate_engineering_artifacts import load_frontmatter


def validate(path: Path) -> list[str]:
    try:
        data, body = load_frontmatter(path)
    except (OSError, ValueError) as exc:
        return [str(exc)]
    errors: list[str] = []
    body_lines = [line.strip() for line in body.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if not any(not (line.startswith("<") and line.endswith(">")) for line in body_lines):
        errors.append("handoff Markdown body must contain recovery context")
    if data.get("artifact") != "HANDOFF":
        errors.append("artifact must be HANDOFF")
    status = data.get("status")
    if status not in {"DONE", "PARTIAL", "BLOCKED", "NO_CODE_CHANGE"}:
        errors.append("invalid handoff status")
    changed = data.get("changed_files")
    if not isinstance(changed, list) or any(not isinstance(item, str) or not item.strip() for item in changed):
        errors.append("changed_files must be a string list")
    tests = data.get("tests")
    if not isinstance(tests, list) or any(not isinstance(row, dict) or not row.get("command") or row.get("result") not in {"PASS", "FAIL"} or row.get("executed") is not True or type(row.get("exit_code")) is not int or not re.fullmatch(r"[0-9a-f]{64}", str(row.get("receipt_sha256", ""))) for row in tests):
        errors.append("tests must contain executed commands, exit codes, results, and receipts")
    if re.fullmatch(r"[0-9a-f]{64}", str(data.get("task_contract_sha256", ""))) is None:
        errors.append("task_contract_sha256 is required")
    resume = data.get("resume_command")
    if status in {"PARTIAL", "BLOCKED"} and (not isinstance(resume, str) or not resume.strip()):
        errors.append("PARTIAL/BLOCKED requires a resume command")
    if status in {"DONE", "NO_CODE_CHANGE"} and resume not in {None, ""}:
        errors.append("DONE/NO_CODE_CHANGE resume command must be null")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("handoff", type=Path)
    args = parser.parse_args()
    errors = validate(args.handoff)
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
