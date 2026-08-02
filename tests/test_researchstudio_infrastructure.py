import json
import unittest
from pathlib import Path

from common.researchstudio_ideation import run_ideation_chain
from common.researchstudio_patterns import load_pattern_library, validate_pattern_library
from common.robotics_research_runtime import AXES, load_runtime, validate_runtime
from common.robotics_research_context import build_research_context
from scripts.validate_researchstudio_idea_card import validate as validate_idea_run


ROOT = Path(__file__).resolve().parents[1]


class ResearchStudioInfrastructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library = load_pattern_library()
        cls.runtime = load_runtime()

    def test_pattern_library_has_15_and_31_cards(self):
        self.assertEqual(validate_pattern_library(self.library), [])
        self.assertEqual(len(self.library["main_patterns"]), 15)
        self.assertEqual(len(self.library["subpatterns"]), 31)

    def test_runtime_is_valid_and_covers_all_axes(self):
        self.assertEqual(validate_runtime(self.runtime), [])
        self.assertEqual(set(self.runtime["paper_exemplars_by_axis"]), set(AXES))
        self.assertEqual(set(self.runtime["axis_strategy_by_axis"]), set(AXES))
        self.assertTrue(all(self.runtime["paper_exemplars_by_axis"][axis] for axis in AXES))
        self.assertEqual(self.runtime["source"]["raw_corpus_loaded_at_runtime"], False)

    def test_runtime_keeps_strategy_and_outcome_boundaries(self):
        self.assertEqual(self.runtime["pattern_system"]["parent_cards"], 15)
        self.assertEqual(self.runtime["pattern_system"]["subpattern_cards"], 31)
        self.assertEqual(self.runtime["outcome_contract"]["acceptance_probability"], "NOT_ESTIMABLE")
        self.assertEqual(
            self.runtime["source"]["source_path_policy"],
            "local_only_not_committed",
        )

    def test_online_chain_stops_without_grounding(self):
        profile = {"topic_tags": ["robotics", "control"], "submanifold_axes": {"C": 3}}
        base = build_research_context(profile, stage="idea")
        result = run_ideation_chain(profile, base)
        self.assertEqual(result["decision"], "DO_NOT_GENERATE")
        self.assertEqual(validate_idea_run(result), [])


if __name__ == "__main__":
    unittest.main()
