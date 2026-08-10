"""Executable Stable-Use golden workflows; these are not fixture-shape tests."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


IDEA_TEST = load("stable_idea", ROOT / "skills/develop-robotics-idea/tests/test_validate_research_card.py")
EXP_TEST = load("stable_exp", ROOT / "skills/design-robotics-experiment/tests/test_v2_experiment.py")
WRITE_TEST = load("stable_write", ROOT / "skills/write-robotics-paper/tests/test_validate_claim_ledger.py")
INFRA_TEST = load("stable_infra", ROOT / "tests/test_researchstudio_infrastructure.py")
ENG_SCRIPTS = ROOT / "skills/develop-robotics-engineering/scripts"
sys.path.insert(0, str(ENG_SCRIPTS))
ENG_ROUTE = load("stable_eng_route", ENG_SCRIPTS / "route_engineering_task.py")
ENG_ART = load("stable_eng_art", ENG_SCRIPTS / "validate_engineering_artifacts.py")
ENG_RUN = load("stable_eng_run", ENG_SCRIPTS / "run_engineering_tests.py")


def supported_bundle(contract: dict) -> dict:
    bundle = json.loads((ROOT / "skills/design-robotics-experiment/assets/result-bundle.template.json").read_text())
    bundle["experiment_contract"] = {"id": contract["experiment_id"], "design_digest": contract["design_digest"]}
    bundle["metric_estimates"][0].update({"estimate": .2, "sample_size": 10})
    bundle["metric_estimates"][0]["interval"].update({"lower": .1, "upper": .3})
    bundle["analysis_results"][0].update({"derived_verdict": "SUPPORTED", "gate_trace": [{"metric_id": "M001", "type": "lower_bound_greater_than", "state": "pass"}]})
    bundle["claim_results"][0]["derived_verdict"] = "SUPPORTED"
    bundle["status"] = "SUPPORTED"
    return bundle


def write_artifact(path: Path, metadata: dict, body: str) -> None:
    lines = ["---", *(f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in metadata.items()), "---", "", body]
    path.write_text("\n".join(lines), encoding="utf-8")


class StableProjectGoldens(unittest.TestCase):
    def test_mdir_full_idea_experiment_result_writing_chain(self):
        profile = INFRA_TEST.ResearchStudioInfrastructureTests()._gated_profile()
        idea_run = INFRA_TEST.run_ideation_chain(profile, INFRA_TEST.build_research_context(profile, stage="idea"))
        self.assertEqual(idea_run["decision"], "ADVANCE")
        card = IDEA_TEST.ready(); self.assertTrue(IDEA_TEST.V.validate(card)["handoff_ready"])
        contract = EXP_TEST.contract(); contract["research_card"] = {"id": card["card_id"], "claim_digest": card["claim_digest"], "claim_ids": [card["claim_contract"]["claim_id"]]}; contract["design_digest"] = EXP_TEST.compute_design_digest(contract)
        self.assertTrue(EXP_TEST.vc.validate(contract, card)["handoff_ready"])
        bundle = supported_bundle(contract); self.assertTrue(EXP_TEST.vr.validate(bundle, contract, ".")["handoff_ready"])
        ledger = WRITE_TEST.ledger(); ledger["research_card"] = {"id": card["card_id"], "claim_digest": card["claim_digest"]}; ledger["result_bundle"] = {"id": bundle["bundle_id"]}; ledger["claims"][0].update(evidence_state="SUPPORTED", support_result_ids=["A001"], source_claim_digest=card["claim_digest"], claim_boundary=card["claim_contract"]["claim_boundary"]); ledger["figures"][0]["result_ids"] = ["A001"]
        self.assertTrue(WRITE_TEST.V.validate(ledger, bundle, card)["handoff_ready"])
        expanded = deepcopy(ledger); expanded["claims"][0]["claim_boundary"] = "all robots and humans"
        self.assertFalse(WRITE_TEST.V.validate(expanded, bundle, card)["handoff_ready"])

    def test_pace_writing_only_cannot_redesign_science(self):
        ledger = WRITE_TEST.ledger(); ledger["mode"] = "WRITING_ONLY"; ledger["claims"][0].update(evidence_state="SUPPORTED", support_result_ids=["R001"])
        self.assertTrue(WRITE_TEST.V.validate(ledger)["handoff_ready"])
        escaped = deepcopy(ledger); escaped["change_envelope"]["forbidden"].remove("new_experiment")
        self.assertFalse(WRITE_TEST.V.validate(escaped)["handoff_ready"])

    def test_cmdir_cpact_micro_adjustment_preserves_core(self):
        card = IDEA_TEST.ready(); contract = EXP_TEST.contract(); contract["mode"] = "MICRO_ADJUSTMENT"; contract["research_card"] = {"id": card["card_id"], "claim_digest": card["claim_digest"], "claim_ids": ["C001"]}; contract["change_envelope"] = {"allowed": ["mechanism_isolation", "additional_safety"], "forbidden": ["core_claim", "core_idea"], "reason": "isolate CP-ACT without redesigning CMDIR"}; contract["design_digest"] = EXP_TEST.compute_design_digest(contract)
        self.assertTrue(EXP_TEST.vc.validate(contract, card)["handoff_ready"])
        escaped = deepcopy(contract); escaped["change_envelope"]["allowed"].append("new_method"); escaped["design_digest"] = EXP_TEST.compute_design_digest(escaped)
        self.assertFalse(EXP_TEST.vc.validate(escaped, card)["handoff_ready"])

    def test_hivir_nested_data_and_semantic_negative_controls(self):
        contract = EXP_TEST.contract(); contract["unit_hierarchy"] = ["participant_id", "demo_id", "condition_id"]; contract["nesting"] = {"keys": ["participant_id", "demo_id", "condition_id"], "complete_conditions_per_demo": True}; contract["metrics"][0].update(experimental_unit="participant_id", aggregation="condition_to_demo_to_participant")
        types = ("wrong_channel", "constant_input", "shuffled_alignment")
        contract["negative_controls"] = [{"control_id": f"NC{i}", "type": kind, "intervention_variable_id": "V001", "condition_id": "COND-NEG", "comparator_condition_id": "COND-BASELINE", "measured_metric_ids": ["M001"]} for i, kind in enumerate(types, 1)]
        contract["design_digest"] = EXP_TEST.compute_design_digest(contract)
        self.assertTrue(EXP_TEST.vc.validate(contract)["handoff_ready"])
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); registry = root / "registry.csv"; measurements = root / "measurements.csv"
            with registry.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=sorted(EXP_TEST.sm.REQUIRED_REGISTRY)); writer.writeheader(); base = {key: "" for key in EXP_TEST.sm.REQUIRED_REGISTRY}
                index = 0
                for participant in ("S1", "S2"):
                    for demo in ("D1", "D2"):
                        demo_id = f"{participant}-{demo}"
                        for condition in ("COND-BASELINE", "COND-METHOD", "COND-NEG"):
                            index += 1; writer.writerow({**base, "trial_id": f"T{index:03d}", "experiment_id": contract["experiment_id"], "condition_id": condition, "unit_id": participant, "participant_id": participant, "demo_id": demo_id, "success": "true", "abort": "false", "excluded": "false"})
            with measurements.open("w", newline="", encoding="utf-8") as handle:
                csv.DictWriter(handle, fieldnames=sorted(EXP_TEST.sm.REQUIRED_MEAS)).writeheader()
            summary = EXP_TEST.sm.summarize(registry, measurements, contract["abort_policy"], contract)
            self.assertEqual((summary["participants"], summary["demonstrations"]), (2, 4))
            self.assertEqual({row["type"] for row in contract["negative_controls"]}, set(types))

    def test_seven_engineering_types_execute_frozen_tests(self):
        cases = {
            "ROS node change": "def update(timeout):\n    return timeout if timeout > 0 else 1\n",
            "controller bug": "def update(value):\n    return max(-1, min(1, value))\n",
            "convex optimizer modification": "def update(feasible):\n    return 'SOLVED' if feasible else 'FALLBACK'\n",
            "ML deployment change": "def update(shape):\n    return shape\n",
            "embedded firmware fallback": "def update(watchdog):\n    return 'SAFE' if watchdog else 'RUN'\n",
            "engineering tuning": "def update(gain):\n    return max(0.0, gain)\n",
            "simple config change": "def update(timeout):\n    return int(timeout)\n",
        }
        with tempfile.TemporaryDirectory() as raw:
            suite = Path(raw)
            for index, (prompt, source) in enumerate(cases.items()):
                with self.subTest(prompt=prompt):
                    root = suite / str(index); (root / "src").mkdir(parents=True); (root / "tests").mkdir(); (root / "src/component.py").write_text(source, encoding="utf-8")
                    (root / "tests/test_component.py").write_text("import sys,unittest\nfrom pathlib import Path\nsys.path.insert(0,str(Path(__file__).parents[1]/'src'))\nimport component\nclass T(unittest.TestCase):\n def test_update(self): self.assertIsNotNone(component.update(1))\n", encoding="utf-8")
                    routed = ENG_ROUTE.route(prompt); axes = [routed["primary_axis"], *routed["secondary_axes"]]; command = "python3 -m unittest discover -s tests -v"; base = {"task_id": f"ENG-{index}", "language": "en", "axes": axes, "risk_tier": routed["risk_tier"]}
                    if prompt == "simple config change":
                        self.assertEqual(routed["risk_tier"], "T1"); self.assertFalse(routed["expert_required"])
                    expert = {"affected_call_path": ["test -> component.update"], "critical_interfaces": ["update"], "invariants": ["bounded output"], "smallest_change_locus": ["src/component.py"], "mandatory_safeguards": ["offline test"], "minimal_tests": [command], "blockers": []} if routed["expert_required"] else None
                    plan = root / "plan.md"; task = root / "task.md"; report = root / "report.md"; handoff = root / "handoff.md"
                    write_artifact(plan, {**base, "artifact": "PLAN", "status": "DRAFT", "allowed_paths": ["src"]}, "# Plan\n\nImplement the bounded requested behavior.")
                    task_meta = {**base, "artifact": "TASK", "status": "FROZEN", "development_modes": routed["development_modes"], "original_request": prompt, "allowed_paths": ["src"], "forbidden_scope": ["unrelated refactor"], "steps": ["inspect", "implement", "test"], "tests": [{"command": command}], "stop_conditions": ["scope expansion"], "safeguards": (["offline test"] if routed["expert_required"] else ["preserve existing interface"]), "expert_required": routed["expert_required"], "expert_brief": expert, "device_actions": [], "real_device_authorized": False}
                    write_artifact(task, task_meta, "# Task\n\nChange only src/component.py and preserve its interface.")
                    receipts = ENG_RUN.run(task, root); self.assertTrue(all(row["result"] == "PASS" for row in receipts)); task_hash = ENG_ART.task_contract_sha256(task_meta)
                    write_artifact(report, {**base, "artifact": "REPORT", "status": "DONE", "task_contract_sha256": task_hash, "changed_files": ["src/component.py"], "tests": receipts}, "# Report\n\nImplemented the bounded change; frozen tests passed.")
                    write_artifact(handoff, {**base, "artifact": "HANDOFF", "status": "DONE", "task_contract_sha256": task_hash, "changed_files": ["src/component.py"], "tests": receipts, "resume_command": None}, "# Handoff\n\nTask is complete and receipts bind the final state.")
                    self.assertTrue(ENG_ART.validate_paths(plan, task, report, handoff)["valid"])


if __name__ == "__main__":
    unittest.main()
