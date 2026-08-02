"""测试环境 manifest、ONLINE_VERIFIED gate 和安全执行规则。

Test environment manifests, the ONLINE_VERIFIED gate, and safe execution rules.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from robotics_ar_core.environment import EnvironmentAdapter, EnvironmentError
from robotics_ar_core.process_registry import ProcessRegistry
from robotics_ar_core.receipts import file_sha256


MOCK = Path(__file__).resolve().parents[1] / "assets" / "mock-environment" / "adapter.py"


def make_manifest(root: Path) -> Path:
    shutil.copy2(MOCK, root / "adapter.py")
    manifest = {
        "schema_version": "robotics-ar-environment.v1",
        "id": "test-mock",
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


class EnvironmentTests(unittest.TestCase):
    def test_online_verification_and_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = make_manifest(Path(directory))
            adapter = EnvironmentAdapter.from_file(path)
            receipt = adapter.verify_online()
            self.assertEqual(receipt["status"], "ONLINE_VERIFIED")
            self.assertEqual(len(receipt["checks"]["stop"]), 2)
            self.assertEqual(receipt["fingerprint"], adapter.fingerprint())

    def test_planning_only_and_missing_receipt_block_batch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            adapter = EnvironmentAdapter.from_file(make_manifest(Path(directory)))
            with self.assertRaises(EnvironmentError):
                adapter.run_batch("PLANNING_ONLY", None, request={"x": 1})
            with self.assertRaises(EnvironmentError):
                adapter.run_batch("EXECUTION_ENABLED", None, request={"x": 1})

    def test_path_escape_and_shell_string_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = make_manifest(Path(directory))
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["io"]["result_dir"] = "../escape"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(EnvironmentError):
                EnvironmentAdapter.from_file(path).validate_manifest()
        with tempfile.TemporaryDirectory() as directory:
            path = make_manifest(Path(directory))
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["commands"]["health_check"] = "python3 adapter.py health-check"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(EnvironmentError):
                EnvironmentAdapter.from_file(path).validate_manifest()

    def test_adapter_hash_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = make_manifest(root)
            (root / "adapter.py").write_text((root / "adapter.py").read_text(encoding="utf-8") + "\n# drift\n", encoding="utf-8")
            with self.assertRaises(EnvironmentError):
                EnvironmentAdapter.from_file(path).validate_manifest()

    def test_invalid_executable_and_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = make_manifest(Path(directory))
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["commands"]["health_check"] = ["sh", "-c", "echo bad"]
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(EnvironmentError):
                EnvironmentAdapter.from_file(path).validate_manifest()

    def test_timeout_invalid_result_and_process_stop_are_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = make_manifest(root)
            slow = root / "slow.py"
            slow.write_text("import time; time.sleep(2)\n", encoding="utf-8")
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["commands"]["health_check"] = ["python3", "slow.py"]
            path.write_text(json.dumps(manifest), encoding="utf-8")
            result = EnvironmentAdapter.from_file(path).run_argv(["python3", "slow.py"], label="slow", timeout_s=0.05)
            self.assertEqual(result["status"], "TIMEOUT")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = make_manifest(root)
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["commands"]["health_check"] = ["python3", "-c", "print('not-json')"]
            path.write_text(json.dumps(manifest), encoding="utf-8")
            adapter = EnvironmentAdapter.from_file(path)
            result = adapter.run_argv(manifest["commands"]["health_check"], label="bad-json")
            with self.assertRaises(EnvironmentError):
                adapter._json_output(result, "bad-json")
            receipt = adapter.verify_online()
            self.assertEqual(receipt["status"], "BLOCKED_ENVIRONMENT")

    def test_fingerprint_drift_blocks_batch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = make_manifest(Path(directory))
            adapter = EnvironmentAdapter.from_file(path)
            receipt = adapter.verify_online()
            adapter.manifest["limits"]["timeout_s"] = 11
            with self.assertRaises(EnvironmentError):
                adapter.run_batch("EXECUTION_ENABLED", receipt, request={"batch": 1})
            stop = ProcessRegistry(Path(directory) / "processes.json").stop(999999)
            self.assertEqual(stop["status"], "ALREADY_STOPPED")


if __name__ == "__main__":
    unittest.main()
