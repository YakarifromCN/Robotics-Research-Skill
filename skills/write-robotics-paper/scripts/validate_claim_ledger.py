#!/usr/bin/env python3
"""校验 V2 Claim Ledger 与证据状态单调性。 / Validate V2 ledger and evidence monotonicity."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from common.canonical_json import load_json,finite_number
from common.contract_core import Findings,WRITING_MODES,validate_change_envelope,validate_finite_tree
STATES={"SUPPORTED","PARTIALLY_SUPPORTED","NOT_SUPPORTED","INCONCLUSIVE"}
def validate(x,result=None,card=None):
 f=Findings();validate_finite_tree(x,f)
 if not isinstance(x,dict) or x.get("schema_version")!="robotics-claim-ledger.v2":f.fail("SCHEMA","schema_version","expected robotics-claim-ledger.v2");return f.report("robotics-claim-ledger.v2",None,False)
 if x.get("mode") not in WRITING_MODES:f.fail("MODE","mode","unsupported mode")
 validate_change_envelope(x.get("change_envelope"),f)
 if card:
  ref=x.get("research_card",{})
  if ref.get("id")!=card.get("card_id") or ref.get("claim_digest")!=card.get("claim_digest"):f.fail("CLAIM_LOCK","research_card","card ID or digest mismatch")
 if result and x.get("result_bundle",{}).get("id")!=result.get("bundle_id"):f.fail("RESULT_REF","result_bundle","bundle ID mismatch")
 result_state=result.get("status") if result else None
 ids=set()
 for i,c in enumerate(x.get("claims",[])):
  cid=c.get("claim_id");state=c.get("evidence_state")
  if not isinstance(cid,str) or cid in ids:f.fail("CLAIM_ID",f"claims[{i}].claim_id","missing or duplicate");ids.add(cid)
  if state not in STATES:f.fail("CLAIM_STATE",f"claims[{i}].evidence_state","unsupported state")
  if result_state in {"INCONCLUSIVE","NOT_SUPPORTED"} and state in {"SUPPORTED","PARTIALLY_SUPPORTED"}:f.fail("STATE_UPGRADE",f"claims[{i}]","cannot upgrade result evidence")
  if state=="PARTIALLY_SUPPORTED" and (not c.get("support_result_ids") or not c.get("boundary_result_ids")):f.fail("PARTIAL_NEEDS_BOUNDARY",f"claims[{i}]","needs positive and independent boundary results")
 number_ids=set()
 for i,n in enumerate(x.get("numbers",[])):
  nid=n.get("number_id")
  if not isinstance(nid,str) or nid in number_ids:f.fail("NUMBER_ID",f"numbers[{i}]","missing or duplicate number ID")
  number_ids.add(nid)
  if not finite_number(n.get("value")):f.fail("NUMBER_VALUE",f"numbers[{i}].value","must be finite")
 state=x.get("status")
 if state not in {"READY","REVISE","EVIDENCE_GAPS"}:f.fail("STATUS","status","unsupported terminal state")
 return f.report("robotics-claim-ledger.v2",state,state=="READY")
def main():
 p=argparse.ArgumentParser();p.add_argument("ledger");p.add_argument("--result");p.add_argument("--card");p.add_argument("--ready",action="store_true");a=p.parse_args();r=validate(load_json(a.ledger),load_json(a.result) if a.result else None,load_json(a.card) if a.card else None);print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(0 if (r["handoff_ready"] if a.ready else r["contract_consistent"]) else 1)
if __name__=="__main__":main()
