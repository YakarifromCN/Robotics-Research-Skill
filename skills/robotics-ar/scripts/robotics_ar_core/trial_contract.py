"""Hash-bound Trial Contract and amendment gates."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Optional

from .atomic_io import atomic_write_json
from .canonical import sha256_obj
from .gates import ApprovalManager, GateError
from .models import utc_now
from .schema_validation import SchemaValidationError, validate_artifact
from .structured import read_mapping, write_structured


class TrialContractError(RuntimeError):
    """Raised when a trial would exceed the approved contract."""


CONTRACT_STATUSES = frozenset({"DRAFT", "APPROVED", "AMENDED", "INVALIDATED", "EXHAUSTED"})
TIERS = frozenset({0, 1, 2, 3})
BASELINE_APPROVAL_STATUSES = frozenset({"REPRODUCED", "REPRODUCED_WITH_VARIANCE"})
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def contract_hash(contract: Mapping[str, Any]) -> str:
    mutable = {"contract_sha256", "approved_by_user", "approval_id", "approved_at", "approval_subject_sha256", "status", "approval"}
    return sha256_obj({key: value for key, value in contract.items() if key not in mutable})


def contract_allowed_tiers(contract: Mapping[str, Any]) -> set[int]:
    """Return the tiers explicitly granted by the contract.

    The contract deliberately stores domain-neutral search-space labels such as
    ``tier_0_parameters``.  This helper only extracts the numeric permission;
    it does not interpret the parameter payload.
    """

    search_space = contract.get("allowed_search_space", {})
    if not isinstance(search_space, Mapping):
        return set()
    tiers: set[int] = set()
    for key, value in search_space.items():
        match = re.match(r"^tier_(\d+)(?:_|$)", str(key))
        if match and isinstance(value, list) and value:
            tiers.add(int(match.group(1)))
    return tiers


def _validate_relative_rules(contract: Mapping[str, Any]) -> None:
    """Reject path rules that could grant or hide traversal outside a project."""

    for field in ("allowed_paths", "forbidden_paths", "read_only_paths"):
        value = contract.get(field, [])
        if not isinstance(value, list):
            raise TrialContractError(f"{field} must be a list")
        for rule in value:
            text = str(rule)
            if not text or "\x00" in text or Path(text).is_absolute() or ".." in Path(text).parts:
                raise TrialContractError(f"unsafe path rule in {field}: {rule}")
    for field in ("forbidden_changes", "conditionally_allowed"):
        value = contract.get(field, [])
        if not isinstance(value, list):
            raise TrialContractError(f"{field} must be a list")


def validate_contract(contract: Mapping[str, Any], *, require_hash: bool = True) -> None:
    required = ("schema_version", "contract_id", "entry_mode", "project_core_sha256", "baseline_receipt_sha256", "environment_receipt_sha256", "current_bottleneck", "primary_hypothesis", "primary_objective", "allowed_search_space", "conditionally_allowed", "forbidden_changes", "trial_policy", "budget", "stop_conditions", "escalation_conditions", "approval")
    missing = [key for key in required if key not in contract]
    if missing:
        raise TrialContractError(f"trial contract missing: {missing}")
    if contract.get("schema_version") != "robotics-ar-trial-contract.v1":
        raise TrialContractError("unsupported trial contract schema")
    if contract.get("entry_mode") != "MIDSTREAM_TAKEOVER":
        raise TrialContractError("trial contract must use MIDSTREAM_TAKEOVER")
    if not str(contract.get("contract_id", "")).strip() or not str(contract.get("current_bottleneck", "")).strip():
        raise TrialContractError("contract_id and current_bottleneck are required")
    if not contract.get("primary_hypothesis") or not isinstance(contract.get("primary_objective"), Mapping):
        raise TrialContractError("primary hypothesis and objective are required")
    for binding in ("project_core_sha256", "baseline_receipt_sha256", "environment_receipt_sha256"):
        if not str(contract.get(binding, "")):
            raise TrialContractError(f"trial contract binding is missing: {binding}")
    if not isinstance(contract.get("budget"), Mapping) or int(contract["budget"].get("max_trials", 0)) <= 0:
        raise TrialContractError("positive max_trials is required")
    budget = contract["budget"]
    for field in ("max_wall_time_hours", "max_gpu_hours", "max_disk_gb"):
        try:
            if float(budget.get(field, 0) or 0) < 0:
                raise TrialContractError(f"{field} must be non-negative")
        except (TypeError, ValueError) as exc:
            raise TrialContractError(f"{field} must be numeric") from exc
    if int(budget.get("max_parallel_jobs", 0) or 0) <= 0:
        raise TrialContractError("positive max_parallel_jobs is required")
    if not isinstance(contract.get("allowed_search_space"), Mapping):
        raise TrialContractError("allowed_search_space must be an object")
    if not isinstance(contract.get("trial_policy"), Mapping):
        raise TrialContractError("trial_policy must be an object")
    _validate_relative_rules(contract)
    if contract.get("upstream_approval_binding_required") is True:
        for field in ("project_core_approval_id", "baseline_approval_id", "project_core_path", "baseline_receipt_path", "environment_receipt_path"):
            if not str(contract.get(field, "")).strip():
                raise TrialContractError(f"upstream approval binding is incomplete: {field}")
    if contract.get("status") not in CONTRACT_STATUSES:
        raise TrialContractError("invalid contract status")
    # A draft may carry false approval flags, but an APPROVED contract must
    # explicitly prove both upstream gates.  Missing is not equivalent to
    # approved: otherwise a hand-written contract could bypass Project Core
    # and baseline review.
    if contract.get("status") == "APPROVED":
        if contract.get("project_core_approved") is not True or contract.get("baseline_approved") is not True:
            raise TrialContractError("approved contract requires approved Project Core and baseline")
        if contract.get("baseline_reproduction_status") not in BASELINE_APPROVAL_STATUSES:
            raise TrialContractError("approved contract requires a reproduced baseline")
        if not contract_allowed_tiers(contract):
            raise TrialContractError("approved contract must grant at least one search-space tier")
        if contract.get("upstream_approval_binding_required") is True:
            for field in ("project_core_approval_id", "baseline_approval_id"):
                if not str(contract.get(field, "")).strip():
                    raise TrialContractError(f"approved contract requires upstream approval receipt: {field}")
    reproduction_status = contract.get("baseline_reproduction_status")
    if reproduction_status is not None and reproduction_status not in BASELINE_APPROVAL_STATUSES:
        raise TrialContractError("baseline is not approved for autonomous trials")
    if reproduction_status == "REPRODUCED_WITH_VARIANCE" and contract.get("baseline_user_approved_variance") is not True:
        raise TrialContractError("baseline variance requires explicit user approval")
    if require_hash and contract.get("contract_sha256") != contract_hash(contract):
        raise TrialContractError("trial contract hash mismatch")
    try:
        validate_artifact("robotics-ar-trial-contract.v1", contract)
    except SchemaValidationError as exc:
        raise TrialContractError(str(exc)) from exc


def compile_trial_contract(values: Mapping[str, Any], *, project_core_sha256: str = "", baseline_receipt_sha256: str = "", environment_receipt_sha256: str = "") -> dict[str, Any]:
    if not isinstance(values, Mapping):
        raise TrialContractError("contract input must be an object")
    budget = dict(values.get("budget", {}))
    budget.setdefault("max_trials", 1)
    budget.setdefault("max_wall_time_hours", 0)
    budget.setdefault("max_gpu_hours", 0)
    budget.setdefault("max_parallel_jobs", 1)
    budget.setdefault("max_disk_gb", 0)
    trial_policy = dict(values.get("trial_policy", {}))
    trial_policy.setdefault("one_primary_hypothesis_per_trial", True)
    trial_policy.setdefault("minimal_change_required", True)
    trial_policy.setdefault("max_debug_cycles", 2)
    trial_policy.setdefault("max_expert_rounds", 2)
    contract = {
        "schema_version": "robotics-ar-trial-contract.v1",
        "contract_id": str(values.get("contract_id", "batch-001")),
        "entry_mode": "MIDSTREAM_TAKEOVER",
        "project_core_sha256": project_core_sha256 or str(values.get("project_core_sha256", "")),
        "baseline_receipt_sha256": baseline_receipt_sha256 or str(values.get("baseline_receipt_sha256", "")),
        "environment_receipt_sha256": environment_receipt_sha256 or str(values.get("environment_receipt_sha256", "")),
        "current_bottleneck": str(values.get("current_bottleneck", "")),
        "primary_hypothesis": values.get("primary_hypothesis", ""),
        "primary_objective": dict(values.get("primary_objective", {})),
        "secondary_metrics": list(values.get("secondary_metrics", [])) if isinstance(values.get("secondary_metrics", []), list) else [],
        "allowed_search_space": dict(values.get("allowed_search_space", {})),
        "conditionally_allowed": list(values.get("conditionally_allowed", [])),
        "forbidden_changes": list(values.get("forbidden_changes", [])),
        "allowed_paths": list(values.get("allowed_paths", values.get("allowed_code_paths", [])) or []),
        "forbidden_paths": list(values.get("forbidden_paths", values.get("forbidden_code_paths", [])) or []),
        "read_only_paths": list(values.get("read_only_paths", []) or []),
        "baselines_required": list(values.get("baselines_required", [])),
        "trial_policy": trial_policy,
        "budget": budget,
        "reporting": dict(values.get("reporting", {})),
        "stop_conditions": list(values.get("stop_conditions", [])),
        "escalation_conditions": list(values.get("escalation_conditions", [])),
        "real_robot_permissions": dict(values.get("real_robot_permissions", {})),
        "upstream_approval_binding_required": bool(values.get("upstream_approval_binding_required", False)),
        "project_core_approval_id": str(values.get("project_core_approval_id", "")),
        "baseline_approval_id": str(values.get("baseline_approval_id", "")),
        "project_core_path": str(values.get("project_core_path", "")),
        "baseline_receipt_path": str(values.get("baseline_receipt_path", "")),
        "environment_receipt_path": str(values.get("environment_receipt_path", "")),
        "approval": {"required": True, "approved_by_user": False},
        "status": "DRAFT",
        "created_at": utc_now(),
    }
    if values.get("baseline_reproduction_status") is not None:
        contract["baseline_reproduction_status"] = values["baseline_reproduction_status"]
        contract["baseline_user_approved_variance"] = bool(values.get("baseline_user_approved_variance", False))
    contract["project_core_approved"] = bool(values.get("project_core_approved", False))
    contract["baseline_approved"] = bool(values.get("baseline_approved", False))
    contract["contract_sha256"] = contract_hash(contract)
    validate_contract(contract)
    return contract


class TrialContractManager:
    """Persist contracts and make every execution check explicit."""

    def __init__(self, contracts_dir: Path | str, approvals_dir: Optional[Path | str] = None) -> None:
        self.contracts_dir = Path(contracts_dir)
        self.approvals = ApprovalManager(approvals_dir or self.contracts_dir.parent / "approvals")
        self.contracts_dir.mkdir(parents=True, exist_ok=True)

    def save(self, contract: Mapping[str, Any], *, filename: Optional[str] = None) -> Path:
        validate_contract(contract)
        path = self.contracts_dir / (filename or f"{contract['contract_id']}.yaml")
        return write_structured(path, dict(contract))

    def load(self, path: Path | str) -> dict[str, Any]:
        contract = read_mapping(path)
        validate_contract(contract)
        return contract

    def create_user_approval(self, contract_path: Path | str) -> dict[str, Any]:
        contract = self.load(contract_path)
        return self.approvals.create("TRIAL_CONTRACT", contract_path, scope="persistent-until-drift")

    def validate_upstream_bindings(self, contract: Mapping[str, Any]) -> None:
        """Validate the concrete upstream artifacts for production contracts.

        Boolean flags are retained for v2 compatibility, but a takeover
        contract produced by the v3 CLI can opt into this stronger check.  It
        verifies the approved Project Core, baseline receipt, environment
        receipt, and the consumed approval receipts all agree with the hashes
        embedded in the contract.
        """

        if contract.get("upstream_approval_binding_required") is not True:
            return
        try:
            from .baseline import assert_baseline_usable
            from .environment import validate_environment_receipt
            from .project_core import assert_project_core_approved, core_hash, load_project_core

            core_path = Path(str(contract["project_core_path"])).resolve()
            core = load_project_core(core_path)
            assert_project_core_approved(core)
            if core_hash(core) != contract.get("project_core_sha256") or core.get("approval_id") != contract.get("project_core_approval_id"):
                raise TrialContractError("Project Core approval/hash binding drift")

            baseline_path = Path(str(contract["baseline_receipt_path"])).resolve()
            baseline = read_mapping(baseline_path)
            assert_baseline_usable(baseline, allow_variance=True)
            if baseline.get("receipt_sha256") != contract.get("baseline_receipt_sha256") or baseline.get("approval_id") != contract.get("baseline_approval_id") or baseline.get("approved_by_user") is not True:
                raise TrialContractError("baseline approval/hash binding drift")

            environment = read_mapping(Path(str(contract["environment_receipt_path"])).resolve())
            validate_environment_receipt(environment, require_online=True)
            if environment.get("receipt_sha256") != contract.get("environment_receipt_sha256"):
                raise TrialContractError("environment receipt binding drift")
        except TrialContractError:
            raise
        except Exception as exc:
            raise TrialContractError(f"upstream approval artifacts are invalid: {exc}") from exc

        expected_approvals = {
            str(contract["project_core_approval_id"]): {"TAKEOVER_CORE", "IDEA"},
            str(contract["baseline_approval_id"]): {"BASELINE", "EXPERIMENT"},
        }
        for approval_id, gates in expected_approvals.items():
            path = self.approvals.approvals_dir / f"{approval_id}.json"
            if not path.is_file():
                raise TrialContractError(f"upstream approval receipt is missing: {approval_id}")
            receipt = read_mapping(path)
            if receipt.get("approval_id") != approval_id or receipt.get("status") != "consumed" or receipt.get("gate") not in gates:
                raise TrialContractError(f"upstream approval receipt is not consumed: {approval_id}")

    def approve(self, contract_path: Path | str, approval_path: Path | str) -> dict[str, Any]:
        contract = self.load(contract_path)
        if contract.get("project_core_approved") is not True or contract.get("baseline_approved") is not True:
            raise TrialContractError("Project Core and baseline approvals must be recorded before contract approval")
        self.validate_upstream_bindings(contract)
        approval = self.approvals.consume(
            approval_path,
            expected_gate="TRIAL_CONTRACT",
            expected_subject_path=contract_path,
        )
        if approval.get("gate") != "TRIAL_CONTRACT":
            raise TrialContractError("approval gate is not TRIAL_CONTRACT")
        updated = dict(contract)
        updated["status"] = "APPROVED"
        updated["approved_by_user"] = True
        updated["approval_id"] = approval["approval_id"]
        updated["approval_subject_sha256"] = approval.get("subject_sha256")
        updated["approved_at"] = utc_now()
        updated["approval"] = {"required": True, "approved_by_user": True, "approval_id": approval["approval_id"]}
        updated["contract_sha256"] = contract_hash(updated)
        validate_contract(updated)
        self.save(updated, filename=Path(contract_path).name)
        return updated

    def assert_approved(self, contract_path: Path | str, *, expected_hash: Optional[str] = None) -> dict[str, Any]:
        contract = self.load(contract_path)
        if contract.get("status") != "APPROVED" or contract.get("approved_by_user") is not True or contract.get("approval", {}).get("approved_by_user") is not True:
            raise TrialContractError("trial contract is not approved")
        if contract.get("project_core_approved") is not True or contract.get("baseline_approved") is not True:
            raise TrialContractError("trial contract upstream approvals are incomplete")
        if not contract.get("approval_id") or contract.get("approval", {}).get("approval_id") != contract.get("approval_id"):
            raise TrialContractError("trial contract approval receipt is incomplete")
        if expected_hash and contract_hash(contract) != expected_hash:
            raise TrialContractError("trial contract drift")
        self.validate_upstream_bindings(contract)
        return contract

    def amend(self, contract_path: Path | str, *, user_instruction: str, changes: Mapping[str, Any]) -> dict[str, Any]:
        old = self.load(contract_path)
        amendment = {
            "schema_version": "robotics-ar-trial-contract-amendment.v1",
            "amendment_id": f"{old['contract_id']}-amendment-{len(list(self.contracts_dir.glob(old['contract_id'] + '-amendment-*.yaml'))) + 1:03d}",
            "parent_contract_sha256": contract_hash(old),
            "user_instruction_verbatim": user_instruction,
            "changes": dict(changes),
            "created_at": utc_now(),
            "approval": {"required": True, "approved_by_user": False},
        }
        amendment["amendment_sha256"] = sha256_obj(amendment)
        try:
            validate_artifact("robotics-ar-trial-contract-amendment.v1", amendment)
        except SchemaValidationError as exc:
            raise TrialContractError(str(exc)) from exc
        path = self.contracts_dir / f"{amendment['amendment_id']}.yaml"
        write_structured(path, amendment)
        invalidated = dict(old)
        invalidated["status"] = "INVALIDATED"
        invalidated["approval"] = {"required": True, "approved_by_user": False, "invalidated_by": amendment["amendment_id"]}
        invalidated["contract_sha256"] = contract_hash(invalidated)
        self.save(invalidated, filename=Path(contract_path).name)
        return amendment

    def compile_amended(self, contract_path: Path | str, amendment_path: Path | str) -> dict[str, Any]:
        """Compile a new draft from an amendment; never revive the old approval."""

        old = self.load(contract_path)
        amendment = read_mapping(amendment_path)
        expected_amendment_hash = sha256_obj({key: value for key, value in amendment.items() if key != "amendment_sha256"})
        if amendment.get("amendment_sha256") != expected_amendment_hash:
            raise TrialContractError("amendment hash mismatch")
        if amendment.get("parent_contract_sha256") != contract_hash(old):
            raise TrialContractError("amendment parent contract mismatch")
        if old.get("status") != "INVALIDATED":
            raise TrialContractError("parent contract must be invalidated before compiling an amendment")
        changes = dict(amendment.get("changes", {}))
        updated = dict(old)
        for key in ("approved_by_user", "approval_id", "approved_at", "approval_subject_sha256"):
            updated.pop(key, None)
        updated["status"] = "DRAFT"
        updated["approval"] = {"required": True, "approved_by_user": False}
        updated["contract_id"] = f"{old['contract_id']}-{amendment['amendment_id'].rsplit('-', 1)[-1]}"
        updated["amendment_id"] = amendment["amendment_id"]
        updated["parent_contract_sha256"] = amendment["parent_contract_sha256"]
        updated["amendment_changes"] = changes
        if isinstance(changes.get("budget"), Mapping):
            budget = dict(updated.get("budget", {}))
            budget.update(dict(changes["budget"]))
            updated["budget"] = budget
        if isinstance(changes.get("primary_objective"), Mapping):
            updated["primary_objective"] = dict(changes["primary_objective"])
        if "objective" in changes and not isinstance(changes["objective"], Mapping):
            updated["amendment_objective"] = str(changes["objective"])
        if isinstance(changes.get("allowed_search_space"), Mapping):
            search_space = dict(updated.get("allowed_search_space", {}))
            search_space.update(dict(changes["allowed_search_space"]))
            updated["allowed_search_space"] = search_space
        if isinstance(changes.get("allowed_changes"), list):
            search_space = dict(updated.get("allowed_search_space", {}))
            search_space["amendment_allowed_changes"] = list(changes["allowed_changes"])
            updated["allowed_search_space"] = search_space
        if isinstance(changes.get("forbidden_changes"), list):
            existing = list(updated.get("forbidden_changes", []))
            updated["forbidden_changes"] = existing + [item for item in changes["forbidden_changes"] if item not in existing]
        if any(key in changes for key in ("project_core_sha256", "baseline_receipt_sha256", "environment_receipt_sha256")):
            updated["project_core_approved"] = False
            updated["baseline_approved"] = False
            updated["upstream_approval_binding_required"] = bool(updated.get("upstream_approval_binding_required", False))
            for key in ("project_core_approval_id", "baseline_approval_id"):
                updated.pop(key, None)
        if "task_sha256" in changes:
            updated["task_sha256"] = changes["task_sha256"]
        updated["created_at"] = utc_now()
        updated["contract_sha256"] = contract_hash(updated)
        validate_contract(updated)
        try:
            validate_artifact("robotics-ar-trial-contract.v1", updated)
        except SchemaValidationError as exc:
            raise TrialContractError(str(exc)) from exc
        return updated

    @staticmethod
    def check_trial(contract: Mapping[str, Any], proposal: Mapping[str, Any], *, used_trials: int = 0, parallel_jobs: int = 0, environment_receipt_sha256: str = "") -> None:
        validate_contract(contract)
        if contract.get("status") != "APPROVED" or contract.get("approval", {}).get("approved_by_user") is not True:
            raise TrialContractError("approved contract required")
        parent = str(proposal.get("parent_contract", ""))
        if not parent:
            raise TrialContractError("trial proposal must bind to an approved contract")
        if parent not in {str(contract.get("contract_sha256")), str(contract.get("contract_id"))}:
            raise TrialContractError("trial proposal is bound to a different contract")
        if contract.get("project_core_approved") is not True or contract.get("baseline_approved") is not True:
            raise TrialContractError("Project Core and baseline approvals are required")
        if contract.get("baseline_reproduction_status") is not None:
            status = contract.get("baseline_reproduction_status")
            if status != "REPRODUCED" and not (status == "REPRODUCED_WITH_VARIANCE" and contract.get("baseline_user_approved_variance") is True):
                raise TrialContractError("baseline is not approved for autonomous trials")
        budget = contract["budget"]
        if used_trials >= int(budget.get("max_trials", 0)):
            raise TrialContractError("trial budget exhausted")
        if parallel_jobs >= int(budget.get("max_parallel_jobs", 1)):
            raise TrialContractError("parallel-job budget exceeded")
        if not environment_receipt_sha256:
            raise TrialContractError("environment receipt binding is required for every trial")
        if environment_receipt_sha256 != contract.get("environment_receipt_sha256"):
            raise TrialContractError("environment receipt drift")
        change = proposal.get("change", {}) if isinstance(proposal.get("change", {}), Mapping) else {}
        tier = int(change.get("tier", 3))
        if tier not in TIERS:
            raise TrialContractError("invalid trial tier")
        allowed_tiers = set()
        for key, value in contract.get("allowed_search_space", {}).items():
            if isinstance(value, list):
                allowed_tiers.add(int(key.split("_")[-1]) if key.split("_")[-1].isdigit() else 0)
        if allowed_tiers and tier not in allowed_tiers:
            raise TrialContractError("trial tier is not in approved search space")
        paths = list(change.get("files_allowed", change.get("components", [])) or [])
        allowed_paths = [str(item).strip("/") for item in contract.get("allowed_paths", [])]
        read_only_paths = [str(item).strip("/") for item in contract.get("read_only_paths", [])]
        for path in paths:
            raw_path = str(path)
            if "\x00" in raw_path or Path(raw_path).is_absolute() or ".." in Path(raw_path).parts:
                raise TrialContractError(f"trial path contains traversal: {path}")
            normalized = raw_path.strip("/")
            if allowed_paths and not any(normalized == rule or normalized.startswith(rule.rstrip("/") + "/") for rule in allowed_paths):
                raise TrialContractError(f"trial changes outside allowed paths: {path}")
            if any(normalized == rule or normalized.startswith(rule.rstrip("/") + "/") for rule in read_only_paths):
                raise TrialContractError(f"trial changes a read-only path: {path}")
            if any(normalized == str(forbidden).strip("/") or normalized.startswith(str(forbidden).strip("/").rstrip("/") + "/") for forbidden in contract.get("forbidden_paths", []) + contract.get("forbidden_changes", [])):
                raise TrialContractError(f"trial changes forbidden path/component: {path}")
        forbidden_files = list(change.get("files_forbidden", []) or [])
        for path in forbidden_files:
            if not isinstance(path, str) or ".." in Path(path).parts or Path(path).is_absolute():
                raise TrialContractError(f"trial forbidden path contains traversal: {path}")
        if tier >= 3:
            raise TrialContractError("Tier 3 method/claim pivot requires escalation")


def compile_and_save(values: Mapping[str, Any], path: Path | str) -> dict[str, Any]:
    contract = compile_trial_contract(values)
    write_structured(path, contract)
    return contract
