import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "skills" / "review-robotic-feedback"
REVIEWERS = (
    "manuscript-proofreading",
    "contribution-calibration-review",
    "robotics-contribution-review",
    "control-optimization-review",
    "robot-learning-review",
    "hardware-review",
    "evidence-artifact-audit",
    "venue-compliance-review",
)


def report(reviewer, report_id=None, score=4, applicable=True, issue="主张范围超过结果范围", critical=False, resolved=False):
    severity = "CRITICAL" if critical else "MAJOR"
    state = "resolved" if resolved else "open"
    finding = {
        "finding_id": f"{reviewer[:3].upper()}-001",
        "severity": severity,
        "category": "claim_evidence_mismatch",
        "location": {"file": "main.tex", "anchor": "Section 3"},
        "evidence_anchor": {"type": "quote", "value": "the quoted sentence"},
        "issue": issue,
        "impact": "读者会高估证据",
        "action": "收窄 claim boundary 或补充决定性证据" if not resolved else "保留已确认的正向证据",
        "state": state,
        "claim_ids": ["C001"],
        "evidence_state": "SUPPORTED" if critical else "INCONCLUSIVE",
        "evidence_claim_relation": "OVER_CEILING",
        "objection_burden": {
            "target_claim_id": "C001",
            "claimed_scope": "the evaluated robot tasks",
            "specific_gap": "the sentence exceeds the recorded result scope",
            "why_this_gap_invalidates_or_weakens_the_claim": "the prose asserts evidence outside C001",
            "required_action": "restore the frozen claim boundary",
        },
        "role": "primary",
        "critical_basis": "CLAIM_EVIDENCE_MISMATCH" if critical else None,
        "action_kind": "preserve" if resolved else "revise",
        "resolution_note": "已由结果与正文交叉核验" if resolved else None,
    }
    return {
        "schema_version": "robotics-review-report.v1",
        "report_id": report_id,
        "reviewer_id": reviewer,
        "review_id": "REV-001",
        "mode": "full",
        "assessed_scope": ["main.tex"],
        "applicability": {"applicable": applicable, "reason": "该维度由当前稿件范围覆盖" if applicable else "当前稿件没有该维度"},
        "score": {"overall": score if applicable else None, "confidence": 4, "dimensions": {}},
        "summary": "具体的评审摘要",
        "strengths": [{"strength_id": "S001", "category": "traceability", "statement": "可核验的优点", "evidence_anchor": {"type": "quote", "value": "positive evidence"}, "claim_ids": ["C001"]}],
        "findings": [finding] if issue is not None else [],
        "evidence_gaps": [],
        "not_assessable": [],
        "recommendation": "MAJOR_REVISION" if issue is not None else "READY_WITH_MINOR_REVISIONS",
        "generated_at": "2026-01-01T00:00:00Z",
    }


