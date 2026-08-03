"""Non-destructive v2-to-v3 state migration helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .atomic_io import atomic_write_json
from .models import utc_now
from .structured import read_mapping


def migrate_session_state(state: Mapping[str, Any]) -> dict[str, Any]:
    """Add v3 optional fields without renaming or invalidating v2 artifacts."""

    updated = dict(state)
    updated.setdefault("entry_mode", "NEW_RESEARCH")
    updated.setdefault("migration", {"from": "robotics-ar-session-state.v1", "at": utc_now(), "non_destructive": True})
    return updated


def migrate_project(project_root: Path | str) -> dict[str, Any]:
    root = Path(project_root).resolve()
    state_path = root / ".robotics-ar" / "state.json"
    if not state_path.exists():
        return {"status": "NOT_INITIALIZED", "project_root": root.as_posix()}
    state = migrate_session_state(read_mapping(state_path))
    atomic_write_json(state_path, state)
    return {"status": "PASS", "project_root": root.as_posix(), "state": state, "non_destructive": True}
