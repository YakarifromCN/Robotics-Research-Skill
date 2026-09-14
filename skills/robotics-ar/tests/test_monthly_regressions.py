"""月度故障的合成回归，不读取用户会话。 / Synthetic monthly regressions; no user sessions."""
import json
import multiprocessing
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from robotics_ar_core.atomic_io import atomic_write_json
from robotics_ar_core.canonical import sha256_obj
from robotics_ar_core.event_log import EventLog
from robotics_ar_core.session import SessionManager, SessionError
from robotics_ar_core.takeover import TakeoverManager
from robotics_ar_core.project_audit import audit_project
from robotics_ar_core.repository_ledger import snapshot, validate_snapshot
from robotics_ar_core.migration import doctor_project, migrate_session_state
from robotics_ar_core.execution_registry import ExecutionRegistry


def append_events(path):
    for _ in range(20):
        EventLog(Path(path), "test").append("CHECK", "test", "A", "A")


def acquire_lock(root, queue):
    from robotics_ar_core.transaction import writer_lock
    with writer_lock(root):
        queue.put("acquired")


class MonthlyRegressions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manager = SessionManager(self.root)
        self.manager.initialize(mode="EXECUTION_ENABLED", interaction_language="zh")

    def state(self, state):
        data = self.manager.state
        data["state"] = state
        atomic_write_json(self.manager.paths.state, data)
        self.manager._state = data

    def test_reconciliation_is_monotone_and_bound(self):
        self.state("TAKEOVER_AUDITING")
        takeover = TakeoverManager(self.manager)
        audit = {"requires_reconciliation": True}
        audit["receipt_sha256"] = sha256_obj(audit)
        takeover.record_audit(audit)
        takeover.mark_history_reconstructed(needs_reconciliation=False)
        self.assertEqual(self.manager.state["state"], "TAKEOVER_IDEA_RECONCILIATION")

    def test_selected_baseline_is_idempotent(self):
        self.state("TAKEOVER_BASELINE_SELECTION")
        takeover = TakeoverManager(self.manager)
        selection = {"baseline_id": "B1", "config_sha256": "a" * 64, "reason": "fixture"}
        takeover.begin_baseline(selection)
        takeover.begin_baseline(selection)
        with self.assertRaises(RuntimeError):
            takeover.begin_baseline({**selection, "baseline_id": "B2"})

    def test_repeated_recovery_preserves_receipts(self):
        self.state("TAKEOVER_BASELINE_RECOVERY")
        takeover = TakeoverManager(self.manager)
        for index in range(3):
            receipt = {"status": "NOT_REPRODUCED", "error": f"cause-{index}"}
            receipt["receipt_sha256"] = sha256_obj(receipt)
            with patch("robotics_ar_core.takeover.validate_artifact"):
                takeover.baseline_result(receipt)
        self.assertEqual(len(list((self.manager.paths.takeover_baseline / "attempts").glob("*.json"))), 3)
        self.assertEqual(self.manager.state["state"], "TAKEOVER_BASELINE_RECOVERY")

    def test_concurrent_events_are_unique(self):
        path = self.root / "parallel" / "events.jsonl"
        workers = [multiprocessing.Process(target=append_events, args=(str(path),)) for _ in range(4)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(10)
            self.assertEqual(worker.exitcode, 0)
        self.assertEqual(len(EventLog(path, "test").read_events()), 80)

    def test_stale_writer_is_rejected(self):
        stale = SessionManager(self.root)
        stale.state
        self.manager.transition("TASK_COMPILATION", "START")
        with self.assertRaises(SessionError):
            stale.transition("INVOKING_IDEA_SKILL", "STALE")

    def test_projection_recovers_after_interrupted_write(self):
        from robotics_ar_core import session
        original = session.atomic_write_json
        def interrupted(path, data):
            if path == self.manager.paths.state:
                raise OSError("synthetic crash")
            original(path, data)
        with patch.object(session, "atomic_write_json", side_effect=interrupted):
            with self.assertRaises(OSError):
                self.manager.transition("TASK_COMPILATION", "START")
        self.assertEqual(SessionManager(self.root).state["state"], "TASK_COMPILATION")

    def test_failed_environment_receipt_survives(self):
        self.state("TAKEOVER_ENVIRONMENT_VALIDATION")
        with self.assertRaises(RuntimeError):
            TakeoverManager(self.manager).mark_environment({"status": "FAILED", "error": "synthetic"})
        self.assertTrue((self.manager.paths.takeover / "environment-receipt.yaml").exists())

    def test_audit_caps_and_skips_large_content(self):
        for i in range(10):
            (self.root / f"file-{i}.txt").write_text("x" * 20)
        result = audit_project(self.root, max_files=2, max_bytes=10)
        self.assertEqual(result["status"], "PARTIAL")
        self.assertLessEqual(result["receipt"]["coverage"]["visited"], 2)

    def test_non_git_and_content_drift(self):
        path = self.root / "source.txt"
        path.write_text("first")
        spec = {"authorization": "fixture user scope", "roots": [{"id": "source", "kind": "directory", "path": str(self.root), "files": ["source.txt"]}]}
        receipt = snapshot(spec)
        validate_snapshot(receipt)
        path.write_text("other")
        with self.assertRaises(ValueError):
            validate_snapshot(receipt)

    def test_terminal_resume_is_noop(self):
        self.manager.transition("COMPLETE", "DONE")
        before = self.manager.paths.events.read_bytes()
        self.manager.resume()
        self.assertEqual(before, self.manager.paths.events.read_bytes())

    def test_doctor_future_version_does_not_migrate(self):
        with self.assertRaises(ValueError):
            migrate_session_state({"schema_version": "future"})
        self.manager.paths.budget.unlink()
        self.assertEqual(doctor_project(self.root)["status"], "BLOCKED")

    def test_bootstrap_does_not_report_pass_on_validation_failure(self):
        manager = SessionManager(self.root / "bootstrap-failure")
        with patch("robotics_ar_core.session.validate_artifact", side_effect=ValueError("fixture schema error")):
            with self.assertRaises(SessionError):
                manager.initialize(mode="PLANNING_ONLY", interaction_language="en")
        receipt = json.loads((manager.paths.root / "bootstrap-receipt.json").read_text())
        self.assertEqual(receipt["status"], "BLOCKED_BOOTSTRAP")
        self.assertEqual(manager.state["state"], "FAILED_RECOVERABLE")

    def test_repository_symlink_escape_is_rejected(self):
        inside = self.root / "inside"
        inside.mkdir()
        outside = self.root / "outside.txt"
        outside.write_text("outside")
        (inside / "escape").symlink_to(outside)
        with self.assertRaises(ValueError):
            snapshot({"authorization": "fixture", "roots": [{"id": "r", "kind": "directory", "path": str(inside), "files": ["escape"]}]})

    def test_failed_cli_has_private_optional_receipt(self):
        import contextlib
        import io
        from robotics_ar import main
        path = self.root / "invocation.json"
        with contextlib.redirect_stdout(io.StringIO()):
            code = main(["doctor", "--project-root", str(self.root / "missing"), "--invocation-receipt", str(path)])
        self.assertEqual(code, 2)
        receipt = json.loads(path.read_text())
        self.assertEqual(receipt["result_status"], "BLOCKED")
        self.assertNotIn(str(self.root), path.read_text())
        self.assertFalse(receipt["network_telemetry"])

    def test_long_execution_does_not_block_pause_lock(self):
        import contextlib
        import io
        import robotics_ar
        def long_command(args):
            queue = multiprocessing.Queue()
            worker = multiprocessing.Process(target=acquire_lock, args=(self.manager.paths.root, queue))
            worker.start()
            try:
                self.assertEqual(queue.get(timeout=2), "acquired")
            finally:
                worker.join(2)
                if worker.is_alive():
                    worker.terminate()
                    worker.join()
                queue.close()
            return {"status": "PASS"}
        with patch.dict(robotics_ar.COMMANDS, {"run-batch": long_command}), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(robotics_ar.main(["run-batch", "--project-root", str(self.root)]), 0)

    def test_cli_baseline_uses_reproduction_status(self):
        from argparse import Namespace
        from unittest.mock import MagicMock
        import robotics_ar
        spec = {"baseline_id": "B1"}
        atomic_write_json(self.manager.paths.takeover_baseline / "baseline-spec.yaml", spec)
        atomic_write_json(self.manager.paths.takeover_baseline / "baseline-selection.json", {"config_sha256": sha256_obj(spec)})
        registry = MagicMock()
        adapter = MagicMock()
        adapter.manifest = {"kind": "simulation"}
        args = Namespace(baseline=None, dry_run=False, environment_manifest="fixture", allow_variance=False, execution_id="EX1", lease_token="token")
        with patch.object(robotics_ar, "_manager", return_value=self.manager), patch.object(robotics_ar.EnvironmentAdapter, "from_file", return_value=adapter), patch.object(robotics_ar, "_start_bound_execution", return_value=(registry, {})), patch.object(robotics_ar, "reproduce_baseline", return_value={"reproduction_status": "REPRODUCED"}):
            robotics_ar.command_baseline_run(args)
        self.assertEqual(registry.finish.call_args[0][2]["status"], "PASS")

    def test_execution_lease_budget_and_idempotency(self):
        data = self.manager.state
        data["environment_fingerprint"] = "a" * 64
        atomic_write_json(self.manager.paths.state, data)
        self.manager._state = data
        path = self.root / "spec.json"
        atomic_write_json(path, {"execution_id": "EX1", "task_id": "T1", "design_timing": "prospective", "environment_fingerprint": "a" * 64, "costs": {"trials": 1}})
        approval = self.manager.approve_subject("TASK", path)
        registry = ExecutionRegistry(self.manager)
        approval_path = self.manager.paths.approvals / f"{approval['approval_id']}.json"
        row = registry.reserve(path, approval_path)
        self.assertEqual(row, registry.reserve(path, approval_path))
        with self.assertRaises(ValueError):
            registry.start("EX1", "wrong")
        registry.start("EX1", row["lease_token"])
        with self.assertRaises(ValueError):
            registry.start("EX1", row["lease_token"])
        result = {"execution_id": "EX1", "status": "PASS", "actual_costs": {"trials": 2}}
        done = registry.finish("EX1", row["lease_token"], result)
        self.assertEqual(done, registry.finish("EX1", row["lease_token"], result))
        history = registry.import_history("OLD", {"status": "PASS"})
        self.assertFalse(history["authorized_execution"])
        over = self.root / "over.json"
        atomic_write_json(over, {"execution_id": "EX2", "task_id": "T1", "design_timing": "prospective", "environment_fingerprint": "a" * 64, "costs": {"trials": 100}})
        with self.assertRaisesRegex(ValueError, "budget exhausted"):
            registry.reserve(over, approval_path)
        self.assertEqual(self.manager.state["exploration_budget"]["trials_used"], 2)
        self.assertEqual(done["accounting_status"], "RECONCILED")


if __name__ == "__main__":
    unittest.main()
