"""Hypothesis-driven trial proposals, priority ordering, and queue states."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Optional

from .canonical import sha256_obj
from .history_reconstruction import DoNotRepeatRegistry, trial_fingerprint
from .models import utc_now
from .schema_validation import SchemaValidationError, validate_artifact
from .structured import read_mapping, write_structured


class TrialQueueError(RuntimeError):
    """Raised when a proposal is malformed or repeats a forbidden trial."""


VALID_QUEUE_STATES = frozenset({"PROPOSED", "QUEUED", "ACTIVE", "COMPLETED", "REJECTED", "BLOCKED"})
_SAFE_TRIAL_ID = re.compile(r"^[^/\\\x00\r\n]+$")


def proposal_hash(proposal: Mapping[str, Any]) -> str:
    mutable = {"proposal_sha256", "status", "priority", "queue_sha256", "activated_at", "completed_at", "decision", "retry"}
    return sha256_obj({key: value for key, value in proposal.items() if key not in mutable})


def validate_trial_id(value: Any) -> str:
    """Validate an ID before it is used as a queue or experiment directory."""

    trial_id = str(value)
    if not trial_id or trial_id in {".", ".."} or not _SAFE_TRIAL_ID.fullmatch(trial_id):
        raise TrialQueueError("trial_id must be a safe path component")
    return trial_id


def queue_hash(value: Mapping[str, Any]) -> str:
    return sha256_obj({key: item for key, item in value.items() if key != "queue_sha256"})


def validate_proposal(proposal: Mapping[str, Any], *, require_hash: bool = True) -> None:
    required = ("schema_version", "trial_id", "parent_contract", "hypothesis", "uncertainty_target", "change", "experiment", "metrics", "resource_estimate", "rollback", "status")
    missing = [key for key in required if key not in proposal]
    if missing:
        raise TrialQueueError(f"trial proposal missing: {missing}")
    if proposal.get("schema_version") != "robotics-ar-trial-proposal.v1":
        raise TrialQueueError("unsupported trial proposal schema")
    validate_trial_id(proposal.get("trial_id", ""))
    if not str(proposal.get("parent_contract", "")).strip():
        raise TrialQueueError("trial proposal must bind to an approved contract")
    if proposal.get("status") not in VALID_QUEUE_STATES:
        raise TrialQueueError("invalid trial proposal status")
    hypothesis = proposal.get("hypothesis")
    if not isinstance(hypothesis, Mapping) or not hypothesis.get("statement") or not hypothesis.get("expected_observation") or not hypothesis.get("falsification_condition"):
        raise TrialQueueError("hypothesis requires statement, expected observation, and falsification condition")
    change = proposal.get("change")
    if not isinstance(change, Mapping) or int(change.get("tier", 3)) not in {0, 1, 2, 3}:
        raise TrialQueueError("change tier must be 0, 1, 2, or 3")
    if not bool(change.get("minimal_patch", False)):
        raise TrialQueueError("minimal_patch must be true")
    if require_hash and proposal.get("proposal_sha256") != proposal_hash(proposal):
        raise TrialQueueError("trial proposal hash mismatch")
    try:
        validate_artifact("robotics-ar-trial-proposal.v1", proposal)
    except SchemaValidationError as exc:
        raise TrialQueueError(str(exc)) from exc


def build_proposal(values: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(values, Mapping):
        raise TrialQueueError("proposal input must be an object")
    change = dict(values.get("change", {}))
    change.setdefault("tier", 0)
    change.setdefault("minimal_patch", True)
    change.setdefault("components", [])
    hypothesis = dict(values.get("hypothesis", {}))
    proposal = {
        "schema_version": "robotics-ar-trial-proposal.v1",
        "trial_id": str(values.get("trial_id", "trial-0001")),
        "parent_contract": str(values.get("parent_contract", "")),
        "current_best_trial": values.get("current_best_trial"),
        "hypothesis": hypothesis,
        "uncertainty_target": values.get("uncertainty_target", ""),
        "change": change,
        "experiment": dict(values.get("experiment", {})),
        "metrics": dict(values.get("metrics", {})),
        "resource_estimate": dict(values.get("resource_estimate", {})),
        "rollback": dict(values.get("rollback", {})),
        "expert_assessment_receipts": list(values.get("expert_assessment_receipts", [])),
        "status": "PROPOSED",
        "created_at": utc_now(),
    }
    proposal["trial_fingerprint"] = trial_fingerprint(proposal)
    proposal["proposal_sha256"] = proposal_hash(proposal)
    validate_proposal(proposal)
    return proposal


def priority_score(proposal: Mapping[str, Any]) -> float:
    estimate = proposal.get("resource_estimate", {}) if isinstance(proposal.get("resource_estimate", {}), Mapping) else {}
    expected = float(estimate.get("expected_uncertainty_reduction", proposal.get("uncertainty_reduction", 1.0)) or 0.0)
    implementation = float(estimate.get("implementation_cost", 1.0) or 0.0)
    compute = float(estimate.get("compute_cost", estimate.get("wall_time_minutes", 1.0)) or 0.0)
    risk = float(estimate.get("execution_risk", 0.0) or 0.0)
    return expected / max(implementation + compute + risk, 1e-9)


class TrialQueue:
    def __init__(self, root: Path | str, *, do_not_repeat: Optional[Path | str] = None) -> None:
        self.root = Path(root)
        self.queued = self.root / "queued"
        self.active = self.root / "active"
        self.completed = self.root / "completed"
        self.rejected = self.root / "rejected"
        self.blocked = self.root / "blocked"
        for path in (self.queued, self.active, self.completed, self.rejected, self.blocked):
            path.mkdir(parents=True, exist_ok=True)
        self.registry = DoNotRepeatRegistry(do_not_repeat or self.root.parent / "takeover" / "history" / "do-not-repeat.yaml")

    def add(self, proposal: Mapping[str, Any], *, retry_justification: str = "") -> dict[str, Any]:
        validate_proposal(proposal)
        retry = self.registry.retry_evidence(proposal, justification=retry_justification)
        if self.registry.match(proposal) is not None and retry is None:
            raise TrialQueueError("proposal is blocked by Do-Not-Repeat Registry")
        path = self.queued / f"{proposal['trial_id']}.yaml"
        value = dict(proposal)
        if retry is not None:
            value["retry"] = retry
        value["status"] = "QUEUED"
        value["priority"] = priority_score(value)
        value["queue_sha256"] = queue_hash(value)
        write_structured(path, value)
        return value

    def next(self) -> Optional[dict[str, Any]]:
        if any(self.active.glob("*.yaml")):
            raise TrialQueueError("one active code-writing trial is already registered")
        candidates = []
        for path in self.queued.glob("*.yaml"):
            value = read_mapping(path)
            validate_proposal(value)
            candidates.append((float(value.get("priority", 0.0)), path.name, path, value))
        if not candidates:
            return None
        _, _, path, value = sorted(candidates, key=lambda item: (-item[0], item[1]))[0]
        value["status"] = "ACTIVE"
        value["activated_at"] = utc_now()
        value["queue_sha256"] = queue_hash(value)
        write_structured(self.active / path.name, value)
        path.unlink()
        return value

    def complete(self, trial_id: str, *, status: str, decision: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
        if status not in {"COMPLETED", "REJECTED", "BLOCKED"}:
            raise TrialQueueError("invalid completion status")
        path = self.active / f"{trial_id}.yaml"
        if not path.exists():
            raise TrialQueueError("active trial not found")
        value = read_mapping(path)
        value["status"] = status
        value["decision"] = dict(decision or {})
        if status == "COMPLETED" and not value["decision"]:
            raise TrialQueueError("a completed trial requires an explicit conclusion")
        value["completed_at"] = utc_now()
        value["queue_sha256"] = queue_hash(value)
        destination = self.completed if status == "COMPLETED" else self.blocked if status == "BLOCKED" else self.rejected
        write_structured(destination / path.name, value)
        path.unlink()
        reason = str(value["decision"].get("decision") or value["decision"].get("reason") or status.lower())
        self.registry.add(value, reason=reason, category="COMPLETED_CONCLUSION" if status == "COMPLETED" else f"TRIAL_{status}")
        return value

    def list(self, status: Optional[str] = None) -> list[dict[str, Any]]:
        groups = {"QUEUED": self.queued, "ACTIVE": self.active, "COMPLETED": self.completed, "REJECTED": self.rejected, "BLOCKED": self.blocked}
        paths = [groups[status]] if status in groups else list(groups.values())
        values = []
        for path in paths:
            for item in sorted(path.glob("*.yaml")):
                values.append(read_mapping(item))
        return values
