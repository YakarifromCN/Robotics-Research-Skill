"""写入中英双语 report、handoff 和用户指令快照。

Write bilingual reports, handoffs, and user-instruction snapshots.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from .atomic_io import atomic_write_bytes


def write_report(report_path: Path | str, *, title: str, state: str, summary: str, actions: Iterable[str] = ()) -> None:
    """写一个可恢复的报告。 / Write a recoverable report."""

    lines = [
        f"# {title}",
        "",
        "## 中文",
        "",
        f"状态：`{state}`。",
        "",
        summary,
        "",
        "后续动作：",
        "",
        *[f"- {item}" for item in actions],
        "",
        "# English",
        "",
        f"State: `{state}`.",
        "",
        summary,
        "",
        "Next actions:",
        "",
        *[f"- {item}" for item in actions],
        "",
    ]
    atomic_write_bytes(Path(report_path), "\n".join(lines).encode("utf-8"))


def write_handoff(handoff_path: Path | str, *, state: str, session_id: str, reason: str) -> None:
    """写出最小 handoff。 / Write a minimal handoff."""

    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    text = (
        "# Robotics-AR handoff\n\n"
        "## 中文\n\n"
        f"session：`{session_id}`\n\n状态：`{state}`\n\n原因：{reason}\n\n"
        "恢复只读取磁盘工件、事件日志和 receipt。\n\n"
        "# English\n\n"
        f"Session: `{session_id}`\n\nState: `{state}`\n\nReason: {reason}\n\n"
        "Resume reads only disk artifacts, the event log, and receipts.\n\n"
        f"Generated: {timestamp}\n"
    )
    atomic_write_bytes(Path(handoff_path), text.encode("utf-8"))
