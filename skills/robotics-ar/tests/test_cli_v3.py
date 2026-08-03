"""CLI and migration coverage for Robot-AR v3."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CLI = Path(__file__).resolve().parents[1] / "scripts" / "robotics_ar.py"


class CLIV3Tests(unittest.TestCase):
    def run_cli(self, project: Path, *args: str) -> dict:
        result = subprocess.run([sys.executable, str(CLI), *args, "--project-root", str(project)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        self.assertIn(result.returncode, {0, 2}, result.stderr)
        value = json.loads(result.stdout)
        self.assertIsInstance(value, dict)
        return value

    def test_takeover_commands_and_v2_migration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            project.mkdir()
            initialized = self.run_cli(project, "init", "--entry-mode", "MIDSTREAM_TAKEOVER", "--mode", "PLANNING_ONLY")
            self.assertEqual(initialized["entry_mode"], "MIDSTREAM_TAKEOVER")
            self.assertEqual(self.run_cli(project, "takeover-init")["state"], "TAKEOVER_REQUESTED")
            self.assertEqual(self.run_cli(project, "takeover-status")["state"], "TAKEOVER_REQUESTED")
            migrated = self.run_cli(project, "migrate-v2")
            self.assertEqual(migrated["status"], "PASS")

    def test_new_research_default_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            project.mkdir()
            state = self.run_cli(project, "init", "--mode", "PLANNING_ONLY")
            self.assertEqual(state["entry_mode"], "NEW_RESEARCH")
            dry = self.run_cli(project, "batch-start", "--dry-run")
            self.assertEqual(dry["status"], "DRY_RUN")

    def test_trial_analyze_requires_raw_evidence_and_metric_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            project.mkdir()
            self.run_cli(project, "init", "--mode", "PLANNING_ONLY")
            unversioned = project / "unversioned.json"
            unversioned.write_text(json.dumps({"raw_evidence": {"sha256": "a" * 64}, "metrics": {"score": 1.0}}), encoding="utf-8")
            blocked = self.run_cli(project, "trial-analyze", "--input", str(unversioned))
            self.assertEqual(blocked["status"], "BLOCKED")
            versioned = project / "versioned.json"
            versioned.write_text(json.dumps({"raw_evidence": {"sha256": "a" * 64}, "metrics": {"score": 1.0}, "metric_versions": {"score": "v1"}}), encoding="utf-8")
            passed = self.run_cli(project, "trial-analyze", "--input", str(versioned))
            self.assertEqual(passed["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
