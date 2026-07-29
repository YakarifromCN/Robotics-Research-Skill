import json
import unittest
from pathlib import Path

from common.researchstudio_ideation import run_ideation_chain
from common.researchstudio_patterns import load_pattern_library, validate_pattern_library
from common.robotics_research_context import build_research_context
from scripts.induce_researchstudio_patterns import build as build_clusters
from scripts.validate_researchstudio_idea_card import validate as validate_idea_run
from scripts.validate_robotics_axis_strategy_analysis import validate as validate_axis_report
from scripts.validate_public_paper_index import load as load_public_corpus


ROOT = Path(__file__).resolve().parents[1]


class ResearchStudioInfrastructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library = load_pattern_library()
        cls.signatures = json.loads((ROOT / "corpus" / "researchstudio-paper-signatures.v1.json").read_text(encoding="utf-8"))
        cls.report = json.loads((ROOT / "corpus" / "robotics-axis-strategy-analysis.v1.json").read_text(encoding="utf-8"))
        cls.public = load_public_corpus(ROOT / "corpus" / "public-paper-index.json")
        cls.catalog = json.loads((ROOT / "corpus" / "venue-catalog.v2.json").read_text(encoding="utf-8"))
        cls.model = json.loads((ROOT / "corpus" / "robotics-submanifold.v1.json").read_text(encoding="utf-8"))

    def test_pattern_library_has_15_and_31_cards(self):
        self.assertEqual(validate_pattern_library(self.library), [])
        self.assertEqual(len(self.library["main_patterns"]), 15)
        self.assertEqual(len(self.library["subpatterns"]), 31)

    def test_axis_report_is_balanced_and_has_an_anchor(self):
        errors = validate_axis_report(self.report, self.signatures, self.library, self.public)
        self.assertEqual(errors, [])
        self.assertEqual({row["axis_id"] for row in self.report["axes"]}, set("EPCLDHAS"))
        for row in self.report["axes"]:
            self.assertTrue(row["best_posting_strategy"]["anchor_pattern"]["pattern_id"])
            self.assertEqual(row["data_fidelity"], "METADATA_ONLY")

    def test_pipeline_discloses_fallback_backends(self):
        result = build_clusters()
        self.assertIn(result["method"]["projection"]["status"], {"REAL_UMAP", "FALLBACK_NOT_UMAP"})
        self.assertIn(result["method"]["clustering"]["status"], {"REAL_HDBSCAN", "FALLBACK_NOT_HDBSCAN"})
        self.assertEqual(result["outcome_contrast"]["status"], "DISABLED")

    def test_online_chain_stops_without_grounding(self):
        profile = {"topic_tags": ["robotics", "control"], "submanifold_axes": {"C": 3}}
        base = build_research_context(profile, stage="idea")
        result = run_ideation_chain(profile, base)
        self.assertEqual(result["decision"], "DO_NOT_GENERATE")
        self.assertEqual(validate_idea_run(result), [])


if __name__ == "__main__":
    unittest.main()
