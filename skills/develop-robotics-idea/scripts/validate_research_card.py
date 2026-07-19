#!/usr/bin/env python3
"""校验 V2 Research Card。 / Validate a V2 Research Card."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; sys.path.insert(0,str(ROOT))
from common.canonical_json import JsonIntegrityError, load_json
from common.contract_core import (Findings, IDEA_MODES, compute_claim_digest, meaningful,
 validate_change_envelope, validate_claim_dimensions, validate_domain_packs,
 validate_finite_tree, validate_obligations)
from common.evidence_profile import validate_requirement

def validate(card):
 f=Findings(); validate_finite_tree(card,f)
 if not isinstance(card,dict) or card.get("schema_version")!="robotics-research-card.v2":
  f.fail("SCHEMA","schema_version","expected robotics-research-card.v2"); return f.report("robotics-research-card.v2",None,False)
 if card.get("mode") not in IDEA_MODES: f.fail("MODE","mode","unsupported mode")
 validate_change_envelope(card.get("change_envelope"),f)
 validate_claim_dimensions(card.get("claim_shape"),f,"claim_shape")
 validate_obligations(card.get("evidence_obligations"),f)
 validate_domain_packs(card.get("domain_packs"),f)
 for section,keys in (("claim_contract",("claim_id","task","system_boundary","core_claim","claim_boundary")),("mechanism_contract",("mechanism_id","mechanism","load_bearing_variable_id","load_bearing_variable")),("falsification_contract",("decisive_test_id","falsification_target","stop_state_if_failed"))):
  obj=card.get(section)
  if not isinstance(obj,dict) or set(obj)!=set(keys): f.fail("SECTION",section,f"must contain exactly {list(keys)}")
  elif any(not meaningful(obj.get(k)) for k in keys): f.fail("CONTENT",section,"all fields must contain a decision")
 reqs=card.get("evidence_requirements")
 if not isinstance(reqs,list): f.fail("EVIDENCE_REQUIREMENTS","evidence_requirements","must be a list")
 else:
  for i,req in enumerate(reqs):
   for err in validate_requirement(req): f.fail("EVIDENCE_REQUIREMENT",f"evidence_requirements[{i}]",err)
 expected=compute_claim_digest(card)
 if card.get("claim_digest")!=expected: f.fail("CLAIM_DIGEST","claim_digest",f"expected {expected}")
 state=card.get("status")
 if state not in {"READY","REVISE","DO_NOT_GENERATE","ABANDON"}: f.fail("STATUS","status","unsupported terminal state")
 return f.report("robotics-research-card.v2",state,state=="READY")

def main():
 p=argparse.ArgumentParser(); p.add_argument("card"); p.add_argument("--ready",action="store_true"); a=p.parse_args()
 try: report=validate(load_json(a.card))
 except (OSError,ValueError,JsonIntegrityError) as e: report={"schema":"robotics-research-card.v2","schema_valid":False,"contract_consistent":False,"handoff_ready":False,"terminal_state":None,"findings":[{"level":"fail","code":"JSON","path":"$","message":str(e)}]}
 print(json.dumps(report,ensure_ascii=False,indent=2)); raise SystemExit(0 if (report["handoff_ready"] if a.ready else report["contract_consistent"]) else 1)
if __name__=="__main__": main()
