"""Non-destructive v2-to-v3 state migration helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .atomic_io import atomic_write_json
from .models import utc_now
from .structured import read_mapping
from .canonical import sha256_obj
from .schema_validation import validate_artifact
from .event_log import EventLog
from .transaction import writer_lock


def migrate_session_state(state: Mapping[str, Any]) -> dict[str, Any]:
    """Add v3 optional fields without renaming or invalidating v2 artifacts."""

    updated = dict(state)
    if state.get("schema_version") != "robotics-ar-session-state.v1":
        raise ValueError("unsupported state version; no automatic migration")
    updated.setdefault("entry_mode", "NEW_RESEARCH")
    updated.setdefault("migration", {"from": "robotics-ar-session-state.v1", "at": utc_now(), "non_destructive": True})
    return updated


def migrate_project(project_root: Path | str) -> dict[str, Any]:
    root = Path(project_root).resolve()
    state_path = root / ".robotics-ar" / "state.json"
    if not state_path.exists():
        return {"status": "NOT_INITIALIZED", "project_root": root.as_posix()}
    with writer_lock(state_path.parent):
        original = read_mapping(state_path)
        state = migrate_session_state(original)
        validate_artifact("robotics-ar-session-state.v1", state)
        backup = state_path.with_name(f"state.backup.{sha256_obj(original)}.json")
        if not backup.exists():
            atomic_write_json(backup, original)
        atomic_write_json(state_path, state)
    return {"status": "PASS", "project_root": root.as_posix(), "state": state, "non_destructive": True}


def doctor_project(project_root):
    """只诊断，不修补事件历史或补造批准。 / Diagnose without rewriting events or inventing approvals."""
    root = Path(project_root) / ".robotics-ar"
    errors = []
    state = {}
    try:
        state = read_mapping(root / "state.json")
        validate_artifact("robotics-ar-session-state.v1", state)
    except (ValueError, OSError, RuntimeError) as exc:
        errors.append({"artifact": "state.json", "error": str(exc), "action": "restore a verified backup; migrate only known versions"})
    if state.get("session_id"):
        try:
            EventLog(root / "events.jsonl", state["session_id"]).read_events()
        except (ValueError, OSError) as exc:
            errors.append({"artifact": "events.jsonl", "error": str(exc), "action": "preserve original; reconcile ambiguous order manually"})
    for name in ("config.yaml", "budget.yaml", "permissions.yaml", "pointers.json"):
        try:
            value = read_mapping(root / name)
            required = {"config.yaml": {"schema_version", "session_id", "mode", "interaction_language"},
                        "permissions.yaml": {"supervisor_owned", "agent_roots"},
                        "pointers.json": {"schema_version", "session_id"}}
            if name == "budget.yaml":
                from .models import Budget
                missing = set(Budget().to_dict()) - set(value)
                Budget.from_mapping(value)
            else:
                missing = required[name] - set(value)
            if missing:
                raise ValueError(f"missing fields: {sorted(missing)}")
            if "session_id" in value and value["session_id"] != state.get("session_id"):
                raise ValueError("session_id mismatch")
        except (ValueError, OSError) as exc:
            errors.append({"artifact": name, "error": str(exc), "action": "restore or explicitly regenerate from approved inputs"})
    execution_path = root / "execution-registry.json"
    if execution_path.exists():
        try:
            import time
            executions = read_mapping(execution_path)
            if executions.get("schema_version") != "robotics-ar-executions.v1":
                raise ValueError("unsupported execution registry version")
            for identifier, row in executions["executions"].items():
                if row["status"] == "PREPARING" or (row["status"] in {"RESERVED", "RUNNING"} and time.time() >= row.get("lease_expires", 0)):
                    errors.append({"artifact": "execution-registry.json", "execution_id": identifier,
                                   "error": "uncertain reservation or expired lease", "action": "inspect external process, then approved reconcile-execution"})
        except (ValueError, OSError, KeyError, TypeError) as exc:
            errors.append({"artifact": "execution-registry.json", "error": str(exc), "action": "restore a verified registry; do not reconstruct approval"})
    return {"status": "BLOCKED" if errors else "PASS", "errors": errors,
            "migration_available": state.get("schema_version") == "robotics-ar-session-state.v1" and "entry_mode" not in state,
            "history_rewritten": False}
