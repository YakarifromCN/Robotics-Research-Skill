#!/usr/bin/env python3
"""验证 candidate→audit→patch 不可变边界。 / Validate immutable candidate→audit→patch boundaries."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from common.canonical_json import load_json,sha256_value
PROTECTED=("/claim_contract/core_claim","/mechanism_contract/mechanism","/mechanism_contract/load_bearing_variable","/falsification_contract/falsification_target")
def main():
 p=argparse.ArgumentParser();p.add_argument("candidate");p.add_argument("audit");p.add_argument("patch");a=p.parse_args();c=load_json(a.candidate);u=load_json(a.audit);r=load_json(a.patch);errors=[]
 if u.get("candidate_id")!=c.get("candidate_id") or r.get("candidate_id")!=c.get("candidate_id"):errors.append("candidate ID mismatch")
 if u.get("candidate_digest")!=sha256_value(c.get("research_card_draft")):errors.append("candidate digest mismatch")
 allowed=set(u.get("allowed_revision_paths",[]))
 for op in r.get("operations",[]):
  path=op.get("path")
  if path not in allowed:errors.append(f"unauthorized revision path: {path}")
  if path in PROTECTED:errors.append(f"protected change requires a new candidate: {path}")
 print(json.dumps({"valid":not errors,"errors":errors},ensure_ascii=False,indent=2));raise SystemExit(bool(errors))
if __name__=="__main__":main()
