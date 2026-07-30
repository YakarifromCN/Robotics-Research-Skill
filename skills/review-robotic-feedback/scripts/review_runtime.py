"""评审 Skill 的独立运行时兼容层。

Standalone runtime compatibility helpers for the review Skill.  The complete
repository uses ``common/`` as the canonical implementation; this module keeps
an installed copy usable without silently weakening JSON or evidence checks.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


class JsonIntegrityError(ValueError):
    """拒绝重复键、NaN/Infinity 和非标准 JSON。

    Reject duplicate keys, NaN/Infinity, and non-standard JSON.
    """


def _reject_constant(value: str) -> None:
    raise JsonIntegrityError(f"non-standard numeric constant is forbidden: {value}")


def _unique_object(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise JsonIntegrityError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: str | Path) -> Any:
    """读取严格 JSON。 / Load strict JSON."""
    return json.loads(
        Path(path).read_text(encoding="utf-8"),
        object_pairs_hook=_unique_object,
        parse_constant=_reject_constant,
    )


def write_json(path: str | Path, value: Any) -> None:
    """写出拒绝非有限数的 JSON。 / Write JSON while rejecting non-finite numbers."""
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def sha256_file(path: str | Path) -> str:
    """计算带前缀的文件摘要。 / Compute a prefixed file digest."""
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256_value(value: Any) -> str:
    """计算规范对象摘要。 / Compute a digest over canonical JSON."""
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


@dataclass
class Findings:
    """收集 validator 发现项。 / Collect validator findings."""

    items: list[dict[str, Any]] = field(default_factory=list)

    def add(self, level: str, code: str, path: str, message: str) -> None:
        self.items.append({"level": level, "code": code, "path": path, "message": message})

    def fail(self, code: str, path: str, message: str) -> None:
        self.add("fail", code, path, message)

    def warn(self, code: str, path: str, message: str) -> None:
        self.add("warn", code, path, message)

    def info(self, code: str, path: str, message: str) -> None:
        self.add("info", code, path, message)

    def count(self, level: str) -> int:
        return sum(item["level"] == level for item in self.items)

    @property
    def consistent(self) -> bool:
        return self.count("fail") == 0

    def report(self, schema: str, terminal_state: str | None, handoff_ready: bool) -> dict[str, Any]:
        return {
            "schema": schema,
            "schema_valid": self.consistent,
            "contract_consistent": self.consistent,
            "handoff_ready": handoff_ready and self.consistent,
            "terminal_state": terminal_state,
            "counts": {level: self.count(level) for level in ("fail", "warn", "info")},
            "findings": self.items,
        }


def validate_finite_tree(value: Any, findings: Findings, path: str = "$") -> None:
    """递归检查有限数。 / Recursively validate finite numeric values."""
    if isinstance(value, float) and not finite_number(value):
        findings.fail("NONFINITE_NUMBER", path, "numeric values must be finite")
    elif isinstance(value, dict):
        for key, child in value.items():
            validate_finite_tree(child, findings, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_finite_tree(child, findings, f"{path}[{index}]")
