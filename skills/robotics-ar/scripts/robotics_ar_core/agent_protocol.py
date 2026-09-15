"""实现隔离执行 Agent、允许路径和 receipt 协议。

Implement isolated execution-agent roles, allowed paths, and receipt contracts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import threading
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .atomic_io import contained_path
from .canonical import sha256_obj
from .models import utc_now
from .receipts import file_sha256, tree_fingerprint


class AgentProtocolError(RuntimeError):
    """Agent 权限或 receipt 违反协议。 / Raised for agent protocol violations."""


ROLE_CONTRACTS: Mapping[str, Mapping[str, Any]] = {
    "Code Agent": {
        "writes": ("implementation", "tests"),
        "reads": ("task", "contracts", "tests"),
        "forbidden": ("raw", "research", "claims", "charter", "environment"),
    },
    "Test Agent": {
        "writes": ("test-receipts",),
        "reads": ("implementation", "tests", "task"),
        "forbidden": ("production", "raw", "research", "claims", "charter"),
    },
    "Environment Runner": {
        "writes": ("raw", "traces", "environment-receipts"),
        "reads": ("task", "environment", "implementation"),
        "forbidden": ("code", "research", "claims", "charter", "budget"),
    },
    "Data Analyst": {
        "writes": ("analysis-receipts",),
        "reads": ("raw", "task", "frozen-metrics"),
        "forbidden": ("raw-write", "code", "research", "claims", "charter", "budget"),
    },
    "Dynamic Expert": {
        "writes": ("expert-receipts",),
        "reads": ("unknown", "allowed-evidence"),
        "forbidden": ("code", "raw", "claims", "charter", "budget"),
    },
}

VALID_ROLES = frozenset(ROLE_CONTRACTS)


def _relative(root: Path, candidate: Path | str) -> str:
    """返回 root 下的规范相对路径。 / Return a normalized path relative to root."""

    target = contained_path(root, candidate, allow_missing=True)
    return target.relative_to(root.resolve()).as_posix()


def _matches(relative: str, rule: str) -> bool:
    """判断路径是否匹配目录或文件规则。 / Match a path against a file or directory rule."""

    normalized = Path(rule).as_posix().strip("/")
    if normalized in {"", "."}:
        return True
    return relative == normalized or relative.startswith(normalized + "/")


@dataclass(frozen=True)
class PathPolicy:
    """一个 Agent 的 frozen allowed/forbidden path policy。 / Frozen path policy for one Agent."""

    root: Path
    allowed_paths: Tuple[str, ...]
    forbidden_paths: Tuple[str, ...] = ()

    @classmethod
    def create(cls, root: Path | str, *, allowed_paths: Iterable[str], forbidden_paths: Iterable[str] = ()) -> "PathPolicy":
        """规范化路径并拒绝 root 之外的条目。

        Normalize paths and reject entries outside the workspace root.
        """

        root_path = Path(root).resolve()
        allowed = tuple(sorted({_relative(root_path, value) for value in allowed_paths}))
        try:
            forbidden = tuple(sorted({_relative(root_path, value) for value in forbidden_paths}))
        except Exception as exc:
            raise AgentProtocolError("forbidden path escapes workspace root") from exc
        if not allowed:
            raise AgentProtocolError("at least one allowed path is required")
        return cls(root_path, allowed, forbidden)

    def check(self, candidate: Path | str, *, write: bool = False) -> Path:
        """检查读写路径；任何越界或 forbidden 路径均失败。

        Check a read or write path; traversal and forbidden paths always fail.
        """

        try:
            relative = _relative(self.root, candidate)
        except Exception as exc:
            raise AgentProtocolError(str(exc)) from exc
        if any(_matches(relative, rule) for rule in self.forbidden_paths):
            raise AgentProtocolError(f"forbidden path: {relative}")
        if not any(_matches(relative, rule) for rule in self.allowed_paths):
            raise AgentProtocolError(f"path is not allowed: {relative}")
        if write:
            from .atomic_io import visible_directory
            try:
                raw = Path(candidate)
                visible_directory((raw if raw.is_absolute() else self.root / raw).parent)
                visible_directory((self.root / relative).parent)
            except ValueError as exc:
                raise AgentProtocolError(str(exc)) from exc
        return self.root / relative

    def assert_write(self, candidate: Path | str) -> Path:
        """检查写入权限。 / Check write permission."""

        return self.check(candidate, write=True)


class WriterLease:
    """同一工作树最多一个写 Agent 的进程内 lease。

    Enforce at most one writer in a worktree within this runtime.
    """

    _leases: Dict[str, str] = {}
    _lock = threading.Lock()

    def __init__(self, root: Path | str, owner: str) -> None:
        self.root = str(Path(root).resolve())
        self.owner = owner
        self.lease_path = Path(self.root) / ".robotics-ar-writer.lock"
        self.acquired = False

    def acquire(self) -> None:
        """获取唯一写 lease。 / Acquire the unique writer lease."""

        with self._lock:
            current = self._leases.get(self.root)
            if current and current != self.owner:
                raise AgentProtocolError(f"writer lease held by {current}")
            if current == self.owner and self.acquired:
                return
            if self.lease_path.exists() and not self.acquired:
                try:
                    existing = self.lease_path.read_text(encoding="utf-8").strip()
                except OSError:
                    existing = "unknown"
                if existing and existing != self.owner:
                    raise AgentProtocolError(f"writer lease held by {existing}")
                raise AgentProtocolError("writer lease file already exists")
            self.lease_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                descriptor = os.open(str(self.lease_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                    handle.write(self.owner)
                    handle.flush()
                    os.fsync(handle.fileno())
            except FileExistsError as exc:
                raise AgentProtocolError("writer lease file already exists") from exc
            self._leases[self.root] = self.owner
            self.acquired = True

    def release(self) -> None:
        """释放自己的 lease。 / Release this owner's lease."""

        with self._lock:
            if self._leases.get(self.root) == self.owner:
                self._leases.pop(self.root, None)
            if self.acquired and self.lease_path.exists():
                try:
                    if self.lease_path.read_text(encoding="utf-8").strip() == self.owner:
                        self.lease_path.unlink()
                except OSError:
                    pass
            self.acquired = False

    def __enter__(self) -> "WriterLease":
        self.acquire()
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.release()


