"""测试 Supervisor、批准 hash、task 编译和暂停恢复。

Test the Supervisor, approval hashes, task compilation, and pause/resume.
"""

from __future__ import annotations

from pathlib import Path
import json
import sys
import tempfile
import unittest
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from robotics_ar_core.gates import GateError
from robotics_ar_core.session import SessionError, SessionManager


class SupervisorTests(unittest.TestCase):
    def test_init_and_reconstruct_without_state_cache(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager = SessionManager(directory)
            state = manager.initialize(mode="PLANNING_ONLY", interaction_language="zh", session_id="RAS-TEST")
            self.assertEqual(state["state"], "PLANNING_READY")
            expected_events = (manager.paths.events).read_text(encoding="utf-8")
            manager.paths.state.unlink()
            rebuilt = manager.reconstruct_state(persist=True)
            self.assertEqual(rebuilt["state"], "PLANNING_READY")
            self.assertEqual((manager.paths.events).read_text(encoding="utf-8"), expected_events)
            manager.paths.state.unlink()
            rebuilt_fresh = SessionManager(directory).reconstruct_state(persist=False)
            self.assertEqual(rebuilt_fresh["session_id"], "RAS-TEST")
            self.assertEqual(rebuilt_fresh["state"], "PLANNING_READY")

    def test_task_compilation_preserves_instruction_and_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager = SessionManager(directory)
            manager.initialize(mode="PLANNING_ONLY", interaction_language="en", session_id="RAS-TEST")
            task = manager.compile_task("请保留这条用户指令", allowed_paths=["src"], forbidden_paths=["raw"], stop_conditions=["budget"])
            self.assertEqual(manager.state["state"], "AWAITING_TASK_APPROVAL")
            self.assertTrue(task["task_sha256"])
            saved = list(manager.paths.user_instructions.glob("*.md"))
            self.assertEqual(saved[0].read_text(encoding="utf-8"), "请保留这条用户指令")

    def test_approval_is_single_use_and_hash_bound(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager = SessionManager(directory)
            manager.initialize(mode="PLANNING_ONLY", interaction_language="zh", session_id="RAS-TEST")
            subject = Path(directory) / "subject.json"
            subject.write_text("{\"value\":1}\n", encoding="utf-8")
            approval = manager.approve_subject("TASK", subject)
            manager.consume_approval(manager.paths.approvals / f"{approval['approval_id']}.json")
            with self.assertRaises(GateError):
                manager.consume_approval(manager.paths.approvals / f"{approval['approval_id']}.json")

    def test_subject_drift_invalidates_approval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager = SessionManager(directory)
            manager.initialize(mode="PLANNING_ONLY", interaction_language="zh", session_id="RAS-TEST")
            subject = Path(directory) / "subject.json"
            subject.write_text("one", encoding="utf-8")
            approval = manager.approve_subject("IDEA", subject)
            subject.write_text("two", encoding="utf-8")
            with self.assertRaises(GateError):
                manager.consume_approval(manager.paths.approvals / f"{approval['approval_id']}.json")

    def test_approval_receipt_tamper_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager = SessionManager(directory)
            manager.initialize(mode="PLANNING_ONLY", interaction_language="zh", session_id="RAS-TEST")
            subject = Path(directory) / "subject.json"
            subject.write_text("one", encoding="utf-8")
            approval = manager.approve_subject("IDEA", subject)
            path = manager.paths.approvals / f"{approval['approval_id']}.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["gate"] = "REAL_ROBOT"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(GateError):
                manager.consume_approval(path)

    def test_pause_and_resume_from_active_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(["git", "init", "-q"], cwd=directory, check=True)
            manager = SessionManager(directory)
            manager.initialize(mode="PLANNING_ONLY", interaction_language="zh", session_id="RAS-TEST")
            subprocess.run(["git", "add", "-A"], cwd=directory, check=True)
            subprocess.run(["git", "-c", "user.email=robotics-ar@test", "-c", "user.name=Robot-AR", "commit", "-qm", "session-init"], cwd=directory, check=True)
            manager.transition("TASK_COMPILATION", "START_TASK")
            manager.pause("user request")
            subprocess.run(["git", "add", "-A"], cwd=directory, check=True)
            subprocess.run(["git", "-c", "user.email=robotics-ar@test", "-c", "user.name=Robot-AR", "commit", "-qm", "pause-checkpoint"], cwd=directory, check=True)
            self.assertEqual(manager.state["state"], "PAUSED")
            manager.resume()
            self.assertEqual(manager.state["state"], "TASK_COMPILATION")
            self.assertFalse((Path(directory) / "robotics-ar" / "report.md").exists())

    def test_active_lock_and_stale_lock(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = SessionManager(directory)
            first.initialize(mode="PLANNING_ONLY", interaction_language="zh", session_id="RAS-ONE")
            with self.assertRaises(SessionError):
                SessionManager(directory).initialize(mode="PLANNING_ONLY", interaction_language="zh", session_id="RAS-TWO")
            first.close()

    def test_environment_receipt_binds_execution_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager = SessionManager(directory)
            manager.initialize(mode="EXECUTION_ENABLED", interaction_language="zh", session_id="RAS-TEST")
            manager.transition("TASK_COMPILATION", "START_TASK")
            manager.transition("AWAITING_TASK_APPROVAL", "TASK_COMPILED")
            manager.transition("IMPLEMENTING", "TASK_APPROVED")
            manager.transition("TESTING", "IMPLEMENTED")
            receipt = {"status": "ONLINE_VERIFIED", "fingerprint": "a" * 64}
            state = manager.enable_execution(receipt)
            self.assertEqual(state["state"], "EXECUTION_READY")
            self.assertEqual(state["environment_fingerprint"], "a" * 64)

    def test_environment_receipt_fingerprint_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager = SessionManager(directory)
            manager.initialize(mode="EXECUTION_ENABLED", interaction_language="zh", session_id="RAS-TEST")
            manager.transition("TASK_COMPILATION", "START_TASK")
            manager.transition("AWAITING_TASK_APPROVAL", "TASK_COMPILED")
            manager.transition("IMPLEMENTING", "TASK_APPROVED")
            manager.transition("TESTING", "IMPLEMENTED")
            with self.assertRaises(SessionError):
                manager.enable_execution({"status": "ONLINE_VERIFIED"})

    def test_resume_rejects_task_hash_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager = SessionManager(directory)
            manager.initialize(mode="PLANNING_ONLY", interaction_language="zh", session_id="RAS-TEST")
            task = manager.compile_task("task", allowed_paths=["src"], forbidden_paths=["raw"], stop_conditions=["budget"])
            manager.pause("user request")
            task_path = Path(task["task_path"])
            data = json.loads(task_path.read_text(encoding="utf-8"))
            data["allowed_paths"] = ["changed"]
            task_path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(SessionError):
                SessionManager(directory).resume()

    def test_dirty_git_detection_is_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(["git", "init", "-q"], cwd=directory, check=True)
            manager = SessionManager(directory)
            self.assertFalse(manager.dirty_git())
            (Path(directory) / "untracked.txt").write_text("change", encoding="utf-8")
            self.assertTrue(manager.dirty_git())


if __name__ == "__main__":
    unittest.main()
