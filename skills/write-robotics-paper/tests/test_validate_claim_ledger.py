import json,importlib.util,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
SCRIPT=Path(__file__).resolve().parents[1]/"scripts/validate_claim_ledger.py";spec=importlib.util.spec_from_file_location("ledger_v2",SCRIPT);V=importlib.util.module_from_spec(spec);spec.loader.exec_module(V)
AUDIT_SCRIPT=Path(__file__).resolve().parents[1]/"scripts/audit_latex.py";audit_spec=importlib.util.spec_from_file_location("audit_latex",AUDIT_SCRIPT);A=importlib.util.module_from_spec(audit_spec);audit_spec.loader.exec_module(A)
BIB_SCRIPT=Path(__file__).resolve().parents[1]/"scripts/render_bibliography.py";bib_spec=importlib.util.spec_from_file_location("render_bibliography",BIB_SCRIPT);B=importlib.util.module_from_spec(bib_spec);bib_spec.loader.exec_module(B)
def ledger():
 x=json.loads((Path(__file__).resolve().parents[1]/"assets/claim-ledger.template.json").read_text());x["status"]="READY";x["external_evidence_registry"]=[{"external_evidence_id":eid,"source_path":f"evidence/{eid}.json","sha256":"a"*64,"evidence_type":"verified_result","verified":True} for eid in ("R001","A001")];x["claims"]=[{"claim_id":"C001","statement":"the bounded mechanism claim","evidence_state":"INCONCLUSIVE","support_result_ids":[],"boundary_result_ids":[]}];x["figures"]=[{"figure_id":"F001","claim_ids":["C001"],"result_ids":["R001"]}];return x
class LedgerV2(unittest.TestCase):
 def test_inconclusive_cannot_upgrade(self):
  x=ledger();x["claims"]=[{"claim_id":"C001","statement":"claim","evidence_state":"SUPPORTED","support_result_ids":["R001"],"boundary_result_ids":[]}];self.assertFalse(V.validate(x,{"bundle_id":"RB-001","status":"INCONCLUSIVE"})["contract_consistent"])
 def test_partial_needs_boundary(self):
  x=ledger();x["claims"]=[{"claim_id":"C001","statement":"claim","evidence_state":"PARTIALLY_SUPPORTED","support_result_ids":["R001"],"boundary_result_ids":[]}];self.assertFalse(V.validate(x)["contract_consistent"])
 def test_nonfinite_number(self):
  x=ledger();x["numbers"]=[{"number_id":"N001","value":float("nan")}];self.assertFalse(V.validate(x)["contract_consistent"])
 def test_empty_ready_ledger_is_rejected(self):
  x=ledger();x["claims"]=[];x["figures"]=[];r=V.validate(x);self.assertTrue(r["schema_valid"]);self.assertFalse(r["scientific_minimums_satisfied"]);self.assertFalse(r["handoff_ready"])
 def test_claim_trace_links_results_numbers_and_figures(self):
  x=ledger();x["claims"][0]["support_result_ids"]=["A001"];x["numbers"]=[{"number_id":"N001","value":1.0,"claim_ids":["C001"],"metric_id":"M001","result_id":"A001"}];trace=A.claim_trace(x);self.assertEqual(trace["C001"]["support_result_ids"],["A001"]);self.assertEqual(trace["C001"]["number_ids"],["N001"]);self.assertEqual(trace["C001"]["figure_ids"],["F001"])
 def test_writing_only_rejects_unregistered_support(self):
  x=ledger();x["mode"]="WRITING_ONLY";x["claims"][0].update(evidence_state="SUPPORTED",support_result_ids=["BOGUS"]);self.assertFalse(V.validate(x)["handoff_ready"])
 def test_latex_number_and_sentence_trace(self):
  x=ledger();x["numbers"]=[{"number_id":"N001","value":1.25,"claim_ids":["C001"],"metric_id":"M001","result_id":"A001"}]
  findings,sentences=A.audit(r"The result is \num{1.25}. \claimref{C001} The bounded claim holds.",x);self.assertFalse(any(row["level"]=="fail" for row in findings));self.assertTrue(A.claim_trace(x,sentences)["C001"]["sentences"])
  findings,_=A.audit(r"The result is \SI{9.9}{m}.",x);self.assertTrue(any(row["code"]=="UNTRACKED_LATEX_NUMBER" for row in findings))
 def test_latex_unknown_refs_and_claim_status_fail_closed(self):
  x=ledger();x["citations"]=[{"citation_id":"Ref1","verified":True}];x["numbers"]=[{"number_id":"N001","value":1.0,"claim_ids":["C001"],"metric_id":"M001","result_id":"A001"}]
  findings,_=A.audit(r"\claimref{C001} The method is effective. \resultref{BOGUS} \numref{N999} \cite{Missing}",x)
  codes={row["code"] for row in findings if row["level"]=="fail"};self.assertTrue({"CLAIM_STATUS_MISMATCH","UNKNOWN_RESULT_REF","UNKNOWN_NUMBER_REF","UNKNOWN_CITATION_REF"}<=codes)
 def test_writing_only_scope_is_frozen(self):
  x=ledger();x["mode"]="WRITING_ONLY";x["change_envelope"]["forbidden"]=["new_experiment"];self.assertFalse(V.validate(x)["handoff_ready"])
 def test_bibtex_entry_types_and_escaping(self):
  x=ledger();x["citations"]=[{"citation_id":"Ref1","entry_type":"conference","title":"Control & Safety","authors":"A_B","year":2026,"booktitle":"ICRA","verified":True}];text=B.render(x);self.assertIn("@inproceedings",text);self.assertIn(r"Control \& Safety",text);self.assertIn(r"A\_B",text)
if __name__=="__main__":unittest.main()