class RawEvidenceGuard:
    """记录 raw evidence 的指纹并拒绝后续修改。

    Record raw-evidence fingerprints and reject later mutation.
    """

    def __init__(self, raw_root: Path | str) -> None:
        self.raw_root = Path(raw_root).resolve()
        self._fingerprints: Dict[str, str] = {}

    def freeze(self, paths: Iterable[Path | str]) -> Dict[str, str]:
        """冻结文件或目录并返回指纹。 / Freeze files or directories and return fingerprints."""

        result: Dict[str, str] = {}
        for candidate in paths:
            raw_path = Path(candidate)
            if raw_path.is_symlink():
                raise AgentProtocolError(f"symlinked raw artifact is not allowed: {raw_path}")
            path = raw_path.resolve()
            try:
                path.relative_to(self.raw_root)
            except ValueError as exc:
                raise AgentProtocolError(f"raw path escapes root: {path}") from exc
            if path.is_file():
                digest = file_sha256(path)
            elif path.is_dir():
                if any(item.is_symlink() for item in path.rglob("*")):
                    raise AgentProtocolError(f"raw directory contains a symlink: {path}")
                digest = tree_fingerprint(path)
            else:
                raise AgentProtocolError(f"raw artifact does not exist: {path}")
            key = path.relative_to(self.raw_root).as_posix()
            self._fingerprints[key] = digest
            result[key] = digest
        return result

    def assert_unchanged(self) -> None:
        """检查所有冻结 raw 工件未发生变化。 / Verify all frozen raw artifacts are unchanged."""

        for relative, expected in self._fingerprints.items():
            path = self.raw_root / relative
            if not path.exists():
                raise AgentProtocolError(f"frozen raw artifact disappeared: {relative}")
            if path.is_symlink():
                raise AgentProtocolError(f"frozen raw artifact became a symlink: {relative}")
            if path.is_dir() and any(item.is_symlink() for item in path.rglob("*")):
                raise AgentProtocolError(f"frozen raw directory gained a symlink: {relative}")
            actual = file_sha256(path) if path.is_file() else tree_fingerprint(path)
            if actual != expected:
                raise AgentProtocolError(f"frozen raw artifact changed: {relative}")

    @property
    def fingerprints(self) -> Dict[str, str]:
        """返回 immutable snapshot。 / Return an immutable snapshot copy."""

        return dict(self._fingerprints)


