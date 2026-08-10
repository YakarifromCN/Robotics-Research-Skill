import json
import unittest
from pathlib import Path

from common.researchstudio_ideation import run_ideation_chain
from common.canonical_json import sha256_value
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

    def test_high_frequency_tactical_cards_are_executable(self):
        profile = {"topic_tags": ["robotics", "control"], "submanifold_axes": {"C": 3}, "structural_gap": "control stability boundary"}
        result = run_ideation_chain(profile, build_research_context(profile, stage="idea"))
        cards = {row["subpattern_id"]: row for row in result["strategy_context"]["tactical_cards"]}
        for card_id in ("R02", "R14"):
            self.assertEqual(len(cards[card_id]["five_step_recipe"]), 5)
            self.assertTrue(cards[card_id]["decisive_experiment"])
            self.assertTrue(cards[card_id]["semantic_negative_control"])

    def test_runtime_exposes_only_active_tactical_cards(self):
        statuses = {row["status"] for row in self.library["subpatterns"]}
        self.assertEqual(statuses, {"runtime_active", "seed_card_requires_full_text_induction"})
        self.assertEqual(sum(row["status"] == "runtime_active" for row in self.library["subpatterns"]), 14)
        for axis in AXES:
            profile = {"topic_tags": ["robotics"], "submanifold_axes": {axis: 3}, "structural_gap": "control stability boundary"}
            result = run_ideation_chain(profile, build_research_context(profile, stage="idea"))
            self.assertTrue(all(row["status"] == "runtime_active" for row in result["strategy_context"]["tactical_cards"]))
            required = {"trigger", "changed_object", "retained_invariant", "step_by_step_recipe", "differentiation_within_parent", "success_conditions", "robotics_failure_modes", "decisive_experiment", "semantic_negative_control", "prior_art_search_signature", "evidence_requirement"}
            self.assertTrue(all(required <= set(row) and all(row[key] for key in required) and len(row["step_by_step_recipe"]) == 5 for row in result["strategy_context"]["tactical_cards"]))

    def test_runtime_active_patterns_cover_high_frequency_axis_pairs(self):
        for pair in (("C", "E"), ("C", "H"), ("L", "D"), ("L", "C"), ("A", "P"), ("S", "C")):
            profile = {"topic_tags": ["robotics"], "submanifold_axes": {pair[0]: 3, pair[1]: 3}, "structural_gap": "control stability boundary"}
            cards = run_ideation_chain(profile, build_research_context(profile, stage="idea"))["strategy_context"]["tactical_cards"]
            self.assertTrue(cards, pair)
            self.assertTrue(all(row["status"] == "runtime_active" for row in cards), pair)

    def test_online_chain_stops_without_grounding(self):
        profile = {"topic_tags": ["robotics", "control"], "submanifold_axes": {"C": 3}}
        base = build_research_context(profile, stage="idea")
        result = run_ideation_chain(profile, base)
        self.assertEqual(result["decision"], "DO_NOT_GENERATE")
        self.assertEqual(validate_idea_run(result), [])
        profile = self._gated_profile(); profile.pop("structural_gap")
        self.assertEqual(run_ideation_chain(profile, build_research_context(profile, stage="idea"))["decision"], "DO_NOT_GENERATE")
        profile = self._gated_profile(); profile["evidence_bundle"] = []
        self.assertEqual(run_ideation_chain(profile, build_research_context(profile, stage="idea"))["decision"], "DO_NOT_GENERATE")

    def _gated_profile(self, *, candidate=True, collision=True, failure=True, exact=False, complete=True):
        candidate_value = {
            "title": "Bounded control mechanism",
            "core_claim": "The intervention changes the bounded control outcome",
            "falsification_prediction": "Removing the intervention returns the outcome toward baseline",
            "compute_budget": "one workstation day",
            "load_bearing_variable": "intervention channel",
        } if candidate else None
        profile = {
            "topic_tags": ["robotics", "control"],
            "submanifold_axes": {"C": 3},
            "structural_gap": "control stability boundary",
            "evidence_bundle": [{"id": "P-001"}],
        }
        if candidate_value:
            if not complete:
                candidate_value.pop("load_bearing_variable")
            profile["candidate"] = candidate_value
            digest = sha256_value(candidate_value)
            base = build_research_context(profile, stage="idea")
            selected = run_ideation_chain(profile, base)["strategy_context"]["pattern_fit"][:3]
            if collision:
                profile["collision_evidence"] = [{
                    "candidate_sha256": digest,
                    "queries": ["closest mechanism"],
                    "sources": ["P-001"],
                    "closest_prior_id": "P-001",
                    "comparison_axes": {axis: {"closest_overlap": "same task family", "candidate_delta": "different load-bearing mechanism", "source_ids": ["P-001"], "threat_level": "MEDIUM"} for axis in ("problem_framing", "core_mechanism", "key_insight", "application_or_evaluation")},
                    "verdict": "EXACT_COLLISION" if exact else "CLEAR",
                }]
            if failure:
                profile["failure_audit"] = [{"candidate_sha256": digest, "pattern_id": item["pattern_id"], "failure_mode_checked": "the closest known tactical failure", "finding": "the candidate avoids the failure within the declared boundary", "evidence_ids": ["P-001"], "mitigation_or_boundary": "limit the claim to the tested operating envelope", "status": "PASS"} for item in selected]
        return profile

    def test_nonsense_gap_abstains_without_prior_only_match(self):
        profile = self._gated_profile()
        profile["structural_gap"] = "nonsense bananas wallpaper"
        result = run_ideation_chain(profile, build_research_context(profile, stage="idea"))
        self.assertEqual(result["decision"], "ABSTAIN")
        self.assertEqual(result["strategy_context"]["pattern_fit"], [])

    def test_candidate_collision_failure_and_validation_are_hard_gates(self):
        cases = (
            (self._gated_profile(candidate=False), "REQUIRES_CANDIDATE"),
            (self._gated_profile(collision=False), "DO_NOT_ADVANCE"),
            (self._gated_profile(failure=False), "REVISE"),
            (self._gated_profile(complete=False), "PENDING_VALIDATION"),
            (self._gated_profile(exact=True), "ABANDON"),
            (self._gated_profile(), "ADVANCE"),
        )
        for profile, expected in cases:
            with self.subTest(expected=expected):
                result = run_ideation_chain(profile, build_research_context(profile, stage="idea"))
                self.assertEqual(result["decision"], expected)
                self.assertEqual(validate_idea_run(result), [])

    def test_full_deterministic_validator_blocks_advance(self):
        profile = self._gated_profile()
        profile["subpattern_ids"] = ["UNKNOWN-SUBPATTERN"]
        result = run_ideation_chain(profile, build_research_context(profile, stage="idea"))
        self.assertEqual(result["decision"], "PENDING_VALIDATION")
        self.assertTrue(result["phases"]["validate"]["errors"])

    def test_empty_collision_and_status_only_failure_cannot_advance(self):
        profile = self._gated_profile()
        profile["collision_evidence"][0]["comparison_axes"] = {axis: {} for axis in ("problem_framing", "core_mechanism", "key_insight", "application_or_evaluation")}
        self.assertEqual(run_ideation_chain(profile, build_research_context(profile, stage="idea"))["decision"], "DO_NOT_ADVANCE")
        profile = self._gated_profile()
        for row in profile["failure_audit"]:
            for key in ("failure_mode_checked", "finding", "evidence_ids", "mitigation_or_boundary"):
                row.pop(key)
        self.assertEqual(run_ideation_chain(profile, build_research_context(profile, stage="idea"))["decision"], "REVISE")
        profile = self._gated_profile()
        profile["collision_evidence"][0].pop("closest_prior_id")
        self.assertEqual(run_ideation_chain(profile, build_research_context(profile, stage="idea"))["decision"], "DO_NOT_ADVANCE")


if __name__ == "__main__":
    unittest.main()