class ReviewFeedbackV2(unittest.TestCase):
    def test_discover_latex_graph_is_frozen_and_language_is_explicit(self):
        script = SKILL / "scripts" / "discover_manuscript.py"
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "sections").mkdir()
            (root / "figures").mkdir()
            (root / "main.tex").write_text(
                "\\documentclass{article}\n\\title{Test}\n\\begin{document}\n"
                "\\input{sections/method}\n\\includegraphics{figures/plot}\n"
                "\\bibliography{refs}\ncontroller hardware trial\n\\end{document}\n",
                encoding="utf-8",
            )
            (root / "sections" / "method.tex").write_text("\\section{Method}\n", encoding="utf-8")
            (root / "figures" / "plot.png").write_bytes(b"not-a-real-image")
            (root / "refs.bib").write_text("@article{a,title={A}}\n", encoding="utf-8")
            (root / "secret.tex").write_text("must not be discovered", encoding="utf-8")
            output = root / "reviews" / "review-202601010600" / "jsons" / "context.json"
            subprocess.run([sys.executable, "-B", str(script), str(root), "--language", "zh", "--output", str(output)], check=True)
            context = json.loads(output.read_text(encoding="utf-8"))
            self.assertIn(str(root / "sections" / "method.tex"), context["paper"]["include_graph"])
            self.assertIn(str(root / "figures" / "plot.png"), context["paper"]["figure_files"])
            self.assertIn(str(root / "refs.bib"), context["paper"]["bibliography_files"])
            self.assertNotIn(str(root / "secret.tex"), context["scope_guard"]["allowed_files"])
            self.assertEqual(context["review_language"], "zh")
            self.assertIsNotNone(context["created_at"])
            self.assertTrue(context["artifact_manifest"])
            self.assertIn("latex_include_graph", context["dependency_graphs"])
            self.assertIn("control-optimization", context["domain_packs"])

    def test_pdf_input_does_not_scan_sibling_workspace(self):
        script = SKILL / "scripts" / "discover_manuscript.py"
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            pdf = root / "paper.pdf"
            pdf.write_bytes(b"%PDF-1.4\n")
            (root / "neighbor.tex").write_text("\\documentclass{article}", encoding="utf-8")
            output = root / "reviews" / "review-202601010601" / "jsons" / "context.json"
            subprocess.run([sys.executable, "-B", str(script), str(pdf), "--language", "en", "--output", str(output)], check=True)
            context = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(context["paper"]["main_file"], str(pdf))
            self.assertEqual(context["paper"]["include_graph"], [str(pdf)])
            self.assertNotIn(str(root / "neighbor.tex"), context["scope_guard"]["allowed_files"])

    def test_pdf_text_extraction_populates_context_without_expanding_scope(self):
        script = SKILL / "scripts" / "discover_manuscript.py"
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            if os.name == "nt":
                pdftotext = fake_bin / "pdftotext.cmd"
                pdftotext.write_text(
                    "@echo off\r\necho Title: Contact-Aware Robot Control\r\necho.\r\necho Abstract\r\necho A robot controller uses feedback and hardware timing.\r\necho.\r\necho 1 Introduction\r\n",
                    encoding="utf-8",
                )
            else:
                pdftotext = fake_bin / "pdftotext"
                pdftotext.write_text(
                    "#!/bin/sh\nprintf 'Title: Contact-Aware Robot Control\\n\\nAbstract\\nA robot controller uses feedback and hardware timing.\\n\\n1 Introduction\\n'\n",
                    encoding="utf-8",
                )
                pdftotext.chmod(pdftotext.stat().st_mode | 0o111)
            pdf = root / "paper.pdf"
            pdf.write_bytes(b"%PDF-1.4\n")
            output = root / "reviews" / "review-202601010605" / "jsons" / "context.json"
            env = os.environ.copy()
            env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")
            subprocess.run([sys.executable, "-B", str(script), str(pdf), "--language", "en", "--output", str(output)], check=True, env=env)
            context = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(context["paper"]["title"], "Contact-Aware Robot Control")
            self.assertIn("feedback", context["paper"]["abstract"])
            self.assertEqual(context["paper"]["pdf_text_extraction"]["status"], "EXTRACTED")
            self.assertIn("control-optimization", context["domain_packs"])
            self.assertEqual(context["scope_guard"]["allowed_files"], [str(pdf)])

    def test_standalone_discovery_uses_bundled_runtime_without_common_package(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            bundle = root / "skill" / "scripts"
            bundle.mkdir(parents=True)
            for name in ("discover_manuscript.py", "review_runtime.py", "review_language.py"):
                shutil.copy2(SKILL / "scripts" / name, bundle / name)
            pdf = root / "paper.pdf"
            pdf.write_bytes(b"%PDF-1.4\n")
            output = root / "reviews" / "review-202601010606" / "jsons" / "context.json"
            env = os.environ.copy()
            env.pop("PYTHONPATH", None)
            checked = subprocess.run([sys.executable, "-B", str(bundle / "discover_manuscript.py"), str(pdf), "--language", "zh", "--output", str(output)], capture_output=True, text=True, env=env)
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            context = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(context["review_language"], "zh")
            self.assertEqual(context["paper"]["main_file"], str(pdf))

    def test_standalone_router_reports_explicit_fallback(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            bundle = root / "skill" / "scripts"
            bundle.mkdir(parents=True)
            shutil.copy2(SKILL / "scripts" / "route_robotics_research.py", bundle / "route_robotics_research.py")
            profile = root / "profile.json"
            profile.write_text(json.dumps({"topic_tags": ["control", "robotics"]}), encoding="utf-8")
            checked = subprocess.run([sys.executable, "-B", str(bundle / "route_robotics_research.py"), str(profile), "--stage", "review", "--venue", "ROBIO"], capture_output=True, text=True)
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            routing = json.loads(checked.stdout)
            self.assertEqual(routing["routing_status"], "LOCAL_FALLBACK_NO_CORPUS")
            self.assertIn("C", routing["active_axes"])

    def test_language_is_required(self):
        script = SKILL / "scripts" / "discover_manuscript.py"
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "main.tex").write_text("\\documentclass{article}", encoding="utf-8")
            checked = subprocess.run([sys.executable, "-B", str(script), str(root)], capture_output=True, text=True)
            self.assertNotEqual(checked.returncode, 0)

    def test_legacy_report_is_normalized_without_null_identity(self):
        from importlib.util import module_from_spec, spec_from_file_location

        spec = spec_from_file_location("review_validator", SKILL / "scripts" / "validate_review_report.py")
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        item = report("hardware-review", report_id=None, issue=None)
        item["positive_findings"] = ["旧版正向发现"]
        item["evidence_gaps"] = None
        item["unassessed"] = ["旧版未评估项"]
        checked = module.validate(item)
        self.assertTrue(checked["contract_consistent"], checked)
        self.assertTrue(checked["normalization_warnings"])

    def test_ready_recommendation_is_blocked_by_critical(self):
        from importlib.util import module_from_spec, spec_from_file_location

        spec = spec_from_file_location("review_validator", SKILL / "scripts" / "validate_review_report.py")
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        item = report("hardware-review", report_id="RPT-003", score=5, critical=True)
        item["recommendation"] = "READY_TO_SUBMIT"
        self.assertFalse(module.validate(item)["contract_consistent"])

    def test_objection_burden_blocks_phantom_major_and_allows_optional_extension(self):
        from importlib.util import module_from_spec, spec_from_file_location
        spec = spec_from_file_location("review_validator_objection", SKILL / "scripts" / "validate_review_report.py")
        module = module_from_spec(spec); spec.loader.exec_module(module)
        item = report("contribution-calibration-review", report_id="RPT-OBJECTION")
        item["findings"][0]["issue"] = "A second embodiment would be interesting"
        item["findings"][0]["claim_ids"] = []
        item["findings"][0]["objection_burden"] = None
        self.assertFalse(module.validate(item)["contract_consistent"])
        finding = item["findings"][0]
        finding.update(severity="MINOR", category="OPTIONAL_EXTENSION", state="resolved", action_kind="monitor", evidence_claim_relation="AT_CEILING", resolution_note="C001 is explicitly limited to the evaluated Franka tasks")
        self.assertFalse(module.validate(item)["contract_consistent"])
        item["recommendation"] = "READY_WITH_MINOR_REVISIONS"
        self.assertTrue(module.validate(item)["contract_consistent"])

    def test_below_ceiling_finding_is_valid_bidirectional_calibration(self):
        from importlib.util import module_from_spec, spec_from_file_location
        spec = spec_from_file_location("review_validator_underclaim", SKILL / "scripts" / "validate_review_report.py")
        module = module_from_spec(spec); spec.loader.exec_module(module)
        item = report("contribution-calibration-review", report_id="RPT-UNDERCLAIM")
        item["findings"][0]["evidence_claim_relation"] = "BELOW_CEILING"
        item["findings"][0]["issue"] = "The manuscript calls 15/15 real-robot executions preliminary feasibility"
        item["findings"][0]["objection_burden"]["specific_gap"] = "the prose does not state the delivered scoped result"
        item["findings"][0]["objection_burden"]["why_this_gap_invalidates_or_weakens_the_claim"] = "the supported C001 contribution is hidden below its evidence ceiling"
        self.assertTrue(module.validate(item)["contract_consistent"])

    def test_missing_evidence_claim_relation_fails_closed(self):
        from importlib.util import module_from_spec, spec_from_file_location
        spec = spec_from_file_location("review_validator_relation", SKILL / "scripts" / "validate_review_report.py")
        module = module_from_spec(spec); spec.loader.exec_module(module)
        item = report("contribution-calibration-review", report_id="RPT-NO-RELATION")
        del item["findings"][0]["evidence_claim_relation"]
        self.assertFalse(module.validate(item)["contract_consistent"])

    def test_duplicate_critical_is_one_root_cause_and_strength_is_protected(self):
        synth = SKILL / "scripts" / "synthesize_reviews.py"
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            json_dir = root / "reviews" / "review-202601010602" / "jsons"
            json_dir.mkdir(parents=True)
            context = {
                "schema_version": "robotics-review-context.v1",
                "review_id": "REV-001",
                "review_language": "zh",
                "paper": {"root": str(root), "output_language": "zh"},
                "reviewer_configuration": list(REVIEWERS),
                "artifact_manifest": [],
            }
            context_path = json_dir / "review-context.json"
            context_path.write_text(json.dumps(context, ensure_ascii=False), encoding="utf-8")
            report_paths = []
            for index, reviewer in enumerate(REVIEWERS):
                item = report(reviewer, report_id=f"REV-001::{reviewer}", score=5, issue=None)
                if reviewer in {"control-optimization-review", "hardware-review"}:
                    item = report(reviewer, report_id=f"REV-001::{reviewer}", score=3, critical=True, issue="控制通道与硬件时序冲突")
                path = json_dir / f"{reviewer}-review.json"
                path.write_text(json.dumps(item, ensure_ascii=False), encoding="utf-8")
                report_paths.append(path)
            checked = subprocess.run([sys.executable, "-B", str(synth), str(context_path)] + [str(path) for path in report_paths], capture_output=True, text=True)
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            meta = json.loads((json_dir / "meta-review.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["critical_gate"]["total"], 2)
            self.assertEqual(meta["critical_gate"]["open_root_cause_count"], 1)
            self.assertEqual(len(meta["revision_roadmap"]), 1)
            self.assertTrue(meta["protected_strengths"])
            self.assertEqual(json.loads((json_dir / "synthesis-status.json").read_text())["status"], "COMPLETED")
            self.assertTrue((root / "reviews" / "review-202601010602" / "markdowns" / "robotic-revision-roadmap.md").is_file())

    def test_snapshot_drift_fails_before_output(self):
        synth = SKILL / "scripts" / "synthesize_reviews.py"
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            json_dir = root / "reviews" / "review-202601010603" / "jsons"
            json_dir.mkdir(parents=True)
            manuscript = root / "main.tex"
            manuscript.write_text("original", encoding="utf-8")
            from common.canonical_json import sha256_file

            context = {"schema_version": "robotics-review-context.v1", "review_id": "REV-DRIFT", "review_language": "zh", "paper": {"root": str(root), "output_language": "zh"}, "reviewer_configuration": list(REVIEWERS), "artifact_manifest": [{"path": str(manuscript), "exists": True, "sha256": sha256_file(manuscript)}]}
            context_path = json_dir / "review-context.json"
            context_path.write_text(json.dumps(context, ensure_ascii=False), encoding="utf-8")
            report_paths = []
            for reviewer in REVIEWERS:
                path = json_dir / f"{reviewer}-review.json"
                path.write_text(json.dumps(report(reviewer, report_id=f"REV-DRIFT::{reviewer}", issue=None), ensure_ascii=False), encoding="utf-8")
                report_paths.append(path)
            manuscript.write_text("changed", encoding="utf-8")
            checked = subprocess.run([sys.executable, "-B", str(synth), str(context_path)] + [str(path) for path in report_paths], capture_output=True, text=True)
            self.assertNotEqual(checked.returncode, 0)
            self.assertFalse((json_dir / "meta-review.json").exists())
            status = json.loads((json_dir / "synthesis-status.json").read_text(encoding="utf-8"))
            self.assertEqual(status["status"], "FAILED")

    def test_panel_prompt_is_fresh_language_scoped_and_creates_run_state(self):
        build = SKILL / "scripts" / "build_panel_prompts.py"
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            json_dir = root / "reviews" / "review-202601010604" / "jsons"
            json_dir.mkdir(parents=True)
            context = {"schema_version": "robotics-review-context.v1", "review_id": "REV-PROMPT", "review_language": "en+zh", "paper": {"root": str(root), "output_language": "en+zh"}, "scope_guard": {"allowed_files": [str(root / "main.pdf")]}, "target_fit_snapshot": {"target": "unspecified"}}
            context_path = json_dir / "review-context.json"
            context_path.write_text(json.dumps(context, ensure_ascii=False), encoding="utf-8")
            subprocess.run([sys.executable, "-B", str(build), str(context_path)], check=True)
            prompts = json.loads((json_dir / "panel-prompts.json").read_text(encoding="utf-8"))
            self.assertEqual(prompts["review_language"], "en+zh")
            self.assertIn("fresh reviewer", prompts["reviewers"][0]["prompt"])
            self.assertIn("project memory", prompts["reviewers"][0]["prompt"])
            self.assertEqual(len(prompts["reviewers"]), 8)
            calibration = next(item for item in prompts["reviewers"] if item["reviewer_id"] == "contribution-calibration-review")
            self.assertIn("objection burden", calibration["prompt"])
            self.assertIn("BELOW_CEILING", calibration["prompt"])
            self.assertEqual(prompts["execution_mode"], "FRESH_SUBAGENT_PANEL")
            state = json.loads((json_dir / "run-state.json").read_text(encoding="utf-8"))
            self.assertEqual(set(state["agents"]), set(REVIEWERS))
            self.assertEqual(state["execution_mode"], "FRESH_SUBAGENT_PANEL")

    def test_language_policy_accepts_arbitrary_single_or_en_plus_language(self):
        from importlib.util import module_from_spec, spec_from_file_location

        spec = spec_from_file_location("review_language", SKILL / "scripts" / "review_language.py")
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.normalize_language("日本語"), "日本語")
        self.assertEqual(module.normalize_language("en+العربية"), "en+العربية")
        with self.assertRaises(ValueError):
            module.normalize_language("zh+en")


if __name__ == "__main__":
    unittest.main()
