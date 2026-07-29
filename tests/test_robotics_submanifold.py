import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common.robotics_submanifold import analyze, load_json, validate_model, venue_vector


CATALOG = load_json(ROOT / "corpus" / "venue-catalog.v1.json")
MODEL = load_json(ROOT / "corpus" / "robotics-submanifold.v1.json")


def venue(venue_id):
    return next(item for item in CATALOG["records"] if item["venue_id"] == venue_id)


class RoboticsSubmanifold(unittest.TestCase):
    def test_model_and_all_catalog_records_are_factorizable(self):
        self.assertEqual(validate_model(MODEL, CATALOG), [])
        vectors = [venue_vector(item, MODEL) for item in CATALOG["records"]]
        self.assertEqual(len(vectors), len(CATALOG["records"]))
        self.assertTrue(all(sum(item["vector"].values()) > 0 for item in vectors))

    def test_axes_separate_learning_hri_and_control(self):
        learning = venue_vector(venue("conf-neurips"), MODEL)["vector"]
        hri = venue_vector(venue("conf-chi"), MODEL)["vector"]
        control = venue_vector(venue("conf-ieee-cdc"), MODEL)["vector"]
        self.assertGreaterEqual(learning["L"], 2)
        self.assertGreaterEqual(hri["H"], 2)
        self.assertGreaterEqual(control["C"], 2)
        self.assertGreater(learning["L"], learning["H"])
        self.assertGreater(hri["H"], hri["C"])
        self.assertGreater(control["C"], control["H"])

    def test_directness_is_a_weight_but_not_a_rating(self):
        direct = venue_vector(venue("journal-t-robotics"), MODEL)
        related = venue_vector(venue("conf-neurips"), MODEL)
        self.assertEqual(direct["directness_weight"], 1.0)
        self.assertEqual(related["directness_weight"], 0.65)

    def test_project_intensity_and_factor_candidates(self):
        profile = {
            "project_id": "P-001",
            "target_kind": "journal",
            "contribution_center": "robotics_core",
            "topic_tags": ["manipulation", "learning", "perception"],
            "claim_shape": {"embodied_system": True, "learning": True, "mechanism": True},
            "domain_packs": ["learning"],
        }
        result = analyze(profile, CATALOG, MODEL, top_k=50)
        self.assertIn(result["research_intensity"]["level"], {"INTEGRATED_SYSTEM", "CROSS_AXIS_SYSTEM"})
        self.assertIn("L", result["project_vector"]["active_axes"])
        self.assertTrue(result["candidates"])
        self.assertNotIn("ratings", result["candidates"][0])
        self.assertEqual(result["infrastructure_status"], "EXPERT_CODED_SEMANTIC_FACTOR_MODEL")


if __name__ == "__main__":
    unittest.main()
