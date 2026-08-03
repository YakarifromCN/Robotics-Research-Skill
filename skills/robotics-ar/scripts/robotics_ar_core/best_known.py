"""Best-Known State with reproducibility and Pareto safeguards."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Mapping, Optional

from .canonical import sha256_obj
from .models import utc_now
from .schema_validation import SchemaValidationError, validate_artifact
from .structured import read_mapping, write_structured


class BestKnownError(RuntimeError):
    """Raised when a candidate cannot be promoted to Best-Known State."""


def _value(metrics: Mapping[str, Any], name: str) -> Optional[float]:
    value = metrics.get(name)
    if isinstance(value, Mapping):
        value = value.get("value", value.get("mean"))
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dominates(left: Mapping[str, Any], right: Mapping[str, Any], objectives: Mapping[str, str]) -> bool:
    better_or_equal = True
    strictly_better = False
    for name, direction in objectives.items():
        a = _value(left.get("primary_metrics", left.get("metrics", {})), name)
        b = _value(right.get("primary_metrics", right.get("metrics", {})), name)
        if a is None or b is None:
            return False
        if direction == "minimize":
            if a > b:
                better_or_equal = False
            if a < b:
                strictly_better = True
        else:
            if a < b:
                better_or_equal = False
            if a > b:
                strictly_better = True
    return better_or_equal and strictly_better


def validate_candidate(candidate: Mapping[str, Any]) -> None:
    required = ("trial_id", "code_version", "configuration", "environment_fingerprint", "baseline_relationship", "primary_metrics", "raw_evidence", "validation_status", "reproduction_command")
    missing = [key for key in required if key not in candidate]
    if missing:
        raise BestKnownError(f"best-known candidate missing: {missing}")
    if candidate.get("validation_status") not in {"REPRODUCED", "REPRODUCED_WITH_VARIANCE"}:
        raise BestKnownError("only reproduced candidates can become best-known")
    if candidate.get("validation_status") == "REPRODUCED_WITH_VARIANCE" and candidate.get("user_approved_variance") is not True:
        raise BestKnownError("variance candidate requires explicit user approval")
    if not candidate.get("raw_evidence"):
        raise BestKnownError("raw evidence is required")
    evidence = candidate.get("raw_evidence")
    if not isinstance(evidence, Mapping):
        raise BestKnownError("raw evidence must be a mapping with a SHA-256 receipt")
    hashes = list(_sha256_claims(evidence))
    if not hashes or not all(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) for value in hashes):
        raise BestKnownError("raw evidence must carry complete SHA-256 receipts")


def _replication_count(candidate: Mapping[str, Any]) -> int:
    for key in ("seeds", "validation_runs", "independent_runs", "replications"):
        value = candidate.get(key)
        if isinstance(value, (list, tuple, set)):
            return len(value)
        if isinstance(value, int) and value >= 0:
            return value
    return 0


def _sha256_claims(value: Any):
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key).lower()
            if key_text == "sha256" or key_text.endswith("_sha256"):
                yield child
            else:
                yield from _sha256_claims(child)
    elif isinstance(value, list):
        for child in value:
            yield from _sha256_claims(child)


class BestKnownState:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        if self.path.exists():
            value = read_mapping(self.path)
            if value.get("schema_version") != "robotics-ar-best-known-state.v1":
                raise BestKnownError("unsupported best-known schema")
            if value.get("best_known_sha256") and value.get("best_known_sha256") != sha256_obj({key: item for key, item in value.items() if key != "best_known_sha256"}):
                raise BestKnownError("best-known state hash mismatch")
            try:
                validate_artifact("robotics-ar-best-known-state.v1", value)
            except SchemaValidationError as exc:
                raise BestKnownError(str(exc)) from exc
            return value
        return {"schema_version": "robotics-ar-best-known-state.v1", "baseline_trial": None, "current_primary_best": None, "current_stable_best": None, "pareto_candidates": [], "invalidated_trials": [], "latest_trial": None, "metric_versions": {}, "updated_at": utc_now()}

    def save(self) -> Path:
        value = dict(self.data)
        value["updated_at"] = utc_now()
        value.pop("best_known_sha256", None)
        value["best_known_sha256"] = sha256_obj(value)
        try:
            validate_artifact("robotics-ar-best-known-state.v1", value)
        except SchemaValidationError as exc:
            raise BestKnownError(str(exc)) from exc
        self.data = value
        return write_structured(self.path, value)

    def promote(self, candidate: Mapping[str, Any], *, objectives: Optional[Mapping[str, str]] = None, stable: bool = False) -> dict[str, Any]:
        validate_candidate(candidate)
        value = dict(candidate)
        candidate_versions = value.get("metric_versions", {})
        if candidate_versions and not isinstance(candidate_versions, Mapping):
            raise BestKnownError("metric_versions must be a mapping")
        current_versions = self.data.get("metric_versions", {})
        if current_versions and candidate_versions:
            for metric, version in candidate_versions.items():
                if metric in current_versions and current_versions[metric] != version:
                    raise BestKnownError(f"metric version drift requires reconciliation: {metric}")
        if stable and _replication_count(value) < 2:
            raise BestKnownError("stable best requires at least two independent seeds or validation runs")
        objectives = dict(objectives or {next(iter(value.get("primary_metrics", {"primary": "max"})), "primary"): "maximize"})
        current = self.data.get("current_primary_best")
        if current is not None and not _dominates(value, current, objectives) and not _dominates(current, value, objectives):
            # A non-dominated trade-off is retained, but a random single-seed
            # result cannot displace the primary or stable candidate.
            if not any(item.get("trial_id") == value.get("trial_id") for item in self.data.get("pareto_candidates", [])):
                self.data.setdefault("pareto_candidates", []).append(value)
        elif current is None or _dominates(value, current, objectives):
            self.data["current_primary_best"] = value
        else:
            self.data.setdefault("pareto_candidates", []).append(value)
        if stable:
            existing = self.data.get("current_stable_best")
            if existing is None or _replication_count(value) >= _replication_count(existing):
                self.data["current_stable_best"] = value
        if candidate_versions:
            merged_versions = dict(current_versions)
            merged_versions.update({str(key): str(version) for key, version in candidate_versions.items()})
            self.data["metric_versions"] = merged_versions
        self.data["latest_trial"] = value
        self.save()
        return dict(self.data)

    def invalidate(self, trial_id: str, *, reason: str) -> dict[str, Any]:
        self.data.setdefault("invalidated_trials", []).append({"trial_id": trial_id, "reason": reason, "at": utc_now()})
        for key in ("current_primary_best", "current_stable_best"):
            if self.data.get(key, {}).get("trial_id") == trial_id:
                self.data[key] = None
        self.save()
        return dict(self.data)

    def current(self) -> dict[str, Any]:
        return dict(self.data)


def build_candidate(*, trial_id: str, code_version: str, configuration: Mapping[str, Any], environment_fingerprint: str, baseline_relationship: str, primary_metrics: Mapping[str, Any], secondary_metrics: Optional[Mapping[str, Any]] = None, raw_evidence: Mapping[str, Any], validation_status: str, reproduction_command: list[str], limitations: Optional[list[str]] = None, **extra: Any) -> dict[str, Any]:
    candidate = {"trial_id": trial_id, "code_version": code_version, "configuration": dict(configuration), "environment_fingerprint": environment_fingerprint, "baseline_relationship": baseline_relationship, "primary_metrics": dict(primary_metrics), "secondary_metrics": dict(secondary_metrics or {}), "raw_evidence": dict(raw_evidence), "validation_status": validation_status, "limitations": list(limitations or []), "reproduction_command": list(reproduction_command), "created_at": utc_now(), **extra}
    return candidate
