"""提供安全路径和 fsync 原子写入。

Provide safe paths and fsync-backed atomic writes.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from .canonical import canonical_bytes, ensure_finite

_hidden_authorized = ContextVar("hidden_directories_authorized", default=False)
_reports_requested = ContextVar("report_files_requested", default=False)


@contextmanager
def output_policy(*, allow_hidden_directories=False, reports_requested=False):
    """仅当前调用的显式用户授权。 / Explicit user authorization scoped to this invocation only."""
    hidden = _hidden_authorized.set(allow_hidden_directories is True)
    reports = _reports_requested.set(reports_requested is True)
    try:
        yield
    finally:
        _reports_requested.reset(reports)
        _hidden_authorized.reset(hidden)


def report_files_requested():
    """报告必须由用户请求。 / Report files require a user request."""
    return _reports_requested.get()


def optional_report_bytes(path, data):
    """不以格式变化绕过报告禁令。 / Report opt-in applies regardless of file format."""
    if report_files_requested():
        atomic_write_bytes(path, data)


class AtomicIOError(ValueError):
    """原子 I/O 失败。 / Raised for atomic I/O failures."""


def visible_directory(path: Path | str) -> Path:
    """禁止新建隐藏目录，保留既有目录。 / Reject new hidden directories; preserve existing ones."""
    target = Path(path).absolute()
    for directory in (target, *target.parents):
        if directory.name.startswith('.') and not directory.is_dir() and not _hidden_authorized.get():
            raise AtomicIOError(f"new hidden directory forbidden: {directory}")
    return target


def runtime_root(project_root: Path | str) -> Path:
    """新会话可见，旧会话原位兼容。 / Visible new sessions, in-place legacy compatibility."""
    project = Path(project_root).resolve()
    current, legacy = project / "robotics-ar", project / ".robotics-ar"
    if current.exists() and legacy.exists():
        raise AtomicIOError("both robotics-ar and .robotics-ar exist; reconcile explicitly before writing")
    selected = legacy if legacy.is_dir() else current
    return contained_path(project, selected)


def project_output_directory(root: Path | str, candidate: Path | str) -> Path:
    """输出留在项目内且不创建隐藏目录。 / Keep outputs in-project without new hidden directories."""
    base = Path(root).resolve()
    raw = Path(candidate)
    visible_directory(raw if raw.is_absolute() else base / raw)
    return visible_directory(contained_path(base, candidate))


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
    visible_directory(target.parent).mkdir(parents=True, exist_ok=True)
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
