"""Bounded autonomous batch controller with fail-closed resource gates."""

from __future__ import annotations

import time
import re
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional

from .atomic_io import atomic_write_json
from .canonical import sha256_obj
from .environment import validate_environment_receipt
from .models import utc_now
from .schema_validation import SchemaValidationError, validate_artifact
from .structured import write_structured
from .trial_contract import TrialContractError, TrialContractManager, contract_allowed_tiers, validate_contract


class BatchControllerError(RuntimeError):
    """Raised when a batch cannot start or must stop."""


def batch_hash(batch: Mapping[str, Any]) -> str:
    return sha256_obj({key: value for key, value in batch.items() if key != "batch_sha256"})


def validate_batch(batch: Mapping[str, Any], *, require_hash: bool = True) -> None:
    required = ("schema_version", "batch_id", "contract_sha256", "max_trials", "max_wall_time_minutes", "max_parallel_jobs", "report_every_trials", "stop_on")
    missing = [key for key in required if key not in batch]
    if missing:
        raise BatchControllerError(f"batch spec missing: {missing}")
    if batch.get("schema_version") != "robotics-ar-autonomous-batch.v1":
        raise BatchControllerError("unsupported autonomous batch schema")
    if int(batch.get("max_trials", 0)) <= 0 or int(batch.get("max_parallel_jobs", 0)) <= 0 or int(batch.get("max_wall_time_minutes", 0)) <= 0 or int(batch.get("report_every_trials", 0)) <= 0:
        raise BatchControllerError("batch limits must be positive")
    for field in ("max_gpu_hours", "max_disk_gb"):
        try:
            if float(batch.get(field, 0) or 0) < 0:
                raise BatchControllerError(f"{field} must be non-negative")
        except (TypeError, ValueError) as exc:
            raise BatchControllerError(f"{field} must be numeric") from exc
    allowed_tiers = batch.get("allowed_tiers", [])
    if not isinstance(allowed_tiers, list) or not allowed_tiers:
        raise BatchControllerError("allowed_tiers must be a non-empty list of tiers 0 through 3")
    try:
        if any(isinstance(item, bool) or int(item) not in {0, 1, 2, 3} for item in allowed_tiers):
            raise BatchControllerError("allowed_tiers must contain only tiers 0 through 3")
    except (TypeError, ValueError) as exc:
        raise BatchControllerError("allowed_tiers must contain only integer tiers") from exc
    if require_hash and batch.get("batch_sha256") != batch_hash(batch):
        raise BatchControllerError("batch hash mismatch")
    try:
        validate_artifact("robotics-ar-autonomous-batch.v1", batch)
    except SchemaValidationError as exc:
        raise BatchControllerError(str(exc)) from exc


def compile_batch(values: Mapping[str, Any], *, contract_sha256: str = "") -> dict[str, Any]:
    batch = {
        "schema_version": "robotics-ar-autonomous-batch.v1",
        "batch_id": str(values.get("batch_id", "batch-001")),
        "contract_sha256": contract_sha256 or str(values.get("contract_sha256", "")),
        "max_trials": int(values.get("max_trials", 10)),
        "max_wall_time_minutes": int(values.get("max_wall_time_minutes", float(values.get("max_wall_time_hours", 8)) * 60)),
        "max_parallel_jobs": int(values.get("max_parallel_jobs", 1)),
        "max_gpu_hours": float(values.get("max_gpu_hours", 0.0)),
        "max_disk_gb": float(values.get("max_disk_gb", 0.0)),
        "allowed_tiers": list(values.get("allowed_tiers", [0, 1])),
        "report_every_trials": int(values.get("report_every_trials", 2)),
        "report_every_minutes": int(values.get("report_every_minutes", 120)),
        "stop_on": list(values.get("stop_on", ["budget_exhausted", "wall_time_exhausted", "repeated_environment_failure", "no_information_gain", "core_change_required", "critical_block"])),
        "no_information_gain_limit": int(values.get("no_information_gain_limit", 3)),
        "created_at": utc_now(),
    }
    batch["batch_sha256"] = batch_hash(batch)
    validate_batch(batch)
    return batch


