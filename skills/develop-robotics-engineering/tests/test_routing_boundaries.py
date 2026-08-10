"""测试 Engineering 路由、工件闭环与独立运行。

Test Engineering routing, artifact closure, and standalone operation.
"""

from __future__ import annotations

import importlib.util
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills/develop-robotics-engineering/scripts"
sys.path.insert(0, str(SCRIPTS))


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROUTER = load("route_engineering_task")
ARTIFACTS = load("validate_engineering_artifacts")


def description(skill: str) -> str:
    text = (ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
    match = re.search(r"^description:\s*(.+)$", text, re.MULTILINE)
    if not match:
        raise AssertionError(f"missing single-line description: {skill}")
    return match.group(1).casefold()


def write_artifact(path: Path, metadata: dict, body: str = "# Artifact\n\nBounded engineering record.\n") -> None:
    lines = ["---", *(f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in metadata.items()), "---", "", body]
    path.write_text("\n".join(lines), encoding="utf-8")


class RoutingBoundaryTests(unittest.TestCase):
    def test_engineering_positive_and_negative_triggers(self):
        value = description("develop-robotics-engineering")
        for token in ("control", "optimization", "ros", "embedded", "simulation", "deployment", "tuning", "code"):
            self.assertIn(token, value)
        for token in ("do not use for scientific experiment", "research ideation", "paper writing", "autonomous cross-stage"):
            self.assertIn(token, value)

    def test_experiment_explicitly_excludes_engineering(self):
        value = description("design-robotics-experiment")
        for token in ("do not use for code implementation", "ros", "controller", "develop-robotics-engineering"):
            self.assertIn(token, value)

    def test_twenty_four_routing_cases(self):
        cases = (
            ("implement a ROS2 node", "S", "ROS_NODE"),
            ("fix the impedance controller", "C", "CONTROL_LOOP"),
            ("repair convex QP solver infeasible handling", "C", "CONVEX_OPTIMIZER"),
            ("extend dataset data pipeline", "L", "ML_DATA_PIPELINE"),
            ("fix model training loss", "L", "ML_TRAINING"),
            ("deploy model with TensorRT", "L", "MODEL_DEPLOYMENT"),
            ("compile STM32 firmware fallback", "S", "EMBEDDED_FIRMWARE"),
            ("repair camera sensor driver", "P", "SENSOR_DRIVER"),
            ("extend Gazebo simulator", "S", "SIMULATOR_EXTENSION"),
            ("implement actuator hardware interface", "S", "HARDWARE_INTERFACE"),
            ("fix planner state machine recovery", "D", "STATE_MACHINE"),
            ("tune controller gains", "C", "SYSTEM_TUNING"),
            ("repair CMake build tooling", "S", "BUILD_TOOLING"),
            ("update URDF contact model", "E", "BUILD_TOOLING"),
            ("calibrate lidar estimation pipeline", "P", "BUILD_TOOLING"),
            ("fix lifecycle recovery", "A", "STATE_MACHINE"),
            ("implement teleop control mapping", "C", "CONTROL_LOOP"),
            ("ROS realtime control rate watchdog", "C", "ROS_REALTIME_INTERFACE"),
            ("MPC controller constraint", "C", "CONVEX_OPTIMIZER"),
            ("checkpoint inference deploy", "L", "MODEL_DEPLOYMENT"),
            ("Mujoco contact simulator", "E", "SIMULATOR_EXTENSION"),
            ("相机驱动时间戳修复", "P", "SENSOR_DRIVER"),
            ("凸优化求解器约束修改", "C", "CONVEX_OPTIMIZER"),
            ("工程调参增益", "C", "SYSTEM_TUNING"),
        )
        self.assertEqual(len(cases), 24)
        for prompt, axis, mode in cases:
            with self.subTest(prompt=prompt):
                routed = ROUTER.route(prompt)
                self.assertIn(axis, [routed["primary_axis"], *routed["secondary_axes"]])
                self.assertIn(mode, routed["development_modes"])

    def _valid_artifacts(self, root: Path, prompt: str) -> tuple[Path, Path, Path, Path]:
        routed = ROUTER.route(prompt)
        axes = [routed["primary_axis"], *routed["secondary_axes"]]
        base = {"task_id": "ENG-GOLDEN", "language": "en", "axes": axes, "risk_tier": routed["risk_tier"]}
        command = "python3 -m unittest test_component"
        expert = None
        if routed["expert_required"]:
            expert = {"affected_call_path": ["entry -> component"], "critical_interfaces": ["public interface"], "invariants": ["units and fallback"], "smallest_change_locus": ["src/component"], "mandatory_safeguards": ["finite check"], "minimal_tests": [command], "blockers": []}
        plan = root / "plan.md"; task = root / "task.md"; report = root / "report.md"; handoff = root / "handoff.md"
        write_artifact(plan, {**base, "artifact": "PLAN", "status": "DRAFT", "allowed_paths": ["src/component"]})
        task_meta = {**base, "artifact": "TASK", "status": "FROZEN", "development_modes": routed["development_modes"], "original_request": prompt, "allowed_paths": ["src/component"], "forbidden_scope": ["unrelated refactor"], "steps": ["inspect", "implement", "test"], "tests": [{"command": command}], "stop_conditions": ["scope expansion"], "safeguards": (["finite check"] if routed["expert_required"] else ["preserve existing fallback"]), "expert_required": routed["expert_required"], "expert_brief": expert, "device_actions": [], "real_device_authorized": False}
        write_artifact(task, task_meta)
        bound = {"command": command, "result": "PASS", "exit_code": 0}
        receipt = {**bound, "executed": True, "receipt_sha256": hashlib.sha256(json.dumps(bound, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}
        task_hash = ARTIFACTS.task_contract_sha256(task_meta)
        write_artifact(report, {**base, "artifact": "REPORT", "status": "DONE", "task_contract_sha256": task_hash, "changed_files": ["src/component/implementation.py"], "tests": [receipt]})
        write_artifact(handoff, {**base, "artifact": "HANDOFF", "status": "DONE", "task_contract_sha256": task_hash, "changed_files": ["src/component/implementation.py"], "tests": [receipt], "resume_command": None})
        return plan, task, report, handoff

    def test_six_end_to_end_engineering_golden_cases(self):
        prompts = ("ROS node modification", "controller bug", "convex solver constraint", "model deploy TensorRT", "STM32 firmware fallback", "controller gain tuning")
        with tempfile.TemporaryDirectory() as directory:
            for index, prompt in enumerate(prompts):
                root = Path(directory) / str(index); root.mkdir()
                paths = self._valid_artifacts(root, prompt)
                with self.subTest(prompt=prompt):
                    self.assertEqual(ARTIFACTS.validate_paths(*paths)["errors"], [])

    def test_artifact_validator_rejects_empty_shell_and_test_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self._valid_artifacts(Path(directory), "ROS node modification")
            report, _ = ARTIFACTS.load_frontmatter(paths[2])
            report["tests"] = [{"command": "true", "result": "PASS", "executed": True, "exit_code": 0, "receipt_sha256": "a" * 64}]
            write_artifact(paths[2], report)
            result = ARTIFACTS.validate_paths(*paths)
            self.assertFalse(result["valid"])
            self.assertTrue(any("frozen commands" in error for error in result["errors"]))

    def test_done_handoff_allows_null_resume_but_empty_shell_is_not_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "handoff.md"
            path.write_text("# Current changed tests next step resume\nDONE\n```bash\n\n```\n", encoding="utf-8")
            result = subprocess.run([sys.executable, str(SCRIPTS / "validate_engineering_handoff.py"), str(path)], text=True, capture_output=True, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((Path(directory) / ".robotics-ar").exists())

    def test_real_device_action_requires_authorization(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self._valid_artifacts(Path(directory), "STM32 firmware fallback")
            task, _ = ARTIFACTS.load_frontmatter(paths[1]); task["device_actions"] = ["flash"]
            write_artifact(paths[1], task)
            self.assertFalse(ARTIFACTS.validate_paths(*paths)["valid"])
            paths = self._valid_artifacts(Path(directory), "controller bug")
            report, _ = ARTIFACTS.load_frontmatter(paths[2]); report["changed_files"] = ["unrelated/framework.py"]
            write_artifact(paths[2], report)
            self.assertFalse(ARTIFACTS.validate_paths(*paths)["valid"])

    def test_empty_bodies_and_forged_pass_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self._valid_artifacts(Path(directory), "ROS node modification")
            for path in paths:
                metadata, _ = ARTIFACTS.load_frontmatter(path)
                write_artifact(path, metadata, body="")
            self.assertFalse(ARTIFACTS.validate_paths(*paths)["valid"])
            paths = self._valid_artifacts(Path(directory), "ROS node modification")
            report, _ = ARTIFACTS.load_frontmatter(paths[2])
            report["tests"][0]["exit_code"] = 1
            write_artifact(paths[2], report)
            self.assertFalse(ARTIFACTS.validate_paths(*paths)["valid"])


if __name__ == "__main__":
    unittest.main()
