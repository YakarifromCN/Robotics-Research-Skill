import unittest
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RuntimeMinimalityTests(unittest.TestCase):
    def test_stable_contract_and_version_are_synchronized(self):
        contract = json.loads((ROOT / "tests/stable_use_contract.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["release_version"], (ROOT / "VERSION").read_text(encoding="utf-8").strip())
        self.assertEqual(len(contract["dimensions"]), 13)
        self.assertEqual(len(contract["hard_gates"]), 4)
    def test_skill_entrypoints_stay_lean(self):
        for path in (ROOT / "skills").glob("*/SKILL.md"):
            limit = 16_000 if path.parent.name == "robotics-ar" else 8_000
            self.assertLess(path.stat().st_size, limit, path)

    def test_simple_engineering_initial_context_is_bounded(self):
        skill = ROOT / "skills/develop-robotics-engineering"
        simple = (skill / "SKILL.md").stat().st_size + (skill / "references/engineering-modes.md").stat().st_size
        complex_context = simple + (skill / "references/artifact-contract.md").stat().st_size
        self.assertLess(simple, 32_000)          # conservative <8k-token proxy
        self.assertLess(complex_context, 60_000) # conservative <15k-token proxy
        text = (skill / "SKILL.md").read_text(encoding="utf-8").casefold()
        for forbidden in ("corpus/papers", "corpus/extracted", "load every sibling", "读取全部 sibling"):
            self.assertNotIn(forbidden, text)

    def test_stage_skills_cap_progressive_disclosure(self):
        for name in ("develop-robotics-idea", "design-robotics-experiment", "write-robotics-paper", "review-robotic-feedback"):
            text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8").casefold()
            self.assertIn("at most two references", text, name)
            self.assertIn("do not preload sibling skills", text, name)

    def test_runtime_install_excludes_offline_state(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        import local_skill_install as installer
        self.assertIn("tests", installer.RUNTIME_IGNORED_DIRS)
        self.assertFalse(any(item.startswith("corpus/papers") or item.startswith("corpus/extracted") for item in installer.STAGED_SHARED_FILES))


if __name__ == "__main__":
    unittest.main()
