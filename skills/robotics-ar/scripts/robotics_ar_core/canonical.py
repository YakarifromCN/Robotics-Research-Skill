"""实现确定性 JSON、有限数和 SHA-256。

Implement deterministic JSON, finite-number checks, and SHA-256 helpers.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any


class CanonicalError(ValueError):
    """规范化输入非法。 / Raised when a value cannot be canonicalized."""


def ensure_finite(value: Any, path: str = "$", *, _skip_domain_payload: bool = False) -> None:
    """递归拒绝 NaN/Infinity，并允许 JSON 原生类型。

    Recursively reject NaN/Infinity and accept only JSON-native values.
    """

    if isinstance(value, bool) or value is None or isinstance(value, str):
        return
    if isinstance(value, int):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CanonicalError(f"non-finite number at {path}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            ensure_finite(item, f"{path}[{index}]", _skip_domain_payload=_skip_domain_payload)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalError(f"non-string key at {path}")
            ensure_finite(item, f"{path}.{key}", _skip_domain_payload=_skip_domain_payload)
        return
    raise CanonicalError(f"unsupported JSON value at {path}: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    """返回排序 key、紧凑分隔符和 UTF-8-safe 的 JSON 字符串。

    Return sorted-key, compact, UTF-8-safe JSON text.
    """

    ensure_finite(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def canonical_bytes(value: Any) -> bytes:
    """返回 canonical JSON 的 UTF-8 字节。

    Return UTF-8 bytes for canonical JSON.
    """

    return canonical_json(value).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    """计算字节 SHA-256。 / Compute SHA-256 for bytes."""

    return hashlib.sha256(value).hexdigest()


def sha256_obj(value: Any) -> str:
    """计算任意 JSON 对象的 canonical SHA-256。

    Compute canonical SHA-256 for a JSON object.
    """

    return sha256_bytes(canonical_bytes(value))
