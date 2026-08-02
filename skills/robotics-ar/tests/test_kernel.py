"""测试领域中立 Kernel、canonical JSON 和 event log。

Test the domain-neutral Kernel, canonical JSON, and event log.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from robotics_ar_core.atomic_io import AtomicIOError, atomic_write_json, read_json
from robotics_ar_core.canonical import CanonicalError, canonical_bytes, sha256_obj
from robotics_ar_core.event_log import EventLog, EventLogError
from robotics_ar_core.models import (
    Budget,
    make_candidate_action,
    make_decision,
    make_evidence,
    make_hypothesis,
    make_research_question,
    validate_core_object,
)


class KernelTests(unittest.TestCase):
    def test_three_domains_use_same_object_path(self) -> None:
        fixtures = Path(__file__).parent / "fixtures"
        for path in sorted(fixtures.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            question = make_research_question(data["research_question"], domain_payload=data["domain_payload"])
            hypothesis = make_hypothesis("The proposed distinction has an observable consequence.", domain_payload=data["domain_payload"], parent_id=question["object_id"])
            action = make_candidate_action("Collect the predeclared observation.", domain_payload=data["domain_payload"], parent_id=hypothesis["object_id"])
            evidence = make_evidence("The observation was recorded.", domain_payload=data["domain_payload"], source_id=action["object_id"])
            decision = make_decision("The result remains bounded by the recorded evidence.", domain_payload=data["domain_payload"], evidence_id=evidence["object_id"])
            for item in (question, hypothesis, action, evidence, decision):
                validate_core_object(item)
                self.assertIn("domain_payload", item)

    def test_forbidden_fields_are_rejected_only_at_core_boundary(self) -> None:
        with self.assertRaises(ValueError):
            make_hypothesis("bad", robot="not allowed")
        allowed = make_hypothesis("domain value is external", domain_payload={"robot": "payload-only"})
        self.assertEqual(allowed["domain_payload"]["robot"], "payload-only")

    def test_canonical_hash_and_nonfinite_rejection(self) -> None:
        first = {"b": 2, "a": [1, 2]}
        second = {"a": [1, 2], "b": 2}
        self.assertEqual(canonical_bytes(first), canonical_bytes(second))
        self.assertEqual(sha256_obj(first), sha256_obj(second))
        with self.assertRaises(CanonicalError):
            canonical_bytes({"value": float("nan")})

    def test_atomic_write_and_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            atomic_write_json(path, {"schema_version": "x", "value": 3})
            self.assertEqual(read_json(path)["value"], 3)

    def test_containment_rejects_escape(self) -> None:
        from robotics_ar_core.atomic_io import contained_path

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(AtomicIOError):
                contained_path(Path(directory), "../outside")

    def test_event_log_append_and_reconstruct(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log = EventLog(Path(directory) / "events.jsonl", "RAS-TEST")
            log.append("BOOT", "supervisor", "UNINITIALIZED", "BOOTSTRAP_VALIDATING", {"ok": True})
            log.append("READY", "supervisor", "BOOTSTRAP_VALIDATING", "PLANNING_READY", {"ok": True})
            state = log.reconstruct()
            self.assertEqual(state["state"], "PLANNING_READY")
            self.assertEqual(state["event_count"], 2)
            self.assertEqual(log.read_events()[0]["event_id"], "EVT-000001")

    def test_event_log_detects_duplicate_or_wrong_previous_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            log = EventLog(path, "RAS-TEST")
            log.append("BOOT", "supervisor", "UNINITIALIZED", "BOOTSTRAP_VALIDATING")
            path.write_text(path.read_text(encoding="utf-8") + path.read_text(encoding="utf-8"), encoding="utf-8")
            with self.assertRaises(EventLogError):
                log.read_events()

    def test_budget_exhaustion_is_deterministic(self) -> None:
        budget = Budget(max_candidates=1)
        budget.consume("candidates")
        with self.assertRaises(RuntimeError):
            budget.consume("candidates")


if __name__ == "__main__":
    unittest.main()
