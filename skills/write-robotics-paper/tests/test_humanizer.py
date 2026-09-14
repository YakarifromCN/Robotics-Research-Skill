"""语言修订不变量回归。 / Prose revision invariant regressions."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_prose_invariants import audit
from resolve_humanizer import resolve


class HumanizerTests(unittest.TestCase):
    def test_bilingual_edit_and_keep_pairs(self):
        cases = json.loads((ROOT / "tests" / "humanizer-fixtures.json").read_text())["cases"]
        self.assertEqual(len(cases), 24)
        for row in cases:
            for language in ("zh", "en"):
                before, after = row[language]["before"], row[language]["after"]
                self.assertTrue(audit(before, after)["mechanical_invariants_match"], row["id"])
                if row["action"] == "KEEP":
                    self.assertEqual(before, after)

    def test_detects_state_number_and_citation_drift(self):
        for before, after in (("INCONCLUSIVE", "SUPPORTED"), ("3 trials", "30 trials"), (r"\cite{a}", r"\cite{b}")):
            self.assertFalse(audit(before, after)["mechanical_invariants_match"])

    def test_bundled_offline_resolution_does_not_claim_language_pass(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"CODEX_HOME": directory}):
            receipt = resolve()
            self.assertEqual(receipt["kind"], "bundled-adaptation")
            self.assertFalse(receipt["language_pass_completed"])


if __name__ == "__main__":
    unittest.main()
