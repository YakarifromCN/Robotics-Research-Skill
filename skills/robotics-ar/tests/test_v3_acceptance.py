"""Acceptance evidence for the Robot-AR v3 takeover boundaries."""

from __future__ import annotations

import json
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from robotics_ar_core.atomic_io import atomic_write_json  # noqa: E402
from robotics_ar_core.agent_protocol import build_dynamic_expert_profiles  # noqa: E402
from robotics_ar_core.baseline import BaselineError, assert_baseline_usable, build_baseline_receipt  # noqa: E402
from robotics_ar_core.blackboard import Blackboard, BlackboardError  # noqa: E402
from robotics_ar_core.canonical import sha256_obj  # noqa: E402
from robotics_ar_core.environment import EnvironmentAdapter  # noqa: E402
from robotics_ar_core.gates import ApprovalManager, GateError  # noqa: E402
from robotics_ar_core.project_core import compile_project_core, save_project_core  # noqa: E402
from robotics_ar_core.reporting_v3 import write_current_handoff, write_current_report  # noqa: E402
from robotics_ar_core.schema_validation import SchemaValidationError, validate_artifact  # noqa: E402
from robotics_ar_core.session import SessionManager  # noqa: E402
from robotics_ar_core.structured import write_structured  # noqa: E402
from robotics_ar_core.trial_contract import TrialContractError, TrialContractManager, compile_trial_contract  # noqa: E402
from robotics_ar_core.trial_loop import TrialDecisionEngine  # noqa: E402
from robotics_ar_core.trial_queue import build_proposal  # noqa: E402
from robotics_ar import CLIError, command_trial_analyze, command_trial_run  # noqa: E402


HASH = "a" * 64
CLI = Path(__file__).resolve().parents[1] / "scripts" / "robotics_ar.py"
MOCK_ADAPTER = Path(__file__).resolve().parents[1] / "assets" / "mock-environment" / "adapter.py"


def _manifest(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MOCK_ADAPTER, root / "adapter.py")
    commands = {
        name: ["python3", "adapter.py", command]
        for name, command in (
            ("capabilities", "capabilities"),
            ("health_check", "health-check"),
            ("minimal_rollout", "minimal-rollout"),
            ("collect_results", "collect-results"),
            ("run_batch", "run-batch"),
            ("stop", "stop"),
        )
    }
    value = {
        "schema_version": "robotics-ar-environment.v1",
        "id": "v3-acceptance-mock",
        "kind": "simulation",
        "root": root.as_posix(),
        "adapter": {"path": "adapter.py", "sha256": ""},
        "commands": commands,
        "io": {"request_dir": "requests", "result_dir": "results", "artifact_dir": "artifacts"},
        "limits": {"timeout_s": 10, "max_parallel_runs": 1, "network": "denied", "executables": ["python3"]},
    }
    # The environment validator hashes the actual adapter bytes, not a JSON
    # object containing them.  Keep the helper dependency-free and explicit.
    import hashlib

    value["adapter"]["sha256"] = hashlib.sha256((root / "adapter.py").read_bytes()).hexdigest()
    path = root / "manifest.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


