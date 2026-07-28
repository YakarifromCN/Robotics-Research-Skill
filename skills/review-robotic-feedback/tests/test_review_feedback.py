import csv,json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
SKILL=ROOT/"skills/review-robotic-feedback"
def report(reviewer,report_id,score=4,applicable=True):
    return {"schema_version":"robotics-review-report.v1","report_id":report_id,"reviewer_id":reviewer,"review_id":"REV-001","mode":"full","assessed_scope":["main.tex"],"applicability":{"applicable":applicable,"reason":None if applicable else "no learning component"},"score":{"overall":score if applicable else None,"confidence":4,"dimensions":{}},"summary":"具体的评审摘要","strengths":["可核验的优点"],"findings":[{"finding_id":"F001","severity":"MAJOR","category":"claim_evidence_mismatch","location":{"file":"main.tex","anchor":"Section 3"},"evidence_anchor":{"type":"quote","value":"the quoted sentence"},"issue":"主张范围超过结果范围","impact":"读者会高估证据","action":"收窄 claim boundary 或补充决定性证据","state":"open","claim_ids":["C001"],"evidence_state":"INCONCLUSIVE"}],"unassessed":[],"recommendation":"MAJOR_REVISION","generated_at":None}
class ReviewFeedbackV1(unittest.TestCase):
    def test_discover_graph_and_scope(self):
        script=SKILL/"scripts/discover_manuscript.py"
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);(root/"sections").mkdir();(root/"figures").mkdir();(root/"main.tex").write_text("\\documentclass{article}\n\\title{Test}\n\\begin{document}\n\\input{sections/method}\n\\includegraphics{figures/plot}\n\\end{document}\n",encoding="utf-8");(root/"sections/method.tex").write_text("\\section{Method}\n",encoding="utf-8");(root/"figures/plot.png").write_text("not-a-real-image",encoding="utf-8");out=root/"context.json";subprocess.run([sys.executable,"-B",str(script),str(root),"--output",str(out)],check=True);ctx=json.loads(out.read_text());self.assertIn(str(root/"sections/method.tex"),ctx["paper"]["include_graph"]);self.assertIn(str(root/"figures/plot.png"),ctx["paper"]["figure_files"]);self.assertEqual(ctx["scope_guard"]["untrusted_materials"],True)
    def test_report_validation_and_meta_gate(self):
        validate=SKILL/"scripts/validate_review_report.py";synth=SKILL/"scripts/synthesize_reviews.py"
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);context={"schema_version":"robotics-review-context.v1","review_id":"REV-001"};(root/"context.json").write_text(json.dumps(context),encoding="utf-8");paths=[]
            for i,name in enumerate(("manuscript-proofreading","robotics-contribution-review"),1):
                path=root/f"{name}.json";path.write_text(json.dumps(report(name,f"RPT-00{i}",score=5)),encoding="utf-8");paths.append(path)
            checked=subprocess.run([sys.executable,"-B",str(validate)]+[str(p) for p in paths],capture_output=True,text=True);self.assertEqual(checked.returncode,0,checked.stdout+checked.stderr)
            meta=root/"meta.json";roadmap=root/"roadmap.md";subprocess.run([sys.executable,"-B",str(synth),str(root/"context.json")]+[str(p) for p in paths]+["--json-out",str(meta),"--markdown-out",str(roadmap)],check=True);result=json.loads(meta.read_text());self.assertEqual(result["critical_gate"]["unresolved"],0);self.assertEqual(result["decision"],"MAJOR_REVISION");self.assertEqual(result["revision_roadmap"][0]["corroboration"],2);self.assertNotIn("CRITICAL gate",roadmap.read_text())
    def test_critical_blocks_ready(self):
        from importlib.util import spec_from_file_location,module_from_spec
        spec=spec_from_file_location("review_validator",SKILL/"scripts/validate_review_report.py");module=module_from_spec(spec);spec.loader.exec_module(module);item=report("hardware-review","RPT-003",score=2);item["findings"][0]["severity"]="CRITICAL";self.assertTrue(module.validate(item)["contract_consistent"])
if __name__=="__main__":unittest.main()
