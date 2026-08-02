#!/usr/bin/env python3
"""安装模式的回归测试。 / Regression tests for the local installation modes."""

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import local_skill_install as installer  # noqa: E402


class LocalSkillInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="robotics-install-test-")
        self.root = Path(self.temp.name)
        self.source = self.root / "repo"
        self.dest = self.root / "codex" / "skills"
        self.receipt = self.dest / ".robotics-research-install.json"
        self._create_repo()

    def tearDown(self):
        self.temp.cleanup()

    def _git(self, *args):
        return subprocess.run(["git", *args], cwd=self.source, check=True, capture_output=True, text=True)

    def _create_repo(self):
        skill = self.source / "skills" / "demo-skill"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("# Demo Skill\n\nInitial\n", encoding="utf-8")
        (skill / "check.py").write_text("print('ok')\n", encoding="utf-8")
        common = self.source / "common"
        common.mkdir()
        (common / "canonical_json.py").write_text("VALUE = True\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=self.source, check=True)
        self._git("config", "user.email", "tests@example.invalid")
        self._git("config", "user.name", "Install Tests")
        self._git("add", ".")
        self._git("commit", "-q", "-m", "initial")
        self._git("branch", "-M", "main")

    def _install(self, *extra):
        args = [
            "--source-root",
            str(self.source),
            "--dest",
            str(self.dest),
            "--manifest",
            str(self.receipt),
            *extra,
        ]
        self.assertEqual(installer.main_install(args), 0)
        return json.loads(self.receipt.read_text(encoding="utf-8"))

    def _update(self, *extra):
        args = [
            "--install-receipt",
            str(self.receipt),
            "--ff-only",
            "--no-fetch",
            *extra,
        ]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = installer.main_update(args)
        payload = json.loads(output.getvalue())
        return code, payload

    def _update_with_fetch(self, *extra):
        args = [
            "--install-receipt",
            str(self.receipt),
            "--ff-only",
            "--fetch",
            *extra,
        ]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = installer.main_update(args)
        payload = json.loads(output.getvalue())
        return code, payload

    def _commit_change(self, text):
        (self.source / "skills" / "demo-skill" / "SKILL.md").write_text(text, encoding="utf-8")
        self._git("add", ".")
        self._git("commit", "-q", "-m", "update")

    def test_development_auto_uses_live_symlink_and_updates_receipt(self):
        manifest = self._install("--purpose", "development")
        installed = self.dest / "demo-skill"
        self.assertEqual(manifest["mode"], "SYMLINK_TRACKED_CLONE")
        self.assertTrue(installed.is_symlink())
        self.assertEqual(installed.resolve(), (self.source / "skills" / "demo-skill").resolve())

        self._commit_change("# Demo Skill\n\nUpdated\n")
        code, payload = self._update("--run-fast-checks")
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "UPDATED")
        self.assertEqual((installed / "SKILL.md").read_text(encoding="utf-8").splitlines()[-1], "Updated")

    def test_use_auto_uses_safe_staged_release(self):
        manifest = self._install("--purpose", "use")
        installed = self.dest / "demo-skill"
        self.assertEqual(manifest["mode"], "SAFE_STAGED_WORKTREE")
        self.assertTrue(installed.is_symlink())
        self.assertNotEqual(installed.resolve(), (self.source / "skills" / "demo-skill").resolve())
        first_target = installed.resolve()
        self.assertTrue((first_target.parent.parent / "common" / "canonical_json.py").is_file())

        self._commit_change("# Demo Skill\n\nSecond release\n")
        code, payload = self._update("--run-fast-checks")
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "UPDATED")
        self.assertNotEqual(installed.resolve(), first_target)
        self.assertIn("Second release", (installed / "SKILL.md").read_text(encoding="utf-8"))

    def test_safe_staged_install_rejects_uncommitted_source(self):
        (self.source / "skills" / "demo-skill" / "SKILL.md").write_text("uncommitted\n", encoding="utf-8")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = installer.main_install(
                [
                    "--source-root",
                    str(self.source),
                    "--dest",
                    str(self.dest),
                    "--manifest",
                    str(self.receipt),
                    "--purpose",
                    "use",
                    "--mode",
                    "SAFE_STAGED_WORKTREE",
                ]
            )
        self.assertEqual(code, 2)
        self.assertIn("clean source worktree", json.loads(output.getvalue())["error"])

    def test_fetch_mode_fast_forwards_when_origin_is_ahead(self):
        self._install("--purpose", "use")
        bare = self.root / "origin.git"
        subprocess.run(["git", "init", "--bare", "-q", str(bare)], check=True, capture_output=True)
        self._git("remote", "add", "origin", str(bare))
        self._git("push", "-q", "-u", "origin", "main")
        producer = self.root / "producer"
        subprocess.run(["git", "clone", "-q", "-b", "main", str(bare), str(producer)], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "producer@example.invalid"], cwd=producer, check=True)
        subprocess.run(["git", "config", "user.name", "Producer"], cwd=producer, check=True)
        (producer / "skills" / "demo-skill" / "SKILL.md").write_text("# Demo Skill\n\nRemote release\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=producer, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-q", "-m", "remote update"], cwd=producer, check=True, capture_output=True)
        subprocess.run(["git", "push", "-q"], cwd=producer, check=True, capture_output=True)
        code, payload = self._update_with_fetch("--run-fast-checks")
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "UPDATED")
        self.assertIn("Remote release", (self.dest / "demo-skill" / "SKILL.md").read_text(encoding="utf-8"))

    def test_copy_pinned_is_not_updatable(self):
        manifest = self._install("--purpose", "use", "--mode", "COPY_PINNED")
        self.assertEqual(manifest["mode"], "COPY_PINNED")
        self.assertFalse((self.dest / "demo-skill").is_symlink())
        code, payload = self._update()
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "NOT_UPDATABLE")

    def test_direct_download_is_a_pinned_archive_install(self):
        archive = self.root / "release.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr("release/skills/demo-skill/SKILL.md", "# Downloaded\n")
            bundle.writestr("release/skills/demo-skill/check.py", "print('downloaded')\n")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = installer.main_install(
                [
                    "--archive-url",
                    archive.as_uri(),
                    "--dest",
                    str(self.dest),
                    "--manifest",
                    str(self.receipt),
                    "--purpose",
                    "use",
                ]
            )
        self.assertEqual(code, 0)
        manifest = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual(manifest["mode"], "DIRECT_DOWNLOAD")
        self.assertIsNone(manifest["source_root"])
        self.assertIsNotNone(manifest["archive_sha256"])
        self.assertFalse((self.dest / "demo-skill").is_symlink())
        self.assertIn("Downloaded", (self.dest / "demo-skill" / "SKILL.md").read_text(encoding="utf-8"))

    def test_dirty_source_blocks_tracked_update(self):
        self._install("--purpose", "development")
        (self.source / "skills" / "demo-skill" / "SKILL.md").write_text("dirty\n", encoding="utf-8")
        code, payload = self._update()
        self.assertEqual(code, 2)
        self.assertEqual(payload["status"], "ERROR")
        self.assertIn("dirty", payload["error"])

    def test_active_robotics_ar_session_blocks_update(self):
        self._install("--purpose", "development")
        session_root = self.root / "session"
        lock = session_root / ".robotics-ar" / "session.lock"
        lock.parent.mkdir(parents=True)
        lock.write_text("active\n", encoding="utf-8")
        manifest = json.loads(self.receipt.read_text(encoding="utf-8"))
        manifest["active_session_roots"] = [str(session_root)]
        self.receipt.write_text(json.dumps(manifest), encoding="utf-8")
        code, payload = self._update()
        self.assertEqual(code, 2)
        self.assertEqual(payload["status"], "ERROR")
        self.assertIn("active session lock", payload["error"])

    def test_doctor_reports_live_install(self):
        self._install("--purpose", "development")
        report = installer.doctor(self.receipt)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["mode"], "SYMLINK_TRACKED_CLONE")


if __name__ == "__main__":
    unittest.main()
