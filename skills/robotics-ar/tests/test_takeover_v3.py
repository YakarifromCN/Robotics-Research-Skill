"""Deterministic Robot-AR v3 takeover tests."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from robotics_ar_core.atomic_io import atomic_write_json  # noqa: E402
from robotics_ar_core.baseline import compile_baseline_spec, reproduce_baseline  # noqa: E402
from robotics_ar_core.batch_controller import BatchController, compile_batch  # noqa: E402
from robotics_ar_core.best_known import BestKnownState, build_candidate  # noqa: E402
from robotics_ar_core.canonical import sha256_obj  # noqa: E402
from robotics_ar_core.environment import EnvironmentAdapter  # noqa: E402
from robotics_ar_core.history_reconstruction import DoNotRepeatRegistry, reconstruct_history  # noqa: E402
from robotics_ar_core.project_audit import audit_project  # noqa: E402
from robotics_ar_core.project_core import mark_project_core_approved, save_project_core  # noqa: E402
from robotics_ar_core.receipts import file_sha256  # noqa: E402
from robotics_ar_core.session import SessionManager  # noqa: E402
from robotics_ar_core.structured import write_structured  # noqa: E402
from robotics_ar_core.takeover import TakeoverManager  # noqa: E402
from robotics_ar_core.trial_contract import TrialContractManager, compile_trial_contract  # noqa: E402
from robotics_ar_core.trial_loop import TrialLoop  # noqa: E402
from robotics_ar_core.trial_queue import TrialQueue, build_proposal  # noqa: E402
from robotics_ar_core.user_correction import compile_correction, confirm_and_resume  # noqa: E402


MOCK = Path(__file__).resolve().parents[1] / "assets" / "mock-environment" / "adapter.py"


def make_manifest(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MOCK, root / "adapter.py")
    manifest = {
        "schema_version": "robotics-ar-environment.v1",
        "id": "takeover-v3-mock",
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


class TakeoverV3Tests(unittest.TestCase):
    def _start(self, root: Path):
        project = root / "project"
        project.mkdir()
        (project / "README.md").write_text("midstream project\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=project, check=True)
        subprocess.run(["git", "add", "README.md"], cwd=project, check=True)
        subprocess.run(["git", "-c", "user.email=robotics-ar@test", "-c", "user.name=Robot-AR", "commit", "-qm", "project-init"], cwd=project, check=True)
        environment_root = root / "environment"
        manifest_path = make_manifest(environment_root)
        manager = SessionManager(project)
        manager.initialize(mode="EXECUTION_ENABLED", interaction_language="en", entry_mode="MIDSTREAM_TAKEOVER", session_id="RAS-V3-TEST")
        takeover = TakeoverManager(manager)
        takeover.initialize()
        takeover.record_intake({"project_id": "demo", "project_path": project.as_posix(), "project_core": {}, "current_goal": "improve feasibility", "current_bottleneck": "solver instability", "environment": {"manifest": manifest_path.as_posix()}, "allowed_directions": ["initialization"], "forbidden_changes": ["objective"], "budget": {"max_trials": 2}, "pause_conditions": ["core-change-required"], "user_asserted": [], "repository_observed": [], "agent_inferred": [], "unresolved": []})
        core = takeover.compile_core({"project_id": "demo", "research_problem": "test problem", "core_method": "test method", "frozen_invariants": ["method definition"], "modifiable_components": ["initialization"], "forbidden_pivots": ["objective"], "current_bottleneck": "solver instability", "current_batch_goal": "improve feasibility", "success_criteria": {"primary": "feasibility"}})
        audit = audit_project(project)
        takeover.record_audit(audit["receipt"])
        history = reconstruct_history(project, sources=[])
        takeover.mark_history_reconstructed(receipt=history["receipt"])
        if manager.state["state"] == "TAKEOVER_IDEA_RECONCILIATION":
            takeover.complete_idea_reconciliation({"resolution": "synthetic fixture explicitly reconciled"})
        environment = EnvironmentAdapter.from_file(manifest_path)
        environment_receipt = environment.verify_online()
        takeover.mark_environment(environment_receipt)
        takeover.begin_baseline()
        baseline_spec = compile_baseline_spec({"baseline_id": "baseline-current", "expected_metrics": {}, "repetitions": 1}, project_core=core, environment_receipt=environment_receipt)
        baseline = reproduce_baseline(baseline_spec, environment, output_dir=manager.paths.takeover_baseline)
        takeover.baseline_result(baseline)
        return manager, takeover, core, environment_receipt, baseline

    def test_full_takeover_trial_pause_and_resume(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager, takeover, core, environment_receipt, baseline = self._start(root)
            core_path = manager.paths.takeover / "project-core.yaml"
            approval = manager.approve_subject("TAKEOVER_CORE", core_path)
            manager.consume_approval(manager.paths.approvals / f"{approval['approval_id']}.json")
            approved_core = mark_project_core_approved(core, approval_id=approval["approval_id"])
            save_project_core(core_path, approved_core)
            manager.record_event("PROJECT_CORE_APPROVED", {"approval_id": approval["approval_id"]})
            manager.transition("TRIAL_CONTRACT_COMPILATION", "PROJECT_CORE_APPROVED")
            contract = compile_trial_contract({"contract_id": "batch-001", "project_core_sha256": approved_core["project_core_sha256"], "baseline_receipt_sha256": baseline["receipt_sha256"], "environment_receipt_sha256": environment_receipt["receipt_sha256"], "current_bottleneck": "solver instability", "primary_hypothesis": {"statement": "initialization improves feasibility"}, "primary_objective": {"metric": "score", "direction": "maximize", "baseline": 0.1}, "allowed_search_space": {"tier_0_parameters": ["initialization"]}, "project_core_approved": True, "baseline_approved": True, "baseline_reproduction_status": "REPRODUCED", "budget": {"max_trials": 2, "max_parallel_jobs": 1}, "stop_conditions": ["budget"], "escalation_conditions": ["core-change"]})
            contract_path = manager.paths.takeover_contracts / "batch-001.yaml"
            write_structured(contract_path, contract)
            manager.transition("AWAITING_TRIAL_CONTRACT_APPROVAL", "TRIAL_CONTRACT_COMPILED")
            contract_approval = manager.approve_subject("TRIAL_CONTRACT", contract_path)
            contract = TrialContractManager(manager.paths.takeover_contracts, manager.paths.approvals).approve(contract_path, manager.paths.approvals / f"{contract_approval['approval_id']}.json")
            manager.transition("TRIAL_BATCH_READY", "TRIAL_CONTRACT_APPROVED")
            updated = dict(manager.state)
            updated.update({"contract_path": contract_path.as_posix(), "contract_sha256": contract["contract_sha256"], "project_core_approved": True, "baseline_approved": True})
            atomic_write_json(manager.paths.state, updated)
            manager._state = updated
            batch = compile_batch({"batch_id": "batch-001", "max_trials": 1, "max_wall_time_minutes": 5, "max_parallel_jobs": 1, "allowed_tiers": [0]}, contract_sha256=contract["contract_sha256"])
            controller = BatchController(manager.paths.experiments / "batch-001", mode="EXECUTION_ENABLED", manager=manager)
            self.assertEqual(controller.start(batch, contract=contract, environment_receipt=environment_receipt)["status"], "RUNNING")
            best_known = BestKnownState(manager.paths.best_known)
            proposal = build_proposal({"trial_id": "trial-0001", "parent_contract": contract["contract_sha256"], "hypothesis": {"statement": "initialization improves feasibility", "expected_observation": "score increases", "falsification_condition": "score does not increase"}, "uncertainty_target": "score", "change": {"tier": 0, "components": ["initialization"], "minimal_patch": True}, "experiment": {}, "metrics": {}, "resource_estimate": {}, "rollback": {}})
            TrialQueue(manager.paths.trial_queue).add(proposal)
            def receipt(value: dict) -> dict:
                value["receipt_sha256"] = sha256_obj(value)
                return value

            def callbacks(_proposal: dict) -> dict:
                code = receipt({"status": "PASS", "trial_id": proposal["trial_id"], "proposal_sha256": proposal["proposal_sha256"], "contract_sha256": contract["contract_sha256"], "code_version": "test", "configuration_sha256": "c" * 64})
                test = receipt({"status": "PASS", "trial_id": proposal["trial_id"], "proposal_sha256": proposal["proposal_sha256"], "contract_sha256": contract["contract_sha256"], "code_receipt_sha256": code["receipt_sha256"], "test_version": "t"})
                return code, test

            def code_callback(_proposal: dict) -> dict:
                return callbacks(_proposal)[0]

            def test_callback(_proposal: dict, code: dict) -> dict:
                return receipt({"status": "PASS", "trial_id": proposal["trial_id"], "proposal_sha256": proposal["proposal_sha256"], "contract_sha256": contract["contract_sha256"], "code_receipt_sha256": code["receipt_sha256"], "test_version": "t"})

            def run_callback(_proposal: dict, code: dict, test: dict) -> dict:
                return receipt({"status": "PASS", "trial_id": proposal["trial_id"], "proposal_sha256": proposal["proposal_sha256"], "contract_sha256": contract["contract_sha256"], "code_receipt_sha256": code["receipt_sha256"], "test_receipt_sha256": test["receipt_sha256"], "code_version": "test", "configuration_sha256": "c" * 64, "environment_receipt_sha256": environment_receipt["receipt_sha256"], "environment_fingerprint": environment_receipt["fingerprint"], "metric_versions": {"score": "v1"}, "raw_evidence": {"sha256": "a" * 64}})

            def analysis_callback(_proposal: dict, run: dict) -> dict:
                return receipt({"status": "PASS", "trial_id": proposal["trial_id"], "proposal_sha256": proposal["proposal_sha256"], "contract_sha256": contract["contract_sha256"], "run_receipt_sha256": run["receipt_sha256"], "code_version": "test", "configuration_sha256": "c" * 64, "environment_receipt_sha256": environment_receipt["receipt_sha256"], "environment_fingerprint": environment_receipt["fingerprint"], "metric_versions": {"score": "v1"}, "valid": True, "reproducible": True, "improved": True})

            decision = TrialLoop(manager.paths.experiments, manager=manager, best_known=best_known).run(proposal, contract, environment_receipt_sha256=environment_receipt["receipt_sha256"], environment_fingerprint=environment_receipt["fingerprint"], callbacks={"code": code_callback, "test": test_callback, "run": run_callback, "analysis": analysis_callback, "candidate": lambda _proposal, _run, _analysis: build_candidate(trial_id="trial-0001", code_version="test", configuration={"initialization": "default"}, environment_fingerprint=environment_receipt["fingerprint"], baseline_relationship="matched", primary_metrics={"score": 1.0}, raw_evidence={"sha256": "a" * 64}, validation_status="REPRODUCED", reproduction_command=["mock-run"])})
            self.assertEqual(decision["decision"], "KEEP")
            self.assertEqual(best_known.current()["current_primary_best"]["trial_id"], "trial-0001")
            self.assertFalse(manager.paths.root_report.exists())
            self.assertFalse(manager.paths.root_handoff.exists())
            self.assertEqual(manager.pause("user pause")["state"], "PAUSED")
            task = compile_correction(manager, "keep the current method and change only initialization", allowed_changes=["initialization"], contract_path=contract_path)
            self.assertTrue((manager.paths.tasks / "task.md").exists())
            task_approval = manager.approve_subject("TASK", task["task_path"])
            contract_approval = manager.approve_subject("TRIAL_CONTRACT", task["contract_path"])
            subprocess.run(["git", "add", "-A"], cwd=manager.paths.project_root, check=True)
            subprocess.run(["git", "-c", "user.email=robotics-ar@test", "-c", "user.name=Robot-AR", "commit", "-qm", "correction-checkpoint"], cwd=manager.paths.project_root, check=True)
            resumed = confirm_and_resume(manager, task_approval_path=manager.paths.approvals / f"{task_approval['approval_id']}.json", contract_approval_path=manager.paths.approvals / f"{contract_approval['approval_id']}.json")
            self.assertEqual(resumed["state"]["state"], "BATCH_CHECKPOINT")

    def test_do_not_repeat_and_contract_drift_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = DoNotRepeatRegistry(root / "do-not-repeat.yaml")
            proposal = {"hypothesis": {"statement": "same"}, "change": {"tier": 0, "components": ["x"]}, "experiment": {}, "metrics": {}, "resource_estimate": {}, "code": {}, "configuration": {}, "environment": {}, "execution": {}}
            registry.add(proposal, reason="user rejected", category="USER_REJECTED")
            self.assertFalse(registry.can_retry(proposal))
            proposal["change"]["material_difference"] = {"environment": "new calibration"}
            self.assertTrue(registry.can_retry(proposal, justification="repaired calibration drift and changed the environment"))


if __name__ == "__main__":
    unittest.main()