class BatchController:
    def __init__(self, root: Path | str, *, mode: str = "PLANNING_ONLY", manager: Any = None, contracts_dir: Optional[Path | str] = None) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.mode = mode
        self.manager = manager
        self.contracts_dir = Path(contracts_dir) if contracts_dir is not None else None
        self.batch: Optional[dict[str, Any]] = None
        self.started_at: Optional[float] = None
        self.completed = 0
        self.results: list[dict[str, Any]] = []
        self.contract: Optional[dict[str, Any]] = None
        self.gpu_hours_used = 0.0
        self.disk_gb_used = 0.0
        self.environment_failures = 0
        self.no_information_gain_streak = 0
        self.real_robot = False
        self.status = "IDLE"
        self.stop_reason = ""
        self.started_at_utc = ""
        self.last_environment_receipt_sha256 = ""
        self.environment_fingerprint = ""
        self.elapsed_wall_time_seconds = 0.0

    @property
    def checkpoint_path(self) -> Path:
        return self.root / "batch-checkpoint.json"

    def start(self, batch: Mapping[str, Any], *, contract: Mapping[str, Any], environment_receipt: Mapping[str, Any], real_robot: bool = False, real_robot_token: Any = None, real_robot_binding: Optional[Mapping[str, Any]] = None, approval_dir: Optional[Path | str] = None) -> dict[str, Any]:
        validate_batch(batch)
        validate_contract(contract)
        if contract.get("status") != "APPROVED":
            raise BatchControllerError("approved Trial Contract required")
        for binding in ("project_core_sha256", "baseline_receipt_sha256", "environment_receipt_sha256"):
            if not str(contract.get(binding, "")):
                raise BatchControllerError(f"contract binding missing: {binding}")
        if batch.get("contract_sha256") != contract.get("contract_sha256"):
            raise BatchControllerError("batch is not bound to the active contract")
        contract_budget = contract.get("budget", {})
        if int(batch["max_trials"]) > int(contract_budget.get("max_trials", batch["max_trials"])):
            raise BatchControllerError("batch max_trials exceeds contract budget")
        if int(batch["max_parallel_jobs"]) > int(contract_budget.get("max_parallel_jobs", batch["max_parallel_jobs"])):
            raise BatchControllerError("batch parallelism exceeds contract budget")
        contract_wall = float(contract_budget.get("max_wall_time_hours", 0) or 0)
        if contract_wall > 0 and float(batch["max_wall_time_minutes"]) > contract_wall * 60:
            raise BatchControllerError("batch wall time exceeds contract budget")
        for batch_key, contract_key in (("max_gpu_hours", "max_gpu_hours"), ("max_disk_gb", "max_disk_gb")):
            contract_limit = float(contract_budget.get(contract_key, 0) or 0)
            if contract_limit > 0 and float(batch.get(batch_key, 0) or 0) > contract_limit:
                raise BatchControllerError(f"batch {batch_key} exceeds contract budget")
        if contract.get("baseline_reproduction_status") is not None:
            if contract.get("baseline_reproduction_status") != "REPRODUCED" and not (contract.get("baseline_reproduction_status") == "REPRODUCED_WITH_VARIANCE" and contract.get("baseline_user_approved_variance") is True):
                raise BatchControllerError("reproduced and approved baseline required")
        if contract.get("project_core_approved") is not True or contract.get("baseline_approved") is not True:
            raise BatchControllerError("approved Project Core and baseline are required")
        if contract.get("upstream_approval_binding_required") is True:
            if approval_dir is None:
                raise BatchControllerError("upstream approval directory is required for a production takeover batch")
            try:
                TrialContractManager(self.contracts_dir or self.root / ".contract-check", approval_dir).validate_upstream_bindings(contract)
            except TrialContractError as exc:
                raise BatchControllerError(str(exc)) from exc
        contract_tiers = contract_allowed_tiers(contract)
        batch_tiers = {int(item) for item in batch.get("allowed_tiers", [])}
        if not batch_tiers or not batch_tiers.issubset({0, 1, 2, 3}):
            raise BatchControllerError("batch allowed_tiers must contain only tiers 0 through 3")
        if contract_tiers and not batch_tiers.issubset(contract_tiers):
            raise BatchControllerError("batch allowed_tiers exceed the Trial Contract search space")
        if self.mode == "PLANNING_ONLY":
            raise BatchControllerError("PLANNING_ONLY cannot start an autonomous batch")
        if environment_receipt.get("status") != "ONLINE_VERIFIED":
            raise BatchControllerError("ONLINE_VERIFIED environment receipt required")
        try:
            validate_environment_receipt(environment_receipt, require_online=True)
        except RuntimeError as exc:
            raise BatchControllerError(str(exc)) from exc
        if not environment_receipt.get("receipt_sha256") or contract.get("environment_receipt_sha256") != environment_receipt.get("receipt_sha256"):
            raise BatchControllerError("environment receipt is not bound to the active contract")
        if real_robot and int(batch["max_trials"]) != 1:
            raise BatchControllerError("real robot batch must contain exactly one trial")
        if real_robot:
            if environment_receipt.get("environment_kind") not in {None, "real_robot", "hybrid"}:
                raise BatchControllerError("real robot batch requires a real-robot or hybrid environment")
            if real_robot_token is None:
                raise BatchControllerError("real robot one-shot caution/token is required")
            try:
                consumed = real_robot_token.consume(binding=dict(real_robot_binding or {}), stop_status="READY", retry_requested=False)
            except Exception as exc:
                raise BatchControllerError(f"real robot token gate failed: {exc}") from exc
            # Do not mutate the hash-bound environment receipt with the token
            # identifier.  Token consumption is recorded by the token gate and
            # checkpoint metadata; changing this mapping would invalidate its
            # self-hash while leaving the contract bound to the old digest.
        self.batch = dict(batch)
        self.contract = dict(contract)
        self.started_at = time.monotonic()
        self.completed = 0
        self.results = []
        self.gpu_hours_used = 0.0
        self.disk_gb_used = 0.0
        self.environment_failures = 0
        self.no_information_gain_streak = 0
        self.real_robot = bool(real_robot)
        self.status = "RUNNING"
        self.stop_reason = ""
        self.started_at_utc = utc_now()
        self.last_environment_receipt_sha256 = str(environment_receipt.get("receipt_sha256", ""))
        self.environment_fingerprint = str(environment_receipt.get("fingerprint", ""))
        self.elapsed_wall_time_seconds = 0.0
        if self.manager is not None and self.manager.state.get("state") == "TRIAL_BATCH_READY":
            self.manager.transition("TRIAL_PLANNING", "BATCH_STARTED", {"batch_id": batch.get("batch_id")})
        self._save_checkpoint(reason="batch-started", environment_receipt=environment_receipt)
        return self.checkpoint()

    def should_stop(self) -> Optional[str]:
        if not self.batch or self.status != "RUNNING":
            return self.status if self.status != "RUNNING" else None
        if self.completed >= int(self.batch["max_trials"]):
            return "budget_exhausted"
        if self._elapsed_wall_time_seconds() >= int(self.batch["max_wall_time_minutes"]) * 60:
            return "wall_time_exhausted"
        if float(self.batch.get("max_gpu_hours", 0.0)) > 0 and self.gpu_hours_used >= float(self.batch["max_gpu_hours"]):
            return "gpu_budget_exhausted"
        if float(self.batch.get("max_disk_gb", 0.0)) > 0 and self.disk_gb_used >= float(self.batch["max_disk_gb"]):
            return "disk_budget_exhausted"
        if self.environment_failures >= 2 and "repeated_environment_failure" in self.batch.get("stop_on", []):
            return "repeated_environment_failure"
        if self.no_information_gain_streak >= int(self.batch.get("no_information_gain_limit", 3)) and "no_information_gain" in self.batch.get("stop_on", []):
            return "no_information_gain"
        return None

    def run(self, proposals: Iterable[Mapping[str, Any]], runner: Callable[[Mapping[str, Any]], Mapping[str, Any]], *, environment_receipt: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
        if self.status != "RUNNING" or self.batch is None:
            raise BatchControllerError("batch is not running")
        if environment_receipt is None:
            self.stop("environment_receipt_missing")
            raise BatchControllerError("a validated environment receipt is required for every trial")
        for proposal in proposals:
            reason = self.should_stop()
            if reason:
                self.stop(reason)
                break
            try:
                validate_environment_receipt(environment_receipt, require_online=True)
                if environment_receipt.get("receipt_sha256") != self.last_environment_receipt_sha256:
                    raise BatchControllerError("environment receipt drift during batch")
                if environment_receipt.get("fingerprint") != self.environment_fingerprint:
                    raise BatchControllerError("environment fingerprint drift during batch")
                if self.contract is not None and environment_receipt.get("receipt_sha256") != self.contract.get("environment_receipt_sha256"):
                    raise BatchControllerError("environment receipt is not bound to the active contract")
            except (BatchControllerError, RuntimeError) as exc:
                self.results.append({"status": "BLOCKED_ENVIRONMENT", "decision": "ESCALATE", "error": str(exc), "trial_id": proposal.get("trial_id")})
                self.stop("environment_drift")
                break
            tier = int(proposal.get("change", {}).get("tier", 3)) if isinstance(proposal.get("change", {}), Mapping) else 3
            if tier not in set(self.batch.get("allowed_tiers", [])):
                self.stop("search_space_tier_violation")
                break
            if self.contract is not None:
                try:
                    TrialContractManager.check_trial(self.contract, proposal, used_trials=self.completed, parallel_jobs=0, environment_receipt_sha256=environment_receipt.get("receipt_sha256", ""))
                except TrialContractError as exc:
                    self.results.append({"status": "BLOCKED", "decision": "ESCALATE", "error": str(exc), "trial_id": proposal.get("trial_id")})
                    self.stop("trial_contract_violation")
                    break
            try:
                raw_result = runner(proposal)
                result = dict(raw_result or {"status": "BLOCKED_ENVIRONMENT", "error": "runner returned no result"})
            except Exception as exc:
                result = {"status": "BLOCKED_ENVIRONMENT", "error": str(exc), "runner_exception": type(exc).__name__}
            self.results.append(result)
            self.completed += 1
            usage = result.get("resource_usage", {}) if isinstance(result.get("resource_usage", {}), Mapping) else {}
            try:
                gpu_used = float(usage.get("gpu_hours", 0.0) or 0.0)
                disk_used = float(usage.get("disk_gb", 0.0) or 0.0)
            except (TypeError, ValueError) as exc:
                self.stop("invalid_resource_receipt")
                raise BatchControllerError("resource usage receipt is not numeric") from exc
            if gpu_used < 0 or disk_used < 0:
                self.stop("invalid_resource_receipt")
                raise BatchControllerError("resource usage cannot be negative")
            self.gpu_hours_used += gpu_used
            self.disk_gb_used += disk_used
            if result.get("status") == "BLOCKED_ENVIRONMENT" or result.get("decision") == "BLOCKED_ENVIRONMENT":
                self.environment_failures += 1
            if result.get("information_gain") is False or result.get("no_information_gain") is True:
                self.no_information_gain_streak += 1
            else:
                self.no_information_gain_streak = 0
            self.last_environment_receipt_sha256 = str(environment_receipt.get("receipt_sha256", self.last_environment_receipt_sha256))
            self.environment_fingerprint = str(environment_receipt.get("fingerprint", self.environment_fingerprint))
            self._save_checkpoint(reason=f"trial-{self.completed}-completed", environment_receipt=environment_receipt or {})
            if self.real_robot and (result.get("status") not in {"PASS", "ONLINE_VERIFIED", "VERIFIED"} or result.get("decision") not in {None, "KEEP"}):
                self.stop("real_robot_failure_default_stop")
                break
            if result.get("decision") in {"ESCALATE", "INVESTIGATE"} or result.get("status") in {"BLOCKED_ENVIRONMENT", "CRITICAL_BLOCK"}:
                self.stop(str(result.get("decision", result.get("status"))))
                break
        if self.status == "RUNNING" and self.should_stop():
            self.stop(self.should_stop() or "batch-complete")
        return self.checkpoint()

    def checkpoint(self) -> dict[str, Any]:
        return {"status": self.status, "stop_reason": self.stop_reason, "batch": dict(self.batch or {}), "completed": self.completed, "results": list(self.results), "gpu_hours_used": self.gpu_hours_used, "disk_gb_used": self.disk_gb_used, "environment_failures": self.environment_failures, "no_information_gain_streak": self.no_information_gain_streak, "real_robot": self.real_robot, "started_at_utc": self.started_at_utc, "elapsed_wall_time_seconds": self._elapsed_wall_time_seconds(), "environment_receipt_sha256": self.last_environment_receipt_sha256, "environment_fingerprint": self.environment_fingerprint, "remaining_trials": max(0, int((self.batch or {}).get("max_trials", 0)) - self.completed), "created_at": utc_now()}

    def _elapsed_wall_time_seconds(self) -> float:
        elapsed = float(self.elapsed_wall_time_seconds)
        if self.started_at is not None and self.status == "RUNNING":
            elapsed += max(0.0, time.monotonic() - self.started_at)
        return elapsed

    def _save_checkpoint(self, *, reason: str, environment_receipt: Mapping[str, Any]) -> None:
        value = self.checkpoint()
        value.update({"reason": reason, "environment_receipt_sha256": environment_receipt.get("receipt_sha256", self.last_environment_receipt_sha256), "checkpoint_sha256": sha256_obj(value)})
        atomic_write_json(self.checkpoint_path, value)
        if self.manager is not None:
            from .reporting_v3 import write_checkpoint_artifacts

            write_checkpoint_artifacts(self.manager, context={"batch_id": self.batch.get("batch_id") if self.batch else "UNKNOWN", "budget": self.batch or {}, "environment_fingerprint": environment_receipt.get("fingerprint", "")}, reason=reason)

    def stop(self, reason: str) -> dict[str, Any]:
        if self.status == "STOPPED":
            return self.checkpoint()
        self.elapsed_wall_time_seconds = self._elapsed_wall_time_seconds()
        self.started_at = None
        self.status = "STOPPED"
        self.stop_reason = str(reason)
        if self.manager is not None and self.manager.state.get("state") in {"TRIAL_PLANNING", "TRIAL_IMPLEMENTING", "TRIAL_TESTING", "TRIAL_RUNNING", "TRIAL_ANALYZING", "TRIAL_EXPERT_REVIEW", "TRIAL_DECIDING"}:
            self.manager.transition("BATCH_CHECKPOINT", "BATCH_CHECKPOINT_CREATED", {"reason": reason, "completed": self.completed})
        self._save_checkpoint(reason=reason, environment_receipt={"receipt_sha256": self.last_environment_receipt_sha256, "fingerprint": self.environment_fingerprint})
        return self.checkpoint()

    def resume(self, *, contract: Mapping[str, Any], environment_receipt: Mapping[str, Any], approval_dir: Optional[Path | str] = None) -> dict[str, Any]:
        """Resume a stopped simulation batch only after rechecking all bindings."""

        if self.status != "STOPPED" or self.batch is None:
            raise BatchControllerError("only a stopped batch can be resumed")
        if self.real_robot:
            raise BatchControllerError("real-robot batches cannot be resumed; issue a new one-shot approval")
        validate_contract(contract)
        if contract.get("status") != "APPROVED" or contract.get("project_core_approved") is not True or contract.get("baseline_approved") is not True:
            raise BatchControllerError("approved Project Core, baseline, and Trial Contract are required")
        if contract.get("upstream_approval_binding_required") is True:
            if approval_dir is None:
                raise BatchControllerError("upstream approval directory is required to resume a production takeover batch")
            try:
                TrialContractManager(self.contracts_dir or self.root / ".contract-check", approval_dir).validate_upstream_bindings(contract)
            except TrialContractError as exc:
                raise BatchControllerError(str(exc)) from exc
        if contract.get("contract_sha256") != self.batch.get("contract_sha256"):
            raise BatchControllerError("resume contract drift")
        if environment_receipt.get("status") != "ONLINE_VERIFIED" or not environment_receipt.get("receipt_sha256"):
            raise BatchControllerError("fresh ONLINE_VERIFIED environment receipt required for resume")
        try:
            validate_environment_receipt(environment_receipt, require_online=True)
        except RuntimeError as exc:
            raise BatchControllerError(str(exc)) from exc
        if environment_receipt.get("receipt_sha256") != self.last_environment_receipt_sha256:
            raise BatchControllerError("resume environment receipt drift")
        if environment_receipt.get("receipt_sha256") != contract.get("environment_receipt_sha256"):
            raise BatchControllerError("resume environment receipt is not bound to the active contract")
        if not re.fullmatch(r"[0-9a-f]{64}", str(environment_receipt.get("fingerprint", ""))) or environment_receipt.get("fingerprint") != self.environment_fingerprint:
            raise BatchControllerError("resume environment fingerprint drift")
        contract_tiers = contract_allowed_tiers(contract)
        batch_tiers = {int(item) for item in self.batch.get("allowed_tiers", [])}
        if contract_tiers and not batch_tiers.issubset(contract_tiers):
            raise BatchControllerError("resume batch tiers exceed the Trial Contract search space")
        reason = self.stop_reason
        if reason in {"budget_exhausted", "wall_time_exhausted", "gpu_budget_exhausted", "disk_budget_exhausted", "no_information_gain", "repeated_environment_failure", "real_robot_failure_default_stop", "ESCALATE", "INVESTIGATE", "BLOCKED_ENVIRONMENT", "environment_drift", "environment_receipt_missing", "search_space_tier_violation", "trial_contract_violation", "invalid_resource_receipt"}:
            raise BatchControllerError(f"batch stopped at a terminal gate: {reason}")
        if self.completed >= int(self.batch.get("max_trials", 0)):
            raise BatchControllerError("batch trial budget is exhausted")
        self.contract = dict(contract)
        self.status = "RUNNING"
        self.stop_reason = ""
        self.started_at = time.monotonic()
        self.started_at_utc = utc_now()
        if self.manager is not None and self.manager.state.get("state") == "BATCH_CHECKPOINT":
            self.manager.transition("TRIAL_PLANNING", "BATCH_RESUMED", {"batch_id": self.batch.get("batch_id")})
        self._save_checkpoint(reason="batch-resumed", environment_receipt=environment_receipt)
        return self.checkpoint()

    @classmethod
    def load_checkpoint(cls, path: Path | str, *, mode: str = "PLANNING_ONLY", manager: Any = None, contracts_dir: Optional[Path | str] = None) -> "BatchController":
        from .structured import read_mapping

        value = read_mapping(path)
        batch = value.get("batch", {})
        validate_batch(batch)
        checkpoint_hash = value.get("checkpoint_sha256")
        if checkpoint_hash:
            base = {key: item for key, item in value.items() if key not in {"reason", "checkpoint_sha256"}}
            if checkpoint_hash != sha256_obj(base):
                raise BatchControllerError("batch checkpoint hash mismatch")
        controller = cls(Path(path).parent, mode=mode, manager=manager, contracts_dir=contracts_dir)
        controller.batch = dict(batch)
        controller.completed = int(value.get("completed", 0))
        controller.results = list(value.get("results", []))
        controller.gpu_hours_used = float(value.get("gpu_hours_used", 0.0))
        controller.disk_gb_used = float(value.get("disk_gb_used", 0.0))
        controller.environment_failures = int(value.get("environment_failures", 0))
        controller.no_information_gain_streak = int(value.get("no_information_gain_streak", 0))
        controller.status = str(value.get("status", "STOPPED"))
        controller.stop_reason = str(value.get("stop_reason", value.get("reason", "")))
        controller.started_at_utc = str(value.get("started_at_utc", ""))
        controller.elapsed_wall_time_seconds = float(value.get("elapsed_wall_time_seconds", 0.0))
        controller.last_environment_receipt_sha256 = str(value.get("environment_receipt_sha256", ""))
        controller.environment_fingerprint = str(value.get("environment_fingerprint", ""))
        controller.real_robot = bool(value.get("real_robot", False))
        # A checkpoint persisted as RUNNING belongs to a process that no
        # longer exists when loaded by a new supervisor. Treat it as a safe,
        # resumable crash stop rather than allowing a second process to assume
        # the old runner is still alive.
        if controller.status == "RUNNING":
            controller.status = "STOPPED"
            controller.stop_reason = "crash_recovery_required"
            controller.started_at = None
        return controller
