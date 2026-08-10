"""测试轻量发行包的大小、内容边界和可重建清单。

Test release bundle sizes, content boundaries, and reproducible manifests.
"""

from __future__ import annotations

import importlib.util
import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("release_builder", ROOT / "scripts/build_release_bundle.py")
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)
import local_skill_install as INSTALLER


class ReleaseBundleTests(unittest.TestCase):
    def test_runtime_and_developer_bundles_are_small_and_clean(self):
        with tempfile.TemporaryDirectory() as directory:
            result = BUILDER.build(ROOT, Path(directory), allow_dirty=True)
            self.assertLess(result["runtime"]["archive_bytes"], 5 * 1024 * 1024)
            self.assertLess(result["developer"]["archive_bytes"], 20 * 1024 * 1024)
            for name in ("runtime.zip", "developer.zip"):
                with zipfile.ZipFile(Path(directory) / name) as archive:
                    members = archive.namelist()
                    self.assertTrue(any(item.endswith("release-manifest.json") for item in members))
                    for forbidden in ("/.git/", "/agent/", "/corpus/papers/", "/corpus/extracted/", "/__pycache__/", ".pyc"):
                        self.assertFalse(any(forbidden in item for item in members), forbidden)
                    manifest = json.loads(archive.read(next(item for item in members if item.endswith("release-manifest.json"))))
                    self.assertEqual(manifest["version"], (ROOT / "VERSION").read_text().strip())
                    self.assertEqual(manifest["source_dirty"], result["dirty_source"])

    def test_runtime_zip_direct_download_preserves_shared_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); bundles = root / "bundles"; dest = root / "codex/skills"; receipt = root / "receipt.json"
            BUILDER.build(ROOT, bundles, allow_dirty=True)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = INSTALLER.main_install(["--archive-url", (bundles / "runtime.zip").as_uri(), "--dest", str(dest), "--manifest", str(receipt), "--purpose", "use"])
            self.assertEqual(code, 0, output.getvalue())
            manifest = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(manifest["mode"], "DIRECT_DOWNLOAD")
            engineering = dest / "develop-robotics-engineering"
            self.assertTrue(engineering.is_symlink())
            release_root = engineering.resolve().parent.parent
            self.assertTrue((release_root / "common/canonical_json.py").is_file())
            self.assertTrue((release_root / "corpus/researchstudio-pattern-cards.v1.json").is_file())
            self.assertEqual(manifest["version"], (ROOT / "VERSION").read_text().strip())
            self.assertIsInstance(manifest["source_dirty"], bool)
            self.assertRegex(manifest["content_tree_sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(manifest["release_manifest"]["content_tree_sha256"], r"^[0-9a-f]{64}$")

    def test_clean_checkout_builds_and_installs_reproducibly(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); checkout = base / "checkout"; bundles = base / "dist"
            shutil.copytree(ROOT, checkout, ignore=shutil.ignore_patterns(".git", "dist", "agent", "papers", "extracted", "__pycache__", "*.pyc"))
            subprocess.run(["git", "init", "-q"], cwd=checkout, check=True)
            subprocess.run(["git", "add", "-A"], cwd=checkout, check=True)
            subprocess.run(["git", "-c", "user.name=Stable Test", "-c", "user.email=stable@example.invalid", "commit", "-qm", "stable fixture"], cwd=checkout, check=True)
            result = BUILDER.build(checkout, bundles)
            self.assertFalse(result["dirty_source"])
            with zipfile.ZipFile(bundles / "runtime.zip") as archive:
                manifest = json.loads(archive.read(next(name for name in archive.namelist() if name.endswith("release-manifest.json"))))
            self.assertFalse(manifest["source_dirty"])
            self.assertEqual(manifest["head_commit"], subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=checkout, text=True).strip())


if __name__ == "__main__":
    unittest.main()
