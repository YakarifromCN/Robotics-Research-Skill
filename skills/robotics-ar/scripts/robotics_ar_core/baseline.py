"""Baseline candidate selection, reproduction, and recovery receipts."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Optional

from .atomic_io import atomic_write_json, runtime_root, visible_directory
from .canonical import sha256_obj
from .environment import EnvironmentAdapter, EnvironmentError, validate_environment_receipt
from .models import utc_now
from .project_core import core_hash, validate_project_core
from .schema_validation import SchemaValidationError, validate_artifact
from .structured import read_mapping, write_structured


class BaselineError(RuntimeError):
    """Raised when a baseline is missing, drifting, or not reproducible."""


REPRODUCTION_STATUSES = frozenset({"REPRODUCED", "REPRODUCED_WITH_VARIANCE", "PARTIALLY_REPRODUCED", "FAILED_REPRODUCTION", "NOT_REPRODUCED", "BLOCKED", "UNTRUSTED", "UNKNOWN"})


def baseline_hash(spec: Mapping[str, Any]) -> str:
    return sha256_obj({key: value for key, value in spec.items() if key != "baseline_spec_sha256"})


def compile_baseline_spec(values: Mapping[str, Any], *, project_core: Optional[Mapping[str, Any]] = None, environment_receipt: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
    if not isinstance(values, Mapping):
        raise BaselineError("baseline input must be an object")
    environment = dict(values.get("environment", {}))
    if project_core is not None:
        validate_project_core(project_core)
    if environment_receipt is not None and environment_receipt.get("status") != "ONLINE_VERIFIED":
        raise BaselineError("ONLINE_VERIFIED environment receipt required for baseline")
    if environment_receipt is not None:
        try:
            validate_environment_receipt(environment_receipt, require_online=True)
        except EnvironmentError as exc:
            raise BaselineError(str(exc)) from exc
    if environment_receipt:
        environment["receipt_sha256"] = environment_receipt.get("receipt_sha256")
        environment["fingerprint"] = environment_receipt.get("fingerprint")
    spec = {
        "schema_version": "robotics-ar-baseline-spec.v1",
        "baseline_id": str(values.get("baseline_id", "baseline-current")),
        "project_core_sha256": core_hash(project_core) if project_core else str(values.get("project_core_sha256", "")),
        "code": dict(values.get("code", {})),
        "config": dict(values.get("config", {})),
        "environment": environment,
        "environment_receipt_sha256": values.get("environment_receipt_sha256") or environment.get("receipt_sha256", ""),
        "dataset_or_task": values.get("dataset_or_task", values.get("dataset", "")),
        "seeds": list(values.get("seeds", [0, 1, 2]) or []),
        "command": list(values.get("command", [])) if isinstance(values.get("command", []), list) else [str(values.get("command"))],
        "expected_metrics": dict(values.get("expected_metrics", {})),
        "repetitions": int(values.get("repetitions", 3)),
        "artifacts_required": list(values.get("artifacts_required", [])),
        "created_at": utc_now(),
    }
    if not spec["baseline_id"] or spec["repetitions"] <= 0:
        raise BaselineError("baseline_id and positive repetitions are required")
    if not spec["project_core_sha256"] or not spec["environment_receipt_sha256"]:
        raise BaselineError("baseline must bind Project Core and environment receipt")
    if not re.fullmatch(r"[0-9a-f]{64}", str(environment.get("fingerprint", ""))):
        raise BaselineError("baseline must bind a complete environment fingerprint")
    spec["baseline_spec_sha256"] = baseline_hash(spec)
    validate_baseline_spec(spec)
    return spec


def validate_baseline_spec(spec: Mapping[str, Any], *, require_hash: bool = True) -> None:
    required = ("schema_version", "baseline_id", "project_core_sha256", "environment_receipt_sha256", "seeds", "expected_metrics", "repetitions", "artifacts_required")
    missing = [key for key in required if key not in spec]
    if missing:
        raise BaselineError(f"baseline spec missing: {missing}")
    if spec.get("schema_version") != "robotics-ar-baseline-spec.v1":
        raise BaselineError("unsupported baseline schema")
    if not str(spec.get("project_core_sha256", "")) or not str(spec.get("environment_receipt_sha256", "")):
        raise BaselineError("baseline must bind Project Core and environment receipt")
    if int(spec.get("repetitions", 0)) <= 0:
        raise BaselineError("baseline repetitions must be positive")
    if require_hash and spec.get("baseline_spec_sha256") != baseline_hash(spec):
        raise BaselineError("baseline spec hash mismatch")
    try:
        validate_artifact("robotics-ar-baseline-spec.v1", spec)
    except SchemaValidationError as exc:
        raise BaselineError(str(exc)) from exc


def _metric_value(metrics: Mapping[str, Any], key: str) -> Optional[float]:
    value = metrics.get(key)
    if isinstance(value, Mapping):
        value = value.get("value", value.get("mean"))
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _expected_match(observed: Mapping[str, Any], expected: Mapping[str, Any]) -> tuple[bool, bool, list[str]]:
    exact = True
    within = True
    reasons: list[str] = []
    for name, target in expected.items():
        if isinstance(target, Mapping):
            expected_value = target.get("value")
            tolerance = float(target.get("tolerance", 0.0))
        else:
            expected_value = target
            tolerance = 0.0
        actual = _metric_value(observed, str(name))
        try:
            expected_float = float(expected_value)
        except (TypeError, ValueError):
            exact = within = False
            reasons.append(f"missing expected metric {name}")
            continue
        if actual is None:
            exact = within = False
            reasons.append(f"missing observed metric {name}")
            continue
        if actual != expected_float:
            exact = False
        if abs(actual - expected_float) > tolerance:
            within = False
            reasons.append(f"metric {name} outside tolerance")
    return exact, within, reasons


def _required_artifacts_present(runs: Iterable[Mapping[str, Any]], required: Iterable[Any]) -> tuple[bool, list[str]]:
    """Check required raw artifact names against collected file receipts."""

    files: set[str] = set()
    for run in runs:
        raw = run.get("raw_evidence", {}) if isinstance(run, Mapping) else {}
        if not isinstance(raw, Mapping):
            continue
        candidates = raw.get("files", raw.get("artifacts", []))
        if isinstance(candidates, Mapping):
            candidates = candidates.get("files", [])
        if isinstance(candidates, list):
            for item in candidates:
                if isinstance(item, Mapping) and item.get("path"):
                    files.add(str(item["path"]))
                elif isinstance(item, str):
                    files.add(item)
    missing = [str(item) for item in required if str(item) not in files and not any(path.endswith(str(item)) for path in files)]
    return not missing, missing


def reproduce_baseline(spec: Mapping[str, Any], environment: EnvironmentAdapter, *, output_dir: Optional[Path | str] = None, user_approved_variance: bool = False) -> dict[str, Any]:
    """Run the baseline without changing algorithm code and classify variance."""

    validate_baseline_spec(spec)
    if environment.fingerprint() != str(spec.get("environment", {}).get("fingerprint", "")):
        return build_baseline_receipt(spec, "BLOCKED", error="environment fingerprint drift")
    target = visible_directory(Path(output_dir) if output_dir else runtime_root(environment.root) / "takeover" / "baseline")
    target.mkdir(parents=True, exist_ok=True)
    runs: list[dict[str, Any]] = []
    errors: list[str] = []
    for index in range(int(spec["repetitions"])):
        run_spec = dict(spec)
        run_spec["baseline_run_index"] = index
        try:
            run = environment.reproduce_baseline(run_spec)
            try:
                run["raw_evidence"] = environment.collect_artifacts(f"baseline-{index}")
            except EnvironmentError as exc:
                errors.append(str(exc))
                break
            runs.append(run)
        except EnvironmentError as exc:
            errors.append(str(exc))
            break
    if errors or len(runs) != int(spec["repetitions"]):
        if not errors and len(runs) != int(spec["repetitions"]):
            errors.append(f"expected {spec['repetitions']} baseline runs, observed {len(runs)}")
        receipt = build_baseline_receipt(spec, "BLOCKED", runs=runs, error="; ".join(errors))
    else:
        metric_outputs = [run.get("output", {}) for run in runs]
        observed = metric_outputs[0] if metric_outputs else {}
        exact, within, reasons = _expected_match(observed, spec.get("expected_metrics", {}))
        artifacts_ok, missing_artifacts = _required_artifacts_present(runs, spec.get("artifacts_required", []))
        if not artifacts_ok:
            reasons.extend(f"missing required artifact: {item}" for item in missing_artifacts)
            status = "BLOCKED"
        elif exact:
            status = "REPRODUCED"
        elif within or (runs and user_approved_variance):
            status = "REPRODUCED_WITH_VARIANCE" if user_approved_variance else "PARTIALLY_REPRODUCED"
        else:
            status = "NOT_REPRODUCED"
        receipt = build_baseline_receipt(spec, status, runs=runs, observed_metrics=observed, reasons=reasons, user_approved_variance=user_approved_variance)
    atomic_write_json(target / "baseline-run-manifest.json", {"schema_version": "robotics-ar-baseline-run-manifest.v1", "runs": runs, "created_at": utc_now()})
    atomic_write_json(target / "metrics.json", receipt.get("observed_metrics", {}))
    write_structured(target / "baseline-receipt.json", receipt)
    return receipt


def build_baseline_receipt(spec: Mapping[str, Any], status: str, *, runs: Optional[Iterable[Mapping[str, Any]]] = None, observed_metrics: Optional[Mapping[str, Any]] = None, reasons: Optional[Iterable[str]] = None, error: str = "", user_approved_variance: bool = False) -> dict[str, Any]:
    if status not in REPRODUCTION_STATUSES:
        raise BaselineError(f"invalid reproduction status: {status}")
    receipt = {
        "schema_version": "robotics-ar-baseline-receipt.v1",
        "baseline_id": spec.get("baseline_id"),
        "baseline_spec_sha256": spec.get("baseline_spec_sha256"),
        "environment_fingerprint": spec.get("environment", {}).get("fingerprint"),
        "reproduction_status": status,
        "runs": list(runs or []),
        "raw_evidence": [run.get("raw_evidence", {}) for run in list(runs or [])],
        "observed_metrics": dict(observed_metrics or {}),
        "reasons": list(reasons or []),
        "error": error,
        "user_approved_variance": bool(user_approved_variance),
        "created_at": utc_now(),
    }
    receipt["receipt_sha256"] = sha256_obj(receipt)
    try:
        validate_artifact("robotics-ar-baseline-receipt.v1", receipt)
    except SchemaValidationError as exc:
        raise BaselineError(str(exc)) from exc
    return receipt


def assert_baseline_usable(receipt: Mapping[str, Any], *, allow_variance: bool = False) -> None:
    try:
        validate_artifact("robotics-ar-baseline-receipt.v1", receipt)
    except SchemaValidationError as exc:
        raise BaselineError(str(exc)) from exc
    if receipt.get("receipt_sha256") != sha256_obj({key: value for key, value in receipt.items() if key != "receipt_sha256"}):
        raise BaselineError("baseline receipt hash mismatch")
    status = receipt.get("reproduction_status", receipt.get("status"))
    if status == "REPRODUCED":
        return
    if status in {"REPRODUCED_WITH_VARIANCE", "PARTIALLY_REPRODUCED"} and allow_variance and receipt.get("user_approved_variance"):
        return
    raise BaselineError("baseline is not approved for autonomous trials")


def recover_baseline(spec: Mapping[str, Any], *, diagnostics: Iterable[str], output_dir: Path | str) -> dict[str, Any]:
    """Record bounded recovery diagnostics without altering the algorithm."""

    receipt = build_baseline_receipt(spec, "UNKNOWN", reasons=list(diagnostics))
    receipt["recovery_only"] = True
    receipt["algorithm_changed"] = False
    receipt["receipt_sha256"] = sha256_obj(receipt)
    write_structured(Path(output_dir) / "baseline-recovery-receipt.yaml", receipt)
    return receipt
