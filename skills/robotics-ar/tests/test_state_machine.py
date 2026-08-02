"""测试静态状态机和未知转移拒绝。

Test the static state machine and rejection of unknown transitions.
"""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from robotics_ar_core.state_machine import STATES, TransitionError, is_active_state, validate_transition


class StateMachineTests(unittest.TestCase):
    def test_required_states_are_present(self) -> None:
        for state in ("PLANNING_READY", "BLOCKED_ENVIRONMENT", "EVIDENCE_FREEZE", "PAUSING", "PAUSED", "COMPLETE"):
            self.assertIn(state, STATES)

    def test_known_transition(self) -> None:
        validate_transition("UNINITIALIZED", "BOOTSTRAP_VALIDATING")
        validate_transition("INVOKING_REVIEW_SKILL", "AWAITING_REVIEW_ROUTE")

    def test_invalid_transition_is_rejected(self) -> None:
        with self.assertRaises(TransitionError):
            validate_transition("COMPLETE", "PLANNING_READY")
        with self.assertRaises(TransitionError):
            validate_transition("UNKNOWN", "PLANNING_READY")

    def test_active_state_can_pause(self) -> None:
        self.assertTrue(is_active_state("IMPLEMENTING"))
        self.assertFalse(is_active_state("PAUSED"))
        for state in STATES:
            if is_active_state(state) and state != "PAUSING":
                validate_transition(state, "PAUSING")

    def test_every_active_state_can_restore_from_bootstrap(self) -> None:
        for state in STATES:
            if is_active_state(state) and state not in {"PAUSING", "BOOTSTRAP_VALIDATING"}:
                validate_transition("BOOTSTRAP_VALIDATING", state)


if __name__ == "__main__":
    unittest.main()
