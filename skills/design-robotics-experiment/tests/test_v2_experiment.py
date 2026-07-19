import csv,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from common.contract_core import compute_design_digest
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
SCRIPTS=Path(__file__).resolve().parents[1]/"scripts"
vc=load("vc",SCRIPTS/"validate_experiment_contract.py");vr=load("vr",SCRIPTS/"validate_result_bundle.py");sm=load("sm",SCRIPTS/"summarize_trials.py")
def contract():
 c=json.loads((Path(__file__).resolve().parents[1]/"assets/experiment-contract.template.json").read_text())
 c["status"]="READY";c["conditions"].append({"condition_id":"COND-NEG","role":"negative_control","description":"wrong channel"});c["design_digest"]=compute_design_digest(c);return c
class V2Experiment(unittest.TestCase):
 def test_contract_and_rule(self):
  self.assertTrue(vc.validate(contract())["handoff_ready"])
 def test_result_is_mechanical(self):
  c=contract();b=json.loads((Path(__file__).resolve().parents[1]/"assets/result-bundle.template.json").read_text());b["experiment_contract"]={"id":c["experiment_id"],"design_digest":c["design_digest"]};b["metric_estimates"][0].update({"estimate":.2,"sample_size":10});b["metric_estimates"][0]["interval"].update({"lower":.1,"upper":.3});b["analysis_results"][0].update({"derived_verdict":"SUPPORTED","gate_trace":[{"metric_id":"M001","type":"lower_bound_greater_than","state":"pass"}]});b["status"]="SUPPORTED";self.assertTrue(vr.validate(b,c,".")["contract_consistent"]);b["status"]="INCONCLUSIVE";self.assertFalse(vr.validate(b,c,".")["contract_consistent"])
 def test_abort_denominator_and_nested_units(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);rp=d/"r.csv";mp=d/"m.csv"
   with rp.open("w",newline="") as h:
    w=csv.DictWriter(h,fieldnames=sorted(sm.REQUIRED_REGISTRY));w.writeheader();base={k:"" for k in sm.REQUIRED_REGISTRY}
    for tid,abort,success in (("T001","false","true"),("T002","true","false")):
     row={**base,"trial_id":tid,"experiment_id":"EXP-001","condition_id":"COND-METHOD","unit_id":"U1","participant_id":"P1","demo_id":tid,"success":success,"abort":abort,"excluded":"false"};w.writerow(row)
   with mp.open("w",newline="") as h:csv.DictWriter(h,fieldnames=sorted(sm.REQUIRED_MEAS)).writeheader()
   out=sm.summarize(rp,mp,"count_as_failure");self.assertEqual(out["conditions"]["COND-METHOD"]["denominator"],2);self.assertEqual(out["participants"],1);self.assertEqual(out["demonstrations"],2)
if __name__=="__main__":unittest.main()
