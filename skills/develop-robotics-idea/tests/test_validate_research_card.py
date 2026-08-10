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
 x["deferred_evidence"]=["evidence collection is frozen in the experiment contract"]
 axes={k:{"closest_overlap":"the closest source shares the task","candidate_delta":"the candidate changes the load-bearing mechanism","source_ids":["P-001"],"threat_level":"MEDIUM"} for k in ("problem_framing","core_mechanism","key_insight","application_or_evaluation")}
 x["collision_audit"]={"candidate_sha256":"a"*64,"queries":["closest mechanism"],"sources":["P-001"],"comparison_axes":axes,"closest_threat_id":"P-001","uncovered_delta":"the candidate changes the load-bearing mechanism","verdict":"CLEAR"}
 x["claim_digest"]=compute_claim_digest(x);return x
class IdeaV2(unittest.TestCase):
 def test_ready(self):self.assertTrue(V.validate(ready())["handoff_ready"])
 def test_target_not_in_digest(self):
  x=ready();before=compute_claim_digest(x);x["target_fit_snapshot"]={"target":"changed"};self.assertEqual(before,compute_claim_digest(x))
 def test_digest_drift(self):
  x=ready();x["claim_contract"]["core_claim"]="changed";self.assertFalse(V.validate(x)["contract_consistent"])
 def test_claim_shape_and_provenance_are_digest_locked(self):
  x=ready();before=compute_claim_digest(x);x["claim_shape"]["human"]=True;self.assertNotEqual(before,compute_claim_digest(x))
  before=compute_claim_digest(x);x["mechanism_contract"]["retained_invariant"]="changed invariant";self.assertNotEqual(before,compute_claim_digest(x))
  before=compute_claim_digest(x);x["adoption_provenance"]["adoption_authority"]="PI";self.assertNotEqual(before,compute_claim_digest(x))
 def test_empty_collision_axes_are_rejected(self):
  x=ready();x["collision_audit"]["comparison_axes"]={k:{} for k in x["collision_audit"]["comparison_axes"]};x["claim_digest"]=compute_claim_digest(x);self.assertFalse(V.validate(x)["handoff_ready"])
 def test_adopt_and_migrate_require_provenance(self):
  for mode in ("ADOPT_LOCKED_IDEA","MIGRATE_LEGACY_PROJECT"):
   x=ready();x["mode"]=mode;x["claim_digest"]=compute_claim_digest(x)
   with self.subTest(mode=mode):self.assertFalse(V.validate(x)["handoff_ready"])
 def test_semantically_empty_ready_is_rejected(self):
  x=ready();x["claim_shape"]={k:False for k in x["claim_shape"]};x["evidence_requirements"]=[];x["deferred_evidence"]=[];x["claim_digest"]=compute_claim_digest(x);r=V.validate(x);self.assertTrue(r["schema_valid"]);self.assertFalse(r["scientific_minimums_satisfied"]);self.assertFalse(r["handoff_ready"])
if __name__=="__main__":unittest.main()
