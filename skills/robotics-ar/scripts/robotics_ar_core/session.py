"""实现 session 初始化、状态缓存、批准、任务和暂停恢复。

Implement session initialization, state caching, approvals, tasks, and pause/resume.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Dict, Iterable, Mapping, Optional

from .atomic_io import atomic_write_bytes, atomic_write_json, read_json
from .canonical import canonical_bytes, sha256_obj
from .event_log import EventLog
from .gates import ApprovalManager, GateError
from .models import Budget, utc_now
from .process_registry import ProcessRegistry
from .reporting import write_handoff, write_report
from .state_machine import ACTIVE_STATES, TransitionError, validate_transition


class SessionError(RuntimeError):
    """session 操作失败。 / Raised for session operation failures."""


@dataclass(frozen=True)
class SessionPaths:
    """项目级 `.robotics-ar` 路径集合。 / Project-level `.robotics-ar` paths."""

    project_root: Path
    root: Path
    config: Path
    state: Path
    events: Path
    permissions: Path
    budget: Path
    pointers: Path
    lock: Path
    approvals: Path
    user_instructions: Path
    tasks: Path
    checkpoints: Path
    reports: Path
    agents: Path
    experiments: Path
    traces: Path
    environment: Path
    research: Path

    @classmethod
    def from_project(cls, project_root: Path | str) -> "SessionPaths":
        """从项目根构造路径。 / Build paths from a project root."""

        project = Path(project_root).resolve()
        root = project / ".robotics-ar"
        return cls(
            project,
            root,
            root / "config.yaml",
            root / "state.json",
            root / "events.jsonl",
            root / "permissions.yaml",
            root / "budget.yaml",
            root / "pointers.json",
            root / "session.lock",
            root / "approvals",
            root / "user-instructions",
            root / "tasks",
            root / "checkpoints",
            root / "reports",
            root / "agents",
            root / "experiments",
            root / "traces",
            root / "environment",
            root / "research",
        )


def _yaml_scalar(value: Any) -> str:
    """写最小 YAML scalar。 / Render a minimal YAML scalar."""

    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def _simple_yaml(mapping: Mapping[str, Any], indent: int = 0) -> str:
    """将有限映射写为无依赖 YAML。 / Render a finite mapping as dependency-free YAML."""

    lines = []
    prefix = " " * indent
    for key, value in mapping.items():
        if isinstance(value, Mapping):
            lines.append(f"{prefix}{key}:")
            lines.extend(_simple_yaml(value, indent + 2).splitlines())
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}:")
            for item in value:
                lines.append(f"{prefix}  - {_yaml_scalar(item)}")
        else:
            lines.append(f"{prefix}{key}: {_yaml_scalar(value)}")
    return "\n".join(lines) + "\n"


class SessionManager:
    """管理一个项目的状态、事件和恢复工件。 / Manage one project's state, events, and recovery artifacts."""

    DIRECTORIES = (
        "sibling-skills",
        "sibling-skills/idea",
        "sibling-skills/experiment",
        "sibling-skills/writing",
        "sibling-skills/review",
        "environment/logs",
        "research/hypotheses",
        "research/evidence",
        "research/decisions",
        "research/claims",
        "tasks",
        "approvals",
        "agents",
        "experiments",
        "traces",
        "checkpoints",
        "reports",
        "user-instructions",
    )

    def __init__(self, project_root: Path | str) -> None:
        self.paths = SessionPaths.from_project(project_root)
        self._state: Optional[Dict[str, Any]] = None

    @property
    def session_id(self) -> str:
        """返回 session ID。 / Return the session ID."""

        state = self.state
        return str(state["session_id"])

    @property
    def state(self) -> Dict[str, Any]:
        """读取或重建 state。 / Read or reconstruct state."""

        if self._state is not None:
            return dict(self._state)
        if self.paths.state.exists():
            self._state = read_json(self.paths.state)
        elif self.paths.events.exists():
            self._state = self.reconstruct_state(persist=True)
        else:
            raise SessionError("session is not initialized")
        return dict(self._state)

    def _lock_is_live(self) -> bool:
        if not self.paths.lock.exists():
            return False
        try:
            lock = read_json(self.paths.lock)
            pid = int(lock.get("pid", 0))
        except (ValueError, OSError, json.JSONDecodeError):
            return True
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError:
            return False
        return True

    def _handle_stale_lock(self) -> None:
        if not self.paths.lock.exists() or self._lock_is_live():
            return
        stale = self.paths.lock.with_name(f"session.lock.stale.{int(datetime.now(timezone.utc).timestamp())}")
        self.paths.lock.replace(stale)

    def _write_lock(self, session_id: str) -> None:
        atomic_write_json(self.paths.lock, {"schema_version": "robotics-ar-session-lock.v1", "session_id": session_id, "pid": os.getpid(), "created_at": utc_now()})

    def initialize(
        self,
        *,
        mode: str,
        interaction_language: str,
        budget: Optional[Mapping[str, Any]] = None,
        session_id: Optional[str] = None,
        validation_policy: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """创建项目 session，并通过 bootstrap 进入 planning ready。

        Create a project session and bootstrap it into planning ready.
        """

        if mode not in {"PLANNING_ONLY", "EXECUTION_ENABLED"}:
            raise SessionError("mode must be PLANNING_ONLY or EXECUTION_ENABLED")
        if not interaction_language:
            raise SessionError("interaction_language is required")
        self.paths.root.mkdir(parents=True, exist_ok=True)
        self._handle_stale_lock()
        if self.paths.lock.exists() and self._lock_is_live():
            raise SessionError("active session lock exists")
        if self.paths.state.exists() or self.paths.events.exists():
            raise SessionError("session already initialized")
        for relative in self.DIRECTORIES:
            (self.paths.root / relative).mkdir(parents=True, exist_ok=True)
        identifier = session_id or f"RAS-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{os.getpid()}"
        limits = Budget.from_mapping(budget or {}).to_dict()
        self._write_lock(identifier)
        config = {"schema_version": "robotics-ar-config.v1", "session_id": identifier, "mode": mode, "interaction_language": interaction_language, "validation_policy": dict(validation_policy or {"required_gates": [], "independent_review_required": False, "deterministic_validation_required": True})}
        atomic_write_bytes(self.paths.config, _simple_yaml(config).encode("utf-8"))
        atomic_write_bytes(self.paths.permissions, _simple_yaml({"supervisor_owned": ["state.json", "events.jsonl", "pointers.json", "task.md", "report.md", "handoff.md"], "agent_roots": ["agents/<role>/<task-id>"]}).encode("utf-8"))
        atomic_write_bytes(self.paths.budget, _simple_yaml(limits).encode("utf-8"))
        atomic_write_json(self.paths.pointers, {"schema_version": "robotics-ar-pointers.v1", "session_id": identifier})
        self._state = {"schema_version": "robotics-ar-session-state.v1", "session_id": identifier, "mode": mode, "interaction_language": interaction_language, "state": "UNINITIALIZED", "exploration_budget": limits, "validation_policy": config["validation_policy"], "updated_at": utc_now()}
        atomic_write_json(self.paths.state, self._state)
        log = EventLog(self.paths.events, identifier)
        self._transition("BOOTSTRAP_VALIDATING", "SESSION_CREATED", {"mode": mode})
        self._transition("PLANNING_READY", "BOOTSTRAP_PASSED", {"mode": mode})
        return self.state

    def _transition(self, new_state: str, event_type: str, payload: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        current = self.state["state"]
        try:
            validate_transition(current, new_state)
        except TransitionError as exc:
            raise SessionError(str(exc)) from exc
        event = EventLog(self.paths.events, self.session_id).append(event_type, "supervisor", current, new_state, payload or {})
        updated = dict(self.state)
        updated["state"] = new_state
        updated["last_event_id"] = event["event_id"]
        updated["updated_at"] = utc_now()
        atomic_write_json(self.paths.state, updated)
        self._state = updated
        return updated

    def transition(self, new_state: str, event_type: str = "STATE_TRANSITION", payload: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        """公开状态转移。 / Public state transition."""

        return self._transition(new_state, event_type, payload)

    def reconstruct_state(self, *, persist: bool = False) -> Dict[str, Any]:
        """从 events.jsonl 重建 state cache。 / Reconstruct the state cache from events.jsonl."""

        if not self.paths.events.exists():
            raise SessionError("event log does not exist")
        log = EventLog(self.paths.events, self.session_id_from_lock_or_events())
        reconstructed = log.reconstruct()
        if self._state is not None:
            current = dict(self._state)
        elif self.paths.state.exists():
            current = read_json(self.paths.state)
        else:
            config_text = self.paths.config.read_text(encoding="utf-8") if self.paths.config.exists() else ""
            mode_match = re.search(r"^mode:\s*['\"]?([^'\"\n]+)", config_text, re.MULTILINE)
            language_match = re.search(r"^interaction_language:\s*['\"]?([^'\"\n]+)", config_text, re.MULTILINE)
            current = {
                "schema_version": "robotics-ar-session-state.v1",
                "session_id": self.session_id_from_lock_or_events(),
                "mode": mode_match.group(1).strip() if mode_match else "PLANNING_ONLY",
                "interaction_language": language_match.group(1).strip() if language_match else "zh",
                "exploration_budget": Budget.from_mapping({}).to_dict(),
                "validation_policy": {"required_gates": [], "independent_review_required": False, "deterministic_validation_required": True},
            }
        current.update({"state": reconstructed["state"], "last_event_id": f"EVT-{reconstructed['event_count']:06d}", "updated_at": utc_now()})
        if persist:
            atomic_write_json(self.paths.state, current)
        self._state = current
        return dict(current)

    def session_id_from_lock_or_events(self) -> str:
        """从缓存或首个事件读取 session ID。 / Read the session ID from cache or the first event."""

        if self._state and self._state.get("session_id"):
            return str(self._state["session_id"])
        if self.paths.state.exists():
            return str(read_json(self.paths.state)["session_id"])
        lines = self.paths.events.read_text(encoding="utf-8").splitlines()
        if not lines:
            raise SessionError("event log is empty")
        return str(json.loads(lines[0])["session_id"])

    def save_user_instruction(self, text: str) -> Path:
        """原样保存用户纠正。 / Preserve a user instruction verbatim."""

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        path = self.paths.user_instructions / f"{timestamp}.md"
        suffix = 1
        while path.exists():
            path = self.paths.user_instructions / f"{timestamp}-{suffix}.md"
            suffix += 1
        atomic_write_bytes(path, text.encode("utf-8"))
        return path

    def compile_task(self, instruction: str, *, allowed_paths: Iterable[str], forbidden_paths: Iterable[str], commands: Iterable[Iterable[str]] = (), stop_conditions: Iterable[str] = (), domain_payload: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        """把自然语言保存后编译为 hash-bound task。 / Preserve text then compile a hash-bound task."""

        self.save_user_instruction(instruction)
        if self.state["state"] != "TASK_COMPILATION":
            self._transition("TASK_COMPILATION", "TASK_COMPILATION_STARTED")
        task = {"schema_version": "robotics-ar-execution-task.v1", "task_id": f"TASK-{len(list(self.paths.tasks.glob('TASK-*.json'))) + 1:06d}", "allowed_paths": list(allowed_paths), "forbidden_paths": list(forbidden_paths), "commands": [list(command) for command in commands], "stop_conditions": list(stop_conditions), "created_at": utc_now(), "domain_payload": dict(domain_payload or {})}
        path = self.paths.tasks / f"{task['task_id']}.json"
        task["task_path"] = path.as_posix()
        task["task_sha256"] = sha256_obj(task)
        atomic_write_json(path, task)
        updated = dict(self.state)
        updated["task_sha256"] = task["task_sha256"]
        updated["task_path"] = path.as_posix()
        atomic_write_json(self.paths.state, updated)
        self._state = updated
        self._transition("AWAITING_TASK_APPROVAL", "TASK_COMPILED", {"task_sha256": task["task_sha256"]})
        return task

    def approve_subject(self, gate: str, subject_path: Path | str, *, scope: str = "single-use") -> Dict[str, Any]:
        """创建 gate approval。 / Create a gate approval."""

        return ApprovalManager(self.paths.approvals).create(gate, subject_path, scope=scope)

    def consume_approval(self, approval_path: Path | str) -> Dict[str, Any]:
        """消费 gate approval。 / Consume a gate approval."""

        return ApprovalManager(self.paths.approvals).consume(approval_path)

    def enable_execution(self, environment_receipt: Mapping[str, Any]) -> Dict[str, Any]:
        """绑定 ONLINE_VERIFIED environment fingerprint 并进入执行就绪。

        Bind an ONLINE_VERIFIED environment fingerprint and enter execution-ready.
        """

        if environment_receipt.get("status") != "ONLINE_VERIFIED":
            raise SessionError("ONLINE_VERIFIED receipt required")
        current = self.state["state"]
        if current == "TESTING":
            self._transition("EXECUTION_READY", "TESTS_PASSED", {"fingerprint": environment_receipt.get("fingerprint")})
        elif current == "BLOCKED_ENVIRONMENT":
            self._transition("EXECUTION_READY", "ENVIRONMENT_VERIFIED", {"fingerprint": environment_receipt.get("fingerprint")})
        elif current != "EXECUTION_READY":
            raise SessionError(f"cannot enable execution from {current}")
        updated = dict(self.state)
        updated["environment_fingerprint"] = environment_receipt.get("fingerprint")
        atomic_write_json(self.paths.state, updated)
        self._state = updated
        return dict(updated)

    def pause(self, reason: str) -> Dict[str, Any]:
        """暂停任意 active state，并写 report/handoff。 / Pause any active state and write report/handoff."""

        current = self.state["state"]
        if current not in ACTIVE_STATES:
            raise SessionError(f"state is not pausable: {current}")
        self._transition("PAUSING", "PAUSE_REQUESTED", {"reason": reason, "safe_state": current})
        registry = ProcessRegistry(self.paths.root / "process-registry.json")
        for entry in registry.stale_entries():
            registry.mark_stopped(int(entry["pid"]), "STALE_PID")
        write_report(self.paths.root / "report.md", title="Robotics-AR report", state="PAUSING", summary=reason, actions=["resume after validating task and environment hashes"])
        write_handoff(self.paths.root / "handoff.md", state="PAUSING", session_id=self.session_id, reason=reason)
        return self._transition("PAUSED", "PAUSE_COMMITTED", {"reason": reason, "safe_state": current})

    def resume(self) -> Dict[str, Any]:
        """从磁盘恢复到 pause 前 safe state。 / Resume to the pre-pause safe state from disk."""

        if self.state["state"] != "PAUSED":
            raise SessionError("session is not paused")
        events = EventLog(self.paths.events, self.session_id).read_events()
        pause_events = [event for event in events if event.get("event_type") == "PAUSE_REQUESTED"]
        safe_state = pause_events[-1].get("payload", {}).get("safe_state") if pause_events else "PLANNING_READY"
        self._transition("BOOTSTRAP_VALIDATING", "RESUME_VALIDATING", {"safe_state": safe_state})
        return self._transition(str(safe_state), "RESUME_VALIDATED", {"safe_state": safe_state})

    def dirty_git(self) -> bool:
        """检查项目 Git 是否有未提交变更。 / Check whether the project Git is dirty."""

        try:
            result = subprocess.run(["git", "status", "--porcelain"], cwd=self.paths.project_root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10, check=False)
        except (OSError, subprocess.SubprocessError):
            return True
        return bool(result.stdout.strip())

    def close(self) -> None:
        """关闭 session lock；只作用于本 session。 / Close this session's lock."""

        if self.paths.lock.exists():
            lock = read_json(self.paths.lock)
            if lock.get("session_id") == self.session_id:
                self.paths.lock.unlink()
