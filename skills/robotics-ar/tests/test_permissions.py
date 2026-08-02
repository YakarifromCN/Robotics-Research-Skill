"""测试执行 Agent 的路径、raw 和 receipt 隔离。

Test execution-agent path, raw, and receipt isolation.
"""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from robotics_ar_core.agent_protocol import (  # noqa: E402
    AgentProtocolError,
    PathPolicy,
    RawEvidenceGuard,
    WriterLease,
    build_expert_profiles,
    make_agent_receipt,
    synthesize_expert_rounds,
)


class PermissionTests(unittest.TestCase):
    def test_allowed_path_guard_rejects_escape_and_forbidden(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            policy = PathPolicy.create(root, allowed_paths=["src", "tests"], forbidden_paths=["raw"])
            self.assertEqual(policy.check("src/main.py").name, "main.py")
            with self.assertRaises(AgentProtocolError):
                policy.assert_write("raw/result.json")
            with self.assertRaises(AgentProtocolError):
                policy.check("../outside")

    def test_raw_evidence_is_immutable_after_freeze(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory) / "raw"
            raw.mkdir()
            path = raw / "result.json"
            path.write_text("{\"x\":1}\n", encoding="utf-8")
            guard = RawEvidenceGuard(raw)
            guard.freeze([path])
            guard.assert_unchanged()
            path.write_text("{\"x\":2}\n", encoding="utf-8")
            with self.assertRaises(AgentProtocolError):
                guard.assert_unchanged()

    def test_single_writer_lease_and_honest_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = WriterLease(directory, "code-1")
            second = WriterLease(directory, "code-2")
            first.acquire()
            with self.assertRaises(AgentProtocolError):
                second.acquire()
            first.release()
            second.acquire()
            second.release()
        with self.assertRaises(AgentProtocolError):
            make_agent_receipt("Dynamic Expert", "TASK-1", allowed_paths=["unknown"], status="PASS", fresh_runtime=False)
        with self.assertRaises(AgentProtocolError):
            make_agent_receipt("Code Agent", "TASK-1", allowed_paths=["src"], status="PASS", fresh_runtime=False)
        fallback = make_agent_receipt("Code Agent", "TASK-1", allowed_paths=["src"], status="SINGLE_AGENT_MODE", fresh_runtime=False)
        self.assertEqual(fallback["runtime_status"], "SINGLE_AGENT_MODE")
        receipt = make_agent_receipt("Dynamic Expert", "TASK-1", allowed_paths=["unknown"], status="PASS", fresh_runtime=True)
        self.assertEqual(receipt["runtime_status"], "FRESH_RUNTIME")

    def test_expert_profiles_are_two_round_bounded(self) -> None:
        profiles = build_expert_profiles(2)
        first = [{"next_action_id": "A1", "decision": "ACCEPT_NEXT_ACTION"} for _ in profiles]
        second = [{"next_action_id": "A1", "decision": "ACCEPT_WITH_CONSTRAINTS"} for _ in profiles]
        result = synthesize_expert_rounds(profiles, first, second)
        self.assertEqual(result["rounds"], 2)
        self.assertEqual(result["next_action_id"], "A1")
        conflict = synthesize_expert_rounds(profiles, [{"next_action_id": "A1"}, {"next_action_id": "A2"}])
        self.assertEqual(conflict["status"], "CRITICAL_BLOCK")


if __name__ == "__main__":
    unittest.main()
