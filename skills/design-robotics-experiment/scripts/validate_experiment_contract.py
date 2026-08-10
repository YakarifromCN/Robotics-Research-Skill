#!/usr/bin/env python3
"""校验实验合同及 Claim/Design 锁。 / Validate experiment and claim/design locks."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; sys.path.insert(0,str(ROOT))
from common.canonical_json import load_json
from common.contract_core import Findings,EXPERIMENT_MODES,DESIGN_TIMINGS,compute_design_digest,compute_safety_floor_digest,meaningful,validate_change_envelope,validate_finite_tree
from common.decision_rules import validate_rule
NEG={"return_toward_baseline","reverse_effect","selective_channel_loss","boundary_shift","no_effect_under_null","alternative_signature","wrong_channel","constant_input","shuffled_alignment"}
ABORT={"count_as_failure","unscored_but_in_denominator","excluded_only_if_predeclared_hardware_fault"}
ANALYSIS_ROLES={"PRIMARY","MECHANISM","SAFETY","SECONDARY","EXPLORATORY"}
def validate(c,card=None):
 f=Findings(); validate_finite_tree(c,f)
 if not isinstance(c,dict) or c.get("schema_version")!="robotics-experiment-contract.v2": f.schema_fail("SCHEMA","schema_version","expected robotics-experiment-contract.v2"); return f.report("robotics-experiment-contract.v2",None,False)
 if c.get("mode") not in EXPERIMENT_MODES:f.fail("MODE","mode","unsupported mode")
 if c.get("design_timing") not in DESIGN_TIMINGS:f.fail("TIMING","design_timing","unsupported timing")
 validate_change_envelope(c.get("change_envelope"),f)
 if c.get("abort_policy") not in ABORT:f.fail("ABORT_POLICY","abort_policy","unsupported abort policy")
 nesting=c.get("nesting")
 if not isinstance(nesting,dict) or set(nesting)!={"keys","complete_conditions_per_demo"} or not isinstance(nesting.get("keys"),list) or not nesting["keys"] or any(not meaningful(x) for x in nesting["keys"]) or type(nesting.get("complete_conditions_per_demo")) is not bool:f.fail("NESTING","nesting","must declare nonempty keys and complete_conditions_per_demo")
 def ids(field,key):
  rows=c.get(field); out=[]
  if not isinstance(rows,list):f.fail("LIST",field,"must be a list"); return out
  for i,row in enumerate(rows):
   if not isinstance(row,dict) or not isinstance(row.get(key),str):f.fail("ID",f"{field}[{i}]",f"missing {key}")
   else:out.append(row[key])
  if len(out)!=len(set(out)):f.fail("DUPLICATE_ID",field,"IDs must be unique")
  return out
 cond=set(ids("conditions","condition_id")); variables=set(ids("variables","variable_id")); metrics=set(ids("metrics","metric_id")); contrasts=set(ids("contrasts","contrast_id")); analyses=set(ids("analyses","analysis_id"))
 for i,x in enumerate(c.get("contrasts",[])):
  if not set(x.get("condition_ids",[]))<=cond:f.reference_fail("REFERENCE",f"contrasts[{i}].condition_ids","unknown condition")
  if not set(x.get("metric_ids",[]))<=metrics:f.reference_fail("REFERENCE",f"contrasts[{i}].metric_ids","unknown metric")
 for i,n in enumerate(c.get("negative_controls",[])):
  if n.get("type") not in NEG:f.fail("NEGATIVE_CONTROL",f"negative_controls[{i}].type","unsupported falsification signature")
  if n.get("intervention_variable_id") not in variables:f.reference_fail("REFERENCE",f"negative_controls[{i}].intervention_variable_id","unknown variable")
  if not {n.get("condition_id"),n.get("comparator_condition_id")}<=cond:f.reference_fail("REFERENCE",f"negative_controls[{i}]","unknown condition")
  if not set(n.get("measured_metric_ids",[]))<=metrics:f.reference_fail("REFERENCE",f"negative_controls[{i}].measured_metric_ids","unknown metric")
 for i,a in enumerate(c.get("analyses",[])):
  if a.get("role") not in ANALYSIS_ROLES:f.fail("ANALYSIS_ROLE",f"analyses[{i}].role",f"must be one of {sorted(ANALYSIS_ROLES)}")
  if a.get("contrast_id") not in contrasts:f.reference_fail("REFERENCE",f"analyses[{i}].contrast_id","unknown contrast")
  for err in validate_rule(a.get("decision_rule")):f.fail("DECISION_RULE",f"analyses[{i}].decision_rule",err)
  rule=a.get("decision_rule",{})
  if rule.get("rule_type")=="all" and not {g.get("metric_id") for g in rule.get("gates",[]) if isinstance(g,dict)}<=metrics:f.reference_fail("REFERENCE",f"analyses[{i}].decision_rule","unknown metric in decision rule")
 ref=c.get("research_card",{})
 claim_ids=ref.get("claim_ids")
 if not isinstance(claim_ids,list) or not claim_ids or len(claim_ids)!=len(set(claim_ids)) or any(not meaningful(x) for x in claim_ids):f.reference_fail("CLAIM_IDS","research_card.claim_ids","must list the frozen Research Card claim IDs")
 if card is not None:
  if ref.get("id")!=card.get("card_id") or ref.get("claim_digest")!=card.get("claim_digest"):f.reference_fail("CLAIM_LOCK","research_card","card ID or claim digest mismatch")
  source_claim=card.get("claim_contract",{}).get("claim_id")
  if source_claim and claim_ids!=[source_claim]:f.reference_fail("CLAIM_IDS","research_card.claim_ids","must match the Research Card claim ID")
 floor=c.get("safety_floor");safety=c.get("safety")
 if not isinstance(floor,dict) or set(floor)!={"controls","stop_conditions"} or any(not isinstance(floor.get(k),list) for k in ("controls","stop_conditions")):f.fail("SAFETY_FLOOR","safety_floor","must contain controls and stop_conditions lists")
 elif not isinstance(safety,dict) or any(not isinstance(safety.get(k),list) or not set(floor[k])<=set(safety[k]) for k in ("controls","stop_conditions")):f.fail("SAFETY_FLOOR","safety","must preserve or strengthen every frozen safety-floor item")
 expected_floor=compute_safety_floor_digest(c)
 if c.get("safety_floor_digest")!=expected_floor:f.fail("SAFETY_FLOOR_DIGEST","safety_floor_digest",f"expected {expected_floor}")
 expected=compute_design_digest(c)
 if c.get("design_digest")!=expected:f.fail("DESIGN_DIGEST","design_digest",f"expected {expected}")
 state=c.get("status")
 if state not in {"READY","REVISE","NO_RUN","CHANGE_REQUEST_TO_IDEA"}:f.fail("STATUS","status","unsupported terminal state")
 if state=="READY":
  units=c.get("unit_hierarchy",[])
  if not isinstance(units,list) or not units or any(not meaningful(x) for x in units):f.minimum_fail("SCIENTIFIC_MINIMUM","unit_hierarchy","READY requires at least one named independent-unit level")
  rows=c.get("conditions",[])
  if any(not meaningful(x.get("description")) for x in rows if isinstance(x,dict)):f.minimum_fail("SCIENTIFIC_MINIMUM","conditions","READY conditions require descriptions")
  if c.get("mode") in {"PROSPECTIVE_DESIGN","PILOT_AMENDMENT","MICRO_ADJUSTMENT"} and len(rows)<2 and not meaningful(c.get("single_condition_justification")):f.minimum_fail("SCIENTIFIC_MINIMUM","conditions","READY requires two conditions or an explicit single-condition estimation justification")
  if c.get("mode")=="MICRO_ADJUSTMENT":
   envelope=c.get("change_envelope",{});allowed=set(envelope.get("allowed",[])) if isinstance(envelope,dict) else set();forbidden=set(envelope.get("forbidden",[])) if isinstance(envelope,dict) else set()
   if not {"core_claim","core_idea"}<=forbidden or not allowed<={"operational_detail","mechanism_isolation","additional_safety","logging"}:f.minimum_fail("MICRO_ADJUSTMENT_SCOPE","change_envelope","MICRO_ADJUSTMENT must preserve the core idea/claim and allow only bounded mechanism or operational changes")
  if not any(x.get("role") in {"baseline","comparator","control"} for x in rows if isinstance(x,dict)) and not meaningful(c.get("comparator_exemption")):f.minimum_fail("SCIENTIFIC_MINIMUM","conditions","READY requires a comparator or a comparator exemption")
  if not variables or any(not meaningful(x.get("name")) for x in c.get("variables",[]) if isinstance(x,dict)):f.minimum_fail("SCIENTIFIC_MINIMUM","variables","READY requires at least one named variable")
  if not metrics or not any(x.get("primary") is True for x in c.get("metrics",[]) if isinstance(x,dict)):f.minimum_fail("SCIENTIFIC_MINIMUM","metrics","READY requires at least one primary metric")
  if any(not all(meaningful(x.get(k)) for k in ("name","unit","estimand","aggregation","experimental_unit")) for x in c.get("metrics",[]) if isinstance(x,dict)):f.minimum_fail("SCIENTIFIC_MINIMUM","metrics","READY metrics require name, unit, estimand, aggregation, and experimental unit")
  if any(x.get("experimental_unit") not in set(units) for x in c.get("metrics",[]) if isinstance(x,dict)):f.reference_fail("METRIC_UNIT","metrics","metric experimental units must occur in unit_hierarchy")
  if not contrasts:f.minimum_fail("SCIENTIFIC_MINIMUM","contrasts","READY requires at least one contrast")
  if not analyses:f.minimum_fail("SCIENTIFIC_MINIMUM","analyses","READY requires at least one deterministic analysis")
  if not any(x.get("role")=="PRIMARY" for x in c.get("analyses",[]) if isinstance(x,dict)):f.minimum_fail("SCIENTIFIC_MINIMUM","analyses","READY requires at least one PRIMARY analysis")
  mechanism_claim=bool(card and card.get("claim_shape",{}).get("mechanism")) or any(x.get("load_bearing") is True for x in c.get("variables",[]) if isinstance(x,dict))
  if mechanism_claim and not c.get("negative_controls"):f.minimum_fail("SCIENTIFIC_MINIMUM","negative_controls","a mechanism claim requires an intervention or semantic negative control")
  if not meaningful(c.get("order_policy")):f.minimum_fail("SCIENTIFIC_MINIMUM","order_policy","READY requires an order/randomization policy")
  if not meaningful(c.get("operational_details",{}).get("logging")):f.minimum_fail("SCIENTIFIC_MINIMUM","operational_details.logging","READY requires data/log provenance")
  if not floor.get("stop_conditions") if isinstance(floor,dict) else True:f.minimum_fail("SCIENTIFIC_MINIMUM","safety_floor.stop_conditions","READY requires a frozen safety stop or explicit not-applicable statement")
 return f.report("robotics-experiment-contract.v2",state,state=="READY")
def main():
 p=argparse.ArgumentParser();p.add_argument("contract");p.add_argument("--card");p.add_argument("--ready",action="store_true");a=p.parse_args();r=validate(load_json(a.contract),load_json(a.card) if a.card else None);print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(0 if (r["handoff_ready"] if a.ready else r["contract_consistent"]) else 1)
if __name__=="__main__":main()