class V3AcceptanceTests(unittest.TestCase):
    def test_runtime_schema_rejects_nonfinite_artifacts(self) -> None:
        core = compile_project_core(
            {
                "project_id": "schema-test",
                "research_problem": "problem",
                "core_method": "method",
                "frozen_invariants": ["method"],
                "modifiable_components": ["init"],
                "forbidden_pivots": ["claim"],
                "current_bottleneck": "bottleneck",
                "current_batch_goal": "goal",
                "success_criteria": {"score": 1.0},
            }
        )
        core["success_criteria"]["score"] = float("nan")
        with self.assertRaises(SchemaValidationError):
            validate_artifact("robotics-ar-project-core.v1", core)

    def test_wrong_gate_or_subject_does_not_consume_approval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subject = root / "subject.json"
            other = root / "other.json"
            subject.write_text("subject\n", encoding="utf-8")
            other.write_text("other\n", encoding="utf-8")
            approvals = ApprovalManager(root / "approvals")
            created = approvals.create("TRIAL_CONTRACT", subject)
            path = root / "approvals" / f"{created['approval_id']}.json"
            with self.assertRaises(GateError):
                approvals.consume(path, expected_gate="BASELINE")
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["status"], "unused")
            with self.assertRaises(GateError):
                approvals.consume(path, expected_gate="TRIAL_CONTRACT", expected_subject_path=other)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["status"], "unused")
            consumed = approvals.consume(path, expected_gate="TRIAL_CONTRACT", expected_subject_path=subject)
            self.assertEqual(consumed["status"], "consumed")

    def test_dynamic_experts_and_blackboard_are_bounded(self) -> None:
        profiles = build_dynamic_expert_profiles({"expert_roles": ["contact", "control", "evaluation"]}, count=3)
        self.assertEqual([item["focus"] for item in profiles], ["contact", "control", "evaluation"])
        with tempfile.TemporaryDirectory() as directory:
            board = Blackboard(Path(directory) / "blackboard")
            with self.assertRaises(BlackboardError):
                board.update("current-objective", {"value": "x"}, actor="Code Agent")
            receipt = {"receipt_sha256": HASH, "status": "PASS"}
            state = board.update_from_receipt("analysis-status", receipt)
            self.assertEqual(state["values"]["analysis-status"]["receipt_ref"], HASH)

    def test_baseline_variance_and_weak_reproduction_need_explicit_approval(self) -> None:
        spec = {"baseline_id": "baseline", "baseline_spec_sha256": HASH, "environment": {"fingerprint": HASH}}
        variance = build_baseline_receipt(spec, "REPRODUCED_WITH_VARIANCE", user_approved_variance=False)
        with self.assertRaises(BaselineError):
            assert_baseline_usable(variance, allow_variance=True)
        with self.assertRaises(TrialContractError):
            compile_trial_contract(
                {
                    "contract_id": "batch-variance",
                    "project_core_sha256": HASH,
                    "baseline_receipt_sha256": variance["receipt_sha256"],
                    "environment_receipt_sha256": HASH,
                    "current_bottleneck": "bottleneck",
                    "primary_hypothesis": {"statement": "h"},
                    "primary_objective": {"metric": "score", "direction": "maximize"},
                    "allowed_search_space": {"tier_0_parameters": ["init"]},
                    "project_core_approved": True,
                    "baseline_approved": True,
                    "baseline_reproduction_status": "REPRODUCED_WITH_VARIANCE",
                    "baseline_user_approved_variance": False,
                    "budget": {"max_trials": 1, "max_parallel_jobs": 1},
                }
            )
        approved = dict(variance)
        approved["user_approved_variance"] = True
        approved.pop("receipt_sha256", None)
        approved["receipt_sha256"] = sha256_obj(approved)
        self.assertIsNone(assert_baseline_usable(approved, allow_variance=True))

    def test_report_and_handoff_hydrate_takeover_context_from_disk(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            manager = SessionManager(project)
            manager.initialize(mode="PLANNING_ONLY", interaction_language="en", entry_mode="MIDSTREAM_TAKEOVER", session_id="RAS-REPORT")
            core = compile_project_core(
                {
                    "project_id": "report-project",
                    "research_problem": "problem",
                    "core_method": "method",
                    "frozen_invariants": ["method"],
                    "modifiable_components": ["initialization"],
                    "forbidden_pivots": ["objective"],
                    "current_bottleneck": "solver instability",
                    "current_batch_goal": "improve feasibility",
                    "success_criteria": {"primary": "feasibility"},
                }
            )
            save_project_core(manager.paths.takeover / "project-core.yaml", core)
            contract = compile_trial_contract(
                {
                    "contract_id": "batch-report",
                    "project_core_sha256": core["project_core_sha256"],
                    "baseline_receipt_sha256": HASH,
                    "environment_receipt_sha256": HASH,
                    "current_bottleneck": "solver instability",
                    "primary_hypothesis": {"statement": "initialization helps"},
                    "primary_objective": {"metric": "feasibility", "direction": "maximize"},
                    "allowed_search_space": {"tier_0_parameters": ["initialization"]},
                    "budget": {"max_trials": 2, "max_parallel_jobs": 1},
                }
            )
            write_structured(manager.paths.takeover_contracts / "batch-001.yaml", contract)
            baseline = build_baseline_receipt(spec={"baseline_id": "baseline", "baseline_spec_sha256": HASH, "environment": {"fingerprint": HASH}}, status="REPRODUCED")
            write_structured(manager.paths.takeover_baseline / "baseline-receipt.json", baseline)
            write_structured(manager.paths.best_known, {"schema_version": "robotics-ar-best-known-state.v1", "baseline_trial": None, "current_primary_best": None, "current_stable_best": None, "pareto_candidates": [], "invalidated_trials": [], "latest_trial": None, "metric_versions": {}})
            task_path = manager.paths.tasks / "task.md"
            task_path.write_text("# Active Task\n", encoding="utf-8")
            updated = dict(manager.state)
            updated.update({"task_path": task_path.as_posix(), "task_sha256": HASH})
            atomic_write_json(manager.paths.state, updated)
            manager._state = updated

            report = write_current_report(manager, reason="acceptance checkpoint")
            handoff = write_current_handoff(manager, reason="acceptance checkpoint")
            report_text = report.read_text(encoding="utf-8")
            handoff_text = handoff.read_text(encoding="utf-8")
            self.assertIn("improve feasibility", report_text)
            self.assertIn("batch-report", report_text)
            self.assertIn("REPRODUCED", report_text)
            self.assertIn("batch-report", handoff_text)
            self.assertIn("task.md", handoff_text)
            self.assertIn("Exact Resume Command", handoff_text)

    def test_cli_takeover_environment_validation_binds_receipt_and_advances_state(self) -> None:
        def run_cli(project: Path, *args: str) -> dict:
            result = subprocess.run(
                [sys.executable, str(CLI), *args, "--project-root", str(project)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            return json.loads(result.stdout)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            manifest = _manifest(root / "environment")
            run_cli(project, "init", "--entry-mode", "MIDSTREAM_TAKEOVER", "--mode", "EXECUTION_ENABLED")
            run_cli(project, "takeover-init")
            intake = {
                "project_id": "cli-project",
                "project_path": project.as_posix(),
                "project_core": {},
                "current_goal": "improve feasibility",
                "current_bottleneck": "solver instability",
                "environment": {"manifest": manifest.as_posix()},
                "allowed_directions": ["initialization"],
                "forbidden_changes": ["objective"],
                "budget": {"max_trials": 1},
                "pause_conditions": ["core-change-required"],
                "user_asserted": [],
                "repository_observed": [],
                "agent_inferred": [],
                "unresolved": [],
            }
            intake_path = root / "intake.json"
            intake_path.write_text(json.dumps(intake), encoding="utf-8")
            run_cli(project, "takeover-record-intake", "--input", str(intake_path))
            run_cli(project, "takeover-audit")
            run_cli(project, "takeover-import-history")
            reconciliation = root / "reconciliation.json"
            reconciliation.write_text(json.dumps({"resolution": "synthetic fixture explicitly reconciled"}), encoding="utf-8")
            run_cli(project, "takeover-reconcile", "--input", str(reconciliation))
            validated = run_cli(project, "validate-environment", "--environment-manifest", str(manifest))
            self.assertEqual(validated["state"]["state"], "TAKEOVER_BASELINE_SELECTION")
            self.assertEqual(validated["receipt"]["status"], "ONLINE_VERIFIED")
            self.assertTrue(Path(validated["receipt_path"]).is_file())

    def test_cli_trial_run_rejects_missing_receipt_and_fingerprint_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            manifest = _manifest(root / "environment")
            manager = SessionManager(project)
            manager.initialize(mode="EXECUTION_ENABLED", interaction_language="en", entry_mode="MIDSTREAM_TAKEOVER", session_id="RAS-TRIAL-GATE")
            contract_path = manager.paths.takeover_contracts / "batch-001.yaml"
            contract_path.write_text("{}\n", encoding="utf-8")
            proposal_path = root / "proposal.json"
            proposal = {"trial_id": "trial-0001", "parent_contract": "contract-hash"}
            proposal_path.write_text(json.dumps(proposal), encoding="utf-8")
            state = dict(manager.state)
            state.update({"state": "TRIAL_BATCH_READY", "contract_path": contract_path.as_posix(), "contract_sha256": "contract-hash", "environment_receipt_path": (root / "missing-receipt.json").as_posix()})
            atomic_write_json(manager.paths.state, state)
            manager._state = state
            args = argparse.Namespace(
                project_root=str(project),
                dry_run=False,
                trial_id="trial-0001",
                proposal=str(proposal_path),
                receipt=None,
                environment_manifest=str(manifest),
            )
            approved_contract = {"contract_id": "batch-001", "contract_sha256": "contract-hash", "environment_receipt_sha256": HASH}
            with mock.patch("robotics_ar._manager", return_value=manager), mock.patch.object(TrialContractManager, "assert_approved", return_value=approved_contract):
                with self.assertRaises(CLIError):
                    command_trial_run(args)

            receipt = EnvironmentAdapter.from_file(manifest).verify_online()
            receipt["fingerprint"] = "b" * 64
            receipt.pop("receipt_sha256", None)
            receipt["receipt_sha256"] = sha256_obj(receipt)
            receipt_path = root / "drifted-receipt.json"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            args.receipt = str(receipt_path)
            approved_contract = {"contract_id": "batch-001", "contract_sha256": "contract-hash", "environment_receipt_sha256": receipt["receipt_sha256"]}
            with mock.patch("robotics_ar._manager", return_value=manager), mock.patch.object(TrialContractManager, "assert_approved", return_value=approved_contract):
                with self.assertRaises(CLIError):
                    command_trial_run(args)

    def test_cli_trial_run_and_analyze_preserve_strict_receipt_bindings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            manifest = _manifest(root / "environment")
            manager = SessionManager(project)
            manager.initialize(mode="EXECUTION_ENABLED", interaction_language="en", entry_mode="MIDSTREAM_TAKEOVER", session_id="RAS-STRICT-CLI")
            environment = EnvironmentAdapter.from_file(manifest).verify_takeover()
            environment_path = manager.paths.takeover / "environment-receipt.yaml"
            write_structured(environment_path, environment)
            contract = compile_trial_contract(
                {
                    "contract_id": "batch-cli",
                    "project_core_sha256": "c" * 64,
                    "baseline_receipt_sha256": "b" * 64,
                    "environment_receipt_sha256": environment["receipt_sha256"],
                    "current_bottleneck": "bottleneck",
                    "primary_hypothesis": {"statement": "initialization helps"},
                    "primary_objective": {"metric": "score", "direction": "maximize"},
                    "allowed_search_space": {"tier_0_parameters": ["src"]},
                    "allowed_paths": ["src"],
                    "project_core_approved": True,
                    "baseline_approved": True,
                    "baseline_reproduction_status": "REPRODUCED",
                    "budget": {"max_trials": 2, "max_parallel_jobs": 1},
                }
            )
            contracts = TrialContractManager(manager.paths.takeover_contracts, manager.paths.approvals)
            contract_path = contracts.save(contract)
            approval = contracts.create_user_approval(contract_path)
            contract = contracts.approve(contract_path, manager.paths.approvals / f"{approval['approval_id']}.json")
            state = dict(manager.state)
            state.update({"state": "TRIAL_BATCH_READY", "contract_path": contract_path.as_posix(), "contract_sha256": contract["contract_sha256"], "environment_receipt_path": environment_path.as_posix(), "environment_receipt_sha256": environment["receipt_sha256"], "environment_fingerprint": environment["fingerprint"]})
            atomic_write_json(manager.paths.state, state)
            manager._state = state
            proposal = build_proposal({"trial_id": "cli-trial-1", "parent_contract": contract["contract_sha256"], "hypothesis": {"statement": "initialization helps", "expected_observation": "score rises", "falsification_condition": "score does not rise"}, "change": {"tier": 0, "components": ["src/init.py"], "minimal_patch": True}, "metrics": {"score": {"metric_version": "v1"}}})
            proposal_path = root / "proposal.yaml"
            write_structured(proposal_path, proposal)

            def receipt(value: dict) -> dict:
                value["receipt_sha256"] = sha256_obj(value)
                return value

            code = receipt({"status": "PASS", "trial_id": proposal["trial_id"], "proposal_sha256": proposal["proposal_sha256"], "contract_sha256": contract["contract_sha256"], "code_version": "commit-test", "configuration_sha256": "d" * 64})
            test = receipt({"status": "PASS", "trial_id": proposal["trial_id"], "proposal_sha256": proposal["proposal_sha256"], "contract_sha256": contract["contract_sha256"], "code_receipt_sha256": code["receipt_sha256"], "test_version": "suite-v1"})
            code_path = root / "code-receipt.json"
            test_path = root / "test-receipt.json"
            write_structured(code_path, code)
            write_structured(test_path, test)
            run_args = argparse.Namespace(project_root=str(project), dry_run=False, trial_id=proposal["trial_id"], proposal=str(proposal_path), receipt=str(environment_path), environment_manifest=str(manifest), contract=str(contract_path), code_receipt=str(code_path), test_receipt=str(test_path))
            with mock.patch("robotics_ar._manager", return_value=manager):
                run_result = command_trial_run(run_args)
            run = run_result["run"]
            self.assertEqual(run["contract_sha256"], contract["contract_sha256"])
            self.assertEqual(run["code_receipt_sha256"], code["receipt_sha256"])
            self.assertEqual(run["test_receipt_sha256"], test["receipt_sha256"])

            analysis_input = root / "analysis.json"
            analysis_input.write_text(json.dumps({"metrics": {"score": 1.0}, "metric_versions": {"score": "v1"}, "valid": True, "reproducible": True, "improved": True}), encoding="utf-8")
            analyze_args = argparse.Namespace(project_root=str(project), dry_run=False, trial_id=proposal["trial_id"], input=str(analysis_input), proposal=None, contract=None)
            with mock.patch("robotics_ar._manager", return_value=manager):
                analysis_result = command_trial_analyze(analyze_args)
            analysis = analysis_result["analysis_receipt"]
            self.assertEqual(analysis["proposal_sha256"], proposal["proposal_sha256"])
            self.assertEqual(analysis["contract_sha256"], contract["contract_sha256"])
            self.assertEqual(analysis["run_receipt_sha256"], run["receipt_sha256"])
            decision = TrialDecisionEngine().decide(proposal=proposal, contract=contract, code_receipt=code, test_receipt=test, run_receipt=run, analysis=analysis, environment_receipt_sha256=environment["receipt_sha256"], environment_fingerprint=environment["fingerprint"])
            self.assertEqual(decision["decision"], "KEEP")


if __name__ == "__main__":
    unittest.main()
