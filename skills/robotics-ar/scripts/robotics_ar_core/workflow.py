"""提供 mock E2E 的监督编排和证据冻结边界。

Provide supervised mock-E2E orchestration and evidence-freeze boundaries.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional

from .agent_protocol import AgentProtocolError, RawEvidenceGuard, make_agent_receipt
from .atomic_io import atomic_write_json, read_json
from .canonical import sha256_obj
from .environment import EnvironmentAdapter, EnvironmentError
from .models import utc_now
from .receipts import artifact_receipt, file_sha256
from .session import SessionError, SessionManager
from .gates import GateError


class WorkflowError(RuntimeError):
    """监督工作流违反阶段或证据边界。 / Raised for workflow boundary violations."""


STAGE_STATES = {
    "idea": ("INVOKING_IDEA_SKILL", "AWAITING_IDEA_APPROVAL"),
    "experiment": ("INVOKING_EXPERIMENT_SKILL", "AWAITING_EXPERIMENT_APPROVAL"),
    "writing": ("INVOKING_WRITING_SKILL", "AWAITING_WRITING_APPROVAL"),
    "review": ("INVOKING_REVIEW_SKILL", "AWAITING_REVIEW_ROUTE"),
}


class SupervisedWorkflow:
    """在不复制 sibling 合同的情况下串联 generic gates。 / Chain generic gates without copying sibling contracts."""

    def __init__(self, manager: SessionManager) -> None:
        self.manager = manager

    def invoke_stage(self, stage: str) -> Dict[str, Any]:
        """进入一个 sibling invocation 状态。 / Enter a sibling invocation state."""

        if stage not in STAGE_STATES:
            raise WorkflowError(f"unknown stage: {stage}")
        if stage == "writing" and self.manager.state["state"] not in {"EVIDENCE_FREEZE", "AWAITING_EVIDENCE_APPROVAL"}:
            raise WorkflowError("writing requires frozen evidence")
        if stage == "review" and self.manager.state["state"] not in {"EVIDENCE_FREEZE", "AWAITING_EVIDENCE_APPROVAL", "AWAITING_WRITING_APPROVAL"}:
            raise WorkflowError("review requires evidence or an approved writing package")
        invoking, _approval = STAGE_STATES[stage]
        state = self.manager.transition(invoking, f"{stage.upper()}_INVOCATION_STARTED")
        return {"stage": stage, "state": state["state"], "session_id": self.manager.session_id}

    def complete_stage(self, stage: str, *, receipt: Mapping[str, Any], runtime_status: str = "SINGLE_AGENT_MODE") -> Dict[str, Any]:
        """保存 generic receipt 并进入 stage approval。 / Save a generic receipt and enter stage approval."""

        if stage not in STAGE_STATES:
            raise WorkflowError(f"unknown stage: {stage}")
        invoking, approval_state = STAGE_STATES[stage]
        if self.manager.state["state"] != invoking:
            raise WorkflowError(f"stage {stage} is not being invoked")
        if runtime_status == "BLOCKED_DEPENDENCY" or (stage == "review" and runtime_status == "SINGLE_AGENT_MODE"):
            self.manager.transition("BLOCKED_DEPENDENCY", f"{stage.upper()}_DEPENDENCY_BLOCKED")
            return {"status": "BLOCKED_DEPENDENCY", "stage": stage}
        payload = dict(receipt)
        payload["runtime_status"] = runtime_status
        path = self.manager.paths.sibling_skills_path(stage) if hasattr(self.manager.paths, "sibling_skills_path") else self.manager.paths.root / "sibling-skills" / stage / "stage-receipt.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(path, payload)
        updated = dict(self.manager.state)
        updated[f"{stage}_receipt_sha256"] = sha256_obj(payload)
        atomic_write_json(self.manager.paths.state, updated)
        self.manager._state = updated
        state = self.manager.transition(approval_state, f"{stage.upper()}_INVOCATION_COMPLETED", {"receipt_sha256": sha256_obj(payload), "runtime_status": runtime_status})
        return {"status": "READY", "stage": stage, "state": state["state"], "receipt_path": path.as_posix()}

    def approve_stage(self, stage: str, *, approval_path: Optional[Path | str] = None) -> Dict[str, Any]:
        """把已验证 stage 交给下一个阶段；不修改 native artifact。

        Advance an approved stage without mutating its native artifact.
        """

        if stage not in STAGE_STATES:
            raise WorkflowError(f"unknown stage: {stage}")
        expected = STAGE_STATES[stage][1]
        if self.manager.state["state"] != expected:
            raise WorkflowError(f"stage {stage} is not awaiting approval")
        if self.manager.state.get("entry_mode") == "MIDSTREAM_TAKEOVER" and approval_path is None:
            raise WorkflowError("hash-bound stage approval is required in MIDSTREAM_TAKEOVER")
        if approval_path is not None:
            expected_gate = {"idea": "IDEA", "experiment": "EXPERIMENT", "writing": "WRITING", "review": "REVIEW_ROUTE"}[stage]
            subject = self.manager.paths.root / "sibling-skills" / stage / "stage-receipt.json"
            approval = self.manager.consume_approval(approval_path, expected_gate=expected_gate, expected_subject_path=subject)
            if approval.get("gate") != expected_gate:
                raise WorkflowError(f"approval gate mismatch for {stage}")
        next_state = {"idea": "INVOKING_EXPERIMENT_SKILL", "experiment": "TASK_COMPILATION", "writing": "INVOKING_REVIEW_SKILL", "review": "COMPLETE"}[stage]
        return self.manager.transition(next_state, f"{stage.upper()}_APPROVED")

    def prepare_execution(self) -> Dict[str, Any]:
        """从已批准 task 进入执行就绪。 / Move an approved task to execution-ready."""

        if self.manager.state["state"] != "AWAITING_TASK_APPROVAL":
            raise WorkflowError("task approval is required")
        return self.manager.transition("IMPLEMENTING", "TASK_APPROVED")

    def mark_tested(self, *, passed: bool, debug: bool = False) -> Dict[str, Any]:
        """记录测试结果，debug 只允许回到实现。 / Record tests; debug may return to implementation."""

        if self.manager.state["state"] == "IMPLEMENTING":
            self.manager.transition("TESTING", "IMPLEMENTATION_COMPLETED")
        if self.manager.state["state"] != "TESTING":
            raise WorkflowError("testing state required")
        if passed:
            return self.manager.transition("EXECUTION_READY", "TESTS_PASSED")
        if debug:
            self.manager.transition("DEBUGGING", "TESTS_FAILED")
            return self.manager.transition("IMPLEMENTING", "DEBUG_PATCH_REQUESTED")
        return self.manager.transition("FAILED_RECOVERABLE", "TESTS_FAILED")

    def run_batch(
        self,
        environment: EnvironmentAdapter,
        environment_receipt: Mapping[str, Any],
        *,
        request: Mapping[str, Any],
        analysis: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """运行已验证 mock batch，再写只读 raw 和 analysis receipt。

        Run a verified mock batch, then write immutable raw and analysis receipts.
        """

        if self.manager.state["state"] != "EXECUTION_READY":
            raise WorkflowError("EXECUTION_READY is required")
        self.manager.transition("RUNNING_ENVIRONMENT", "BATCH_STARTED")
        try:
            result = environment.run_batch(self.manager.state["mode"], environment_receipt, request=request)
        except EnvironmentError as exc:
            self.manager.transition("BLOCKED_ENVIRONMENT", "BATCH_BLOCKED", {"reason": str(exc)})
            return {"status": "BLOCKED_ENVIRONMENT", "reason": str(exc)}
        self.manager.transition("ANALYZING", "BATCH_COMPLETED", {"result_sha256": sha256_obj(result)})
        raw_dir = self.manager.paths.experiments / "mock-batch" / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_path = raw_dir / "result.json"
        atomic_write_json(raw_path, result["result"])
        raw_guard = RawEvidenceGuard(raw_dir)
        raw_fingerprints = raw_guard.freeze([raw_path])
        analysis_value = dict(analysis or {"status": "PASS", "evidence": "mock batch completed"})
        analysis_status = str(analysis_value.get("status", "PASS"))
        analysis_path = self.manager.paths.experiments / "mock-batch" / "analysis.json"
        atomic_write_json(analysis_path, analysis_value)
        receipt = {
            "schema_version": "robotics-ar-analysis-receipt.v1",
            "status": "PASS",
            "analysis_status": analysis_status,
            "raw_paths": raw_fingerprints,
            "analysis_path": analysis_path.as_posix(),
            "analysis_sha256": file_sha256(analysis_path),
            "created_at": utc_now(),
        }
        receipt["receipt_sha256"] = sha256_obj(receipt)
        atomic_write_json(self.manager.paths.experiments / "mock-batch" / "analysis-receipt.json", receipt)
        self.manager.transition("AWAITING_BATCH_REVIEW", "ANALYSIS_COMPLETED", {"receipt_sha256": receipt["receipt_sha256"]})
        return {"status": "PASS", "result": result, "raw_path": raw_path.as_posix(), "analysis_receipt": receipt}

    def freeze_evidence(self, *, raw_paths: Iterable[Path | str], analysis_receipt: Mapping[str, Any]) -> Dict[str, Any]:
        """冻结 raw 与分析 receipt；冻结后才允许 Writing。 / Freeze raw and analysis before Writing."""

        if self.manager.state["state"] not in {"ANALYZING", "AWAITING_BATCH_REVIEW"}:
            raise WorkflowError("batch analysis must complete before evidence freeze")
        if self.manager.state["state"] == "ANALYZING":
            self.manager.transition("AWAITING_BATCH_REVIEW", "ANALYSIS_REVIEW_READY")
        guard = RawEvidenceGuard(self.manager.paths.experiments)
        hashes = guard.freeze(raw_paths)
        freeze = {"schema_version": "robotics-ar-evidence-freeze.v1", "status": "FROZEN", "raw_hashes": hashes, "analysis_receipt_sha256": sha256_obj(dict(analysis_receipt)), "created_at": utc_now()}
        freeze["freeze_sha256"] = sha256_obj(freeze)
        path = self.manager.paths.research / "evidence" / "evidence-freeze.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(path, freeze)
        self.manager.transition("EVIDENCE_FREEZE", "EVIDENCE_FROZEN", {"freeze_sha256": freeze["freeze_sha256"]})
        return freeze

    def approve_evidence(self, freeze_path: Path | str, approval_path: Path | str) -> Dict[str, Any]:
        """Consume an explicit evidence approval before Writing in takeover mode."""

        freeze = self.ensure_writing_allowed(freeze_path, allow_unapproved=True)
        approval = self.manager.consume_approval(approval_path)
        if approval.get("gate") != "EVIDENCE":
            raise WorkflowError("approval gate mismatch for evidence")
        updated = dict(self.manager.state)
        updated["evidence_approval_id"] = approval["approval_id"]
        updated["evidence_approved"] = True
        atomic_write_json(self.manager.paths.state, updated)
        self.manager._state = updated
        if self.manager.state["state"] == "EVIDENCE_FREEZE":
            self.manager.transition("AWAITING_EVIDENCE_APPROVAL", "EVIDENCE_APPROVED", {"approval_id": approval["approval_id"], "freeze_sha256": freeze["freeze_sha256"]})
        return {"status": "PASS", "approval": approval, "freeze": freeze}

    def ensure_writing_allowed(self, freeze_path: Path | str, *, allow_unapproved: bool = False) -> Dict[str, Any]:
        """只接受有效的冻结 evidence。 / Accept only a valid evidence freeze."""

        if self.manager.state["state"] not in {"EVIDENCE_FREEZE", "AWAITING_EVIDENCE_APPROVAL"}:
            raise WorkflowError("writing requires EVIDENCE_FREEZE")
        freeze = read_json(freeze_path)
        if freeze.get("status") != "FROZEN" or freeze.get("freeze_sha256") != sha256_obj({key: value for key, value in freeze.items() if key != "freeze_sha256"}):
            raise WorkflowError("evidence freeze receipt is invalid")
        if self.manager.state.get("entry_mode") == "MIDSTREAM_TAKEOVER" and not self.manager.state.get("evidence_approved") and not allow_unapproved:
            raise WorkflowError("evidence approval is required in MIDSTREAM_TAKEOVER")
        return freeze

    def propose_review_route(self, route: str, *, reason: str) -> Dict[str, Any]:
        """生成有限 route proposal，不自动补实验。 / Create a bounded route proposal without auto-running experiments."""

        if route not in {"IDEA", "EXPERIMENT", "WRITING", "COMPLETE"}:
            raise WorkflowError("review route must be IDEA, EXPERIMENT, WRITING, or COMPLETE")
        if self.manager.state["state"] != "AWAITING_REVIEW_ROUTE":
            raise WorkflowError("review route is not pending")
        proposal = {"schema_version": "robotics-ar-review-route.v1", "route": route, "reason": reason, "auto_execute": False, "created_at": utc_now()}
        proposal["proposal_sha256"] = sha256_obj(proposal)
        path = self.manager.paths.research / "decisions" / "review-route.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(path, proposal)
        return proposal

    def apply_review_route(self, route: str, *, approval_path: Optional[Path | str] = None) -> Dict[str, Any]:
        """Apply one user-approved route; proposals never auto-run experiments."""

        if route not in {"IDEA", "EXPERIMENT", "WRITING", "COMPLETE"}:
            raise WorkflowError("review route must be IDEA, EXPERIMENT, WRITING, or COMPLETE")
        if self.manager.state["state"] != "AWAITING_REVIEW_ROUTE":
            raise WorkflowError("review route is not pending")
        if approval_path is not None:
            approval = self.manager.consume_approval(approval_path)
            if approval.get("gate") != "REVIEW_ROUTE":
                raise WorkflowError("approval gate mismatch for review route")
        elif self.manager.state.get("entry_mode") == "MIDSTREAM_TAKEOVER":
            raise WorkflowError("hash-bound review route approval is required in MIDSTREAM_TAKEOVER")
        next_state = {"IDEA": "INVOKING_IDEA_SKILL", "EXPERIMENT": "INVOKING_EXPERIMENT_SKILL", "WRITING": "INVOKING_WRITING_SKILL", "COMPLETE": "COMPLETE"}[route]
        return self.manager.transition(next_state, "REVIEW_ROUTE_APPLIED", {"route": route})

    def takeover_stage_context(self) -> Dict[str, Any]:
        """Build the neutral context passed to an existing sibling Skill."""

        state = self.manager.state
        return {"entry_mode": "MIDSTREAM_TAKEOVER", "project_core_ref": state.get("project_core_path"), "project_core_sha256": state.get("project_core_sha256"), "history_ledger_ref": (self.manager.paths.takeover_history / "experiment-ledger.jsonl").as_posix(), "baseline_ref": state.get("baseline_receipt_path"), "current_bottleneck": state.get("current_bottleneck", ""), "allowed_search_space": state.get("allowed_search_space", {}), "trial_budget": state.get("trial_budget", {})}
