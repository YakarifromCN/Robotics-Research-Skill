"""测试真实机器人 caution 与一次性 token，不连接设备。

Test real-robot caution and one-shot tokens without connecting to a device.
"""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from robotics_ar_core.real_robot import (  # noqa: E402
    OneShotRealRobotToken,
    RealRobotGateError,
    build_caution_document,
    failure_protocol,
    render_caution_markdown,
)


def caution_values() -> dict:
    return {
        "robot": "mock-arm",
        "experiment_id": "exp-1",
        "task": "one batch",
        "controller_or_policy": "fixed controller",
        "expected_motion": "small bounded motion",
        "expected_contact": "none",
        "workspace_boundary": "tabletop",
        "velocity_limits": "low",
        "acceleration_limits": "low",
        "force_limits": "low",
        "torque_limits": "low",
        "episode_count": 1,
        "operator_presence": "present",
        "emergency_stop": "verified",
        "stop_conditions": ["unexpected motion"],
        "data_recording": "enabled",
        "automatic_retry": False,
    }


class RealRobotGateTests(unittest.TestCase):
    def test_caution_document_is_complete_and_bilingual(self) -> None:
        document = build_caution_document(caution_values())
        rendered = render_caution_markdown(document)
        self.assertIn("## 中文", rendered)
        self.assertIn("## English", rendered)
        self.assertEqual(len(document["caution_sha256"]), 64)

    def test_one_shot_token_rejects_replay_drift_and_retry(self) -> None:
        token = OneShotRealRobotToken.issue(task_sha256="a" * 64, environment_sha256="b" * 64, adapter_sha256="c" * 64, safety_limits_sha256="d" * 64, batch_id="batch-1", operator_presence="present")
        binding = dict(token.token["binding"])
        consumed = token.consume(binding=binding)
        self.assertEqual(consumed["status"], "consumed")
        with self.assertRaises(RealRobotGateError):
            token.consume(binding=binding)
        token2 = OneShotRealRobotToken.issue(task_sha256="a" * 64, environment_sha256="b" * 64, adapter_sha256="c" * 64, safety_limits_sha256="d" * 64, batch_id="batch-1", operator_presence="present")
        with self.assertRaises(RealRobotGateError):
            token2.consume(binding={**binding, "batch_id": "batch-2"})
        token3 = OneShotRealRobotToken.issue(task_sha256="a" * 64, environment_sha256="b" * 64, adapter_sha256="c" * 64, safety_limits_sha256="d" * 64, batch_id="batch-1", operator_presence="present")
        with self.assertRaises(RealRobotGateError):
            token3.consume(binding=binding, retry_requested=True)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "token.json"
            persisted = OneShotRealRobotToken.issue(task_sha256="a" * 64, environment_sha256="b" * 64, adapter_sha256="c" * 64, safety_limits_sha256="d" * 64, batch_id="batch-1", operator_presence="present")
            persisted.save(path)
            loaded = OneShotRealRobotToken.load(path)
            loaded.consume(binding=dict(loaded.token["binding"]))
            self.assertEqual(OneShotRealRobotToken.load(path).token["status"], "consumed")

    def test_failure_protocol_writes_receipt_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outcome = failure_protocol(receipt_path=root / "receipt.json", report_path=root / "report.md", reason="stop")
            self.assertEqual(outcome["status"], "STOP_SAVE_PAUSE_REPORT_USER_DECISION")
            self.assertTrue((root / "receipt.json").exists())
            self.assertIn("STOP", (root / "report.md").read_text(encoding="utf-8"))

    def test_token_integrity_tamper_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "token.json"
            token = OneShotRealRobotToken.issue(task_sha256="a" * 64, environment_sha256="b" * 64, adapter_sha256="c" * 64, safety_limits_sha256="d" * 64, batch_id="batch-1", operator_presence="present")
            token.save(path)
            data = json.loads(path.read_text(encoding="utf-8"))
            data["binding"]["batch_id"] = "tampered"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(RealRobotGateError):
                OneShotRealRobotToken.load(path)


if __name__ == "__main__":
    unittest.main()
