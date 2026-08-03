"""Supervisor-owned shared blackboard reconstructed from structured receipts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional

from .canonical import sha256_obj
from .models import utc_now
from .schema_validation import SchemaValidationError, validate_artifact
from .structured import read_mapping, write_structured


class BlackboardError(RuntimeError):
    """Raised when a non-supervisor attempts a global state write."""


BLACKBOARD_KEYS = ("current-objective", "project-core-ref", "active-contract-ref", "current-baseline-ref", "current-best-ref", "active-trial-ref", "implementation-status", "test-status", "environment-status", "analysis-status", "expert-status", "budget-status", "pending-decisions")


class Blackboard:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.state_path = self.root / "state.json"

    def _read(self) -> dict[str, Any]:
        if self.state_path.exists():
            value = read_mapping(self.state_path)
            try:
                validate_artifact("robotics-ar-blackboard-state.v1", value)
            except SchemaValidationError as exc:
                raise BlackboardError(str(exc)) from exc
            expected = value.get("blackboard_sha256")
            if expected:
                actual = sha256_obj({key: item for key, item in value.items() if key != "blackboard_sha256"})
                if expected != actual:
                    raise BlackboardError("blackboard hash mismatch")
            return value
        return {"schema_version": "robotics-ar-blackboard-state.v1", "updated_at": utc_now(), "values": {}}

    @staticmethod
    def _set_hash(state: dict[str, Any]) -> None:
        """Recompute the state hash without hashing the previous hash value."""

        state.pop("blackboard_sha256", None)
        state["blackboard_sha256"] = sha256_obj(state)

    def update(self, key: str, value: Any, *, actor: str = "supervisor", receipt_ref: str = "") -> dict[str, Any]:
        if actor != "supervisor":
            raise BlackboardError("only Supervisor may update the global blackboard")
        if key not in BLACKBOARD_KEYS:
            raise BlackboardError(f"unknown blackboard key: {key}")
        state = self._read()
        state.setdefault("values", {})[key] = {"value": value, "receipt_ref": receipt_ref, "updated_at": utc_now()}
        state["updated_at"] = utc_now()
        self._set_hash(state)
        try:
            validate_artifact("robotics-ar-blackboard-state.v1", state)
        except SchemaValidationError as exc:
            raise BlackboardError(str(exc)) from exc
        write_structured(self.state_path, state)
        write_structured(self.root / f"{key}.json", state["values"][key])
        return state

    def update_from_receipt(self, key: str, receipt: Mapping[str, Any], *, actor: str = "supervisor") -> dict[str, Any]:
        ref = str(receipt.get("receipt_sha256", receipt.get("proposal_sha256", "")))
        if not ref:
            raise BlackboardError("receipt reference is required")
        return self.update(key, dict(receipt), actor=actor, receipt_ref=ref)

    def get(self, key: str) -> Optional[dict[str, Any]]:
        return self._read().get("values", {}).get(key)

    def rebuild(self, receipts: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
        state = self._read()
        for key, receipt in receipts.items():
            if key not in BLACKBOARD_KEYS:
                raise BlackboardError(f"unknown blackboard key: {key}")
            ref = receipt.get("receipt_sha256", receipt.get("proposal_sha256"))
            if not ref:
                raise BlackboardError(f"receipt hash missing for {key}")
            state.setdefault("values", {})[key] = {"value": dict(receipt), "receipt_ref": ref, "updated_at": utc_now()}
        state["updated_at"] = utc_now()
        self._set_hash(state)
        try:
            validate_artifact("robotics-ar-blackboard-state.v1", state)
        except SchemaValidationError as exc:
            raise BlackboardError(str(exc)) from exc
        write_structured(self.state_path, state)
        return state
