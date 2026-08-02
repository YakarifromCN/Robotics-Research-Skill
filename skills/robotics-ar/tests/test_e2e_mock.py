"""运行 Idea→Evidence→Writing→Review 的 mock E2E。

Run the Idea-to-Evidence-to-Writing-to-Review mock E2E.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from robotics_ar_core.environment import EnvironmentAdapter  # noqa: E402
from robotics_ar_core.receipts import file_sha256  # noqa: E402
from robotics_ar_core.session import SessionManager  # noqa: E402
from robotics_ar_core.workflow import SupervisedWorkflow, WorkflowError  # noqa: E402


MOCK = Path(__file__).resolve().parents[1] / "assets" / "mock-environment" / "adapter.py"


def make_manifest(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MOCK, root / "adapter.py")
    manifest = {
        "schema_version": "robotics-ar-environment.v1",
        "id": "e2e-mock",
        "kind": "simulation",
        "root": root.as_posix(),
        "adapter": {"path": "adapter.py", "sha256": file_sha256(root / "adapter.py")},
        "commands": {name: ["python3", "adapter.py", command] for name, command in (("capabilities", "capabilities"), ("health_check", "health-check"), ("minimal_rollout", "minimal-rollout"), ("collect_results", "collect-results"), ("stop", "stop"))},
        "io": {"request_dir": "requests", "result_dir": "results", "artifact_dir": "artifacts"},
        "limits": {"timeout_s": 10, "max_parallel_runs": 1, "network": "denied", "executables": ["python3"]},
    }
    path = root / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


class MockE2ETests(unittest.TestCase):
    def test_successful_batch_freeze_and_writing_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = SessionManager(root / "project")
            manager.initialize(mode="EXECUTION_ENABLED", interaction_language="zh", session_id="RAS-E2E")
            flow = SupervisedWorkflow(manager)
            flow.invoke_stage("idea")
            flow.complete_stage("idea", receipt={"schema_version": "robotics-ar-stage-receipt.v1", "stage": "idea"})
            flow.approve_stage("idea")
            flow.complete_stage("experiment", receipt={"schema_version": "robotics-ar-stage-receipt.v1", "stage": "experiment"})
            flow.approve_stage("experiment")
            task = manager.compile_task("run one mock batch", allowed_paths=["src"], forbidden_paths=["raw"], stop_conditions=["budget"])
            approval = manager.approve_subject("TASK", task["task_path"])
            manager.consume_approval(manager.paths.approvals / f"{approval['approval_id']}.json")
            flow.prepare_execution()
            flow.mark_tested(passed=True)
            environment = EnvironmentAdapter.from_file(make_manifest(root / "environment"))
            receipt = environment.verify_online()
            result = flow.run_batch(environment, receipt, request={"batch_id": "batch-1"})
            self.assertEqual(result["status"], "PASS")
            freeze = flow.freeze_evidence(raw_paths=[result["raw_path"]], analysis_receipt=result["analysis_receipt"])
            self.assertEqual(freeze["status"], "FROZEN")
            flow.invoke_stage("writing")
            flow.complete_stage("writing", receipt={"schema_version": "robotics-ar-stage-receipt.v1", "stage": "writing"})
            self.assertEqual(manager.state["state"], "AWAITING_WRITING_APPROVAL")

    def test_debug_loop_reaches_execution_ready_after_one_patch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager = SessionManager(directory)
            manager.initialize(mode="EXECUTION_ENABLED", interaction_language="zh", session_id="RAS-DEBUG")
            manager.compile_task("debug once", allowed_paths=["src"], forbidden_paths=["raw"], stop_conditions=["budget"])
            manager.transition("IMPLEMENTING", "TASK_APPROVED")
            manager.transition("TESTING", "IMPLEMENTED")
            flow = SupervisedWorkflow(manager)
            flow.mark_tested(passed=False, debug=True)
            self.assertEqual(manager.state["state"], "IMPLEMENTING")
            self.assertEqual(flow.mark_tested(passed=True)["state"], "EXECUTION_READY")

    def test_negative_result_remains_first_class_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = SessionManager(root / "project")
            manager.initialize(mode="EXECUTION_ENABLED", interaction_language="zh", session_id="RAS-NEGATIVE")
            manager.compile_task("record a negative mock batch", allowed_paths=["src"], forbidden_paths=["raw"], stop_conditions=["budget"])
            manager.transition("IMPLEMENTING", "TASK_APPROVED")
            manager.transition("TESTING", "IMPLEMENTED")
            flow = SupervisedWorkflow(manager)
            flow.mark_tested(passed=True)
            environment = EnvironmentAdapter.from_file(make_manifest(root / "environment"))
            receipt = environment.verify_online()
            result = flow.run_batch(environment, receipt, request={"batch_id": "negative-1"}, analysis={"status": "NOT_SUPPORTED", "evidence": "mock contrast did not clear the frozen threshold"})
            self.assertEqual(result["analysis_receipt"]["analysis_status"], "NOT_SUPPORTED")
            freeze = flow.freeze_evidence(raw_paths=[result["raw_path"]], analysis_receipt=result["analysis_receipt"])
            self.assertEqual(freeze["status"], "FROZEN")

    def test_planning_only_and_fingerprint_block(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = SessionManager(root / "project")
            manager.initialize(mode="PLANNING_ONLY", interaction_language="en", session_id="RAS-PLAN")
            manager.compile_task("planning task", allowed_paths=["src"], forbidden_paths=["raw"], stop_conditions=["budget"])
            manager.transition("IMPLEMENTING", "TASK_APPROVED_FOR_TEST")
            manager.transition("TESTING", "IMPLEMENTATION_COMPLETED")
            manager.transition("EXECUTION_READY", "TESTS_PASSED")
            flow = SupervisedWorkflow(manager)
            environment = EnvironmentAdapter.from_file(make_manifest(root / "environment"))
            receipt = environment.verify_online()
            blocked = flow.run_batch(environment, receipt, request={"batch_id": "batch-1"})
            self.assertEqual(blocked["status"], "BLOCKED_ENVIRONMENT")

    def test_review_route_is_proposal_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager = SessionManager(directory)
            manager.initialize(mode="PLANNING_ONLY", interaction_language="zh", session_id="RAS-ROUTE")
            manager.transition("INVOKING_REVIEW_SKILL", "REVIEW_STARTED")
            manager.transition("AWAITING_REVIEW_ROUTE", "REVIEW_READY")
            proposal = SupervisedWorkflow(manager).propose_review_route("EXPERIMENT", reason="missing contrast")
            self.assertFalse(proposal["auto_execute"])
            self.assertTrue((manager.paths.research / "decisions" / "review-route.json").exists())

    def test_review_without_fresh_runtime_is_blocked_or_manual_import(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager = SessionManager(directory)
            manager.initialize(mode="PLANNING_ONLY", interaction_language="zh", session_id="RAS-REVIEW")
            for state, event in (("TASK_COMPILATION", "TASK_READY"), ("AWAITING_TASK_APPROVAL", "TASK_COMPILED"), ("IMPLEMENTING", "TASK_APPROVED"), ("TESTING", "IMPLEMENTED"), ("EXECUTION_READY", "TESTS_PASSED"), ("RUNNING_ENVIRONMENT", "BATCH_STARTED"), ("ANALYZING", "BATCH_DONE"), ("AWAITING_BATCH_REVIEW", "ANALYSIS_DONE"), ("EVIDENCE_FREEZE", "EVIDENCE_READY")):
                manager.transition(state, event)
            flow = SupervisedWorkflow(manager)
            flow.invoke_stage("review")
            blocked = flow.complete_stage("review", receipt={"schema_version": "robotics-ar-stage-receipt.v1"})
            self.assertEqual(blocked["status"], "BLOCKED_DEPENDENCY")
        with tempfile.TemporaryDirectory() as directory:
            manager = SessionManager(directory)
            manager.initialize(mode="PLANNING_ONLY", interaction_language="zh", session_id="RAS-REVIEW2")
            for state, event in (("TASK_COMPILATION", "TASK_READY"), ("AWAITING_TASK_APPROVAL", "TASK_COMPILED"), ("IMPLEMENTING", "TASK_APPROVED"), ("TESTING", "IMPLEMENTED"), ("EXECUTION_READY", "TESTS_PASSED"), ("RUNNING_ENVIRONMENT", "BATCH_STARTED"), ("ANALYZING", "BATCH_DONE"), ("AWAITING_BATCH_REVIEW", "ANALYSIS_DONE"), ("EVIDENCE_FREEZE", "EVIDENCE_READY")):
                manager.transition(state, event)
            flow = SupervisedWorkflow(manager)
            flow.invoke_stage("review")
            ready = flow.complete_stage("review", receipt={"schema_version": "robotics-ar-stage-receipt.v1"}, runtime_status="MANUAL_REVIEW_IMPORT")
            self.assertEqual(ready["status"], "READY")


if __name__ == "__main__":
    unittest.main()
