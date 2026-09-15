"""测试 sibling discovery、manifest hash、owner validator 和诚实降级。

Test sibling discovery, manifest hashes, owner validators, and honest fallback.
"""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
import shutil
import subprocess
import json

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/robotics-ar/scripts"))
sys.path.insert(0, str(ROOT))

from robotics_ar_core.sibling_skill_adapter import SiblingAdapterError, SiblingSkillInvocationAdapter
from robotics_ar_core.workflow import STAGE_STATES
from common.contract_core import compute_claim_digest


def ready_card() -> dict:
    """构造 sibling validator 可接受的最小 Research Card。

    Build the smallest Research Card accepted by the sibling validator.
    """

    card = json.loads((ROOT / "skills/develop-robotics-idea/assets/research-card.template.json").read_text(encoding="utf-8"))
    card["status"] = "READY"
    for section in ("claim_contract", "mechanism_contract", "falsification_contract"):
        for key, value in card[section].items():
            if value is None:
                card[section][key] = "bounded scientific statement"
    for obligation in card["evidence_obligations"].values():
        obligation["reason"] = obligation["reason"] or "explicit claim-derived reason"
        obligation["claim_boundary"] = obligation["claim_boundary"] or "scope remains bounded"
    card["deferred_evidence"] = ["evidence collection is frozen downstream"]
    card["collision_audit"] = {"candidate_sha256": "a" * 64, "queries": ["closest mechanism"], "sources": ["P-001"], "comparison_axes": {axis: {"closest_overlap": "same task", "candidate_delta": "different mechanism", "source_ids": ["P-001"], "threat_level": "MEDIUM"} for axis in ("problem_framing", "core_mechanism", "key_insight", "application_or_evaluation")}, "closest_threat_id": "P-001", "uncovered_delta": "mechanism delta", "verdict": "CLEAR"}
    card["claim_digest"] = compute_claim_digest(card)
    return card


