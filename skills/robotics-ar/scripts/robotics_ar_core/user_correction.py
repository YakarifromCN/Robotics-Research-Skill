"""Compile human natural-language corrections into auditable tasks and amendments."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional

from .atomic_io import atomic_write_bytes, atomic_write_json
from .canonical import sha256_obj
from .models import utc_now
from .session import SessionManager, SessionError
from .schema_validation import SchemaValidationError, validate_artifact
from .structured import read_mapping, write_structured
from .trial_contract import TrialContractManager


class UserCorrectionError(RuntimeError):
    """Raised when a correction cannot be compiled without ambiguity."""


def _task_hash(task: Mapping[str, Any]) -> str:
    """Hash task content while keeping the separately bound contract reference mutable."""

    ignored = {"task_sha256", "contract_path", "contract_sha256", "contract_amendment_path"}
    return sha256_obj({key: value for key, value in task.items() if key not in ignored})


def compile_correction(manager: SessionManager, instruction: str, *, objective: str = "", project_core_ref: str = "", active_hypothesis: str = "", allowed_changes: Optional[list[str]] = None, forbidden_changes: Optional[list[str]] = None, agents: Optional[list[str]] = None, environment: Optional[Mapping[str, Any]] = None, tests: Optional[list[str]] = None, experiments: Optional[list[str]] = None, metrics: Optional[list[str]] = None, budget: Optional[Mapping[str, Any]] = None, completion_criteria: Optional[list[str]] = None, stop_conditions: Optional[list[str]] = None, escalation_conditions: Optional[list[str]] = None, contract_path: Optional[Path | str] = None) -> dict[str, Any]:
    if not instruction.strip():
        raise UserCorrectionError("user instruction must not be empty")
    root = manager.paths.tasks
    correction_id = f"user-correction-{len(list(root.glob('user-correction-*.yaml'))) + 1:03d}"
    task = {
        "schema_version": "robotics-ar-user-correction.v1",
        "correction_id": correction_id,
        "user_instruction_verbatim": instruction,
        "interpreted_objective": objective,
        "project_core_reference": project_core_ref,
        "active_hypothesis": active_hypothesis,
        "allowed_changes": list(allowed_changes or []),
        "forbidden_changes": list(forbidden_changes or []),
        "assigned_agents": list(agents or ["Supervisor", "Code Agent", "Test Agent", "Environment Runner", "Data Analyst", "Dynamic Expert"]),
        "environment": dict(environment or {}),
        "tests": list(tests or []),
        "experiments": list(experiments or []),
        "metrics": list(metrics or []),
        "budget": dict(budget or {}),
        "completion_criteria": list(completion_criteria or []),
        "stop_conditions": list(stop_conditions or []),
        "escalation_conditions": list(escalation_conditions or []),
        "created_at": utc_now(),
    }
    yaml_path = root / f"{correction_id}.yaml"
    task["task_path"] = yaml_path.as_posix()
    task["task_sha256"] = _task_hash(task)
    try:
        validate_artifact("robotics-ar-user-correction.v1", task)
    except SchemaValidationError as exc:
        raise UserCorrectionError(str(exc)) from exc
    markdown = [
        "# Active Task", "", "## User Instruction Verbatim", "", instruction, "",
        "## Interpreted Objective", "", objective, "",
        "## Project Core Reference", "", project_core_ref, "",
        "## Active Hypothesis", "", active_hypothesis, "",
        "## Allowed Changes", "", *[f"- {item}" for item in task["allowed_changes"]], "",
        "## Forbidden Changes", "", *[f"- {item}" for item in task["forbidden_changes"]], "",
        "## Assigned Agents", "", *[f"- {item}" for item in task["assigned_agents"]], "",
        "## Environment", "", str(task["environment"]), "",
        "## Tests", "", *[f"- {item}" for item in task["tests"]], "",
        "## Experiments", "", *[f"- {item}" for item in task["experiments"]], "",
        "## Metrics", "", *[f"- {item}" for item in task["metrics"]], "",
        "## Budget", "", str(task["budget"]), "",
        "## Completion Criteria", "", *[f"- {item}" for item in task["completion_criteria"]], "",
        "## Stop / Escalation Conditions", "", *[f"- {item}" for item in task["stop_conditions"]], *[f"- ESCALATE: {item}" for item in task["escalation_conditions"]], "",
        f"Task hash: `{task['task_sha256']}`", "",
    ]
    # Keep the supervisor-owned root task for backwards compatibility, while
    # also materialising the v3 task artifact at the documented task root.
    atomic_write_bytes(manager.paths.tasks / "task.md", "\n".join(markdown).encode("utf-8"))
    atomic_write_bytes(root / "task.md", "\n".join(markdown).encode("utf-8"))
    atomic_write_bytes(manager.paths.root_task, "\n".join(markdown).encode("utf-8"))
    if contract_path:
        contracts = TrialContractManager(manager.paths.takeover_contracts, manager.paths.approvals)
        amendment = contracts.amend(contract_path, user_instruction=instruction, changes={"task_sha256": task["task_sha256"], "allowed_changes": task["allowed_changes"], "forbidden_changes": task["forbidden_changes"], "budget": task["budget"], "objective": objective})
        amendment_path = manager.paths.takeover_contracts / f"{amendment['amendment_id']}.yaml"
        amended_contract = contracts.compile_amended(contract_path, amendment_path)
        amended_path = contracts.save(amended_contract, filename=f"{amended_contract['contract_id']}.yaml")
        task["contract_amendment_path"] = amendment_path.as_posix()
        task["contract_path"] = amended_path.as_posix()
        task["contract_sha256"] = amended_contract["contract_sha256"]
        manager.record_event("CONTRACT_AMENDED", {"amendment_sha256": amendment["amendment_sha256"], "contract_sha256": amended_contract["contract_sha256"]})
    write_structured(yaml_path, task)
    current = manager.state["state"]
    if current not in {"AWAITING_USER_DIRECTION", "PAUSED"} and current in __import__("robotics_ar_core.state_machine", fromlist=["ACTIVE_STATES"]).ACTIVE_STATES:
        manager.transition("AWAITING_USER_DIRECTION", "USER_CORRECTION_RECORDED", {"task_sha256": task["task_sha256"], "correction_id": correction_id})
    updated = dict(manager.state)
    updated["task_sha256"] = task["task_sha256"]
    updated["task_path"] = yaml_path.as_posix()
    updated["task_approved"] = False
    if task.get("contract_path"):
        updated["contract_path"] = str(task["contract_path"])
        updated["contract_sha256"] = str(task["contract_sha256"])
        updated["contract_approved"] = False
    atomic_write_json(manager.paths.state, updated)
    manager._state = updated
    return task


def assert_task_current(task_path: Path | str, expected_hash: str) -> dict[str, Any]:
    task = read_mapping(task_path)
    try:
        validate_artifact("robotics-ar-user-correction.v1", task)
    except SchemaValidationError as exc:
        raise UserCorrectionError(str(exc)) from exc
    if task.get("task_sha256") != _task_hash(task):
        raise UserCorrectionError("task hash is invalid")
    if task.get("task_sha256") != expected_hash:
        raise UserCorrectionError("task hash drift")
    return task


def confirm_and_resume(manager: SessionManager, *, task_approval_path: Path | str, contract_path: Optional[Path | str] = None, contract_approval_path: Optional[Path | str] = None) -> dict[str, Any]:
    """Consume user confirmations and re-enter a ready takeover state."""

    starting_state = manager.state.get("state")
    if starting_state not in {"AWAITING_USER_DIRECTION", "PAUSED"}:
        raise UserCorrectionError("session is not awaiting user direction")
    task_path = manager.state.get("task_path")
    task_hash = manager.state.get("task_sha256")
    if not task_path or not task_hash:
        raise UserCorrectionError("active corrected task is missing")
    assert_task_current(task_path, str(task_hash))
    active_contract = contract_path or manager.state.get("contract_path")
    if not active_contract:
        raise UserCorrectionError("an approved active Trial Contract is required")
    contracts = TrialContractManager(manager.paths.takeover_contracts, manager.paths.approvals)
    if contract_approval_path:
        contracts.approve(active_contract, contract_approval_path)
    contract = contracts.assert_approved(active_contract)
    task_approval = manager.consume_approval(
        task_approval_path,
        expected_gate="TASK",
        expected_subject_path=task_path,
    )
    if task_approval.get("gate") != "TASK":
        raise UserCorrectionError("task approval gate mismatch")
    updated = dict(manager.state)
    updated["task_approved"] = True
    updated["contract_approved"] = True
    updated["contract_path"] = Path(active_contract).resolve().as_posix()
    updated["contract_sha256"] = contract["contract_sha256"]
    atomic_write_json(manager.paths.state, updated)
    manager._state = updated
    if starting_state == "PAUSED":
        # SessionManager revalidates the pre-pause safe state, all hashes,
        # environment/baseline bindings, and the process registry.
        resumed = manager.resume()
        return {"status": "PASS", "task_approval": task_approval, "contract": contract, "state": resumed}
    manager.transition("TRIAL_BATCH_READY", "USER_CORRECTION_CONFIRMED", {"task_sha256": task_hash, "contract_sha256": contract["contract_sha256"]})
    return {"status": "PASS", "task_approval": task_approval, "contract": contract, "state": manager.state}
