"""校验 Robotics-AR M1 骨架和 schema 合同。

Validate the Robotics-AR M1 scaffold and schema contracts.
"""

from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ScaffoldTests(unittest.TestCase):
    def test_required_layout(self) -> None:
        for relative in ("SKILL.md", "agents/openai.yaml", "references", "scripts", "schemas", "assets", "tests"):
            self.assertTrue((ROOT / relative).exists(), relative)

    def test_skill_is_lightweight_and_has_no_todo(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(text.splitlines()), 350)
        self.assertNotIn("TODO", text)
        self.assertIn("# English", text)

    def test_schema_ids_are_unique_and_versioned(self) -> None:
        paths = sorted((ROOT / "schemas").glob("*.schema.json"))
        self.assertEqual(len(paths), 10)
        ids = []
        for path in paths:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data.get("type"), "object")
            self.assertTrue(data.get("$id", "").startswith("robotics-ar-"))
            ids.append(data["$id"])
            self.assertTrue(data.get("required"))
        self.assertEqual(len(ids), len(set(ids)))

    def test_core_schema_required_fields_are_domain_neutral(self) -> None:
        forbidden = {"robot", "controller", "simulator", "policy", "reward", "success_rate", "force", "accuracy", "loss", "p_value", "venue", "paper", "baseline", "ablation"}
        for name in ("session-state.schema.json", "event.schema.json", "stage-envelope.schema.json", "stage-receipt.schema.json"):
            data = json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))
            self.assertTrue(forbidden.isdisjoint(set(data.get("required", []))), name)

    def test_agent_metadata_is_deterministic(self) -> None:
        text = (ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
        self.assertIn('display_name: "Robotics-AR"', text)
        self.assertIn("$robotics-ar", text)


if __name__ == "__main__":
    unittest.main()
