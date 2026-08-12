import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
SKILL = ROOT / "skills" / "write-robotics-paper"

spec = importlib.util.spec_from_file_location("revision_validator", SKILL / "scripts" / "validate_revision_audit.py")
V = importlib.util.module_from_spec(spec); spec.loader.exec_module(V)
audit_spec = importlib.util.spec_from_file_location("latex_audit_revision", SKILL / "scripts" / "audit_latex.py")
A = importlib.util.module_from_spec(audit_spec); audit_spec.loader.exec_module(A)


def ledger():
    return {
        "schema_version": "robotics-claim-ledger.v2",
        "ledger_id": "LEDGER-001",
        "research_card": {"id": "CARD-001", "claim_digest": "d" * 64},
        "change_envelope": {"allowed": ["prose", "claim_narrowing"], "forbidden": ["core_idea", "method", "new_experiment"], "reason": "writing does not change the scientific object"},
        "claims": [{"claim_id": "C001", "statement": "The method retains task execution on the evaluated real-robot tasks.", "evidence_state": "SUPPORTED", "support_result_ids": ["R001"], "boundary_result_ids": []}],
        "external_evidence_registry": [{"external_evidence_id": "R001", "source_path": "result.json", "sha256": "a" * 64, "evidence_type": "real_robot_result", "verified": True}],
        "numbers": [{"number_id": "N003", "value": 15, "claim_ids": ["C001"], "metric_id": "M001", "result_id": "R001"}],
        "citations": [{"citation_id": "Ref1", "verified": True}],
    }


def decision(**updates):
    row = {
        "decision_id": "RD-001", "source_anchor": "Abstract/S1", "replacement_anchor": "Abstract/S1",
        "classification": "D3", "disposition": "REFRAME", "executed": True,
        "claim_ids": ["C001"], "evidentiary_function": "RHETORICAL_ONLY",
        "rhetorical_strength_delta": "STRONGER", "semantic_claim_relation": "WITHIN_CEILING",
        "source_status_preserved": True, "scope_preserved": True, "citation_role_preserved": True,
        "source_result_ids": ["R001"], "source_number_ids": ["N003"], "source_citation_ids": ["Ref1"],
        "preserved_in_anchor": "Abstract/S1", "preserved_by_decision_id": None,
    }
    row.update(updates); return row


def artifact(before, after, row=None):
    return {
        "schema_version": "robotics-evidence-bound-revision.v1", "audit_id": "REVISION-001",
        "mode": "AUTHORIZED_REVISION", "status": "REVISED",
        "manuscript_before_sha256": V.sha256_text(before), "manuscript_after_sha256": V.sha256_text(after),
        "claim_ledger_id": "LEDGER-001", "claim_digest": "d" * 64,
        "contribution_contract": {"core_claim_ids": ["C001"], "contribution_first": True, "qualification_in_place": True},
        "authority": {"authorized": True, "allowed": ["prose", "claim_narrowing"], "forbidden": ["core_idea", "method", "new_experiment"], "reason": "writing does not change the scientific object"},
        "decisions": [row or decision()], "open_queries": [],
        "regression": {"claim_ceiling_preserved": True, "evidence_status_preserved": True, "scope_coverage_preserved": True, "citation_role_preserved": True, "conceptual_hierarchy_preserved": True, "contribution_visibility_checked": True},
    }


class EvidenceBoundRevision(unittest.TestCase):
    def setUp(self):
        self.before = r"\claimref{C001} These preliminary results may tentatively suggest that the method could possibly retain task execution."
        self.after = r"\claimref{C001} The method retained task execution in all 15 evaluated real-robot runs. \resultref{R001} \numref{N003} \cite{Ref1}"

    def test_underclaim_may_strengthen_to_frozen_ceiling(self):
        checked = V.validate(artifact(self.before, self.after), ledger(), self.before, self.after)
        self.assertTrue(checked["handoff_ready"], checked)

    def test_semantically_broader_claim_fails_even_if_fluent(self):
        row = decision(semantic_claim_relation="BROADER")
        checked = V.validate(artifact(self.before, self.after, row), ledger(), self.before, self.after)
        self.assertFalse(checked["contract_consistent"])

    def test_k_function_can_be_deduplicated_but_not_disappear(self):
        row = decision(classification="K1", disposition="DEDUPLICATE", source_result_ids=[], source_number_ids=[], source_citation_ids=[], replacement_anchor="Discussion/P2", preserved_in_anchor="Discussion/P2")
        self.assertTrue(V.validate(artifact(self.before, self.after, row), ledger(), self.before, self.after)["contract_consistent"])
        row["replacement_anchor"] = None; row["preserved_in_anchor"] = None
        self.assertFalse(V.validate(artifact(self.before, self.after, row), ledger(), self.before, self.after)["contract_consistent"])

    def test_stable_objects_may_move_but_must_survive(self):
        self.assertTrue(V.validate(artifact(self.before, self.after), ledger(), self.before, self.after)["contract_consistent"])
        missing = self.after.replace(r"\cite{Ref1}", "")
        broken = artifact(self.before, missing); broken["manuscript_after_sha256"] = V.sha256_text(missing)
        self.assertFalse(V.validate(broken, ledger(), self.before, missing)["contract_consistent"])

    def test_unauthorized_or_open_query_cannot_execute(self):
        item = artifact(self.before, self.after); item["authority"]["authorized"] = False
        self.assertFalse(V.validate(item, ledger(), self.before, self.after)["contract_consistent"])
        item = artifact(self.before, self.after); item["open_queries"] = [{"query_id": "Q001", "decision_id": "RD-001", "status": "OPEN", "resolution": None}]
        self.assertFalse(V.validate(item, ledger(), self.before, self.after)["contract_consistent"])

    def test_lexical_cues_are_candidates_not_edit_decisions(self):
        findings, _ = A.audit("We initially tried A and after several attempts eventually discovered B. These preliminary results may tentatively suggest feasibility.", ledger())
        codes = {row["code"] for row in findings}
        self.assertIn("WORK_LOG_CANDIDATE", codes)
        self.assertIn("UNDERCLAIM_CANDIDATE", codes)
        self.assertFalse(any(row["level"] == "fail" for row in findings))


if __name__ == "__main__": unittest.main()