class SiblingAdapterTests(unittest.TestCase):
    def test_discover_and_confirm_current_siblings(self) -> None:
        adapter = SiblingSkillInvocationAdapter(ROOT)
        manifest = adapter.discover()
        self.assertEqual(manifest["missing"], [])
        self.assertEqual(set(manifest["siblings"]), {"idea", "experiment", "engineering", "writing", "review"})
        self.assertEqual(manifest["optional_missing"], [])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            adapter.write_manifest(path, manifest)
            confirmed = adapter.confirm_manifest(path, manifest["manifest_sha256"])
            adapter.validate_manifest(confirmed)
            self.assertTrue(confirmed["confirmed_by_user"])

    def test_manifest_hash_drift_is_rejected(self) -> None:
        adapter = SiblingSkillInvocationAdapter(ROOT)
        manifest = adapter.discover()
        manifest["siblings"]["idea"]["skill_sha256"] = "0" * 64
        manifest["confirmed_by_user"] = True
        manifest["manifest_sha256"] = adapter.manifest_hash(manifest)
        with self.assertRaises(SiblingAdapterError):
            adapter.validate_manifest(manifest)

    def test_optional_engineering_absence_does_not_block_confirmation(self) -> None:
        adapter = SiblingSkillInvocationAdapter(ROOT)
        manifest = adapter.discover()
        manifest["siblings"].pop("engineering")
        manifest["optional_missing"] = ["engineering"]
        manifest["manifest_sha256"] = adapter.manifest_hash(manifest)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            adapter.write_manifest(path, manifest)
            confirmed = adapter.confirm_manifest(path, manifest["manifest_sha256"])
            self.assertTrue(confirmed["confirmed_by_user"])
            self.assertEqual(confirmed["optional_missing"], ["engineering"])

    def test_prepare_request_and_runtime_disclosure(self) -> None:
        adapter = SiblingSkillInvocationAdapter(ROOT)
        manifest = adapter.discover()
        manifest["confirmed_by_user"] = True
        manifest["manifest_sha256"] = adapter.manifest_hash(manifest)
        request = adapter.prepare_invocation(manifest, "idea", session_id="RAS-TEST", prompt="inspect", allowed_files=["README.md"])
        self.assertEqual(request["runtime_status"], "REQUEST_ONLY")
        self.assertTrue(request["prompt_sha256"])
        self.assertIn("do not create dot-prefixed directories", request["prompt"])
        self.assertIn("ask the user to confirm", request["prompt"])
        self.assertEqual(adapter.runtime_status("idea", fresh_runtime=False), "SINGLE_AGENT_MODE")
        self.assertEqual(adapter.runtime_status("review", fresh_runtime=False), "BLOCKED_DEPENDENCY")
        self.assertEqual(adapter.runtime_status("review", fresh_runtime=False, manual_review_import=True), "MANUAL_REVIEW_IMPORT")
        engineering = adapter.prepare_invocation(manifest, "engineering", session_id="RAS-TEST", prompt="implement", allowed_files=["README.md"])
        self.assertEqual(engineering["stage"], "engineering")
        self.assertEqual(engineering["execution_mode"], "AUTONOMOUS_WITHIN_APPROVED_TASK")
        self.assertFalse(engineering["requires_additional_user_approval"])
        self.assertFalse(engineering["requires_stage_approval"])
        self.assertNotIn("engineering", STAGE_STATES)

    def test_owner_validator_and_one_repair_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "skill.md").write_text("skill", encoding="utf-8")
            validator = root / "validator.py"
            validator.write_text("import pathlib, sys\np = pathlib.Path(sys.argv[1])\nraise SystemExit(0 if p.read_text() == 'fixed' else 1)\n", encoding="utf-8")
            artifact = root / "artifact.json"
            artifact.write_text("bad", encoding="utf-8")
            adapter = SiblingSkillInvocationAdapter(root)
            manifest = {"schema_version": "robotics-ar-sibling-skills-manifest.v1", "name": "x", "root": root.as_posix(), "confirmed_by_user": True, "siblings": {"idea": {"skill": "skill.md", "validator": "validator.py", "native_artifact": "artifact.json", "skill_sha256": __import__('hashlib').sha256(b'skill').hexdigest(), "validator_sha256": __import__('hashlib').sha256(validator.read_bytes()).hexdigest()}}, "missing": []}
            manifest["manifest_sha256"] = adapter.manifest_hash(manifest)
            calls = []

            def repair() -> None:
                calls.append(True)
                artifact.write_text("fixed", encoding="utf-8")

            result = adapter.validate_native_artifact("idea", artifact, manifest=manifest, repair=repair)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["attempts"], 2)
            self.assertEqual(len(calls), 1)

    def test_direct_sibling_invocation_works_with_and_without_robotics_ar(self) -> None:
        card = ready_card()
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            artifact = project / "research-card.json"
            artifact.write_text(json.dumps(card), encoding="utf-8")
            command = [sys.executable, str(ROOT / "skills/develop-robotics-idea/scripts/validate_research_card.py"), str(artifact), "--ready"]
            result = subprocess.run(command, cwd=project, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((project / "robotics-ar").exists())

        with tempfile.TemporaryDirectory() as directory:
            staged = Path(directory)
            (staged / "skills/develop-robotics-idea").parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(ROOT / "skills/develop-robotics-idea", staged / "skills/develop-robotics-idea")
            shutil.copytree(ROOT / "common", staged / "common")
            artifact = staged / "research-card.json"
            artifact.write_text(json.dumps(card), encoding="utf-8")
            command = [sys.executable, str(staged / "skills/develop-robotics-idea/scripts/validate_research_card.py"), str(artifact), "--ready"]
            result = subprocess.run(command, cwd=staged, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((staged / "skills/robotics-ar").exists())

    def test_missing_required_sibling_is_blocked_by_robotics_ar_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            adapter = SiblingSkillInvocationAdapter(root)
            manifest = adapter.discover()
            self.assertTrue(set(manifest["missing"]))
            path = root / "manifest.json"
            adapter.write_manifest(path, manifest)
            with self.assertRaises(SiblingAdapterError):
                adapter.confirm_manifest(path, manifest["manifest_sha256"])
            self.assertEqual(adapter.runtime_status("review", fresh_runtime=False), "BLOCKED_DEPENDENCY")


if __name__ == "__main__":
    unittest.main()
