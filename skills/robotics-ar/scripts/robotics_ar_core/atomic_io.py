"""提供安全路径和 fsync 原子写入。

Provide safe paths and fsync-backed atomic writes.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any

from .canonical import canonical_bytes, ensure_finite


class AtomicIOError(ValueError):
    """原子 I/O 失败。 / Raised for atomic I/O failures."""


def contained_path(root: Path, candidate: Path | str, *, allow_missing: bool = True) -> Path:
    """解析 candidate，并确保其位于 root 内。

    Resolve a candidate and ensure that it remains contained under root.
    """

    root_resolved = Path(root).resolve()
    candidate_path = Path(candidate)
    if not candidate_path.is_absolute():
        candidate_path = root_resolved / candidate_path
    resolved = candidate_path.resolve(strict=not allow_missing)
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise AtomicIOError(f"path escapes root: {candidate}") from exc
    return resolved


def atomic_write_bytes(path: Path | str, data: bytes) -> None:
    """以临时文件、fsync 和 replace 写入字节。

    Write bytes using a temporary file, fsync, and atomic replace.
    """

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=str(target.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        try:
            directory_fd = os.open(str(target.parent), os.O_DIRECTORY)
        except (AttributeError, OSError):
            directory_fd = None
        if directory_fd is not None:
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def atomic_write_json(path: Path | str, value: Any) -> None:
    """以 canonical JSON 原子写入对象。

    Atomically write an object as canonical JSON.
    """

    atomic_write_bytes(path, canonical_bytes(value) + b"\n")


def read_json(path: Path | str) -> Any:
    """读取 JSON 并拒绝非有限数。

    Read JSON and reject non-finite numbers.
    """

    value = json.loads(Path(path).read_text(encoding="utf-8"))
    ensure_finite(value)
    return value
