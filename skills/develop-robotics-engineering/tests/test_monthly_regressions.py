"""工程月度回归。 / Engineering monthly regressions."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run_engineering_tests import execute, run
from validate_engineering_artifacts import load_frontmatter, task_contract_sha256
from route_engineering_task import route


class MonthlyEngineeringTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_multiline_yaml(self):
        path = self.root / "task.md"
        path.write_text('---\ntests:\n  - command: "echo ok"\nallowed_paths:\n  - src\n---\nActual task.\n')
        try:
            import yaml
        except ImportError:
            with self.assertRaisesRegex(ValueError, "PyYAML"):
                load_frontmatter(path)
        else:
            data, body = load_frontmatter(path)
            self.assertEqual(data["tests"], [{"command": "echo ok"}])

    def test_env_assignment_and_bounded_output(self):
        row = {"command": f"FIXTURE_VALUE=ok {sys.executable} -c 'import os; print(os.environ[\"FIXTURE_VALUE\"]); print(\"x\"*100000)'"}
        result = execute(row, self.root, limit=1024)
        self.assertTrue(result["stdout"].startswith("ok"))
        self.assertEqual(len(result["stdout"]), 1024)
        self.assertTrue(result["output_truncated"])

    def test_timeout_and_missing_executable_leave_failure(self):
        task = self.root / "task.json"
        task.write_text(json.dumps({"tests": [{"command": f'{sys.executable} -c "import time; time.sleep(2)"'}, {"command": "nonexistent-fixture-executable"}]}))
        results = run(task, self.root, timeout=0.05)
        self.assertEqual([r["result"] for r in results], ["FAIL", "FAIL"])
        self.assertTrue(results[0]["timed_out"])
        self.assertFalse(results[1]["executed"])

    def test_negation_is_clause_scoped(self):
        self.assertNotEqual(route("no real robot; fix build") ["risk_tier"], "T3")
        self.assertNotIn("C", [route("不修改控制器，修复构建")["primary_axis"]])
        self.assertEqual(route("不要运行仿真，但是运行真实机器人")["risk_tier"], "T3")

    def test_typed_roots_enter_contract_digest(self):
        task = {"task_id": "T"}
        before = task_contract_sha256(task)
        task["path_roots"] = {"data": {"path": str(self.root), "access": "external-read", "authorization": "user"}}
        self.assertNotEqual(before, task_contract_sha256(task))

    def test_hidden_argv_and_duplicate_yaml_are_rejected(self):
        with self.assertRaises(ValueError):
            execute({"command": "echo allowed", "argv": ["echo", "different"]}, self.root)
        path = self.root / "duplicate.md"
        path.write_text('---\nstatus: "PASS"\nstatus: "FAIL"\n---\nBody.\n')
        with self.assertRaises(ValueError):
            load_frontmatter(path)

    def test_timeout_stops_grandchild(self):
        import os
        import shlex
        command = "import subprocess,time,pathlib; p=subprocess.Popen([" + repr(sys.executable) + ",'-c','import time; time.sleep(30)']); pathlib.Path('child.pid').write_text(str(p.pid)); time.sleep(30)"
        result = execute({"command": shlex.join([sys.executable, "-c", command])}, self.root, timeout=0.3)
        self.assertTrue(result["timed_out"])
        pid = int((self.root / "child.pid").read_text())
        status = Path(f"/proc/{pid}/status")
        import time
        deadline = time.monotonic() + 1
        while status.exists() and time.monotonic() < deadline:
            if "Z" in status.read_text().split("State:", 1)[1].splitlines()[0]:
                break
            time.sleep(0.01)
        if status.exists():
            self.assertIn("Z", status.read_text().split("State:", 1)[1].splitlines()[0])


if __name__ == "__main__":
    unittest.main()
