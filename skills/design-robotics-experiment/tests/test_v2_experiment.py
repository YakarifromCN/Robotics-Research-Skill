import csv,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from common.contract_core import compute_design_digest,compute_safety_floor_digest
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
SCRIPTS=Path(__file__).resolve().parents[1]/"scripts"
vc=load("vc",SCRIPTS/"validate_experiment_contract.py");vr=load("vr",SCRIPTS/"validate_result_bundle.py");sm=load("sm",SCRIPTS/"summarize_trials.py")
def contract():
 c=json.loads((Path(__file__).resolve().parents[1]/"assets/experiment-contract.template.json").read_text())
 c["status"]="READY"
 for row in c["conditions"]:row["description"]=row["description"] or "predeclared condition"
 for row in c["variables"]:row["name"]=row["name"] or "load-bearing variable"
 for row in c["metrics"]:row["name"]=row["name"] or "primary outcome";row["unit"]=row["unit"] or "dimensionless"
 c["operational_details"]["logging"]="versioned trial registry and measurement log";c["safety"]["stop_conditions"]=["stop on non-finite output"]
 c["safety_floor_digest"]=compute_safety_floor_digest(c);c["design_digest"]=compute_design_digest(c);return c
class V2Experiment(unittest.TestCase):
 def test_contract_and_rule(self):
  self.assertTrue(vc.validate(contract())["handoff_ready"])
 def test_design_lock_covers_variables_controls_order_and_safety_floor(self):
  for field,mutate in (("variables",lambda c:c["variables"][0].update(name="changed")),("negative_controls",lambda c:c["negative_controls"][0].update(type="reverse_effect")),("order_policy",lambda c:c.update(order_policy="fixed")),("safety_floor",lambda c:c["safety_floor"]["stop_conditions"].append("stop on timeout"))):
   c=contract();before=compute_design_digest(c);mutate(c)
   with self.subTest(field=field):self.assertNotEqual(before,compute_design_digest(c))
  c=contract();c["safety_floor"]["stop_conditions"].append("stop on timeout");self.assertNotEqual(c["safety_floor_digest"],compute_safety_floor_digest(c));self.assertFalse(vc.validate(c)["handoff_ready"])
 def test_empty_ready_contract_is_rejected(self):
  c=contract()
  for field in ("unit_hierarchy","conditions","variables","metrics","contrasts","negative_controls","analyses"):c[field]=[]
  c["design_digest"]=compute_design_digest(c);r=vc.validate(c);self.assertTrue(r["schema_valid"]);self.assertFalse(r["scientific_minimums_satisfied"]);self.assertFalse(r["handoff_ready"])
 def test_result_is_mechanical(self):
  c=contract();b=json.loads((Path(__file__).resolve().parents[1]/"assets/result-bundle.template.json").read_text());b["experiment_contract"]={"id":c["experiment_id"],"design_digest":c["design_digest"]};b["metric_estimates"][0].update({"estimate":.2,"sample_size":10});b["metric_estimates"][0]["interval"].update({"lower":.1,"upper":.3});b["analysis_results"][0].update({"derived_verdict":"SUPPORTED","gate_trace":[{"metric_id":"M001","type":"lower_bound_greater_than","state":"pass"}]});b["claim_results"][0]["derived_verdict"]="SUPPORTED";b["status"]="SUPPORTED";self.assertTrue(vr.validate(b,c,".")["contract_consistent"]);b["status"]="INCONCLUSIVE";self.assertFalse(vr.validate(b,c,".")["contract_consistent"])
 def test_result_rejects_unknown_and_duplicate_cross_references(self):
  c=contract();b=json.loads((Path(__file__).resolve().parents[1]/"assets/result-bundle.template.json").read_text());b["experiment_contract"]={"id":c["experiment_id"],"design_digest":c["design_digest"]}
  mutations=(lambda x:x["metric_estimates"][0].update(metric_id="UNKNOWN"),lambda x:x["claim_results"][0].update(claim_id="C999"),lambda x:x["analysis_results"].append(dict(x["analysis_results"][0])))
  for mutate in mutations:
   x=json.loads(json.dumps(b));mutate(x)
   self.assertFalse(vr.validate(x,c,".")["contract_consistent"])
 def test_safety_failure_overrides_primary_and_exploratory_does_not(self):
  c=contract();b=json.loads((Path(__file__).resolve().parents[1]/"assets/result-bundle.template.json").read_text());b["metric_estimates"][0].update({"estimate":.2,"sample_size":10});b["metric_estimates"][0]["interval"].update({"lower":.1,"upper":.3});b["analysis_results"][0].update({"derived_verdict":"SUPPORTED","gate_trace":[{"metric_id":"M001","type":"lower_bound_greater_than","state":"pass"}]});b["claim_results"][0]["derived_verdict"]="SUPPORTED"
  c["analyses"].append({"analysis_id":"A-EXP","role":"EXPLORATORY","contrast_id":"X001","decision_rule":{"rule_type":"all","gates":[{"type":"upper_bound_less_than","metric_id":"M001","threshold":.1}]}});c["design_digest"]=compute_design_digest(c);b["experiment_contract"]={"id":c["experiment_id"],"design_digest":c["design_digest"]};b["analysis_results"].append({"analysis_id":"A-EXP","role":"EXPLORATORY","derived_verdict":"NOT_SUPPORTED","gate_trace":[{"metric_id":"M001","type":"upper_bound_less_than","state":"fail"}]});b["status"]="SUPPORTED";self.assertTrue(vr.validate(b,c,".")["handoff_ready"])
  c["analyses"][-1]["analysis_id"]="A-SAFE";c["analyses"][-1]["role"]="SAFETY";c["design_digest"]=compute_design_digest(c);b["experiment_contract"]["design_digest"]=c["design_digest"];b["analysis_results"][-1].update(analysis_id="A-SAFE",role="SAFETY");b["claim_results"][0].update(analysis_ids=["A001","A-SAFE"],derived_verdict="NOT_SUPPORTED");b["status"]="NOT_SUPPORTED";self.assertTrue(vr.validate(b,c,".")["handoff_ready"])
 def test_claim_level_partial_is_mechanically_derived(self):
  c=contract();c["analyses"].append({"analysis_id":"A-SECONDARY","role":"SECONDARY","contrast_id":"X001","decision_rule":{"rule_type":"all","gates":[{"type":"lower_bound_greater_than","metric_id":"M001","threshold":.2}]}});c["design_digest"]=compute_design_digest(c);b=json.loads((Path(__file__).resolve().parents[1]/"assets/result-bundle.template.json").read_text());b["experiment_contract"]={"id":c["experiment_id"],"design_digest":c["design_digest"]};b["metric_estimates"][0].update({"estimate":.2,"sample_size":10});b["metric_estimates"][0]["interval"].update({"lower":.1,"upper":.3});b["analysis_results"][0].update({"derived_verdict":"SUPPORTED","gate_trace":[{"metric_id":"M001","type":"lower_bound_greater_than","state":"pass"}]});b["analysis_results"].append({"analysis_id":"A-SECONDARY","role":"SECONDARY","derived_verdict":"INCONCLUSIVE","gate_trace":[{"metric_id":"M001","type":"lower_bound_greater_than","state":"inconclusive"}]});b["claim_results"][0].update(analysis_ids=["A001","A-SECONDARY"],derived_verdict="PARTIALLY_SUPPORTED");b["status"]="SUPPORTED";self.assertTrue(vr.validate(b,c,".")["handoff_ready"])
 def test_abort_denominator_and_nested_units(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);rp=d/"r.csv";mp=d/"m.csv"
   with rp.open("w",newline="") as h:
    w=csv.DictWriter(h,fieldnames=sorted(sm.REQUIRED_REGISTRY));w.writeheader();base={k:"" for k in sm.REQUIRED_REGISTRY}
    for tid,abort,success in (("T001","false","true"),("T002","true","false")):
     row={**base,"trial_id":tid,"experiment_id":"EXP-001","condition_id":"COND-METHOD","unit_id":"U1","participant_id":"P1","demo_id":tid,"success":success,"abort":abort,"excluded":"false"};w.writerow(row)
   with mp.open("w",newline="") as h:csv.DictWriter(h,fieldnames=sorted(sm.REQUIRED_MEAS)).writeheader()
   c=contract();out=sm.summarize(rp,mp,"count_as_failure",c);self.assertEqual(out["conditions"]["COND-METHOD"]["denominator"],2);self.assertEqual(out["participants"],1);self.assertEqual(out["demonstrations"],2);self.assertEqual(out["contract_binding"]["design_digest"],c["design_digest"])
if __name__=="__main__":unittest.main()
