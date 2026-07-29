import unittest

from common.robotics_research_context import build_research_context, load_first_core_reference


class RoboticsResearchContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = load_first_core_reference()
        cls.profile = {
            "topic_tags": ["robotics", "embodied_systems", "control", "mechanism"],
            "contribution_center": "robotics_core",
            "target_kind": "conference",
        }

    def test_corpus_is_loaded_as_first_core_reference(self):
        self.assertEqual(self.reference["reference_status"], "LOADED_AND_HARD_VALIDATED")
        self.assertEqual(len(self.reference["corpus"]["records"]), 100)

    def test_every_stage_receives_paper_exemplars(self):
        for stage in ("idea", "experiment", "writing", "review"):
            context = build_research_context(self.profile, stage=stage, target_venue="conf-icra", per_axis=2)
            self.assertEqual(context["first_core_reference"]["status"], "LOADED_AND_HARD_VALIDATED")
            self.assertTrue(context["paper_reference_bundle"]["paper_exemplars_by_axis"])
            self.assertEqual(context["acceptance_probability"]["status"], "NOT_ESTIMABLE")
            self.assertIsNotNone(context["fixed_venue_fit"])

    def test_stage_specific_first_actions_are_distinct(self):
        actions = {
            build_research_context(self.profile, stage=stage)["stage_adapter"]["first_action"]
            for stage in ("idea", "experiment", "writing", "review")
        }
        self.assertEqual(len(actions), 4)


if __name__ == "__main__":
    unittest.main()
