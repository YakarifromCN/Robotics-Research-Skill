"""严格 v3 安全边界回归测试。 / Strict v3 safety-boundary regression tests."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from robotics_ar_core.batch_controller import BatchController, compile_batch  # noqa: E402
from robotics_ar_core.canonical import sha256_obj  # noqa: E402
from robotics_ar_core.environment import EnvironmentAdapter  # noqa: E402
from robotics_ar_core.history_reconstruction import reconstruct_history  # noqa: E402
from robotics_ar_core.project_audit import audit_project  # noqa: E402
from robotics_ar_core.receipts import file_sha256  # noqa: E402
from robotics_ar_core.session import SessionManager  # noqa: E402
from robotics_ar_core.structured import write_structured  # noqa: E402
from robotics_ar_core.trial_contract import TrialContractError, TrialContractManager, compile_trial_contract  # noqa: E402
from robotics_ar_core.trial_queue import build_proposal  # noqa: E402
from robotics_ar_core.user_correction import assert_task_current, compile_correction, confirm_and_resume  # noqa: E402


MOCK = Path(__file__).resolve().parents[1] / "assets" / "mock-environment" / "adapter.py"
ENV_RECEIPT = {"schema_version": "robotics-ar-environment-receipt.v1", "environment_id": "strict", "environment_kind": "simulation", "fingerprint": "e" * 64, "status": "ONLINE_VERIFIED", "checks": {}, "created_at": "2026-01-01T00:00:00Z"}
ENV_RECEIPT["receipt_sha256"] = sha256_obj(ENV_RECEIPT)


def make_manifest(root: Path, *, takeover: bool = False) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MOCK, root / "adapter.py")
    commands = {name: ["python3", "adapter.py", command] for name, command in (("capabilities", "capabilities"), ("health_check", "health-check"), ("minimal_rollout", "minimal-rollout"), ("collect_results", "collect-results"), ("stop", "stop"))}
    if takeover:
        commands.update({"reset": ["python3", "adapter.py", "minimal-rollout"], "trial": ["python3", "adapter.py", "minimal-rollout"]})
    manifest = {
        "schema_version": "robotics-ar-environment.v1",
        "id": "strict-v3-mock",
        "kind": "simulation",
        "root": root.as_posix(),
        "adapter": {"path": "adapter.py", "sha256": file_sha256(root / "adapter.py")},
        "commands": commands,
        "io": {"request_dir": "requests", "result_dir": "results", "artifact_dir": "artifacts"},
        "limits": {"timeout_s": 10, "max_parallel_runs": 1, "network": "denied", "executables": ["python3"]},
    }
    path = root / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


class StrictV3Tests(unittest.TestCase):
    def _contract(self, root: Path) -> tuple[TrialContractManager, Path, dict]:
        manager = TrialContractManager(root / "contracts", root / "approvals")
        contract = compile_trial_contract({
            "contract_id": "batch-001",
            "project_core_sha256": "c" * 64,
            "baseline_receipt_sha256": "b" * 64,
            "environment_receipt_sha256": ENV_RECEIPT["receipt_sha256"],
            "current_bottleneck": "bottleneck",
            "primary_hypothesis": {"statement": "one change"},
            "primary_objective": {"metric": "score", "direction": "maximize"},
            "allowed_search_space": {"tier_0_parameters": ["src"]},
            "allowed_paths": ["src"],
            "read_only_paths": ["raw"],
            "project_core_approved": True,
            "baseline_approved": True,
            "baseline_reproduction_status": "REPRODUCED",
            "budget": {"max_trials": 2, "max_parallel_jobs": 1, "max_wall_time_hours": 1, "max_gpu_hours": 1, "max_disk_gb": 1},
        })
        path = manager.save(contract)
        approval = manager.create_user_approval(path)
        approved = manager.approve(path, root / "approvals" / f"{approval['approval_id']}.json")
        return manager, path, approved

    def test_amendment_compiles_new_draft_and_invalidates_old(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager, path, approved = self._contract(root)
            amendment = manager.amend(path, user_instruction="only change initialization", changes={"budget": {"max_trials": 1}, "allowed_changes": ["src/init.py"]})
            amended = manager.compile_amended(path, root / "contracts" / f"{amendment['amendment_id']}.yaml")
            amended_path = manager.save(amended)
            self.assertNotEqual(amended["contract_sha256"], approved["contract_sha256"])
            self.assertEqual(manager.load(path)["status"], "INVALIDATED")
            self.assertEqual(manager.load(amended_path)["status"], "DRAFT")
            with self.assertRaises(TrialContractError):
                manager.assert_approved(amended_path)

    def test_trial_binding_and_path_policy_are_checked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager, _, contract = self._contract(root)
            proposal = build_proposal({
                "trial_id": "trial-1",
                "parent_contract": contract["contract_sha256"],
                "hypothesis": {"statement": "x", "expected_observation": "y", "falsification_condition": "z"},
                "change": {"tier": 0, "components": ["raw/out.json"], "minimal_patch": True},
            })
            with self.assertRaises(TrialContractError):
                manager.check_trial(contract, proposal)
            proposal["parent_contract"] = "wrong-contract"
            proposal["proposal_sha256"] = __import__("robotics_ar_core.trial_queue", fromlist=["proposal_hash"]).proposal_hash(proposal)
            with self.assertRaises(TrialContractError):
                manager.check_trial(contract, proposal)
            proposal["parent_contract"] = contract["contract_sha256"]
            proposal["change"]["components"] = ["../src/escape.py"]
            proposal["proposal_sha256"] = __import__("robotics_ar_core.trial_queue", fromlist=["proposal_hash"]).proposal_hash(proposal)
            with self.assertRaises(TrialContractError):
                manager.check_trial(contract, proposal)

    def test_takeover_online_gate_checks_reset_and_trial_binding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = make_manifest(Path(directory) / "env", takeover=True)
            receipt = EnvironmentAdapter.from_file(path).verify_takeover()
            self.assertEqual(receipt["status"], "ONLINE_VERIFIED")
            self.assertEqual(receipt["takeover_capabilities"]["trial"], True)
            self.assertEqual(len(receipt["checks"]["reset"]["outputs"]), 2)

    def test_audit_records_symlinked_directories_without_following_them(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            outside = Path(directory) / "outside"
            root.mkdir()
            outside.mkdir()
            (outside / "secret.txt").write_text("secret", encoding="utf-8")
            try:
                (root / "linked").symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest("symlinks are unavailable")
            result = audit_project(root)
            links = [item for item in result["snapshot"]["entries"] if item.get("path") == "linked"]
            self.assertEqual(links[0]["kind"], "symlink")
            self.assertFalse(any(item.get("path") == "linked/secret.txt" for item in result["snapshot"]["entries"]))

    def test_batch_runner_exception_is_checkpointed_and_stopped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, _, contract = self._contract(root)
            batch = compile_batch({"batch_id": "batch-001", "max_trials": 1, "max_wall_time_minutes": 5, "max_parallel_jobs": 1, "allowed_tiers": [0]}, contract_sha256=contract["contract_sha256"])
            controller = BatchController(root / "batch", mode="EXECUTION_ENABLED")
            controller.start(batch, contract=contract, environment_receipt=dict(ENV_RECEIPT))
            proposal = build_proposal({
                "trial_id": "trial-1",
                "parent_contract": contract["contract_sha256"],
                "hypothesis": {"statement": "x", "expected_observation": "y", "falsification_condition": "z"},
                "change": {"tier": 0, "components": ["src"], "minimal_patch": True},
            })
            checkpoint = controller.run([proposal], lambda _: (_ for _ in ()).throw(RuntimeError("runner failed")), environment_receipt=dict(ENV_RECEIPT))
            self.assertEqual(checkpoint["status"], "STOPPED")
            self.assertEqual(checkpoint["results"][0]["status"], "BLOCKED_ENVIRONMENT")

    def test_running_checkpoint_is_recovered_as_a_stopped_batch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, _, contract = self._contract(root)
            batch = compile_batch({"batch_id": "crash-recovery", "max_trials": 1, "max_wall_time_minutes": 5, "max_parallel_jobs": 1, "allowed_tiers": [0]}, contract_sha256=contract["contract_sha256"])
            controller = BatchController(root / "batch", mode="EXECUTION_ENABLED")
            controller.start(batch, contract=contract, environment_receipt=dict(ENV_RECEIPT))
            recovered = BatchController.load_checkpoint(root / "batch" / "batch-checkpoint.json", mode="EXECUTION_ENABLED")
            self.assertEqual(recovered.status, "STOPPED")
            self.assertEqual(recovered.stop_reason, "crash_recovery_required")
            self.assertEqual(recovered.resume(contract=contract, environment_receipt=dict(ENV_RECEIPT))["status"], "RUNNING")

    def test_user_correction_compiles_and_confirms_a_new_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            project.mkdir()
            session = SessionManager(project)
            session.initialize(mode="PLANNING_ONLY", interaction_language="en", entry_mode="MIDSTREAM_TAKEOVER")
            for state in ("TAKEOVER_REQUESTED", "TAKEOVER_INTERVIEW", "TAKEOVER_AUDITING", "TAKEOVER_HISTORY_RECONSTRUCTION", "TAKEOVER_ENVIRONMENT_VALIDATION", "TAKEOVER_BASELINE_SELECTION", "TAKEOVER_BASELINE_REPRODUCTION", "AWAITING_TAKEOVER_APPROVAL", "TRIAL_CONTRACT_COMPILATION", "AWAITING_TRIAL_CONTRACT_APPROVAL", "TRIAL_BATCH_READY"):
                session.transition(state)
            contracts = TrialContractManager(session.paths.takeover_contracts, session.paths.approvals)
            contract = compile_trial_contract({"contract_id": "batch-001", "project_core_sha256": "c" * 64, "baseline_receipt_sha256": "b" * 64, "environment_receipt_sha256": "e" * 64, "current_bottleneck": "b", "primary_hypothesis": {"statement": "h"}, "primary_objective": {"metric": "score"}, "allowed_search_space": {"tier_0_parameters": ["src"]}, "project_core_approved": True, "baseline_approved": True, "baseline_reproduction_status": "REPRODUCED", "budget": {"max_trials": 2}})
            contract_path = contracts.save(contract)
            approval = contracts.create_user_approval(contract_path)
            approved = contracts.approve(contract_path, session.paths.approvals / f"{approval['approval_id']}.json")
            state = dict(session.state)
            state.update({"contract_path": contract_path.as_posix(), "contract_sha256": approved["contract_sha256"]})
            session._state = state
            atomic = __import__("robotics_ar_core.atomic_io", fromlist=["atomic_write_json"])
            atomic.atomic_write_json(session.paths.state, state)
            task = compile_correction(session, "保留当前实现，只改变初始化。", allowed_changes=["src/init.py"], contract_path=contract_path)
            task_loaded = assert_task_current(task["task_path"], task["task_sha256"])
            self.assertTrue(task_loaded["contract_path"].endswith(".yaml"))
            new_contract_path = Path(task["contract_path"])
            self.assertEqual(contracts.load(contract_path)["status"], "INVALIDATED")
            task_approval = session.approve_subject("TASK", task["task_path"])
            contract_approval = session.approve_subject("TRIAL_CONTRACT", new_contract_path)
            resumed = confirm_and_resume(session, task_approval_path=session.paths.approvals / f"{task_approval['approval_id']}.json", contract_approval_path=session.paths.approvals / f"{contract_approval['approval_id']}.json")
            self.assertEqual(resumed["state"]["state"], "TRIAL_BATCH_READY")


if __name__ == "__main__":
    unittest.main()
