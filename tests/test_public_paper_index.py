import json
import unittest
from pathlib import Path

from tools.corpus.validate_public_paper_index import AXES, load, validate


ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "corpus" / "public-paper-index.json"


@unittest.skipUnless(INDEX_PATH.exists(), "local-only raw corpus is not present; run the explicit offline audit")
class PublicPaperIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = load(INDEX_PATH)
        cls.records = cls.index["records"]

    def test_hard_constraints(self):
        self.assertEqual(validate(self.index), [])

    def test_kind_axis_strata_are_balanced(self):
        for kind in ("journal", "conference"):
            counts = {
                axis: sum(record["venue_kind"] == kind and record["primary_axis"] == axis for record in self.records)
                for axis in AXES
            }
            self.assertLessEqual(max(counts.values()) - min(counts.values()), 1)

    def test_direct_robotics_journal_coverage(self):
        venues = {record["venue"] for record in self.records if record["venue_kind"] == "journal"}
        expected = {
            "IEEE Transactions on Robotics",
            "IEEE Robotics and Automation Letters",
            "The International Journal of Robotics Research",
            "Science Robotics",
            "Autonomous Robots",
            "IEEE Robotics and Automation Practice",
            "IEEE Transactions on Haptics",
        }
        self.assertTrue(expected.issubset(venues))

    def test_award_status_is_not_collapsed(self):
        statuses = {record["award"]["status"] for record in self.records if "award" in record}
        self.assertIn("winner", statuses)
        self.assertIn("finalist", statuses)
        self.assertNotEqual(statuses, {"winner"})

    def test_no_duplicate_titles(self):
        titles = [record["title"] for record in self.records]
        self.assertEqual(len(titles), len(set(titles)))


if __name__ == "__main__":
    unittest.main()
