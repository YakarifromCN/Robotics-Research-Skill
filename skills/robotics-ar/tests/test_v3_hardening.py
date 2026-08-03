"""Focused regression tests for Robot-AR v3 fail-closed boundaries."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from robotics_ar_core.best_known import BestKnownError, BestKnownState, build_candidate  # noqa: E402
from robotics_ar_core.batch_controller import BatchController, BatchControllerError, compile_batch  # noqa: E402
from robotics_ar_core.blackboard import Blackboard, BlackboardError  # noqa: E402
from robotics_ar_core.atomic_io import atomic_write_json  # noqa: E402
from robotics_ar_core.canonical import sha256_obj  # noqa: E402
from robotics_ar_core.history_reconstruction import DoNotRepeatRegistry, ExperimentLedger, reconstruct_history  # noqa: E402
from robotics_ar_core.project_audit import audit_project  # noqa: E402
from robotics_ar_core.project_core import compile_project_core, save_project_core  # noqa: E402
from robotics_ar_core.session import SessionManager  # noqa: E402
from robotics_ar_core.trial_contract import TrialContractError, TrialContractManager, compile_trial_contract  # noqa: E402
from robotics_ar_core.trial_loop import TrialDecisionEngine, TrialLoop  # noqa: E402
from robotics_ar_core.trial_queue import TrialQueue, TrialQueueError, build_proposal  # noqa: E402


HASH = "a" * 64
ENV_RECEIPT = {"schema_version": "robotics-ar-environment-receipt.v1", "environment_id": "hardening", "environment_kind": "simulation", "fingerprint": HASH, "status": "ONLINE_VERIFIED", "checks": {}, "created_at": "2026-01-01T00:00:00Z"}
ENV_RECEIPT["receipt_sha256"] = sha256_obj(ENV_RECEIPT)


class _FakeManager:
    def __init__(self) -> None:
        self._state = {"state": "TRIAL_BATCH_READY"}
        self.events: list[tuple[str, str]] = []

    @property
    def state(self) -> dict[str, str]:
        return dict(self._state)

    def transition(self, target: str, event: str = "", payload: dict | None = None) -> dict[str, str]:
        from robotics_ar_core.state_machine import validate_transition

        validate_transition(self._state["state"], target)
        self.events.append((self._state["state"], target))
        self._state["state"] = target
        return self.state


def _approved_contract(root: Path) -> tuple[TrialContractManager, Path, dict]:
    manager = TrialContractManager(root / "contracts", root / "approvals")
    draft = compile_trial_contract({
        "contract_id": "batch-001",
        "project_core_sha256": "c" * 64,
        "baseline_receipt_sha256": "b" * 64,
        "environment_receipt_sha256": ENV_RECEIPT["receipt_sha256"],
        "project_core_approved": True,
        "baseline_approved": True,
        "baseline_reproduction_status": "REPRODUCED",
        "current_bottleneck": "bottleneck",
        "primary_hypothesis": {"statement": "one minimal change"},
        "primary_objective": {"metric": "score", "direction": "maximize"},
        "allowed_search_space": {"tier_0_parameters": ["src"]},
        "allowed_paths": ["src"],
        "budget": {"max_trials": 3, "max_parallel_jobs": 1},
    })
    path = manager.save(draft)
    approval = manager.create_user_approval(path)
    approved = manager.approve(path, root / "approvals" / f"{approval['approval_id']}.json")
    return manager, path, approved


def _proposal(contract: dict, trial_id: str = "trial-1") -> dict:
    return build_proposal({
        "trial_id": trial_id,
        "parent_contract": contract["contract_sha256"],
        "hypothesis": {"statement": "change initialization", "expected_observation": "score rises", "falsification_condition": "score does not rise"},
        "change": {"tier": 0, "components": ["src/init.py"], "minimal_patch": True},
    })


class TrialLoopHardeningTests(unittest.TestCase):
    def test_status_only_success_receipts_cannot_produce_keep(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, _, contract = _approved_contract(root)
            proposal = _proposal(contract)
            decision = TrialDecisionEngine().decide(
                proposal=proposal,
                contract=contract,
                code_receipt={"status": "PASS"},
                test_receipt={"status": "PASS"},
                run_receipt={"status": "PASS", "raw_evidence": {"sha256": HASH}},
                analysis={"status": "PASS", "improved": True},
                environment_receipt_sha256=ENV_RECEIPT["receipt_sha256"],
            )
            self.assertEqual(decision["decision"], "REVERT")
            self.assertTrue(any("receipt" in reason for reason in decision["reasons"]))

    def test_trial_requires_parent_contract_and_environment_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager, _, contract = _approved_contract(root)
            with self.assertRaises(TrialQueueError):
                build_proposal({"trial_id": "unbound", "hypothesis": {"statement": "x", "expected_observation": "y", "falsification_condition": "z"}, "change": {"tier": 0, "minimal_patch": True}})
            with self.assertRaises(TrialQueueError):
                build_proposal({"trial_id": "../escape", "parent_contract": contract["contract_sha256"], "hypothesis": {"statement": "x", "expected_observation": "y", "falsification_condition": "z"}, "change": {"tier": 0, "minimal_patch": True}})
            with self.assertRaises(TrialContractError):
                manager.check_trial(contract, _proposal(contract))

    def test_failures_use_safe_states_and_do_not_enter_expert_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, _, contract = _approved_contract(root)
            cases = [
                ({"code": {"status": "FAIL"}}, "TRIAL_DEBUGGING"),
                ({"code": {"status": "PASS"}, "test": {"status": "FAIL"}}, "TRIAL_DEBUGGING"),
                ({"code": {"status": "PASS"}, "test": {"status": "PASS"}, "run": {"status": "BLOCKED_ENVIRONMENT"}}, "BLOCKED_ENVIRONMENT"),
            ]
            for index, (receipts, expected_state) in enumerate(cases):
                fake = _FakeManager()
                callbacks = {
                    "code": lambda _p, value=receipts.get("code", {"status": "PASS"}): value,
                    "test": lambda _p, _c, value=receipts.get("test", {"status": "PASS"}): value,
                    "run": lambda _p, _c, _t, value=receipts.get("run", {"status": "PASS", "raw_evidence": {"sha256": HASH}}): value,
                    "analysis": lambda _p, _r: {"status": "PASS", "improved": True},
                }
                decision = TrialLoop(root / f"experiments-{index}", manager=fake).run(_proposal(contract, f"trial-{index}"), contract, callbacks=callbacks, environment_receipt_sha256=ENV_RECEIPT["receipt_sha256"])
                self.assertIn(decision["decision"], {"REVERT", "ESCALATE"})
                self.assertEqual(fake.state["state"], expected_state)
                self.assertNotIn(("TRIAL_EXPERT_REVIEW", "TRIAL_DECIDING"), fake.events)

    def test_raw_evidence_and_rollback_are_receipted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, _, contract = _approved_contract(root)
            fake = _FakeManager()
            proposal = _proposal(contract)
            decision = TrialLoop(root / "experiments", manager=fake).run(
                proposal,
                contract,
                environment_receipt_sha256=ENV_RECEIPT["receipt_sha256"],
                callbacks={
                    "code": lambda _p: {"status": "PASS"},
                    "test": lambda _p, _c: {"status": "PASS"},
                    "run": lambda _p, _c, _t: {"status": "PASS", "raw_evidence": {"sha256": "not-a-hash"}},
                    "analysis": lambda _p, _r: {"status": "PASS", "improved": True},
                },
            )
            self.assertEqual(decision["decision"], "REVERT")
            self.assertEqual(fake.state["state"], "AWAITING_USER_DIRECTION")

            fake = _FakeManager()
            decision = TrialLoop(root / "experiments-good", manager=fake).run(
                _proposal(contract, "trial-2"),
                contract,
                environment_receipt_sha256=ENV_RECEIPT["receipt_sha256"],
                callbacks={
                    "code": lambda _p: {"status": "PASS"},
                    "test": lambda _p, _c: {"status": "PASS"},
                    "run": lambda _p, _c, _t: {"status": "PASS", "raw_evidence": {"sha256": HASH}},
                    "analysis": lambda _p, _r: {"status": "PASS", "improved": False},
                    "rollback": lambda _p, _c, _r, _a: {"status": "ROLLED_BACK", "receipt_sha256": HASH},
                },
            )
            self.assertEqual(decision["decision"], "REVERT")
            receipt = json.loads((root / "experiments-good" / "trial-2" / "decision-receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["rollback"]["status"], "ROLLED_BACK")


class HistoryQueueAndBestKnownTests(unittest.TestCase):
    def test_completed_conclusion_enters_do_not_repeat_and_queue_hash_survives_states(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            queue = TrialQueue(root / "queue", do_not_repeat=root / "history" / "do-not-repeat.yaml")
            proposal = _proposal({"contract_sha256": "contract"})
            queued = queue.add(proposal)
            self.assertEqual(queue.next()["status"], "ACTIVE")
            completed = queue.complete(proposal["trial_id"], status="COMPLETED", decision={"decision": "KEEP", "conclusion": "no measurable change"})
            self.assertEqual(completed["status"], "COMPLETED")
            equivalent = dict(proposal)
            equivalent["trial_id"] = "trial-equivalent"
            equivalent["proposal_sha256"] = __import__("robotics_ar_core.trial_queue", fromlist=["proposal_hash"]).proposal_hash(equivalent)
            with self.assertRaises(TrialQueueError):
                queue.add(equivalent)
            equivalent["change"] = dict(equivalent["change"], material_difference={"seed": 7})
            equivalent["proposal_sha256"] = __import__("robotics_ar_core.trial_queue", fromlist=["proposal_hash"]).proposal_hash(equivalent)
            retried = queue.add(equivalent, retry_justification="changed the seed to isolate the prior conclusion")
            self.assertEqual(retried["retry"]["material_difference"], {"seed": 7})

    def test_metric_versions_and_malformed_history_remain_visible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "history.jsonl"
            records = [
                {"trial_id": "t1", "status": "VERIFIED", "code": {"commit": "c1"}, "configuration": {"sha256": HASH}, "environment": {"fingerprint": HASH}, "metrics": {"score": 1}, "metric_versions": {"score": "v1"}},
                {"trial_id": "t2", "status": "VERIFIED", "code": {"commit": "c1"}, "configuration": {"sha256": HASH}, "environment": {"fingerprint": HASH}, "metrics": {"score": 1}, "metric_versions": {"score": "v2"}},
            ]
            source.write_text("\n".join([json.dumps(records[0]), "{malformed", json.dumps(records[1])]) + "\n", encoding="utf-8")
            result = reconstruct_history(root, sources=[source], output_dir=root / "out")
            self.assertEqual(result["receipt"]["invalid_count"], 1)
            self.assertTrue(result["receipt"]["requires_reconciliation"])
            self.assertEqual(len(result["receipt"]["metric_version_conflicts"]), 1)
            unresolved = (root / "out" / "unresolved-history.md").read_text(encoding="utf-8")
            self.assertIn("metric-version:score", unresolved)

    def test_ledger_read_and_append_preserve_malformed_jsonl_as_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "experiment-ledger.jsonl"
            path.write_text("{malformed\n", encoding="utf-8")
            ledger = ExperimentLedger(path)
            rows = ledger.records()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["status"], "INVALID")
            self.assertEqual(rows[0]["failure_class"], "malformed_history_record")
            appended = ledger.append({"trial_id": "new", "status": "UNKNOWN", "interpretation": "needs review"})
            self.assertEqual(appended["trial_id"], "new")
            self.assertEqual(len(ledger.records()), 2)

    def test_blackboard_hash_is_stable_and_tamper_checked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            board = Blackboard(Path(directory) / "blackboard")
            first = board.update("analysis-status", {"status": "PASS"})
            self.assertEqual(first["blackboard_sha256"], sha256_obj({key: value for key, value in first.items() if key != "blackboard_sha256"}))
            second = board.update("analysis-status", {"status": "REVIEW"})
            self.assertEqual(second["blackboard_sha256"], sha256_obj({key: value for key, value in second.items() if key != "blackboard_sha256"}))
            tampered = json.loads(board.state_path.read_text(encoding="utf-8"))
            tampered["values"]["analysis-status"]["value"]["status"] = "TAMPERED"
            board.state_path.write_text(json.dumps(tampered), encoding="utf-8")
            with self.assertRaises(BlackboardError):
                board.get("analysis-status")

    def test_best_known_requires_reproduction_and_never_auto_stabilizes_single_seed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state = BestKnownState(Path(directory) / "best-known.yaml")
            candidate = build_candidate(trial_id="t1", code_version="c1", configuration={"x": 1}, environment_fingerprint=HASH, baseline_relationship="matched", primary_metrics={"score": 0.8}, raw_evidence={"sha256": HASH}, validation_status="REPRODUCED", reproduction_command=["run"], metric_versions={"score": "v1"}, seeds=[0])
            current = state.promote(candidate)
            self.assertIsNone(current["current_stable_best"])
            with self.assertRaises(BestKnownError):
                state.promote(candidate, stable=True)
            degraded = dict(candidate)
            degraded.update({"trial_id": "t2", "primary_metrics": {"score": 0.2}})
            degraded["metric_versions"] = {"score": "v1"}
            state.promote(degraded)
            self.assertEqual(state.current()["current_primary_best"]["trial_id"], "t1")
            irreproducible = dict(candidate)
            irreproducible.update({"trial_id": "t3", "validation_status": "FAILED"})
            with self.assertRaises(BestKnownError):
                state.promote(irreproducible)
            drifted = dict(candidate)
            drifted.update({"trial_id": "t4", "metric_versions": {"score": "v2"}, "seeds": [0, 1]})
            with self.assertRaises(BestKnownError):
                state.promote(drifted)


class AuditAndGateTests(unittest.TestCase):
    def test_audit_surfaces_method_metric_and_entry_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "run.py").write_text("algorithm: alpha\n", encoding="utf-8")
            (root / "train.py").write_text("algorithm: beta\n", encoding="utf-8")
            (root / "config.json").write_text(json.dumps({"score": 1}), encoding="utf-8")
            (root / "result.json").write_text(json.dumps({"score": 2}), encoding="utf-8")
            (root / "broken.yaml").write_text("a: [broken\n", encoding="utf-8")
            result = audit_project(root)
            kinds = {item["kind"] for item in result["receipt"]["discrepancies"]}
            self.assertIn("CODE_DOCUMENT_CONFLICT", kinds)
            self.assertIn("CONFIG_RESULT_CONFLICT", kinds)
            self.assertIn("MULTIPLE_FORMAL_ENTRY_CANDIDATES", kinds)
            self.assertTrue(result["receipt"]["requires_reconciliation"])

    def test_contract_without_upstream_approvals_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = TrialContractManager(root / "contracts", root / "approvals")
            contract = compile_trial_contract({"contract_id": "batch", "project_core_sha256": "c" * 64, "baseline_receipt_sha256": "b" * 64, "environment_receipt_sha256": ENV_RECEIPT["receipt_sha256"], "current_bottleneck": "b", "primary_hypothesis": {"statement": "h"}, "primary_objective": {"metric": "score"}, "allowed_search_space": {"tier_0_parameters": ["src"]}, "budget": {"max_trials": 1}})
            path = manager.save(contract)
            approval = manager.create_user_approval(path)
            with self.assertRaises(TrialContractError):
                manager.approve(path, root / "approvals" / f"{approval['approval_id']}.json")

    def test_production_contract_binding_cannot_be_enabled_without_receipts(self) -> None:
        with self.assertRaises(TrialContractError):
            compile_trial_contract({
                "contract_id": "production-contract",
                "project_core_sha256": "c" * 64,
                "baseline_receipt_sha256": "b" * 64,
                "environment_receipt_sha256": ENV_RECEIPT["receipt_sha256"],
                "current_bottleneck": "b",
                "primary_hypothesis": {"statement": "h"},
                "primary_objective": {"metric": "score"},
                "allowed_search_space": {"tier_0_parameters": ["src"]},
                "project_core_approved": True,
                "baseline_approved": True,
                "baseline_reproduction_status": "REPRODUCED",
                "upstream_approval_binding_required": True,
            })

    def test_batch_checkpoint_persists_elapsed_time_and_rechecks_environment_on_resume(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, _, contract = _approved_contract(root)
            batch = compile_batch({"batch_id": "batch-001", "max_trials": 2, "max_wall_time_minutes": 5, "max_parallel_jobs": 1, "allowed_tiers": [0]}, contract_sha256=contract["contract_sha256"])
            receipt = dict(ENV_RECEIPT)
            controller = BatchController(root / "batch", mode="EXECUTION_ENABLED")
            controller.start(batch, contract=contract, environment_receipt=receipt)
            controller.started_at = __import__("time").monotonic() - 123
            stopped = controller.stop("operator_pause")
            self.assertGreaterEqual(stopped["elapsed_wall_time_seconds"], 123)
            loaded = BatchController.load_checkpoint(root / "batch" / "batch-checkpoint.json", mode="EXECUTION_ENABLED")
            resumed = loaded.resume(contract=contract, environment_receipt=receipt)
            self.assertEqual(resumed["status"], "RUNNING")
            loaded.stop("search_space_tier_violation")
            terminal = BatchController.load_checkpoint(root / "batch" / "batch-checkpoint.json", mode="EXECUTION_ENABLED")
            with self.assertRaises(BatchControllerError):
                terminal.resume(contract=contract, environment_receipt=receipt)

    def test_batch_tiers_are_a_subset_of_contract_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, _, contract = _approved_contract(root)
            batch = compile_batch({"batch_id": "tier-violation", "max_trials": 1, "max_wall_time_minutes": 5, "max_parallel_jobs": 1, "allowed_tiers": [0, 1]}, contract_sha256=contract["contract_sha256"])
            with self.assertRaises(BatchControllerError):
                BatchController(root / "batch", mode="EXECUTION_ENABLED").start(batch, contract=contract, environment_receipt=dict(ENV_RECEIPT))

    def test_batch_rechecks_environment_before_each_trial(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, _, contract = _approved_contract(root)
            batch = compile_batch({"batch_id": "env-drift", "max_trials": 1, "max_wall_time_minutes": 5, "max_parallel_jobs": 1, "allowed_tiers": [0]}, contract_sha256=contract["contract_sha256"])
            controller = BatchController(root / "batch", mode="EXECUTION_ENABLED")
            controller.start(batch, contract=contract, environment_receipt=dict(ENV_RECEIPT))
            changed = dict(ENV_RECEIPT)
            changed["fingerprint"] = "b" * 64
            changed.pop("receipt_sha256", None)
            changed["receipt_sha256"] = sha256_obj(changed)
            called = {"runner": False}
            checkpoint = controller.run([_proposal(contract)], lambda _: called.__setitem__("runner", True) or {"status": "PASS"}, environment_receipt=changed)
            self.assertEqual(checkpoint["status"], "STOPPED")
            self.assertEqual(checkpoint["stop_reason"], "environment_drift")
            self.assertFalse(called["runner"])

    def test_takeover_pause_can_resume_before_baseline_or_contract_artifacts_exist(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            manager = SessionManager(root)
            manager.initialize(mode="EXECUTION_ENABLED", interaction_language="en", entry_mode="MIDSTREAM_TAKEOVER", session_id="RAS-EARLY-PAUSE")
            for state in ("TAKEOVER_REQUESTED", "TAKEOVER_INTERVIEW", "TAKEOVER_AUDITING", "TAKEOVER_HISTORY_RECONSTRUCTION", "TAKEOVER_ENVIRONMENT_VALIDATION", "TAKEOVER_BASELINE_SELECTION", "TAKEOVER_BASELINE_REPRODUCTION"):
                manager.transition(state)
            environment_path = manager.paths.takeover / "environment-receipt.yaml"
            from robotics_ar_core.structured import write_structured

            write_structured(environment_path, ENV_RECEIPT)
            updated = dict(manager.state)
            updated.update({"environment_fingerprint": ENV_RECEIPT["fingerprint"], "environment_receipt_sha256": ENV_RECEIPT["receipt_sha256"], "environment_receipt_path": environment_path.as_posix()})
            atomic_write_json(manager.paths.state, updated)
            manager._state = updated
            subprocess.run(["git", "add", "-A"], cwd=root, check=True)
            subprocess.run(["git", "-c", "user.email=robotics-ar@test", "-c", "user.name=Robot-AR", "commit", "-qm", "checkpoint"], cwd=root, check=True)
            manager.pause("pause during baseline reproduction")
            resumed = SessionManager(root).resume()
            self.assertEqual(resumed["state"], "TAKEOVER_BASELINE_REPRODUCTION")

    def test_contract_compilation_pause_does_not_require_uncompiled_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            manager = SessionManager(root)
            manager.initialize(mode="EXECUTION_ENABLED", interaction_language="en", entry_mode="MIDSTREAM_TAKEOVER", session_id="RAS-CONTRACT-PAUSE")
            for state in ("TAKEOVER_REQUESTED", "TAKEOVER_INTERVIEW", "TAKEOVER_AUDITING", "TAKEOVER_HISTORY_RECONSTRUCTION", "TAKEOVER_ENVIRONMENT_VALIDATION", "TAKEOVER_BASELINE_SELECTION", "TAKEOVER_BASELINE_REPRODUCTION"):
                manager.transition(state)
            from robotics_ar_core.baseline import build_baseline_receipt
            from robotics_ar_core.project_core import core_hash, mark_project_core_approved
            from robotics_ar_core.structured import write_structured

            environment_path = manager.paths.takeover / "environment-receipt.yaml"
            write_structured(environment_path, ENV_RECEIPT)
            core = compile_project_core({"project_id": "pause", "research_problem": "p", "core_method": "m", "frozen_invariants": ["m"], "modifiable_components": ["src"], "forbidden_pivots": ["objective"], "current_bottleneck": "b", "current_batch_goal": "g", "success_criteria": {"score": 1}})
            core = mark_project_core_approved(core, approval_id="approval-for-pause-test")
            core_path = manager.paths.takeover / "project-core.yaml"
            save_project_core(core_path, core)
            baseline = build_baseline_receipt({"baseline_id": "b", "baseline_spec_sha256": HASH, "environment": {"fingerprint": HASH}}, "REPRODUCED")
            baseline_path = manager.paths.takeover_baseline / "baseline-receipt.json"
            write_structured(baseline_path, baseline)
            manager.transition("AWAITING_TAKEOVER_APPROVAL", "BASELINE_REPRODUCED")
            manager.transition("TRIAL_CONTRACT_COMPILATION", "BASELINE_APPROVED")
            updated = dict(manager.state)
            updated.update({"environment_fingerprint": ENV_RECEIPT["fingerprint"], "environment_receipt_sha256": ENV_RECEIPT["receipt_sha256"], "environment_receipt_path": environment_path.as_posix(), "project_core_path": core_path.as_posix(), "project_core_sha256": core_hash(core), "baseline_receipt_path": baseline_path.as_posix(), "baseline_receipt_sha256": baseline["receipt_sha256"], "project_core_approved": True, "baseline_approved": True})
            atomic_write_json(manager.paths.state, updated)
            manager._state = updated
            subprocess.run(["git", "add", "-A"], cwd=root, check=True)
            subprocess.run(["git", "-c", "user.email=robotics-ar@test", "-c", "user.name=Robot-AR", "commit", "-qm", "checkpoint"], cwd=root, check=True)
            manager.pause("pause before contract draft is compiled")
            resumed = SessionManager(root).resume()
            self.assertEqual(resumed["state"], "TRIAL_CONTRACT_COMPILATION")


if __name__ == "__main__":
    unittest.main()
