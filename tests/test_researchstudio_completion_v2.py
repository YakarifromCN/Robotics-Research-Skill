from __future__ import annotations

import json
import unittest
from pathlib import Path

from common.robotics_research_runtime import load_runtime


ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class ResearchStudioCompletionV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime = load_runtime()
        cls.induction = load("corpus/researchstudio-pattern-induction.v2.json")
        cls.axis = load("corpus/robotics-axis-strategy-analysis.v2.json")
        cls.outcome = load("corpus/researchstudio-outcome-contrast.v1.json")

    def test_runtime_projection_is_explicit(self) -> None:
        self.assertEqual(self.runtime["source"]["record_count"], 100)
        self.assertEqual(self.runtime["runtime_contract"]["exemplar_count_per_axis"], 4)
        self.assertFalse(self.runtime["source"]["raw_corpus_loaded_at_runtime"])
        self.assertEqual(len(self.runtime["paper_exemplars_by_axis"]), 8)

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

    def test_four_skills_use_progressive_stage_context(self) -> None:
        self.assertTrue((ROOT / "references/unified-venue-workflow-adapter.v1.md").is_file())
        for skill in (
            "develop-robotics-idea",
            "design-robotics-experiment",
            "write-robotics-paper",
            "review-robotic-feedback",
        ):
            text = (ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8").casefold()
            self.assertIn("at most two references", text)
            self.assertIn("do not preload sibling skills", text)


if __name__ == "__main__":
    unittest.main()
