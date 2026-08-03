"""Project Core compilation and drift protection for midstream takeover."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from .atomic_io import atomic_write_bytes
from .canonical import ensure_finite, sha256_obj
from .models import utc_now
from .schema_validation import SchemaValidationError, validate_artifact
from .structured import read_mapping, write_structured


class ProjectCoreError(ValueError):
    """Raised when the frozen research core is incomplete or drifts."""


CORE_STATUSES = frozenset({"frozen", "provisional", "unsupported"})
FACT_BUCKETS = ("user_asserted", "repository_observed", "agent_inferred", "unresolved")


def _list(value: Any, field: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ProjectCoreError(f"{field} must be a list")
    return list(value)


def core_hash(core: Mapping[str, Any]) -> str:
    """Return the hash over immutable Project Core content."""

    ignored = {"project_core_sha256", "approval", "approved_by_user", "approval_id", "approved_at"}
    return sha256_obj({key: value for key, value in core.items() if key not in ignored})


def validate_project_core(core: Mapping[str, Any], *, require_hash: bool = True) -> None:
    """Validate generic takeover invariants without interpreting domain science."""

    if not isinstance(core, Mapping):
        raise ProjectCoreError("project core must be a mapping")
    required = ("schema_version", "project_id", "research_problem", "core_method", "frozen_invariants", "modifiable_components", "forbidden_pivots", "current_bottleneck", "current_batch_goal", "success_criteria", "source_evidence", "approval")
    missing = [key for key in required if key not in core]
    if missing:
        raise ProjectCoreError(f"project core missing: {missing}")
    if core.get("schema_version") != "robotics-ar-project-core.v1":
        raise ProjectCoreError("unsupported project core schema")
    if not str(core.get("project_id", "")).strip():
        raise ProjectCoreError("project_id is required")
    for field in ("research_problem", "core_method", "current_bottleneck", "current_batch_goal"):
        if not isinstance(core.get(field), str) or not core[field].strip():
            raise ProjectCoreError(f"{field} must be a non-empty string")
    for field in ("frozen_invariants", "modifiable_components", "forbidden_pivots"):
        _list(core.get(field), field)
    if not isinstance(core.get("success_criteria"), Mapping):
        raise ProjectCoreError("success_criteria must be an object")
    if not isinstance(core.get("source_evidence"), Mapping):
        raise ProjectCoreError("source_evidence must be an object")
    if not isinstance(core.get("approval"), Mapping):
        raise ProjectCoreError("approval must be an object")
    if core.get("current_claims") is not None:
        claims = _list(core.get("current_claims"), "current_claims")
        for claim in claims:
            if not isinstance(claim, Mapping) or not str(claim.get("id", "")) or claim.get("status") not in CORE_STATUSES:
                raise ProjectCoreError("current_claims must contain id and a valid status")
    for bucket in FACT_BUCKETS:
        if bucket in core and not isinstance(core[bucket], (list, Mapping)):
            raise ProjectCoreError(f"{bucket} must be a list or object")
    ensure_finite(dict(core))
    if require_hash and core.get("project_core_sha256") != core_hash(core):
        raise ProjectCoreError("project core hash mismatch")
    try:
        validate_artifact("robotics-ar-project-core.v1", core)
    except SchemaValidationError as exc:
        raise ProjectCoreError(str(exc)) from exc


def compile_project_core(
    values: Mapping[str, Any],
    *,
    project_id: Optional[str] = None,
    user_statement_sha256: str = "",
    repository_snapshot_sha256: str = "",
) -> dict[str, Any]:
    """Compile a frozen-core candidate; approval is deliberately false."""

    if not isinstance(values, Mapping):
        raise ProjectCoreError("project core input must be a mapping")
    source = dict(values.get("source_evidence", {}))
    if user_statement_sha256:
        source["user_statement_sha256"] = user_statement_sha256
    if repository_snapshot_sha256:
        source["repository_snapshot_sha256"] = repository_snapshot_sha256
    approval = dict(values.get("approval", {}))
    approval.setdefault("required", True)
    # Compilation always creates a new candidate.  User approval from an
    # older core must never be copied into the new immutable subject.
    approval["approved_by_user"] = False
    for key in ("approval_id", "approved_at"):
        approval.pop(key, None)
    raw_claims = list(values.get("current_claims", []) or [])
    if not raw_claims and values.get("frozen_contributions"):
        raw_claims = [{"id": f"claim-{index:02d}", "text": item, "status": "provisional"} for index, item in enumerate(values.get("frozen_contributions", []), 1)]
    normalized_claims = []
    for index, claim in enumerate(raw_claims, 1):
        if isinstance(claim, Mapping):
            item = dict(claim)
            item.setdefault("id", f"claim-{index:02d}")
            item.setdefault("status", "provisional")
        else:
            item = {"id": f"claim-{index:02d}", "text": str(claim), "status": "provisional"}
        normalized_claims.append(item)
    core: dict[str, Any] = {
        "schema_version": "robotics-ar-project-core.v1",
        "project_id": str(project_id or values.get("project_id", "")).strip(),
        "research_problem": str(values.get("research_problem", "")),
        "core_method": str(values.get("core_method", "")),
        "current_claims": normalized_claims,
        "frozen_invariants": list(values.get("frozen_invariants", values.get("frozen_contributions", [])) or []),
        "modifiable_components": list(values.get("modifiable_components", []) or []),
        "conditionally_modifiable": list(values.get("conditionally_modifiable", []) or []),
        "forbidden_pivots": list(values.get("forbidden_pivots", values.get("forbidden_changes", [])) or []),
        "current_bottleneck": str(values.get("current_bottleneck", "")),
        "current_batch_goal": str(values.get("current_batch_goal", "")),
        "success_criteria": dict(values.get("success_criteria", {})),
        "source_evidence": source,
        "fact_buckets": {bucket: list(values.get(bucket, [])) if isinstance(values.get(bucket, []), list) else dict(values.get(bucket, {})) for bucket in FACT_BUCKETS},
        "approval": approval,
        "created_at": utc_now(),
    }
    core["project_core_sha256"] = core_hash(core)
    validate_project_core(core)
    return core


def save_project_core(path: Path | str, core: Mapping[str, Any]) -> Path:
    """Validate and save Project Core as canonical JSON/YAML-subset."""

    validate_project_core(core)
    return write_structured(path, dict(core))


def load_project_core(path: Path | str) -> dict[str, Any]:
    core = read_mapping(path)
    validate_project_core(core)
    return core


def mark_project_core_approved(core: Mapping[str, Any], *, approval_id: str) -> dict[str, Any]:
    """Return an approved copy while keeping its immutable content hash stable."""

    validate_project_core(core)
    if not approval_id:
        raise ProjectCoreError("approval_id is required")
    updated = dict(core)
    approval = dict(updated.get("approval", {}))
    approval.update({"required": True, "approved_by_user": True, "approval_id": approval_id, "approved_at": utc_now()})
    updated["approval"] = approval
    updated["approved_by_user"] = True
    updated["approval_id"] = approval_id
    updated["approved_at"] = approval["approved_at"]
    updated["project_core_sha256"] = core_hash(updated)
    validate_project_core(updated)
    return updated


def assert_project_core_approved(core: Mapping[str, Any]) -> None:
    """Fail closed unless the core is valid, approved, and still hash-bound."""

    validate_project_core(core)
    approval = core.get("approval", {})
    if not isinstance(approval, Mapping) or approval.get("approved_by_user") is not True:
        raise ProjectCoreError("project core is not user-approved")
    if not core.get("approval_id"):
        raise ProjectCoreError("project core approval id is missing")


def project_core_drift(path: Path | str, expected_hash: str) -> bool:
    """Return whether the current core differs from an expected immutable hash."""

    core = load_project_core(path)
    return core_hash(core) != expected_hash


def write_core_summary(path: Path | str, core: Mapping[str, Any]) -> Path:
    """Write a human-readable core summary without replacing the structured artifact."""

    validate_project_core(core)
    lines = [
        "# Project Core",
        "",
        f"Project: `{core['project_id']}`",
        f"Research problem: {core['research_problem']}",
        f"Core method: {core['core_method']}",
        f"Current bottleneck: {core['current_bottleneck']}",
        f"Current batch goal: {core['current_batch_goal']}",
        "",
        "## Frozen invariants",
        "",
        *[f"- {item}" for item in core.get("frozen_invariants", [])],
        "",
        "## Allowed changes",
        "",
        *[f"- {item}" for item in core.get("modifiable_components", [])],
        "",
        "## Forbidden pivots",
        "",
        *[f"- {item}" for item in core.get("forbidden_pivots", [])],
        "",
        f"Core hash: `{core['project_core_sha256']}`",
        "",
    ]
    target = Path(path)
    atomic_write_bytes(target, "\n".join(lines).encode("utf-8"))
    return target
