#!/usr/bin/env python3
"""校验实验合同及 Claim/Design 锁。 / Validate experiment and claim/design locks."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; sys.path.insert(0,str(ROOT))
from common.canonical_json import load_json
from common.contract_core import Findings,EXPERIMENT_MODES,DESIGN_TIMINGS,compute_design_digest,validate_change_envelope,validate_finite_tree
from common.decision_rules import validate_rule
NEG={"return_toward_baseline","reverse_effect","selective_channel_loss","boundary_shift","no_effect_under_null","alternative_signature"}
ABORT={"count_as_failure","unscored_but_in_denominator","excluded_only_if_predeclared_hardware_fault"}
def validate(c,card=None):
 f=Findings(); validate_finite_tree(c,f)
 if not isinstance(c,dict) or c.get("schema_version")!="robotics-experiment-contract.v2": f.fail("SCHEMA","schema_version","expected robotics-experiment-contract.v2"); return f.report("robotics-experiment-contract.v2",None,False)
 if c.get("mode") not in EXPERIMENT_MODES:f.fail("MODE","mode","unsupported mode")
 if c.get("design_timing") not in DESIGN_TIMINGS:f.fail("TIMING","design_timing","unsupported timing")
 validate_change_envelope(c.get("change_envelope"),f)
 if c.get("abort_policy") not in ABORT:f.fail("ABORT_POLICY","abort_policy","unsupported abort policy")
 def ids(field,key):
  rows=c.get(field); out=[]
  if not isinstance(rows,list):f.fail("LIST",field,"must be a list"); return out
  for i,row in enumerate(rows):
   if not isinstance(row,dict) or not isinstance(row.get(key),str):f.fail("ID",f"{field}[{i}]",f"missing {key}")
   else:out.append(row[key])
  if len(out)!=len(set(out)):f.fail("DUPLICATE_ID",field,"IDs must be unique")
  return out
 cond=set(ids("conditions","condition_id")); variables=set(ids("variables","variable_id")); metrics=set(ids("metrics","metric_id")); contrasts=set(ids("contrasts","contrast_id")); ids("analyses","analysis_id")
 for i,x in enumerate(c.get("contrasts",[])):
  if not set(x.get("condition_ids",[]))<=cond:f.fail("REFERENCE",f"contrasts[{i}].condition_ids","unknown condition")
  if not set(x.get("metric_ids",[]))<=metrics:f.fail("REFERENCE",f"contrasts[{i}].metric_ids","unknown metric")
 for i,n in enumerate(c.get("negative_controls",[])):
  if n.get("type") not in NEG:f.fail("NEGATIVE_CONTROL",f"negative_controls[{i}].type","unsupported falsification signature")
  if n.get("intervention_variable_id") not in variables:f.fail("REFERENCE",f"negative_controls[{i}].intervention_variable_id","unknown variable")
  if not {n.get("condition_id"),n.get("comparator_condition_id")}<=cond:f.fail("REFERENCE",f"negative_controls[{i}]","unknown condition")
  if not set(n.get("measured_metric_ids",[]))<=metrics:f.fail("REFERENCE",f"negative_controls[{i}].measured_metric_ids","unknown metric")
 for i,a in enumerate(c.get("analyses",[])):
  if a.get("contrast_id") not in contrasts:f.fail("REFERENCE",f"analyses[{i}].contrast_id","unknown contrast")
  for err in validate_rule(a.get("decision_rule")):f.fail("DECISION_RULE",f"analyses[{i}].decision_rule",err)
 if card is not None:
  ref=c.get("research_card",{})
  if ref.get("id")!=card.get("card_id") or ref.get("claim_digest")!=card.get("claim_digest"):f.fail("CLAIM_LOCK","research_card","card ID or claim digest mismatch")
 expected=compute_design_digest(c)
 if c.get("design_digest")!=expected:f.fail("DESIGN_DIGEST","design_digest",f"expected {expected}")
 state=c.get("status")
 if state not in {"READY","REVISE","NO_RUN","CHANGE_REQUEST_TO_IDEA"}:f.fail("STATUS","status","unsupported terminal state")
 return f.report("robotics-experiment-contract.v2",state,state=="READY")
def main():
 p=argparse.ArgumentParser();p.add_argument("contract");p.add_argument("--card");p.add_argument("--ready",action="store_true");a=p.parse_args();r=validate(load_json(a.contract),load_json(a.card) if a.card else None);print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(0 if (r["handoff_ready"] if a.ready else r["contract_consistent"]) else 1)
if __name__=="__main__":main()
