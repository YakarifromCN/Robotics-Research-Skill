"""安全 JSON、规范序列化与摘要工具。

Safe JSON loading, canonical serialization, and digest utilities.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable


class JsonIntegrityError(ValueError):
    """表示 JSON 含重复键、非有限常量或其他完整性错误。

    Signal duplicate keys, non-finite constants, or another JSON integrity error.
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
    """读取严格 JSON，拒绝重复键与 NaN/Infinity。

    Load strict JSON, rejecting duplicate keys and NaN/Infinity.
    """

    source = Path(path)
    return json.loads(
        source.read_text(encoding="utf-8"),
        object_pairs_hook=_unique_object,
        parse_constant=_reject_constant,
    )


def canonical_bytes(value: Any) -> bytes:
    """返回稳定、禁止非有限数的 UTF-8 JSON 字节。

    Return stable UTF-8 JSON bytes with non-finite numbers forbidden.
    """

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_value(value: Any) -> str:
    """计算规范 JSON 的带前缀 SHA-256。

    Compute a prefixed SHA-256 over canonical JSON.
    """

    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: str | Path) -> str:
    """计算文件的带前缀 SHA-256。

    Compute a prefixed SHA-256 over a file.
    """

    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


def finite_number(value: Any) -> bool:
    """仅接受非布尔的有限整数或浮点数。

    Accept only finite, non-Boolean integers or floats.
    """

    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def write_json(path: str | Path, value: Any) -> None:
    """以可读格式写出标准 JSON，并拒绝非有限数。

    Write readable standard JSON while rejecting non-finite numbers.
    """

    Path(path).write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )

