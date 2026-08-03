import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from common.robotics_submanifold import analyze, load_json, validate_model, venue_vector


CATALOG = load_json(ROOT / "corpus" / "venue-catalog.v2.json")
MODEL = load_json(ROOT / "corpus" / "robotics-submanifold.v1.json")


def find(venue_id):
    return next(item for item in CATALOG["records"] if item["venue_id"] == venue_id)


class SubmanifoldV1(unittest.TestCase):
    def test_every_supplied_venue_has_a_vector(self):
        self.assertEqual(validate_model(MODEL, CATALOG), [])
        self.assertEqual(len(CATALOG["records"]), 0 if not CATALOG["records"] else len(CATALOG["records"]))
        for record in CATALOG["records"]:
            self.assertGreater(sum(venue_vector(record, MODEL)["vector"].values()), 0, record["venue_id"])

    def test_semantic_axes_are_distinct(self):
        learning = venue_vector(find("conf-neurips"), MODEL)["vector"]
        hri = venue_vector(find("conf-chi"), MODEL)["vector"]
        control = venue_vector(find("conf-ieee-cdc"), MODEL)["vector"]
        self.assertGreaterEqual(learning["L"], 2)
        self.assertGreaterEqual(hri["H"], 2)
        self.assertGreaterEqual(control["C"], 2)
        self.assertGreater(learning["L"], learning["H"])
        self.assertGreater(hri["H"], hri["C"])
        self.assertGreater(control["C"], control["H"])

    def test_direct_venue_priority_is_separate_from_factor_loading(self):
        direct = venue_vector(find("journal-t-robotics"), MODEL)
        related = venue_vector(find("conf-neurips"), MODEL)
        self.assertEqual(direct["directness_weight"], 1.0)
        self.assertEqual(related["directness_weight"], 0.65)

    def test_project_vector_proposes_but_does_not_lock_evidence(self):
        profile = {
            "target_kind": "journal",
            "contribution_center": "robotics_core",
            "topic_tags": ["manipulation", "learning", "perception"],
            "claim_shape": {"embodied_system": True, "learning": True, "mechanism": True},
            "domain_packs": ["learning"],
        }
        result = analyze(profile, CATALOG, MODEL, top_k=20)
        self.assertIn(result["research_intensity"]["level"], {"INTEGRATED_SYSTEM", "CROSS_AXIS_SYSTEM"})
        self.assertTrue(result["research_intensity"]["proposed_evidence_pressures"])
        self.assertEqual(result["infrastructure_status"], "EXPERT_CODED_SEMANTIC_FACTOR_MODEL")
        self.assertNotIn("ratings", result["candidates"][0])


if __name__ == "__main__":
    unittest.main()
