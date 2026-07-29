from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class ResearchStudioCompletionV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.signatures = load("corpus/researchstudio-paper-signatures.v2.json")
        cls.induction = load("corpus/researchstudio-pattern-induction.v2.json")
        cls.axis = load("corpus/robotics-axis-strategy-analysis.v2.json")
        cls.outcome = load("corpus/researchstudio-outcome-contrast.v1.json")

    def test_mixed_fidelity_signature_coverage_is_explicit(self) -> None:
        self.assertEqual(self.signatures["record_count"], 100)
        self.assertEqual(
            self.signatures["fidelity_counts"],
            {"FULLTEXT_EXTRACTED": 81, "METADATA_FALLBACK": 19},
        )
        self.assertEqual(len({row["paper_id"] for row in self.signatures["records"]}), 100)

    def test_simulated_induction_covers_complete_card_vocabulary(self) -> None:
        self.assertEqual(self.induction["coverage"], {
            "cluster_count": 8,
            "parent_cards": 15,
            "subpattern_cards": 31,
        })
        self.assertFalse(self.induction["simulation_boundary"]["real_clustering_claim"])

    def test_eight_axis_strategy_is_regenerated(self) -> None:
        self.assertEqual({row["axis_id"] for row in self.axis["axes"]}, set("EPCLDHAS"))
        self.assertEqual(self.axis["acceptance_probability"], "NOT_ESTIMABLE")
        self.assertTrue(
            all(row["official_scope_status"] == "REFRESH_REQUIRED" for row in self.axis["axes"])
        )

    def test_outcome_gap_is_closed_without_fabrication(self) -> None:
        self.assertEqual(self.outcome["status"], "CLOSED_NO_DECISION_ALIGNED_DATA")
        self.assertFalse(self.outcome["runtime_behavior"]["contrast_enabled"])
        self.assertEqual(self.outcome["runtime_behavior"]["acceptance_probability"], "NOT_ESTIMABLE")

    def test_four_skills_reference_the_shared_adapter(self) -> None:
        for skill in (
            "develop-robotics-idea",
            "design-robotics-experiment",
            "write-robotics-paper",
            "review-robotic-feedback",
        ):
            text = (ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("references/unified-venue-workflow-adapter.v1.md", text)


if __name__ == "__main__":
    unittest.main()
