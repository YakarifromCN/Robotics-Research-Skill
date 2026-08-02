"""实现 append-only event log 和从事件重建状态。

Implement an append-only event log and event-based state reconstruction.
"""

from __future__ import annotations

from pathlib import Path
import json
from typing import Any, Dict, Iterable, List, Mapping, Optional

from .atomic_io import atomic_write_bytes
from .canonical import canonical_bytes, ensure_finite, sha256_obj
from .models import utc_now


class EventLogError(ValueError):
    """事件日志非法。 / Raised for invalid event logs."""


class EventLog:
    """提供顺序 ID、重复检测和 state reconstruction。 / Provide ordered IDs, duplicate checks, and reconstruction."""

    def __init__(self, path: Path | str, session_id: str) -> None:
        self.path = Path(path)
        self.session_id = session_id

    def read_events(self) -> List[Dict[str, Any]]:
        """读取所有事件并验证 ID 顺序。 / Read and validate all events."""

        if not self.path.exists():
            return []
        events: List[Dict[str, Any]] = []
        seen = set()
        for line_number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise EventLogError(f"invalid JSON at line {line_number}") from exc
            if event.get("schema_version") != "robotics-ar-event.v1":
                raise EventLogError(f"event schema mismatch at line {line_number}")
            try:
                ensure_finite(event)
            except ValueError as exc:
                raise EventLogError(f"non-finite event at line {line_number}") from exc
            if event.get("payload_sha256") != sha256_obj(event.get("payload", {})):
                raise EventLogError(f"event payload hash mismatch at line {line_number}")
            event_id = event.get("event_id")
            if event_id in seen:
                raise EventLogError(f"duplicate event id: {event_id}")
            seen.add(event_id)
            events.append(event)
        for expected, event in enumerate(events, 1):
            if event.get("event_id") != f"EVT-{expected:06d}":
                raise EventLogError(f"event sequence mismatch at {expected}")
            if event.get("session_id") != self.session_id:
                raise EventLogError("event session mismatch")
        return events

    def append(
        self,
        event_type: str,
        actor: str,
        previous_state: str,
        new_state: str,
        payload: Optional[Mapping[str, Any]] = None,
        artifact_refs: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        """追加一个 canonical event，且禁止重写历史。

        Append one canonical event without rewriting history.
        """

        events = self.read_events()
        event_id = f"EVT-{len(events) + 1:06d}"
        payload_obj = dict(payload or {})
        event = {
            "schema_version": "robotics-ar-event.v1",
            "event_id": event_id,
            "session_id": self.session_id,
            "timestamp": utc_now(),
            "event_type": event_type,
            "actor": actor,
            "previous_state": previous_state,
            "new_state": new_state,
            "artifact_refs": list(artifact_refs or []),
            "payload_sha256": sha256_obj(payload_obj),
            "payload": payload_obj,
        }
        line = canonical_bytes(event) + b"\n"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("ab") as handle:
            handle.write(line)
            handle.flush()
            import os

            os.fsync(handle.fileno())
        return event

    def reconstruct(self, initial_state: str = "UNINITIALIZED") -> Dict[str, Any]:
        """从事件重建最后状态和转移历史。

        Reconstruct the last state and transition history from events.
        """

        state = initial_state
        history: List[str] = [state]
        for event in self.read_events():
            if event.get("previous_state") != state:
                raise EventLogError("event previous_state does not match reconstructed state")
            state = str(event["new_state"])
            history.append(state)
        return {"state": state, "history": history, "event_count": len(history) - 1}
