#!/usr/bin/env python3
"""校验 V2 Claim Ledger 与证据状态单调性。 / Validate V2 ledger and evidence monotonicity."""
from __future__ import annotations
import argparse,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from common.canonical_json import load_json,finite_number
from common.contract_core import Findings,WRITING_MODES,meaningful,validate_change_envelope,validate_finite_tree
STATES={"SUPPORTED","PARTIALLY_SUPPORTED","NOT_SUPPORTED","INCONCLUSIVE"}
def validate(x,result=None,card=None):
 f=Findings();validate_finite_tree(x,f)
 if not isinstance(x,dict) or x.get("schema_version")!="robotics-claim-ledger.v2":f.schema_fail("SCHEMA","schema_version","expected robotics-claim-ledger.v2");return f.report("robotics-claim-ledger.v2",None,False)
 if x.get("mode") not in WRITING_MODES:f.fail("MODE","mode","unsupported mode")
 validate_change_envelope(x.get("change_envelope"),f)
 if x.get("mode")=="WRITING_ONLY":
  envelope=x.get("change_envelope",{});forbidden=set(envelope.get("forbidden",[])) if isinstance(envelope,dict) else set()
  if not {"core_idea","method","new_experiment"}<=forbidden:f.minimum_fail("WRITING_ONLY_SCOPE","change_envelope.forbidden","WRITING_ONLY must forbid core_idea, method, and new_experiment")
 if card:
  ref=x.get("research_card",{})
  if ref.get("id")!=card.get("card_id") or ref.get("claim_digest")!=card.get("claim_digest"):f.reference_fail("CLAIM_LOCK","research_card","card ID or digest mismatch")
 if result and x.get("result_bundle",{}).get("id")!=result.get("bundle_id"):f.reference_fail("RESULT_REF","result_bundle","bundle ID mismatch")
 result_state=result.get("status") if result else None
 result_claims={row.get("claim_id"):row.get("derived_verdict") for row in (result or {}).get("claim_results",[]) if isinstance(row,dict)}
 known_result_ids={row.get("analysis_id") for row in (result or {}).get("analysis_results",[]) if isinstance(row,dict)}
 if result and meaningful(result.get("bundle_id")):known_result_ids.add(result["bundle_id"])
 external=x.get("external_evidence_registry",[])
 if not isinstance(external,list):f.schema_fail("LIST","external_evidence_registry","must be a list");external=[]
 external_ids=set()
 for i,row in enumerate(external):
  if not isinstance(row,dict) or set(row)!={"external_evidence_id","source_path","sha256","evidence_type","verified"}:f.fail("EXTERNAL_EVIDENCE",f"external_evidence_registry[{i}]","must contain ID, source path, SHA-256, type, and verified state");continue
  eid=row.get("external_evidence_id")
  if not meaningful(eid) or eid in external_ids:f.fail("EXTERNAL_EVIDENCE",f"external_evidence_registry[{i}].external_evidence_id","must be nonempty and unique")
  external_ids.add(eid)
  if not meaningful(row.get("source_path")) or not meaningful(row.get("evidence_type")) or re.fullmatch(r"[0-9a-f]{64}",str(row.get("sha256",""))) is None or row.get("verified") is not True:f.fail("EXTERNAL_EVIDENCE",f"external_evidence_registry[{i}]","external evidence must have a verified source path, type, and SHA-256")
 known_result_ids|=external_ids
 ids=set()
 claims=x.get("claims",[])
 if not isinstance(claims,list):f.schema_fail("LIST","claims","must be a list");claims=[]
 if card:
  frozen=card.get("claim_contract",{}).get("claim_id");ledger_ids={row.get("claim_id") for row in claims if isinstance(row,dict)}
  if frozen and ledger_ids!={frozen}:f.reference_fail("CLAIM_CLOSURE","claims","Ledger claim IDs must exactly preserve the frozen Research Card claim")
  frozen_boundary=card.get("claim_contract",{}).get("claim_boundary")
  for i,row in enumerate(claims):
   if row.get("source_claim_digest")!=card.get("claim_digest") or row.get("claim_boundary")!=frozen_boundary:f.reference_fail("CLAIM_BOUNDARY",f"claims[{i}]","each written claim must bind the frozen claim digest and boundary")
 for i,c in enumerate(claims):
  cid=c.get("claim_id");state=c.get("evidence_state")
  if not isinstance(cid,str) or cid in ids:f.fail("CLAIM_ID",f"claims[{i}].claim_id","missing or duplicate");ids.add(cid)
  if state not in STATES:f.fail("CLAIM_STATE",f"claims[{i}].evidence_state","unsupported state")
  source_state=result_claims.get(cid,result_state)
  if source_state in {"INCONCLUSIVE","NOT_SUPPORTED"} and state in {"SUPPORTED","PARTIALLY_SUPPORTED"}:f.fail("STATE_UPGRADE",f"claims[{i}]","cannot upgrade result evidence")
  if state=="PARTIALLY_SUPPORTED" and (not c.get("support_result_ids") or not c.get("boundary_result_ids")):f.fail("PARTIAL_NEEDS_BOUNDARY",f"claims[{i}]","needs positive and independent boundary results")
  if state=="SUPPORTED" and not c.get("support_result_ids"):f.minimum_fail("SCIENTIFIC_MINIMUM",f"claims[{i}].support_result_ids","a supported claim requires a result/analysis mapping")
  for field in ("support_result_ids","boundary_result_ids"):
   refs=c.get(field,[])
   if not isinstance(refs,list) or len(refs)!=len(set(refs)) or not set(refs)<=known_result_ids:f.reference_fail("EVIDENCE_REF",f"claims[{i}].{field}","every evidence ID must resolve to a Result Bundle analysis or verified external evidence")
  if not meaningful(c.get("statement")):f.minimum_fail("SCIENTIFIC_MINIMUM",f"claims[{i}].statement","claim statement is required")
 number_ids=set()
 for i,n in enumerate(x.get("numbers",[])):
  nid=n.get("number_id")
  if not isinstance(nid,str) or nid in number_ids:f.fail("NUMBER_ID",f"numbers[{i}]","missing or duplicate number ID")
  number_ids.add(nid)
  if not finite_number(n.get("value")):f.fail("NUMBER_VALUE",f"numbers[{i}].value","must be finite")
 state=x.get("status")
 if state not in {"READY","REVISE","EVIDENCE_GAPS"}:f.fail("STATUS","status","unsupported terminal state")
 if state=="READY":
  if not claims:f.minimum_fail("SCIENTIFIC_MINIMUM","claims","READY requires at least one load-bearing claim")
  claim_ids={row.get("claim_id") for row in claims if isinstance(row,dict)}
  for i,n in enumerate(x.get("numbers",[])):
   if not set(n.get("claim_ids",[])) or not set(n.get("claim_ids",[]))<=claim_ids or not meaningful(n.get("metric_id")) or n.get("result_id") not in known_result_ids:f.minimum_fail("SCIENTIFIC_MINIMUM",f"numbers[{i}]","each number must map to a claim, metric estimate, and known result")
  for i,citation in enumerate(x.get("citations",[])):
   if citation.get("verified") is not True:f.minimum_fail("SCIENTIFIC_MINIMUM",f"citations[{i}]","READY citations must be verified")
  figures=x.get("figures",[])
  if x.get("mode") in {"FULL_DRAFT","REVISION_ONLY"} and not figures:f.minimum_fail("SCIENTIFIC_MINIMUM","figures","a full draft or revision requires at least one claim-linked figure/table")
  for i,figure in enumerate(figures):
   if not set(figure.get("claim_ids",[])) or not set(figure.get("claim_ids",[]))<=claim_ids or not figure.get("result_ids") or not set(figure.get("result_ids",[]))<=known_result_ids:f.minimum_fail("SCIENTIFIC_MINIMUM",f"figures[{i}]","each figure/table must map to claims and known results")
 return f.report("robotics-claim-ledger.v2",state,state=="READY")
def main():
 p=argparse.ArgumentParser();p.add_argument("ledger");p.add_argument("--result");p.add_argument("--card");p.add_argument("--ready",action="store_true");a=p.parse_args();r=validate(load_json(a.ledger),load_json(a.result) if a.result else None,load_json(a.card) if a.card else None);print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(0 if (r["handoff_ready"] if a.ready else r["contract_consistent"]) else 1)
if __name__=="__main__":main()
