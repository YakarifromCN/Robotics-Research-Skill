"""稳定科研对象 ID 的公共定义。

Shared definitions for stable research-object identifiers.
"""

from __future__ import annotations

import re


ID_PATTERNS = {
    "claim": re.compile(r"^C\d{3,}$"),
    "variable": re.compile(r"^V\d{3,}$"),
    "metric": re.compile(r"^M\d{3,}$"),
    "condition": re.compile(r"^COND-[A-Z0-9][A-Z0-9_-]*$"),
    "experiment": re.compile(r"^X\d{3,}$"),
    "analysis": re.compile(r"^A\d{3,}$"),
    "trial": re.compile(r"^T\d{3,}$"),
    "result": re.compile(r"^R\d{3,}$"),
    "figure": re.compile(r"^F\d{3,}$"),
    "number": re.compile(r"^N\d{3,}$"),
    "evidence": re.compile(r"^E\d{3,}$"),
    "control": re.compile(r"^NC\d{3,}$"),
    "requirement": re.compile(r"^REQ\d{3,}$"),
}


def valid_id(value: object, kind: str) -> bool:
    """检查值是否符合具名稳定 ID 类型。

    Check whether a value matches a named stable-ID type.
    """

    pattern = ID_PATTERNS.get(kind)
    return isinstance(value, str) and pattern is not None and pattern.fullmatch(value) is not None

