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

from .atomic_io import atomic_write_bytes, atomic_write_json, read_json, runtime_root
from .canonical import canonical_bytes, sha256_obj
from .event_log import EventLog
from .gates import ApprovalManager, GateError
from .models import Budget, utc_now
from .process_registry import ProcessRegistry
from .reporting import write_handoff, write_report
from .schema_validation import SchemaValidationError, validate_artifact
from .state_machine import ACTIVE_STATES, TransitionError, validate_transition
from .structured import read_mapping, write_structured
from .transaction import serialized


class SessionError(RuntimeError):
    """session 操作失败。 / Raised for session operation failures."""


@dataclass(frozen=True)
class SessionPaths:
    """项目级 `robotics-ar` 路径集合。 / Project-level `robotics-ar` paths."""

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
    takeover: Path
    takeover_intake: Path
    takeover_audit: Path
    takeover_history: Path
    takeover_baseline: Path
    takeover_contracts: Path
    trial_queue: Path
    trial_queue_queued: Path
    trial_queue_active: Path
    trial_queue_completed: Path
    trial_queue_rejected: Path
    blackboard: Path
    best_known: Path
    root_report: Path
    root_handoff: Path
    root_task: Path

    @classmethod
    def from_project(cls, project_root: Path | str) -> "SessionPaths":
        """从项目根构造路径。 / Build paths from a project root."""

        project = Path(project_root).resolve()
        root = runtime_root(project)
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
            root / "takeover",
            root / "takeover" / "intake",
            root / "takeover" / "audit",
            root / "takeover" / "history",
            root / "takeover" / "baseline",
            root / "takeover" / "contracts",
            root / "trial-queue",
            root / "trial-queue" / "queued",
            root / "trial-queue" / "active",
            root / "trial-queue" / "completed",
            root / "trial-queue" / "rejected",
            root / "blackboard",
            root / "best-known-state.yaml",
            root / "report.md",
            root / "handoff.md",
            root / "task.md",
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
        "takeover",
        "takeover/intake",
        "takeover/audit",
        "takeover/history",
        "takeover/baseline",
        "takeover/contracts",
        "trial-queue",
        "trial-queue/queued",
        "trial-queue/active",
        "trial-queue/completed",
        "trial-queue/rejected",
        "blackboard",
    )

    ENVIRONMENT_BOUND_STATES = frozenset(
        {
            "EXECUTION_READY",
            "RUNNING_ENVIRONMENT",
            "ANALYZING",
            "AWAITING_BATCH_REVIEW",
            "EVIDENCE_FREEZE",
            "AWAITING_EVIDENCE_APPROVAL",
            "INVOKING_WRITING_SKILL",
            "AWAITING_WRITING_APPROVAL",
            "INVOKING_REVIEW_SKILL",
            "AWAITING_REVIEW_ROUTE",
        }
    )

    TAKEOVER_ENVIRONMENT_STATES = frozenset({
        "TAKEOVER_BASELINE_SELECTION",
        "TAKEOVER_BASELINE_REPRODUCTION",
        "TAKEOVER_BASELINE_RECOVERY",
        "AWAITING_TAKEOVER_APPROVAL",
        "TRIAL_CONTRACT_COMPILATION",
        "AWAITING_TRIAL_CONTRACT_APPROVAL",
        "TRIAL_BATCH_READY",
        "TRIAL_PLANNING",
        "TRIAL_IMPLEMENTING",
        "TRIAL_TESTING",
        "TRIAL_DEBUGGING",
        "TRIAL_RUNNING",
        "TRIAL_ANALYZING",
        "TRIAL_EXPERT_REVIEW",
        "TRIAL_DECIDING",
        "BATCH_CHECKPOINT",
        "AWAITING_USER_DIRECTION",
    })
    TAKEOVER_BASELINE_STATES = frozenset({
        "TAKEOVER_BASELINE_REPRODUCTION",
        "TAKEOVER_BASELINE_RECOVERY",
        "AWAITING_TAKEOVER_APPROVAL",
        "TRIAL_CONTRACT_COMPILATION",
        "AWAITING_TRIAL_CONTRACT_APPROVAL",
        "TRIAL_BATCH_READY",
        "TRIAL_PLANNING",
        "TRIAL_IMPLEMENTING",
        "TRIAL_TESTING",
        "TRIAL_DEBUGGING",
        "TRIAL_RUNNING",
        "TRIAL_ANALYZING",
        "TRIAL_EXPERT_REVIEW",
        "TRIAL_DECIDING",
        "BATCH_CHECKPOINT",
        "AWAITING_USER_DIRECTION",
    })
    # A pause during reproduction or recovery is a valid checkpoint before a
    # baseline receipt exists.  Once the workflow reaches the approval gate,
    # however, the receipt must be present and hash-bound.
    TAKEOVER_BASELINE_REQUIRED_STATES = frozenset({
        "AWAITING_TAKEOVER_APPROVAL",
        "TRIAL_CONTRACT_COMPILATION",
        "AWAITING_TRIAL_CONTRACT_APPROVAL",
        "TRIAL_BATCH_READY",
        "TRIAL_PLANNING",
        "TRIAL_IMPLEMENTING",
        "TRIAL_TESTING",
        "TRIAL_DEBUGGING",
        "TRIAL_RUNNING",
        "TRIAL_ANALYZING",
        "TRIAL_EXPERT_REVIEW",
        "TRIAL_DECIDING",
        "BATCH_CHECKPOINT",
        "AWAITING_USER_DIRECTION",
    })
    TAKEOVER_CONTRACT_STATES = frozenset({
        "TRIAL_CONTRACT_COMPILATION",
        "AWAITING_TRIAL_CONTRACT_APPROVAL",
        "TRIAL_BATCH_READY",
        "TRIAL_PLANNING",
        "TRIAL_IMPLEMENTING",
        "TRIAL_TESTING",
        "TRIAL_DEBUGGING",
        "TRIAL_RUNNING",
        "TRIAL_ANALYZING",
        "TRIAL_EXPERT_REVIEW",
        "TRIAL_DECIDING",
        "BATCH_CHECKPOINT",
        "AWAITING_USER_DIRECTION",
    })
    # Contract compilation itself may be paused before the draft is written.
    # The approval-wait and all execution states cannot be resumed without it.
    TAKEOVER_CONTRACT_REQUIRED_STATES = frozenset({
        "AWAITING_TRIAL_CONTRACT_APPROVAL",
        "TRIAL_BATCH_READY",
        "TRIAL_PLANNING",
        "TRIAL_IMPLEMENTING",
        "TRIAL_TESTING",
        "TRIAL_DEBUGGING",
        "TRIAL_RUNNING",
        "TRIAL_ANALYZING",
        "TRIAL_EXPERT_REVIEW",
        "TRIAL_DECIDING",
        "BATCH_CHECKPOINT",
        "AWAITING_USER_DIRECTION",
    })

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
            # 已提交事件可恢复中断的状态投影。 / Committed events recover interrupted projections.
            from .transaction import writer_lock

            with writer_lock(self.paths.root):
                self._state = read_json(self.paths.state)
                events = EventLog(self.paths.events, self._state["session_id"]).read_events()
                for event in events:
                    projection = event["payload"].get("state_projection")
                    if projection and event["event_id"] > self._state.get("last_event_id", ""):
                        if event["previous_state"] != self._state["state"]:
                            raise SessionError("state projection conflict; run doctor")
                        self._state = {**projection, "last_event_id": event["event_id"]}
                        atomic_write_json(self.paths.state, self._state)
            self._state.setdefault("entry_mode", "NEW_RESEARCH")
            try:
                validate_artifact("robotics-ar-session-state.v1", self._state)
            except SchemaValidationError as exc:
                raise SessionError(str(exc)) from exc
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

    @serialized
    def initialize(
        self,
        *,
        mode: str,
        interaction_language: str,
        budget: Optional[Mapping[str, Any]] = None,
        session_id: Optional[str] = None,
        validation_policy: Optional[Mapping[str, Any]] = None,
        entry_mode: str = "NEW_RESEARCH",
    ) -> Dict[str, Any]:
        """创建项目 session，并通过 bootstrap 进入 planning ready。

        Create a project session and bootstrap it into planning ready.
        """

        if mode not in {"PLANNING_ONLY", "EXECUTION_ENABLED"}:
            raise SessionError("mode must be PLANNING_ONLY or EXECUTION_ENABLED")
        if not interaction_language:
            raise SessionError("interaction_language is required")
        if entry_mode not in {"NEW_RESEARCH", "MIDSTREAM_TAKEOVER"}:
            raise SessionError("entry_mode must be NEW_RESEARCH or MIDSTREAM_TAKEOVER")
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
        config = {"schema_version": "robotics-ar-config.v1", "session_id": identifier, "mode": mode, "entry_mode": entry_mode, "interaction_language": interaction_language, "validation_policy": dict(validation_policy or {"required_gates": [], "independent_review_required": False, "deterministic_validation_required": True})}
        atomic_write_bytes(self.paths.config, _simple_yaml(config).encode("utf-8"))
        atomic_write_bytes(self.paths.permissions, _simple_yaml({"supervisor_owned": ["state.json", "events.jsonl", "pointers.json", "task.md", "report.md", "handoff.md"], "agent_roots": ["agents/<role>/<task-id>"]}).encode("utf-8"))
        atomic_write_bytes(self.paths.budget, _simple_yaml(limits).encode("utf-8"))
        atomic_write_json(self.paths.pointers, {"schema_version": "robotics-ar-pointers.v1", "session_id": identifier})
        self._state = {"schema_version": "robotics-ar-session-state.v1", "session_id": identifier, "mode": mode, "entry_mode": entry_mode, "interaction_language": interaction_language, "state": "UNINITIALIZED", "exploration_budget": limits, "validation_policy": config["validation_policy"], "updated_at": utc_now()}
        atomic_write_json(self.paths.state, self._state)
        log = EventLog(self.paths.events, identifier)
        self._transition("BOOTSTRAP_VALIDATING", "SESSION_CREATED", {"mode": mode})
        try:
            validate_artifact("robotics-ar-session-state.v1", self.state)
            if read_mapping(self.paths.config)["session_id"] != identifier:
                raise SessionError("config session mismatch")
            if read_json(self.paths.pointers)["session_id"] != identifier:
                raise SessionError("pointer session mismatch")
            if not read_mapping(self.paths.permissions).get("supervisor_owned"):
                raise SessionError("supervisor permissions missing")
            actual_budget = read_mapping(self.paths.budget)
            if actual_budget != limits or any(isinstance(v, (int, float)) and v < 0 for v in actual_budget.values()):
                raise SessionError("invalid bootstrap budget")
        except (ValueError, KeyError, OSError, RuntimeError) as exc:
            atomic_write_json(self.paths.root / "bootstrap-receipt.json", {"status": "BLOCKED_BOOTSTRAP", "error": str(exc)})
            self._transition("FAILED_RECOVERABLE", "BOOTSTRAP_FAILED", {"error": str(exc)})
            raise SessionError(f"bootstrap failed: {exc}") from exc
        atomic_write_json(self.paths.root / "bootstrap-receipt.json", {"status": "PASS", "session_id": identifier})
        self._transition("PLANNING_READY", "BOOTSTRAP_PASSED", {"mode": mode})
        return self.state

    @serialized
    def _transition(self, new_state: str, event_type: str, payload: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        if self.paths.state.exists() and self._state is not None:
            disk = read_json(self.paths.state)
            if disk != self._state:
                raise SessionError("concurrent state change; reload before retry")
        current = self.state["state"]
        try:
            validate_transition(current, new_state)
        except TransitionError as exc:
            raise SessionError(str(exc)) from exc
        updated = dict(self.state)
        updated["state"] = new_state
        updated["updated_at"] = utc_now()
        event = EventLog(self.paths.events, self.session_id).append(event_type, "supervisor", current, new_state, {**dict(payload or {}), "state_projection": updated})
        updated["last_event_id"] = event["event_id"]
        atomic_write_json(self.paths.state, updated)
        self._state = updated
        return updated

    def transition(self, new_state: str, event_type: str = "STATE_TRANSITION", payload: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        """公开状态转移。 / Public state transition."""

        return self._transition(new_state, event_type, payload)

    @serialized
    def record_event(self, event_type: str, payload: Optional[Mapping[str, Any]] = None, *, actor: str = "supervisor", artifact_refs: Optional[Iterable[str]] = None) -> Dict[str, Any]:
        """Append an observational event without changing the state."""

        current = self.state["state"]
        event = EventLog(self.paths.events, self.session_id).append(event_type, actor, current, current, {**dict(payload or {}), "state_projection": self.state}, artifact_refs=artifact_refs)
        updated = dict(self.state)
        updated["last_event_id"] = event["event_id"]
        updated["updated_at"] = utc_now()
        atomic_write_json(self.paths.state, updated)
        self._state = updated
        return updated

    @serialized
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
                "entry_mode": "MIDSTREAM_TAKEOVER" if re.search(r"^entry_mode:\s*['\"]?MIDSTREAM_TAKEOVER", config_text, re.MULTILINE) else "NEW_RESEARCH",
                "interaction_language": language_match.group(1).strip() if language_match else "zh",
                "exploration_budget": Budget.from_mapping({}).to_dict(),
                "validation_policy": {"required_gates": [], "independent_review_required": False, "deterministic_validation_required": True},
            }
        projections = [event["payload"]["state_projection"] for event in log.read_events() if "state_projection" in event["payload"]]
        if projections:
            current = dict(projections[-1])
        current.update({"state": reconstructed["state"], "last_event_id": f"EVT-{reconstructed['event_count']:06d}", "updated_at": utc_now()})
        current.setdefault("entry_mode", "NEW_RESEARCH")
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

    @serialized
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

    @serialized
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

    @serialized
    def approve_subject(self, gate: str, subject_path: Path | str, *, scope: str = "single-use") -> Dict[str, Any]:
        """创建 gate approval。 / Create a gate approval."""

        return ApprovalManager(self.paths.approvals).create(gate, subject_path, scope=scope)

    @serialized
    def consume_approval(self, approval_path: Path | str, *, expected_gate: Optional[str | tuple[str, ...] | list[str]] = None, expected_subject_path: Optional[Path | str] = None) -> Dict[str, Any]:
        """消费 gate approval。 / Consume a gate approval."""

        return ApprovalManager(self.paths.approvals).consume(approval_path, expected_gate=expected_gate, expected_subject_path=expected_subject_path)

    @serialized
    def enable_execution(self, environment_receipt: Mapping[str, Any], *, receipt_path: Optional[Path | str] = None) -> Dict[str, Any]:
        """绑定 ONLINE_VERIFIED environment fingerprint 并进入执行就绪。

        Bind an ONLINE_VERIFIED environment fingerprint and enter execution-ready.
        """

        if environment_receipt.get("status") != "ONLINE_VERIFIED":
            raise SessionError("ONLINE_VERIFIED receipt required")
        fingerprint = str(environment_receipt.get("fingerprint") or "")
        if not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
            raise SessionError("ONLINE_VERIFIED receipt fingerprint must be a 64-hex digest")
        current = self.state["state"]
        if current == "TESTING":
            self._transition("EXECUTION_READY", "TESTS_PASSED", {"fingerprint": fingerprint})
        elif current == "BLOCKED_ENVIRONMENT":
            self._transition("EXECUTION_READY", "ENVIRONMENT_VERIFIED", {"fingerprint": fingerprint})
        elif current != "EXECUTION_READY":
            raise SessionError(f"cannot enable execution from {current}")
        updated = dict(self.state)
        updated["environment_fingerprint"] = fingerprint
        if environment_receipt.get("receipt_sha256"):
            updated["environment_receipt_sha256"] = str(environment_receipt["receipt_sha256"])
        if receipt_path is not None:
            updated["environment_receipt_path"] = Path(receipt_path).resolve().as_posix()
        atomic_write_json(self.paths.state, updated)
        self._state = updated
        return dict(updated)

    @serialized
    def bind_environment_receipt(self, environment_receipt: Mapping[str, Any], *, receipt_path: Optional[Path | str] = None) -> Dict[str, Any]:
        """Bind a verified environment without changing the current v3 takeover state."""

        from .environment import EnvironmentError, validate_environment_receipt

        try:
            validate_environment_receipt(environment_receipt, require_online=True)
        except EnvironmentError as exc:
            raise SessionError(str(exc)) from exc
        fingerprint = str(environment_receipt.get("fingerprint") or "")
        if not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
            raise SessionError("environment fingerprint must be a 64-hex digest")
        updated = dict(self.state)
        old_receipt = str(updated.get("environment_receipt_sha256", ""))
        old_fingerprint = str(updated.get("environment_fingerprint", ""))
        environment_changed = bool(old_receipt and old_receipt != str(environment_receipt.get("receipt_sha256", ""))) or bool(old_fingerprint and old_fingerprint != fingerprint)
        if environment_changed and updated.get("entry_mode", "NEW_RESEARCH") == "MIDSTREAM_TAKEOVER":
            # Baseline and contracts are evidence-bound to the old runtime;
            # carrying their approval flags across an environment replacement
            # would make a new runtime look approved without revalidation.
            updated["baseline_approved"] = False
            updated["contract_approved"] = False
            updated.pop("baseline_approval_id", None)
            contract_path_value = updated.get("contract_path")
            if contract_path_value:
                contract_path = Path(str(contract_path_value)).resolve()
                try:
                    contract_path.relative_to(self.paths.takeover_contracts.resolve())
                    if contract_path.is_file():
                        from .trial_contract import contract_hash

                        contract = read_mapping(contract_path)
                        if contract.get("status") == "APPROVED":
                            invalidated = dict(contract)
                            invalidated["status"] = "INVALIDATED"
                            invalidated["approval"] = {"required": True, "approved_by_user": False, "invalidated_by": "environment-drift"}
                            invalidated["contract_sha256"] = contract_hash(invalidated)
                            write_structured(contract_path, invalidated)
                except (OSError, ValueError):
                    raise SessionError("environment drift found an invalid contract path")
        updated["environment_fingerprint"] = fingerprint
        if environment_receipt.get("receipt_sha256"):
            updated["environment_receipt_sha256"] = str(environment_receipt["receipt_sha256"])
        if receipt_path is not None:
            updated["environment_receipt_path"] = Path(receipt_path).resolve().as_posix()
        atomic_write_json(self.paths.state, updated)
        self._state = updated
        return dict(updated)

    @serialized
    def pause(self, reason: str) -> Dict[str, Any]:
        """暂停任意 active state，并写 report/handoff。 / Pause any active state and write report/handoff."""

        current = self.state["state"]
        if current not in ACTIVE_STATES:
            raise SessionError(f"state is not pausable: {current}")
        self._transition("PAUSING", "PAUSE_REQUESTED", {"reason": reason, "safe_state": current})
        registry = ProcessRegistry(self.paths.root / "process-registry.json")
        for entry in list(registry._read()):
            if entry.get("status") != "RUNNING":
                continue
            pid = int(entry["pid"])
            if ProcessRegistry.is_alive(pid):
                registry.stop(pid)
            else:
                registry.mark_stopped(pid, "STALE_PID")
        from .atomic_io import report_files_requested
        if report_files_requested():
            write_report(self.paths.root / "report.md", title="Robotics-AR report", state="PAUSING", summary=reason, actions=["resume after validating task and environment hashes"])
            write_handoff(self.paths.root / "handoff.md", state="PAUSING", session_id=self.session_id, reason=reason)
        if self.state.get("entry_mode", "NEW_RESEARCH") == "MIDSTREAM_TAKEOVER":
            from .reporting_v3 import write_checkpoint_artifacts

            write_checkpoint_artifacts(self, context={"pause_reason": reason}, reason=reason)
        return self._transition("PAUSED", "PAUSE_COMMITTED", {"reason": reason, "safe_state": current})

    @serialized
    def resume(self) -> Dict[str, Any]:
        """从磁盘恢复到 pause 前 safe state。 / Resume to the pre-pause safe state from disk."""

        if self.state["state"] in {"COMPLETE", "TAKEOVER_COMPLETE", "ABORTED"}:
            return self.state
        if self.state["state"] != "PAUSED":
            raise SessionError("session is not paused")
        events = EventLog(self.paths.events, self.session_id).read_events()
        pause_events = [event for event in events if event.get("event_type") == "PAUSE_REQUESTED"]
        safe_state = pause_events[-1].get("payload", {}).get("safe_state") if pause_events else "PLANNING_READY"
        self._validate_resume_artifacts(str(safe_state))
        self._transition("BOOTSTRAP_VALIDATING", "RESUME_VALIDATING", {"safe_state": safe_state})
        return self._transition(str(safe_state), "RESUME_VALIDATED", {"safe_state": safe_state})

    def _validate_resume_artifacts(self, safe_state: str) -> None:
        """恢复前校验 task、环境、预算和 token 工件。

        Validate task, environment, budget, and token artifacts before resume.
        """

        state = self.state
        repository_receipt = self.paths.root / "repository-ledger.json"
        if repository_receipt.exists():
            from .repository_ledger import validate_snapshot

            validate_snapshot(read_json(repository_receipt))
        elif self.dirty_git():
            raise SessionError("resume blocked: project Git worktree is dirty")
        budget = Budget.from_mapping(state.get("exploration_budget", {}))
        for used, maximum in (
            (budget.candidates_used, budget.max_candidates),
            (budget.expert_rounds_used, budget.max_expert_rounds),
            (budget.debug_rounds_used, budget.max_debug_rounds),
            (budget.batches_used, budget.max_batches),
            (budget.trials_used, budget.max_trials),
            (budget.gpu_hours_used, budget.max_gpu_hours),
            (budget.disk_gb_used, budget.max_disk_gb),
            (budget.wall_time_used_minutes, budget.max_wall_time_minutes),
            (budget.parallel_jobs_used, budget.max_parallel_jobs),
        ):
            if used > maximum:
                raise SessionError("resume blocked: exploration budget exceeded")

        task_path_value = state.get("task_path")
        task_hash = state.get("task_sha256")
        task_bound_states = {
            "AWAITING_TASK_APPROVAL",
            "IMPLEMENTING",
            "TESTING",
            "DEBUGGING",
            "EXECUTION_READY",
            "RUNNING_ENVIRONMENT",
            "ANALYZING",
            "AWAITING_BATCH_REVIEW",
            "EVIDENCE_FREEZE",
            "AWAITING_EVIDENCE_APPROVAL",
        }
        if safe_state in task_bound_states and not task_hash:
            raise SessionError("resume blocked: task hash missing")
        if task_path_value:
            task_path = Path(str(task_path_value)).resolve()
            try:
                task_path.relative_to(self.paths.tasks.resolve())
            except ValueError as exc:
                raise SessionError("resume blocked: task path escapes session") from exc
            if not task_path.is_file():
                raise SessionError("resume blocked: task artifact missing")
            task = read_mapping(task_path)
            if task.get("schema_version") == "robotics-ar-user-correction.v1":
                from .user_correction import _task_hash

                actual_task_hash = _task_hash(task)
            else:
                actual_task_hash = sha256_obj({key: value for key, value in task.items() if key != "task_sha256"})
            if task.get("task_sha256") != actual_task_hash or task_hash != actual_task_hash:
                raise SessionError("resume blocked: task hash drift")
        elif task_hash:
            raise SessionError("resume blocked: task path missing")

        environment_fingerprint = state.get("environment_fingerprint")
        if safe_state in self.ENVIRONMENT_BOUND_STATES and self.state.get("mode") == "EXECUTION_ENABLED":
            if not isinstance(environment_fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", environment_fingerprint):
                raise SessionError("resume blocked: environment fingerprint missing or invalid")
        receipt_path_value = state.get("environment_receipt_path")
        if receipt_path_value:
            receipt_path = Path(str(receipt_path_value)).resolve()
            if not receipt_path.is_file():
                raise SessionError("resume blocked: environment receipt missing")
            receipt = read_json(receipt_path)
            from .environment import EnvironmentError, validate_environment_receipt

            try:
                validate_environment_receipt(receipt, require_online=True)
            except EnvironmentError as exc:
                raise SessionError(f"resume blocked: invalid environment receipt: {exc}") from exc
            if receipt.get("fingerprint") != environment_fingerprint:
                raise SessionError("resume blocked: environment receipt drift")
            receipt_hash = receipt.get("receipt_sha256")
            if receipt_hash and state.get("environment_receipt_sha256") and receipt_hash != state.get("environment_receipt_sha256"):
                raise SessionError("resume blocked: environment receipt hash drift")

        if state.get("entry_mode", "NEW_RESEARCH") == "MIDSTREAM_TAKEOVER":
            # Validate a compiled core in every takeover state, including the
            # interview/audit boundary before a contract exists.
            if state.get("project_core_path") or state.get("project_core_sha256"):
                core_path_value = state.get("project_core_path")
                core_hash_value = state.get("project_core_sha256")
                if not core_path_value or not core_hash_value:
                    raise SessionError("resume blocked: Project Core binding is incomplete")
                core_path = Path(str(core_path_value)).resolve()
                try:
                    core_path.relative_to(self.paths.takeover.resolve())
                except ValueError as exc:
                    raise SessionError("resume blocked: Project Core path escapes takeover root") from exc
                if not core_path.is_file():
                    raise SessionError("resume blocked: Project Core artifact missing")
                from .project_core import assert_project_core_approved, load_project_core, core_hash

                core = load_project_core(core_path)
                if core_hash(core) != core_hash_value:
                    raise SessionError("resume blocked: Project Core drift")
                if state.get("project_core_approved") is True:
                    assert_project_core_approved(core)
            if safe_state in self.TAKEOVER_ENVIRONMENT_STATES:
                if not isinstance(state.get("environment_fingerprint"), str) or not re.fullmatch(r"[0-9a-f]{64}", str(state.get("environment_fingerprint"))):
                    raise SessionError("resume blocked: takeover environment fingerprint missing or invalid")
                if not state.get("environment_receipt_path"):
                    raise SessionError("resume blocked: takeover environment receipt binding missing")
            if safe_state in self.TAKEOVER_BASELINE_STATES:
                baseline_path_value = state.get("baseline_receipt_path")
                baseline_hash_value = state.get("baseline_receipt_sha256")
                baseline_bound = bool(baseline_path_value or baseline_hash_value)
                if safe_state in self.TAKEOVER_BASELINE_REQUIRED_STATES and not (baseline_path_value and baseline_hash_value):
                    raise SessionError("resume blocked: baseline receipt binding missing")
                if baseline_bound:
                    if not baseline_path_value or not baseline_hash_value:
                        raise SessionError("resume blocked: baseline receipt binding is incomplete")
                    baseline_path = Path(str(baseline_path_value)).resolve()
                    try:
                        baseline_path.relative_to(self.paths.takeover_baseline.resolve())
                    except ValueError as exc:
                        raise SessionError("resume blocked: baseline receipt path escapes takeover baseline root") from exc
                    if not baseline_path.is_file():
                        raise SessionError("resume blocked: baseline receipt missing")
                    baseline = read_json(baseline_path)
                    if baseline.get("receipt_sha256") != sha256_obj({key: value for key, value in baseline.items() if key != "receipt_sha256"}) or baseline.get("receipt_sha256") != baseline_hash_value:
                        raise SessionError("resume blocked: baseline receipt drift")
            if safe_state in self.TAKEOVER_CONTRACT_STATES:
                if state.get("project_core_approved") is False or state.get("baseline_approved") is False:
                    raise SessionError("resume blocked: Project Core and baseline approvals are invalid")
                core_path_value = state.get("project_core_path")
                core_hash_value = state.get("project_core_sha256")
                if not core_path_value or not core_hash_value:
                    raise SessionError("resume blocked: Project Core binding missing")
                core_path = Path(str(core_path_value)).resolve()
                try:
                    core_path.relative_to(self.paths.takeover.resolve())
                except ValueError as exc:
                    raise SessionError("resume blocked: Project Core path escapes takeover root") from exc
                if not core_path.is_file():
                    raise SessionError("resume blocked: Project Core artifact missing")
                from .project_core import load_project_core, core_hash

                core = load_project_core(core_path)
                if core_hash(core) != core_hash_value:
                    raise SessionError("resume blocked: Project Core drift")
                if state.get("project_core_approved") is True:
                    from .project_core import assert_project_core_approved

                    assert_project_core_approved(core)
            if safe_state in self.TAKEOVER_CONTRACT_STATES:
                contract_path_value = state.get("contract_path")
                contract_hash_value = state.get("contract_sha256")
                contract_bound = bool(contract_path_value or contract_hash_value)
                if safe_state in self.TAKEOVER_CONTRACT_REQUIRED_STATES and not (contract_path_value and contract_hash_value):
                    raise SessionError("resume blocked: Trial Contract binding missing")
                if contract_bound:
                    if not contract_path_value or not contract_hash_value:
                        raise SessionError("resume blocked: Trial Contract binding is incomplete")
                    contract_path = Path(str(contract_path_value)).resolve()
                    try:
                        contract_path.relative_to(self.paths.takeover_contracts.resolve())
                    except ValueError as exc:
                        raise SessionError("resume blocked: Trial Contract path escapes contracts root") from exc
                    from .trial_contract import TrialContractManager, contract_hash

                    contract = TrialContractManager(self.paths.takeover_contracts, self.paths.approvals).load(contract_path)
                    if contract_hash(contract) != contract_hash_value:
                        raise SessionError("resume blocked: Trial Contract drift")
                    if safe_state in {"TRIAL_BATCH_READY", "TRIAL_PLANNING", "TRIAL_IMPLEMENTING", "TRIAL_TESTING", "TRIAL_DEBUGGING", "TRIAL_RUNNING", "TRIAL_ANALYZING", "TRIAL_EXPERT_REVIEW", "TRIAL_DECIDING", "BATCH_CHECKPOINT"} and contract.get("status") != "APPROVED":
                        raise SessionError("resume blocked: active Trial Contract is not approved")
            registry = ProcessRegistry(self.paths.root / "process-registry.json")
            if registry.stale_entries():
                raise SessionError("resume blocked: stale registered process")

        token_path_value = state.get("real_robot_token_path")
        if token_path_value:
            from .real_robot import OneShotRealRobotToken

            token = OneShotRealRobotToken.load(token_path_value)
            if token.token.get("status") != "unused":
                raise SessionError("resume blocked: real-robot token is not unused")

    def dirty_git(self) -> bool:
        """检查项目 Git 是否有未提交变更。 / Check whether the project Git is dirty."""

        try:
            # Runtime receipts live under robotics-ar and are expected to
            # change during pause/approval/resume.  Git cleanliness here is a
            # guard on the user's project source, so exclude that supervisor
            # ledger while still reporting every source/untracked file.
            result = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all", "--", ":(exclude)robotics-ar", ":(exclude).robotics-ar"], cwd=self.paths.project_root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10, check=False)
        except (OSError, subprocess.SubprocessError):
            return True
        # A missing repository, a timeout, or any non-zero Git result is not
        # evidence of cleanliness.  Resume must fail closed when Git cannot
        # establish the worktree state.
        return result.returncode != 0 or bool(result.stdout.strip())

    def close(self) -> None:
        """关闭 session lock；只作用于本 session。 / Close this session's lock."""

        if self.paths.lock.exists():
            lock = read_json(self.paths.lock)
            if lock.get("session_id") == self.session_id:
                self.paths.lock.unlink()
