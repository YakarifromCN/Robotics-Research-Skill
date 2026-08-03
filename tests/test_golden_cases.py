#!/usr/bin/env python3
"""Validate the public synthetic regression-case registry. / 校验公开合成回归案例。"""

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class GoldenCaseRegistryTests(unittest.TestCase):
    def test_registry_is_public_synthetic_and_structurally_closed(self):
        path = ROOT / "corpus" / "golden" / "synthetic-cases.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data.get("schema_version"), "robotics-golden-cases.v1")
        self.assertEqual(data.get("privacy"), "public_sources_and_fully_synthetic_cases_only")
        cases = data.get("cases")
        self.assertIsInstance(cases, list)
        self.assertEqual(len(cases), 6)
        ids = [case.get("case_id") for case in cases]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids, [f"GOLD-{index:03d}" for index in range(1, 7)])
        for case in cases:
            self.assertIsInstance(case.get("purpose"), str)
            self.assertTrue(case["purpose"])
            self.assertIsInstance(case.get("expected"), list)
            self.assertTrue(case["expected"])
            serialized = json.dumps(case, ensure_ascii=False)
            self.assertNotIn("/mnt/", serialized)
            self.assertNotIn("/home/", serialized)
            self.assertNotIn("E:", serialized)


if __name__ == "__main__":
    unittest.main()
