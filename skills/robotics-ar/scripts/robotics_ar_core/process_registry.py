"""记录进程并提供幂等、非强制的停止协议。

Record processes and provide an idempotent, non-coercive stop protocol.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import signal
from typing import Any, Dict, List, Optional

from .atomic_io import atomic_write_json
from .models import utc_now


class ProcessRegistry:
    """保存 active process metadata。 / Store active process metadata."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def _read(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, entries: List[Dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.path, entries)

    def register(self, pid: int, command: List[str], cwd: Path | str, stdout: str = "", stderr: str = "") -> Dict[str, Any]:
        """登记进程。 / Register a process."""

        entry = {"pid": int(pid), "command": list(command), "cwd": str(cwd), "stdout": stdout, "stderr": stderr, "registered_at": utc_now(), "status": "RUNNING"}
        entries = [item for item in self._read() if item.get("pid") != pid]
        entries.append(entry)
        self._write(entries)
        return entry

    def mark_stopped(self, pid: int, status: str = "STOPPED", *, stdout: str = "", stderr: str = "") -> None:
        """标记进程停止并保存输出。 / Mark a process stopped and save output."""

        entries = self._read()
        for entry in entries:
            if entry.get("pid") == pid:
                entry["status"] = status
                entry["stopped_at"] = utc_now()
                if stdout:
                    entry["stdout"] = stdout
                if stderr:
                    entry["stderr"] = stderr
        self._write(entries)

    @staticmethod
    def is_alive(pid: int) -> bool:
        """判断 PID 是否存在。 / Check whether a PID exists."""

        try:
            os.kill(int(pid), 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError:
            return False
        return True

    def stale_entries(self) -> List[Dict[str, Any]]:
        """返回登记但已不存在的进程。 / Return registered but missing processes."""

        return [entry for entry in self._read() if entry.get("status") == "RUNNING" and not self.is_alive(int(entry["pid"]))]

    def stop(self, pid: int, *, grace_s: float = 0.2) -> Dict[str, Any]:
        """幂等地请求停止，不自动 retry。 / Idempotently request stop without retry."""

        if not self.is_alive(pid):
            self.mark_stopped(pid, "ALREADY_STOPPED")
            return {"pid": pid, "status": "ALREADY_STOPPED"}
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
            status = "STOP_REQUESTED"
        except (ProcessLookupError, PermissionError, OSError) as exc:
            status = "STOP_FAILED"
            self.mark_stopped(pid, status)
            return {"pid": pid, "status": status, "error": str(exc)}
        self.mark_stopped(pid, status)
        return {"pid": pid, "status": status}
