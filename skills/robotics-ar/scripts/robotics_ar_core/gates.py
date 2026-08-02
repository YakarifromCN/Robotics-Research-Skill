"""实现批准 hash、漂移检查和一次性消费。

Implement approval hashes, drift checks, and single-use consumption.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from .atomic_io import atomic_write_json, read_json
from .canonical import sha256_obj
from .receipts import file_sha256
from .models import utc_now


class GateError(ValueError):
    """批准 gate 失败。 / Raised when an approval gate fails."""


def subject_hash(path: Path | str) -> str:
    """计算文件或目录 subject hash。 / Hash a file or directory subject."""

    target = Path(path)
    if target.is_file():
        return file_sha256(target)
    if target.is_dir():
        from .receipts import tree_fingerprint

        return tree_fingerprint(target)
    raise GateError(f"subject does not exist: {path}")


class ApprovalManager:
    """管理 hash-bound、single-use approvals。 / Manage hash-bound single-use approvals."""

    def __init__(self, approvals_dir: Path | str) -> None:
        self.approvals_dir = Path(approvals_dir)
        self.approvals_dir.mkdir(parents=True, exist_ok=True)

    def create(self, gate: str, subject_path: Path | str, *, scope: str = "single-use", approval_id: Optional[str] = None) -> Dict[str, Any]:
        """创建未消费批准。 / Create an unused approval."""

        if scope not in {"single-use", "persistent-until-drift"}:
            raise GateError("invalid approval scope")
        identifier = approval_id or f"APR-{len(list(self.approvals_dir.glob('APR-*.json'))) + 1:06d}"
        approval = {
            "schema_version": "robotics-ar-approval.v1",
            "approval_id": identifier,
            "gate": gate,
            "subject_path": Path(subject_path).as_posix(),
            "subject_sha256": subject_hash(subject_path),
            "approved_at": utc_now(),
            "scope": scope,
            "status": "unused",
        }
        approval["approval_sha256"] = sha256_obj(approval)
        atomic_write_json(self.approvals_dir / f"{identifier}.json", approval)
        return approval

    def consume(self, approval_path: Path | str) -> Dict[str, Any]:
        """验证当前 subject hash 并消费批准一次。

        Validate the current subject hash and consume an approval once.
        """

        path = Path(approval_path)
        approval = read_json(path)
        if approval.get("status") != "unused":
            raise GateError("approval is not unused")
        expected_receipt_hash = approval.get("approval_sha256")
        actual_receipt_hash = sha256_obj({key: value for key, value in approval.items() if key != "approval_sha256"})
        if not expected_receipt_hash or expected_receipt_hash != actual_receipt_hash:
            raise GateError("approval receipt hash invalid")
        current = subject_hash(approval["subject_path"])
        if current != approval.get("subject_sha256"):
            approval["status"] = "invalidated"
            approval["approval_sha256"] = sha256_obj({key: value for key, value in approval.items() if key != "approval_sha256"})
            atomic_write_json(path, approval)
            raise GateError("approval subject hash drift")
        approval["status"] = "consumed"
        approval["consumed_at"] = utc_now()
        approval["approval_sha256"] = sha256_obj({key: value for key, value in approval.items() if key != "approval_sha256"})
        atomic_write_json(path, approval)
        return approval

    def invalidate_drift(self) -> int:
        """把漂移批准标为 invalidated。 / Invalidate approvals with subject drift."""

        count = 0
        for path in sorted(self.approvals_dir.glob("APR-*.json")):
            approval = read_json(path)
            if approval.get("status") != "unused":
                continue
            try:
                current = subject_hash(approval["subject_path"])
            except GateError:
                current = None
            if current != approval.get("subject_sha256"):
                approval["status"] = "invalidated"
                approval["approval_sha256"] = sha256_obj({key: value for key, value in approval.items() if key != "approval_sha256"})
                atomic_write_json(path, approval)
                count += 1
        return count
