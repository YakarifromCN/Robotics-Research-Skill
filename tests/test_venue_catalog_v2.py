import json
import unittest
from pathlib import Path

from scripts.validate_venue_catalog_v2 import validate


ROOT = Path(__file__).resolve().parents[1]


class VenueCatalogV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((ROOT / "corpus" / "venue-catalog.v2.json").read_text(encoding="utf-8"))

    def test_catalog_is_rating_free_and_weighted(self):
        self.assertEqual(validate(self.catalog), [])
        self.assertTrue(all("ratings" not in record for record in self.catalog["records"]))
        self.assertTrue(all(record["directness_weight"] in (1.0, 0.65) for record in self.catalog["records"]))

    def test_expected_layer_coverage(self):
        layers = {record["layer"] for record in self.catalog["records"]}
        self.assertEqual(layers, {"direct_robotics", "robotics_strong_related"})


if __name__ == "__main__":
    unittest.main()
