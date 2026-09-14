"""隔离安装与依赖闭包回归。 / Isolated installation and dependency-closure regressions."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import local_skill_install as installer
from build_release_bundle import runtime_files


class MonthlyInstallationTests(unittest.TestCase):
    def test_four_modes_preserve_runtime_from_unrelated_cwd(self):
        with tempfile.TemporaryDirectory(prefix="rrs-install-regression-") as temporary:
            base = Path(temporary)
            source = base / "source"
            for path in runtime_files(ROOT):
                target = source / path.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
            subprocess.run(["git", "init", "-q", str(source)], check=True)
            subprocess.run(["git", "add", "."], cwd=source, check=True)
            subprocess.run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture"], cwd=source, check=True)
            archive = base / "runtime.zip"
            profile = base / "profile.json"
            profile.write_text(json.dumps({"task": "control under bounded disturbances", "active_axes": ["C"]}))
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
                for path in source.rglob("*"):
                    if path.is_file() and ".git" not in path.relative_to(source).parts:
                        output.write(path, "runtime/" + path.relative_to(source).as_posix())
            self.assertLess(archive.stat().st_size, 5 * 1024 * 1024)
            for mode in installer.MODES:
                with self.subTest(mode=mode):
                    dest = base / mode
                    args = ["--dest", str(dest), "--mode", mode, "--purpose", "development" if mode == "SYMLINK_TRACKED_CLONE" else "use"]
                    if mode == "DIRECT_DOWNLOAD":
                        args += ["--archive-url", archive.as_uri()]
                    else:
                        args += ["--source-root", str(source)]
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        code = installer.main_install(args)
                    self.assertEqual(code, 0, output.getvalue())
                    hidden = base / "hidden-source"
                    if mode != "SYMLINK_TRACKED_CLONE":
                        source.rename(hidden)
                    try:
                        for skill in ("develop-robotics-idea", "design-robotics-experiment", "write-robotics-paper", "review-robotic-feedback"):
                            result = subprocess.run([sys.executable, "-B", str(dest / skill / "scripts" / "route_robotics_research.py"), str(profile)], cwd=base, capture_output=True, text=True)
                            self.assertEqual(result.returncode, 0, result.stderr)
                            self.assertFalse(json.loads(result.stdout)["routing_contract"]["raw_corpus_loaded"])
                        env = {**os.environ, "CODEX_HOME": str(base / "empty-codex")}
                        result = subprocess.run([sys.executable, "-B", str(dest / "write-robotics-paper" / "scripts" / "resolve_humanizer.py")], cwd=base, env=env, capture_output=True, text=True)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(json.loads(result.stdout)["kind"], "bundled-adaptation")
                        for skill, script in (("develop-robotics-engineering", "run_engineering_tests.py"), ("robotics-ar", "robotics_ar.py")):
                            result = subprocess.run([sys.executable, "-B", str(dest / skill / "scripts" / script), "--help"], cwd=base, capture_output=True, text=True)
                            self.assertEqual(result.returncode, 0, result.stderr)
                    finally:
                        if hidden.exists():
                            hidden.rename(source)


if __name__ == "__main__":
    unittest.main()
