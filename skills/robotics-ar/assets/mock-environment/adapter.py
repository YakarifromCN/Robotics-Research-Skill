#!/usr/bin/env python3
"""提供确定性 mock environment，不连接外部设备。

Provide a deterministic mock environment with no external-device connection.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
ARTIFACTS = ROOT / "artifacts"


def emit(value: dict) -> None:
    """输出单个 JSON 对象。 / Emit one JSON object."""

    print(json.dumps(value, sort_keys=True, separators=(",", ":")))


def main() -> int:
    """运行 mock command。 / Run a mock command."""

    command = sys.argv[1] if len(sys.argv) > 1 else ""
    RESULTS.mkdir(exist_ok=True)
    ARTIFACTS.mkdir(exist_ok=True)
    if command == "capabilities":
        emit({"status": "PASS", "capabilities": ["mock", "finite-results", "idempotent-stop"]})
    elif command == "health-check":
        emit({"status": "PASS", "health": "ok"})
    elif command in {"minimal-rollout", "run-batch"}:
        (RESULTS / "latest.json").write_text(json.dumps({"status": "PASS", "value": 1.0}) + "\n", encoding="utf-8")
        (ARTIFACTS / "latest.receipt").write_text("mock-result\n", encoding="utf-8")
        emit({"status": "PASS", "value": 1.0})
    elif command == "collect-results":
        emit({"status": "PASS", "results": [{"value": 1.0}]})
    elif command == "stop":
        emit({"status": "PASS", "stopped": True})
    else:
        emit({"status": "FAIL", "error": "unknown command"})
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