def make_agent_receipt(
    role: str,
    task_id: str,
    *,
    allowed_paths: Iterable[str],
    status: str,
    output_refs: Iterable[str] = (),
    fresh_runtime: bool = False,
    runtime_status: Optional[str] = None,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    """生成诚实的 Agent receipt；没有 fresh runtime 时不伪造 PASS panel。

    Build an honest Agent receipt; never fabricate an independent panel without fresh runtime.
    """

    if role not in VALID_ROLES:
        raise AgentProtocolError(f"unknown role: {role}")
    if status not in {"PASS", "FAIL", "BLOCKED_DEPENDENCY", "SINGLE_AGENT_MODE"}:
        raise AgentProtocolError(f"invalid receipt status: {status}")
    if status == "PASS" and not fresh_runtime:
        raise AgentProtocolError("PASS receipt requires a fresh runtime")
    if role == "Dynamic Expert" and not fresh_runtime and status not in {"BLOCKED_DEPENDENCY", "SINGLE_AGENT_MODE"}:
        raise AgentProtocolError("independent expert receipt requires fresh runtime")
    effective_runtime = runtime_status or ("FRESH_RUNTIME" if fresh_runtime else "SINGLE_AGENT_MODE")
    receipt: Dict[str, Any] = {
        "schema_version": "robotics-ar-agent-receipt.v1",
        "receipt_id": f"AGENT-{sha256_obj({'role': role, 'task_id': task_id, 'paths': sorted(allowed_paths), 'time': utc_now()})[:16]}",
        "role": role,
        "task_id": task_id,
        "allowed_paths": sorted(set(str(item) for item in allowed_paths)),
        "status": status,
        "runtime_status": effective_runtime,
        "fresh_runtime": bool(fresh_runtime),
        "output_refs": sorted(set(str(item) for item in output_refs)),
        "created_at": utc_now(),
    }
    if error:
        receipt["error"] = str(error)
    receipt["receipt_sha256"] = sha256_obj(receipt)
    return receipt


def validate_agent_receipt(receipt: Mapping[str, Any], *, expected_role: Optional[str] = None, expected_task_id: Optional[str] = None) -> None:
    """Validate the immutable receipt envelope before Supervisor registration."""

    if not isinstance(receipt, Mapping):
        raise AgentProtocolError("agent receipt must be an object")
    if receipt.get("schema_version") != "robotics-ar-agent-receipt.v1":
        raise AgentProtocolError("agent receipt schema mismatch")
    role = str(receipt.get("role", ""))
    if role not in VALID_ROLES:
        raise AgentProtocolError("unknown agent role")
    if expected_role and role != expected_role:
        raise AgentProtocolError("agent role mismatch")
    if expected_task_id and receipt.get("task_id") != expected_task_id:
        raise AgentProtocolError("agent task mismatch")
    if receipt.get("status") not in {"PASS", "FAIL", "BLOCKED_DEPENDENCY", "SINGLE_AGENT_MODE"}:
        raise AgentProtocolError("invalid agent receipt status")
    expected = receipt.get("receipt_sha256")
    actual = sha256_obj({key: value for key, value in receipt.items() if key != "receipt_sha256"})
    if not expected or expected != actual:
        raise AgentProtocolError("agent receipt hash mismatch")
    if role == "Dynamic Expert" and receipt.get("status") == "PASS" and not receipt.get("fresh_runtime"):
        raise AgentProtocolError("independent Dynamic Expert PASS requires fresh runtime")


def validate_role_access(role: str, *, read_path: Optional[str] = None, write_path: Optional[str] = None) -> None:
    """执行角色的显式读写 allow-list 和 forbidden 检查。

    Apply the role's explicit read/write allow-lists as well as its forbidden
    paths.  The values in ``ROLE_CONTRACTS`` are logical workspace roots (for
    example ``implementation`` or ``raw``), so callers may pass a descendant
    path such as ``implementation/src/model.py``.
    """

    if role not in VALID_ROLES:
        raise AgentProtocolError(f"unknown role: {role}")
    rules = ROLE_CONTRACTS[role]

    def check_target(target: str, *, operation: str) -> None:
        if not target:
            raise AgentProtocolError(f"{operation} path is required for {role}")
        candidate = Path(str(target))
        if candidate.is_absolute() or ".." in candidate.parts or "\x00" in str(target):
            raise AgentProtocolError(f"unsafe {operation} path: {target}")
        normalized = candidate.as_posix().strip("/")
        forbidden = tuple(str(item) for item in rules.get("forbidden", ()))
        if any(_matches(normalized, item) for item in forbidden):
            raise AgentProtocolError(f"role {role} cannot {operation} {target}")
        allowed_key = "writes" if operation == "write" else "reads"
        allowed = tuple(str(item) for item in rules.get(allowed_key, ()))
        if not any(_matches(normalized, item) for item in allowed):
            raise AgentProtocolError(f"role {role} is not allowed to {operation} {target}")

    if read_path is not None:
        check_target(read_path, operation="read")
    if write_path is not None:
        check_target(write_path, operation="write")


def build_expert_profiles(count: int = 2) -> List[Dict[str, Any]]:
    """创建 2–4 个确定性专家 profile。 / Build 2–4 deterministic expert profiles."""

    if count < 2 or count > 4:
        raise AgentProtocolError("dynamic expert count must be between 2 and 4")
    return [{"expert_id": f"expert-{index:02d}", "role": "Dynamic Expert", "focus": f"unknown-{index:02d}"} for index in range(1, count + 1)]


def build_dynamic_expert_profiles(domain_payload: Optional[Mapping[str, Any]] = None, *, count: int = 2) -> List[Dict[str, Any]]:
    """Derive bounded expert focuses from the active problem, not a fixed committee."""

    if count < 2 or count > 4:
        raise AgentProtocolError("dynamic expert count must be between 2 and 4")
    payload = dict(domain_payload or {})
    requested = payload.get("expert_roles", payload.get("expert_focuses", []))
    focuses = [str(item) for item in requested] if isinstance(requested, list) else []
    if not focuses:
        unknowns = payload.get("unknowns", payload.get("open_questions", []))
        focuses = [f"unknown-{index:02d}" for index in range(1, max(count, len(unknowns) if isinstance(unknowns, list) else count) + 1)]
    return [{"expert_id": f"dynamic-expert-{index:02d}", "role": "Dynamic Expert", "focus": focuses[index - 1]} for index in range(1, count + 1)]


def synthesize_expert_rounds(
    profiles: Sequence[Mapping[str, Any]],
    round_one: Sequence[Mapping[str, Any]],
    round_two: Optional[Sequence[Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    """合并最多两轮专家判断，禁止第三轮或多 next action。

    Synthesize at most two expert rounds; reject third rounds or multiple next actions.
    """

    if len(profiles) < 2 or len(profiles) > 4:
        raise AgentProtocolError("expert panel must contain 2–4 profiles")
    if len(round_one) != len(profiles):
        raise AgentProtocolError("round one must have one response per expert")
    rounds: List[Sequence[Mapping[str, Any]]] = [round_one]
    if round_two is not None:
        if len(round_two) != len(profiles):
            raise AgentProtocolError("round two must have one response per expert")
        rounds.append(round_two)
    actions = {str(item.get("next_action_id", "")) for group in rounds for item in group if item.get("next_action_id")}
    if len(actions) > 1:
        return {"status": "CRITICAL_BLOCK", "rounds": len(rounds), "next_action_id": None, "disagreements": sorted(actions)}
    action = next(iter(actions), None)
    if len(rounds) == 1 and any(item.get("needs_second_round") for item in round_one):
        return {"status": "ACCEPT_WITH_CONSTRAINTS", "rounds": 1, "next_action_id": action, "requires_round_two": True}
    if any(item.get("decision") == "CRITICAL_BLOCK" for group in rounds for item in group):
        status = "CRITICAL_BLOCK"
    elif any(item.get("decision") == "REQUEST_DISCRIMINATIVE_EXPERIMENT" for group in rounds for item in group):
        status = "REQUEST_DISCRIMINATIVE_EXPERIMENT"
    elif any(item.get("decision") == "ACCEPT_WITH_CONSTRAINTS" for group in rounds for item in group):
        status = "ACCEPT_WITH_CONSTRAINTS"
    else:
        status = "ACCEPT"
    return {"status": status, "rounds": len(rounds), "next_action_id": action, "disagreements": []}
