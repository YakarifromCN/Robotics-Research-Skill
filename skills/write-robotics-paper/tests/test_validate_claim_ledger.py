import json,importlib.util,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
SCRIPT=Path(__file__).resolve().parents[1]/"scripts/validate_claim_ledger.py";spec=importlib.util.spec_from_file_location("ledger_v2",SCRIPT);V=importlib.util.module_from_spec(spec);spec.loader.exec_module(V)
def ledger():
 x=json.loads((Path(__file__).resolve().parents[1]/"assets/claim-ledger.template.json").read_text());x["status"]="READY";return x
class LedgerV2(unittest.TestCase):
 def test_inconclusive_cannot_upgrade(self):
  x=ledger();x["claims"]=[{"claim_id":"C001","evidence_state":"SUPPORTED","support_result_ids":["R001"],"boundary_result_ids":[]}];self.assertFalse(V.validate(x,{"bundle_id":"RB-001","status":"INCONCLUSIVE"})["contract_consistent"])
 def test_partial_needs_boundary(self):
  x=ledger();x["claims"]=[{"claim_id":"C001","evidence_state":"PARTIALLY_SUPPORTED","support_result_ids":["R001"],"boundary_result_ids":[]}];self.assertFalse(V.validate(x)["contract_consistent"])
 def test_nonfinite_number(self):
  x=ledger();x["numbers"]=[{"number_id":"N001","value":float("nan")}];self.assertFalse(V.validate(x)["contract_consistent"])
if __name__=="__main__":unittest.main()
