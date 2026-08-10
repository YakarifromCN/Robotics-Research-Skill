#!/usr/bin/env python3
"""执行 0–3 个冻结工程测试并生成绑定回执。

Execute the 0-3 frozen Engineering tests and emit bound receipts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import subprocess
from pathlib import Path

from validate_engineering_artifacts import load_frontmatter


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def run(task_path: Path, workspace: Path, timeout: int = 300) -> list[dict]:
    task, _ = load_frontmatter(task_path)
    rows = task.get("tests")
    if not isinstance(rows, list) or len(rows) > 3:
        raise ValueError("Task tests must contain 0-3 frozen commands")
    receipts = []
    for index, row in enumerate(rows):
        command = row.get("command") if isinstance(row, dict) else None
        if not isinstance(command, str) or not command.strip():
            raise ValueError(f"tests[{index}] has no command")
        completed = subprocess.run(shlex.split(command), cwd=workspace, text=True, capture_output=True, timeout=timeout, check=False)
        result = "PASS" if completed.returncode == 0 else "FAIL"
        bound = {"command": command, "result": result, "exit_code": completed.returncode}
        receipts.append({
            **bound,
            "executed": True,
            "receipt_sha256": hashlib.sha256(json.dumps(bound, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "stdout_sha256": _sha(completed.stdout),
            "stderr_sha256": _sha(completed.stderr),
            "runner": "run_engineering_tests.py",
        })
    return receipts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("task", type=Path)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    try:
        receipts = run(args.task, args.workspace.resolve(), args.timeout)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    payload = json.dumps({"schema_version": "robotics-engineering-test-receipts.v1", "tests": receipts}, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0 if all(row["result"] == "PASS" for row in receipts) else 1


if __name__ == "__main__":
    raise SystemExit(main())
