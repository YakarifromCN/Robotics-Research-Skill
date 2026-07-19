import json,importlib.util,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from common.contract_core import compute_claim_digest
SCRIPT=Path(__file__).resolve().parents[1]/"scripts/validate_research_card.py";spec=importlib.util.spec_from_file_location("idea_v2",SCRIPT);V=importlib.util.module_from_spec(spec);spec.loader.exec_module(V)
def ready():
 x=json.loads((Path(__file__).resolve().parents[1]/"assets/research-card.template.json").read_text());x["status"]="READY"
 for section in ("claim_contract","mechanism_contract","falsification_contract"):
  for k,v in x[section].items():
   if v is None:x[section][k]="bounded scientific statement"
 for o in x["evidence_obligations"].values():
  if o["reason"] is None:o["reason"]="explicit claim-derived reason"
  if o["claim_boundary"] is None:o["claim_boundary"]="scope remains bounded"
 x["claim_digest"]=compute_claim_digest(x);return x
class IdeaV2(unittest.TestCase):
 def test_ready(self):self.assertTrue(V.validate(ready())["handoff_ready"])
 def test_target_not_in_digest(self):
  x=ready();before=compute_claim_digest(x);x["target_fit_snapshot"]={"target":"changed"};self.assertEqual(before,compute_claim_digest(x))
 def test_digest_drift(self):
  x=ready();x["claim_contract"]["core_claim"]="changed";self.assertFalse(V.validate(x)["contract_consistent"])
if __name__=="__main__":unittest.main()
