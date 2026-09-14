"""Midstream Takeover intake and lifecycle orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional

from .atomic_io import atomic_write_bytes, atomic_write_json
from .canonical import sha256_obj
from .event_log import EventLog
from .models import utc_now
from .receipts import file_sha256
from .schema_validation import SchemaValidationError, validate_artifact
from .project_core import ProjectCoreError, compile_project_core, load_project_core, mark_project_core_approved, save_project_core, write_core_summary
from .session import SessionError, SessionManager
from .transaction import serialized
from .environment import validate_environment_receipt
from .structured import read_mapping, write_structured
from .trial_contract import contract_hash


class TakeoverError(RuntimeError):
    """Raised when a midstream takeover cannot proceed safely."""


INTAKE_REQUIRED = ("project_id", "project_path", "project_core", "current_goal", "current_bottleneck", "environment", "allowed_directions", "forbidden_changes", "budget", "pause_conditions")


def intake_hash(intake: Mapping[str, Any]) -> str:
    return sha256_obj({key: value for key, value in intake.items() if key != "intake_sha256"})


def validate_intake(intake: Mapping[str, Any], *, require_hash: bool = True) -> None:
    if not isinstance(intake, Mapping):
        raise TakeoverError("takeover intake must be a mapping")
    missing = [key for key in INTAKE_REQUIRED if key not in intake]
    if missing:
        raise TakeoverError(f"takeover intake missing: {missing}")
    if intake.get("schema_version") != "robotics-ar-takeover-intake.v1":
        raise TakeoverError("unsupported takeover intake schema")
    for field in ("user_asserted", "repository_observed", "agent_inferred", "unresolved"):
        if field not in intake or not isinstance(intake[field], (list, dict)):
            raise TakeoverError(f"intake fact bucket missing or invalid: {field}")
    if not isinstance(intake.get("project_core"), Mapping):
        raise TakeoverError("project_core must be an object")
    if not isinstance(intake.get("environment"), Mapping):
        raise TakeoverError("environment must be an object")
    if not isinstance(intake.get("budget"), Mapping):
        raise TakeoverError("budget must be an object")
    if require_hash and intake.get("intake_sha256") != intake_hash(intake):
        raise TakeoverError("takeover intake hash mismatch")
    try:
        validate_artifact("robotics-ar-takeover-intake.v1", intake)
    except SchemaValidationError as exc:
        raise TakeoverError(str(exc)) from exc


def build_intake(values: Mapping[str, Any], *, user_statement: str = "") -> dict[str, Any]:
    """Compile an intake while retaining source provenance buckets."""

    if not isinstance(values, Mapping):
        raise TakeoverError("intake input must be a mapping")
    intake = {
        "schema_version": "robotics-ar-takeover-intake.v1",
        "project_id": str(values.get("project_id", "")).strip(),
        "project_path": str(values.get("project_path", "")),
        "project_core": dict(values.get("project_core", {})),
        "current_goal": str(values.get("current_goal", values.get("current_batch_goal", ""))),
        "current_bottleneck": str(values.get("current_bottleneck", "")),
        "environment": dict(values.get("environment", {})),
        "allowed_directions": list(values.get("allowed_directions", values.get("allowed_search_directions", [])) or []),
        "forbidden_changes": list(values.get("forbidden_changes", values.get("forbidden_pivots", [])) or []),
        "budget": dict(values.get("budget", {})),
        "pause_conditions": list(values.get("pause_conditions", values.get("stop_conditions", [])) or []),
        "user_asserted": list(values.get("user_asserted", [])) if isinstance(values.get("user_asserted", []), list) else dict(values.get("user_asserted", {})),
        "repository_observed": list(values.get("repository_observed", [])) if isinstance(values.get("repository_observed", []), list) else dict(values.get("repository_observed", {})),
        "agent_inferred": list(values.get("agent_inferred", [])) if isinstance(values.get("agent_inferred", []), list) else dict(values.get("agent_inferred", {})),
        "unresolved": list(values.get("unresolved", [])) if isinstance(values.get("unresolved", []), list) else dict(values.get("unresolved", {})),
        "created_at": utc_now(),
    }
    if user_statement:
        intake["user_statement_sha256"] = sha256_obj({"user_statement": user_statement})
    intake["intake_sha256"] = intake_hash(intake)
    validate_intake(intake)
    return intake


class TakeoverManager:
    """Own takeover artifacts and only advance through explicit v3 states."""

    def __init__(self, manager: SessionManager) -> None:
        self.manager = manager

    @property
    def paths(self):
        return self.manager.paths

    def _require_mode(self) -> None:
        if self.manager.state.get("entry_mode", "NEW_RESEARCH") != "MIDSTREAM_TAKEOVER":
            raise TakeoverError("session entry_mode is not MIDSTREAM_TAKEOVER")

    def _invalidate_active_contract(self) -> None:
        """Invalidate a previously approved contract after upstream drift."""

        value = self.manager.state.get("contract_path")
        if not value:
            return
        path = Path(str(value)).resolve()
        try:
            path.relative_to(self.paths.takeover_contracts.resolve())
        except ValueError as exc:
            raise TakeoverError("active Trial Contract path escapes the contracts root") from exc
        if not path.is_file():
            return
        try:
            contract = read_mapping(path)
        except Exception as exc:
            raise TakeoverError("active Trial Contract cannot be read during upstream invalidation") from exc
        if contract.get("status") != "APPROVED":
            return
        invalidated = dict(contract)
        invalidated["status"] = "INVALIDATED"
        invalidated["approval"] = {"required": True, "approved_by_user": False, "invalidated_by": "upstream-drift"}
        invalidated["contract_sha256"] = contract_hash(invalidated)
        write_structured(path, invalidated)

    def initialize(self) -> dict[str, Any]:
        self._require_mode()
        state = self.manager.state["state"]
        if state == "PLANNING_READY":
            state = self.manager.transition("TAKEOVER_REQUESTED", "TAKEOVER_INITIALIZED", {"entry_mode": "MIDSTREAM_TAKEOVER"})
        elif state != "TAKEOVER_REQUESTED":
            raise TakeoverError(f"takeover cannot initialize from {state}")
        return state

    def record_intake(self, values: Mapping[str, Any], *, user_statement: str = "") -> dict[str, Any]:
        self._require_mode()
        if self.manager.state["state"] == "TAKEOVER_REQUESTED":
            self.manager.transition("TAKEOVER_INTERVIEW", "TAKEOVER_INTERVIEW_STARTED")
        if self.manager.state["state"] != "TAKEOVER_INTERVIEW":
            raise TakeoverError("takeover interview state required")
        intake = build_intake(values, user_statement=user_statement)
        if user_statement:
            atomic_write_bytes(self.paths.takeover_intake / "user-statement.md", user_statement.encode("utf-8"))
        write_structured(self.paths.takeover_intake / "takeover-intake.yaml", intake)
        questions = intake.get("unresolved", [])
        lines = ["# Open questions", "", *[f"- {item}" for item in questions], ""]
        atomic_write_bytes(self.paths.takeover_intake / "open-questions.md", "\n".join(lines).encode("utf-8"))
        self.manager.transition("TAKEOVER_AUDITING", "TAKEOVER_INTAKE_RECORDED", {"intake_sha256": intake["intake_sha256"]})
        return intake

    @serialized
    def record_audit(self, audit_receipt: Mapping[str, Any]) -> dict[str, Any]:
        if self.manager.state["state"] != "TAKEOVER_AUDITING":
            raise TakeoverError("takeover audit state required")
        receipt = dict(audit_receipt)
        if receipt.get("receipt_sha256") and receipt.get("receipt_sha256") != sha256_obj({key: value for key, value in receipt.items() if key != "receipt_sha256"}):
            raise TakeoverError("audit receipt hash mismatch")
        atomic_write_json(self.paths.takeover_audit / "audit-receipt.json", receipt)
        self.manager.transition("TAKEOVER_HISTORY_RECONSTRUCTION", "PROJECT_AUDIT_COMPLETED", {"receipt_sha256": sha256_obj(receipt)})
        return receipt

    @serialized
    def mark_history_reconstructed(self, *, needs_reconciliation: bool = False, receipt: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
        if self.manager.state["state"] != "TAKEOVER_HISTORY_RECONSTRUCTION":
            raise TakeoverError("history reconstruction state required")
        if receipt is not None:
            atomic_write_json(self.paths.takeover_history / "history-reconstruction-receipt.json", dict(receipt))
        # 审计要求只能加强。 / Audit requirements may only be strengthened.
        audit_path = self.paths.takeover_audit / "audit-receipt.json"
        bound_audits = [event for event in EventLog(self.manager.paths.events, self.manager.session_id).read_events() if event["event_type"] == "PROJECT_AUDIT_COMPLETED"]
        if bound_audits and not audit_path.exists():
            raise TakeoverError("bound audit receipt is missing")
        if audit_path.exists():
            from .structured import read_mapping

            audit = read_mapping(audit_path)
            digest = audit.get("receipt_sha256")
            if digest and digest != sha256_obj({k: v for k, v in audit.items() if k != "receipt_sha256"}):
                raise TakeoverError("audit receipt hash mismatch")
            bindings = [e for e in EventLog(self.manager.paths.events, self.manager.session_id).read_events() if e["event_type"] == "PROJECT_AUDIT_COMPLETED"]
            if bindings and bindings[-1]["payload"].get("receipt_sha256") != sha256_obj(audit):
                raise TakeoverError("bound audit receipt changed")
            needs_reconciliation = needs_reconciliation or bool(audit.get("requires_reconciliation"))
        target = "TAKEOVER_IDEA_RECONCILIATION" if needs_reconciliation else "TAKEOVER_ENVIRONMENT_VALIDATION"
        return self.manager.transition(target, "HISTORY_RECONSTRUCTED", {"needs_reconciliation": needs_reconciliation})

    def complete_idea_reconciliation(self, result: Mapping[str, Any]) -> dict[str, Any]:
        if self.manager.state["state"] != "TAKEOVER_IDEA_RECONCILIATION":
            raise TakeoverError("idea reconciliation state required")
        write_structured(self.paths.takeover / "idea-reconciliation.yaml", dict(result))
        return self.manager.transition("TAKEOVER_ENVIRONMENT_VALIDATION", "TAKEOVER_IDEA_RECONCILIATION_COMPLETED", {"result_sha256": sha256_obj(dict(result))})

    @serialized
    def mark_environment(self, receipt: Mapping[str, Any]) -> dict[str, Any]:
        if self.manager.state["state"] != "TAKEOVER_ENVIRONMENT_VALIDATION":
            raise TakeoverError("environment validation state required")
        write_structured(self.paths.takeover / "environment-receipt.yaml", dict(receipt))
        if receipt.get("status") != "ONLINE_VERIFIED":
            self.manager.transition("BLOCKED_ENVIRONMENT", "ENVIRONMENT_VERIFICATION_FAILED", {"status": receipt.get("status")})
            raise TakeoverError("environment is not ONLINE_VERIFIED")
        try:
            validate_environment_receipt(receipt, require_online=True)
        except (SchemaValidationError, RuntimeError) as exc:
            raise TakeoverError(str(exc)) from exc
        write_structured(self.paths.takeover / "environment-receipt.yaml", dict(receipt))
        self.manager.bind_environment_receipt(receipt, receipt_path=self.paths.takeover / "environment-receipt.yaml")
        return self.manager.transition("TAKEOVER_BASELINE_SELECTION", "ENVIRONMENT_VERIFIED", {"fingerprint": receipt.get("fingerprint")})

    @serialized
    def begin_baseline(self, selection: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
        if selection is not None:
            from .structured import read_mapping

            path = self.paths.takeover_baseline / "baseline-selection.json"
            if path.exists():
                if read_mapping(path) != dict(selection):
                    raise TakeoverError("baseline selection changed; explicit amendment required")
                if self.manager.state["state"] == "TAKEOVER_BASELINE_REPRODUCTION":
                    return self.manager.state
        if self.manager.state["state"] != "TAKEOVER_BASELINE_SELECTION":
            raise TakeoverError("baseline selection state required")
        if selection is not None:
            atomic_write_json(path, dict(selection))
        return self.manager.transition("TAKEOVER_BASELINE_REPRODUCTION", "BASELINE_SELECTED")

    @serialized
    def baseline_result(self, result: Mapping[str, Any], *, recovery: bool = False) -> dict[str, Any]:
        current = self.manager.state["state"]
        if current not in {"TAKEOVER_BASELINE_REPRODUCTION", "TAKEOVER_BASELINE_RECOVERY"}:
            raise TakeoverError("baseline reproduction state required")
        try:
            validate_artifact("robotics-ar-baseline-receipt.v1", result)
        except SchemaValidationError as exc:
            raise TakeoverError(str(exc)) from exc
        if result.get("receipt_sha256") != sha256_obj({key: value for key, value in result.items() if key != "receipt_sha256"}):
            raise TakeoverError("baseline receipt hash mismatch")
        self._invalidate_active_contract()
        # 留存各次结果，不覆盖失败原因。 / Retain every result and failure cause.
        import uuid
        atomic_write_json(self.paths.takeover_baseline / "attempts" / f"{uuid.uuid4().hex}-{result['receipt_sha256']}.json", dict(result))
        write_structured(self.paths.takeover_baseline / "baseline-receipt.json", dict(result))
        updated = dict(self.manager.state)
        updated["baseline_receipt_sha256"] = result.get("receipt_sha256")
        updated["baseline_receipt_path"] = (self.paths.takeover_baseline / "baseline-receipt.json").as_posix()
        updated["baseline_reproduction_status"] = result.get("reproduction_status", result.get("status"))
        # A newly written receipt is a new evidence subject.  Never carry an
        # approval from an earlier reproduction into this result.
        updated["baseline_approved"] = False
        updated["contract_approved"] = False
        updated.pop("baseline_approval_id", None)
        atomic_write_json(self.manager.paths.state, updated)
        self.manager._state = updated
        status = str(result.get("reproduction_status", result.get("status", "")))
        if status in {"REPRODUCED", "REPRODUCED_WITH_VARIANCE", "PARTIALLY_REPRODUCED"}:
            return self.manager.transition("AWAITING_TAKEOVER_APPROVAL", "BASELINE_REPRODUCED", {"status": status})
        if status in {"NOT_REPRODUCED", "FAILED_REPRODUCTION", "BLOCKED", "UNTRUSTED", "UNKNOWN"}:
            if current == "TAKEOVER_BASELINE_RECOVERY":
                from .event_log import EventLog

                EventLog(self.manager.paths.events, self.manager.session_id).append("BASELINE_RECOVERY_FAILED", "supervisor", current, current, {"status": status, "receipt_sha256": result["receipt_sha256"]})
                return self.manager.state
            return self.manager.transition("TAKEOVER_BASELINE_RECOVERY", "BASELINE_RECOVERY_REQUIRED", {"status": status})
        raise TakeoverError("invalid baseline result")

    @serialized
    def amend_baseline_selection(self, selection, spec_path, approval_path):
        """批准后修改未完成的基线选择，保留旧绑定。 / Amend an unfinished selection with approval and preserve its prior binding."""
        if self.manager.state["state"] not in {"TAKEOVER_BASELINE_REPRODUCTION", "TAKEOVER_BASELINE_RECOVERY"}:
            raise TakeoverError("selection amendment requires reproduction or recovery state")
        from .execution_registry import ExecutionRegistry
        if any(row["status"] in {"PREPARING", "RESERVED", "RUNNING"} for row in ExecutionRegistry(self.manager).read()["executions"].values()):
            raise TakeoverError("close outstanding execution before amending baseline")
        path = self.paths.takeover_baseline / "baseline-selection.json"
        previous = read_mapping(path)
        if previous == dict(selection):
            return self.manager.state
        approval = self.manager.consume_approval(approval_path, expected_gate="BASELINE", expected_subject_path=spec_path)
        atomic_write_json(self.paths.takeover_baseline / "selections" / f"{sha256_obj(previous)}.json", previous)
        atomic_write_json(path, dict(selection))
        self._invalidate_active_contract()
        state = self.manager.state
        for field in ("baseline_receipt_path", "baseline_receipt_sha256", "baseline_approval_id"):
            state.pop(field, None)
        state.update(baseline_approved=False, contract_approved=False)
        atomic_write_json(self.manager.paths.state, state)
        self.manager._state = state
        return self.manager.record_event("BASELINE_SELECTION_AMENDED", {"selection_sha256": sha256_obj(selection), "approval_id": approval["approval_id"]})

    def approve_baseline(self, approval_id: str) -> dict[str, Any]:
        """Record a user baseline approval and release the contract-compilation gate."""

        if not approval_id:
            raise TakeoverError("baseline approval id is required")
        if self.manager.state.get("state") != "AWAITING_TAKEOVER_APPROVAL":
            raise TakeoverError("baseline approval state required")
        path = self.paths.takeover_baseline / "baseline-receipt.json"
        if not path.exists():
            raise TakeoverError("baseline receipt is missing")
        approval_path = self.paths.approvals / f"{approval_id}.json"
        if not approval_path.is_file():
            raise TakeoverError("baseline approval receipt is missing")
        approval = read_mapping(approval_path)
        if approval.get("gate") not in {"BASELINE", "EXPERIMENT"} or approval.get("status") != "consumed":
            raise TakeoverError("baseline approval receipt is not a consumed baseline gate")
        if Path(str(approval.get("subject_path", ""))).resolve() != path.resolve():
            raise TakeoverError("baseline approval subject mismatch")
        if approval.get("subject_sha256") != file_sha256(path):
            raise TakeoverError("baseline approval subject drift")
        receipt = read_mapping(path)
        if receipt.get("receipt_sha256") and receipt.get("receipt_sha256") != sha256_obj({key: value for key, value in receipt.items() if key != "receipt_sha256"}):
            raise TakeoverError("baseline receipt hash mismatch")
        status = str(receipt.get("reproduction_status", receipt.get("status", "")))
        if status not in {"REPRODUCED", "REPRODUCED_WITH_VARIANCE", "PARTIALLY_REPRODUCED"}:
            raise TakeoverError("only a reproduced baseline can be approved")
        if status in {"PARTIALLY_REPRODUCED", "REPRODUCED_WITH_VARIANCE"}:
            status = "REPRODUCED_WITH_VARIANCE"
            receipt["reproduction_status"] = status
            receipt["user_approved_variance"] = True
        receipt["approved_by_user"] = True
        receipt["approval_id"] = approval_id
        receipt.pop("receipt_sha256", None)
        receipt["receipt_sha256"] = sha256_obj(receipt)
        write_structured(path, receipt)
        updated = dict(self.manager.state)
        updated["baseline_approved"] = True
        updated["baseline_approval_id"] = approval_id
        updated["baseline_receipt_sha256"] = receipt["receipt_sha256"]
        updated["baseline_reproduction_status"] = receipt.get("reproduction_status")
        from .atomic_io import atomic_write_json

        atomic_write_json(self.manager.paths.state, updated)
        self.manager._state = updated
        if self.manager.state["state"] == "AWAITING_TAKEOVER_APPROVAL" and self.manager.state.get("project_core_approved"):
            self.manager.transition("TRIAL_CONTRACT_COMPILATION", "BASELINE_APPROVED", {"approval_id": approval_id})
        return receipt

    def approve_core(self, approval_path: Path | str, *, core_path: Optional[Path | str] = None) -> dict[str, Any]:
        """Consume a TAKEOVER_CORE approval and persist the approved core."""

        target_core_path = Path(core_path) if core_path else self.paths.takeover / "project-core.yaml"
        core = load_project_core(target_core_path)
        approval = self.manager.consume_approval(
            approval_path,
            expected_gate=("TAKEOVER_CORE", "IDEA"),
            expected_subject_path=target_core_path,
        )
        if approval.get("gate") not in {"TAKEOVER_CORE", "IDEA"}:
            raise TakeoverError("approval gate is not TAKEOVER_CORE")
        approved = mark_project_core_approved(core, approval_id=str(approval["approval_id"]))
        save_project_core(target_core_path, approved)
        updated = dict(self.manager.state)
        updated.update({"project_core_sha256": approved["project_core_sha256"], "project_core_approved": True})
        updated["project_core_approval_id"] = str(approval["approval_id"])
        from .atomic_io import atomic_write_json

        atomic_write_json(self.manager.paths.state, updated)
        self.manager._state = updated
        self.manager.record_event("PROJECT_CORE_APPROVED", {"approval_id": approval["approval_id"]})
        if self.manager.state["state"] == "AWAITING_TAKEOVER_APPROVAL" and self.manager.state.get("baseline_approved"):
            self.manager.transition("TRIAL_CONTRACT_COMPILATION", "PROJECT_CORE_APPROVED", {"approval_id": approval["approval_id"]})
        return approved

    def compile_core(self, values: Mapping[str, Any]) -> dict[str, Any]:
        if self.manager.state["state"] not in {"TAKEOVER_INTERVIEW", "TAKEOVER_AUDITING", "TAKEOVER_HISTORY_RECONSTRUCTION", "TAKEOVER_IDEA_RECONCILIATION", "TAKEOVER_ENVIRONMENT_VALIDATION", "TAKEOVER_BASELINE_REPRODUCTION", "TAKEOVER_BASELINE_RECOVERY", "AWAITING_TAKEOVER_APPROVAL"}:
            raise TakeoverError("takeover planning state required")
        self._invalidate_active_contract()
        user_statement_hash = file_sha256(self.paths.takeover_intake / "user-statement.md") if (self.paths.takeover_intake / "user-statement.md").is_file() else ""
        snapshot_hash = ""
        snapshot_path = self.paths.takeover_audit / "project-snapshot.json"
        if snapshot_path.is_file():
            snapshot_hash = str(read_mapping(snapshot_path).get("snapshot_sha256", ""))
        core = compile_project_core(values, user_statement_sha256=user_statement_hash, repository_snapshot_sha256=snapshot_hash)
        save_project_core(self.paths.takeover / "project-core.yaml", core)
        write_core_summary(self.paths.takeover / "project-core.md", core)
        updated = dict(self.manager.state)
        updated["project_core_sha256"] = core["project_core_sha256"]
        updated["project_core_path"] = (self.paths.takeover / "project-core.yaml").as_posix()
        # Recompiling the core changes the immutable takeover subject.  Any
        # prior core/baseline/contract approval must be reacquired.
        updated["project_core_approved"] = False
        updated["baseline_approved"] = False
        updated["contract_approved"] = False
        updated.pop("project_core_approval_id", None)
        updated.pop("baseline_approval_id", None)
        from .atomic_io import atomic_write_json

        atomic_write_json(self.manager.paths.state, updated)
        self.manager._state = updated
        self.manager.record_event("PROJECT_CORE_COMPILED", {"project_core_sha256": core["project_core_sha256"]})
        return core

    def status(self) -> dict[str, Any]:
        state = self.manager.state
        result = {"entry_mode": state.get("entry_mode", "NEW_RESEARCH"), "state": state.get("state"), "session_id": state.get("session_id")}
        for name, path in (("intake", self.paths.takeover_intake / "takeover-intake.yaml"), ("project_core", self.paths.takeover / "project-core.yaml"), ("baseline", self.paths.takeover_baseline / "baseline-receipt.json"), ("environment", self.paths.takeover / "environment-receipt.yaml")):
            if path.exists():
                result[f"{name}_path"] = path.as_posix()
        return result


def initialize_takeover(manager: SessionManager) -> dict[str, Any]:
    return TakeoverManager(manager).initialize()
