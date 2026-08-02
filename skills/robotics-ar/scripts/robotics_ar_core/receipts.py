"""生成文件、目录和 invocation 的确定性 receipt。

Create deterministic receipts for files, directories, and invocations.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional

from .canonical import sha256_bytes, sha256_obj
from .models import utc_now


def file_sha256(path: Path | str) -> str:
    """计算文件 SHA-256。 / Compute a file SHA-256."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_fingerprint(root: Path | str, *, include: Optional[Iterable[str]] = None) -> str:
    """按相对 POSIX 路径和内容计算目录指纹。

    Compute a directory fingerprint from relative POSIX paths and contents.
    """

    root_path = Path(root).resolve()
    allowed = set(include or [])
    rows = []
    for path in sorted(item for item in root_path.rglob("*") if item.is_file()):
        relative = path.relative_to(root_path).as_posix()
        if allowed and relative not in allowed:
            continue
        rows.append(f"{relative}\0{file_sha256(path)}")
    return sha256_bytes("\n".join(rows).encode("utf-8"))


def artifact_receipt(path: Path | str, *, schema_version: str = "artifact-receipt.v1", status: str = "READY", extra: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """创建通用 artifact receipt。 / Create a generic artifact receipt."""

    target = Path(path)
    if not target.exists() or not target.is_file():
        raise FileNotFoundError(str(target))
    receipt: Dict[str, Any] = {
        "schema_version": schema_version,
        "path": target.as_posix(),
        "sha256": file_sha256(target),
        "status": status,
        "created_at": utc_now(),
    }
    if extra:
        receipt.update(dict(extra))
    receipt["receipt_sha256"] = sha256_obj({key: value for key, value in receipt.items() if key != "receipt_sha256"})
    return receipt
