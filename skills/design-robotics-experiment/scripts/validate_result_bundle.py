#!/usr/bin/env python3
"""校验结果并机械重算三态结论。 / Validate results and recompute verdicts."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from common.canonical_json import load_json
from common.contract_core import Findings,VERDICTS,meaningful,validate_finite_tree
from common.decision_rules import validate_estimate,evaluate_rule
from common.evidence_profile import validate_profile
def validate(b,c,base):
 f=Findings();validate_finite_tree(b,f)
 if not isinstance(b,dict) or b.get("schema_version")!="robotics-result-bundle.v2":f.schema_fail("SCHEMA","schema_version","expected robotics-result-bundle.v2");return f.report("robotics-result-bundle.v2",None,False)
 ref=b.get("experiment_contract",{})
 if ref.get("id")!=c.get("experiment_id") or ref.get("design_digest")!=c.get("design_digest"):f.reference_fail("DESIGN_LOCK","experiment_contract","experiment ID or design digest mismatch")
 estimates=b.get("metric_estimates",[])
 if not isinstance(estimates,list):f.schema_fail("LIST","metric_estimates","must be a list");estimates=[]
 contract_metrics={row.get("metric_id"):row for row in c.get("metrics",[]) if isinstance(row,dict)}
 estimate_ids=[]
 for i,e in enumerate(estimates):
  for err in validate_estimate(e):f.fail("ESTIMATE",f"metric_estimates[{i}]",err)
  if isinstance(e,dict):
   mid=e.get("metric_id");estimate_ids.append(mid);spec=contract_metrics.get(mid)
   if spec is None:f.reference_fail("UNKNOWN_METRIC",f"metric_estimates[{i}].metric_id","metric is not declared in the Experiment Contract")
   else:
    for field in ("unit","estimand","aggregation","experimental_unit"):
     if e.get(field)!=spec.get(field):f.reference_fail("METRIC_CONTRACT_DRIFT",f"metric_estimates[{i}].{field}",f"must equal Contract value {spec.get(field)!r}")
 if len(estimate_ids)!=len(set(estimate_ids)):f.fail("DUPLICATE_ID","metric_estimates","metric estimates must be unique by metric_id")
 rows=b.get("analysis_results",[])
 if not isinstance(rows,list):f.schema_fail("LIST","analysis_results","must be a list");rows=[]
 actual_ids=[x.get("analysis_id") for x in rows if isinstance(x,dict)]
 if len(actual_ids)!=len(set(actual_ids)):f.fail("DUPLICATE_ID","analysis_results","analysis IDs must be unique")
 expected_analysis_ids={x.get("analysis_id") for x in c.get("analyses",[]) if isinstance(x,dict)}
 if set(actual_ids)!=expected_analysis_ids:f.reference_fail("ANALYSIS_CLOSURE","analysis_results","analysis IDs must exactly match the frozen Contract analyses; post-hoc additions require an amendment")
 actual={x.get("analysis_id"):x for x in rows if isinstance(x,dict)}
 derived=[];derived_by_analysis={};role_by_analysis={}
 for i,a in enumerate(c.get("analyses",[])):
  verdict,trace=evaluate_rule(a["decision_rule"],estimates,base);derived.append(verdict);derived_by_analysis[a.get("analysis_id")]=verdict;role_by_analysis[a.get("analysis_id")]=a.get("role");row=actual.get(a.get("analysis_id"))
  if row and row.get("role")!=a.get("role"):f.reference_fail("ANALYSIS_ROLE",f"analysis_results[{a.get('analysis_id')}].role","must equal the frozen Contract role")
  if not row or row.get("derived_verdict")!=verdict:f.fail("VERDICT_MISMATCH",f"analysis_results[{a.get('analysis_id')}]",f"mechanically derived verdict is {verdict}")
  if row and row.get("gate_trace")!=trace:f.fail("TRACE_MISMATCH",f"analysis_results[{a.get('analysis_id')}].gate_trace","must equal deterministic trace")
 for i,p in enumerate(b.get("evidence_profiles",[])):
  for err in validate_profile(p):f.fail("EVIDENCE_PROFILE",f"evidence_profiles[{i}]",err)
 claim_ids=set();allowed_claim_ids=set(c.get("research_card",{}).get("claim_ids",[]))
 claim_results=b.get("claim_results",[])
 if not isinstance(claim_results,list):f.schema_fail("LIST","claim_results","must be a list");claim_results=[]
 for i,row in enumerate(claim_results):
  cid=row.get("claim_id");aids=row.get("analysis_ids",[])
  if not meaningful(cid) or cid in claim_ids:f.fail("CLAIM_RESULT_ID",f"claim_results[{i}].claim_id","claim ID must be nonempty and unique")
  claim_ids.add(cid)
  if cid not in allowed_claim_ids:f.reference_fail("UNKNOWN_CLAIM",f"claim_results[{i}].claim_id","claim ID is not frozen by the Research Card reference")
  if not isinstance(aids,list) or not aids or not set(aids)<=set(derived_by_analysis):f.reference_fail("CLAIM_RESULT_ANALYSES",f"claim_results[{i}].analysis_ids","claim result must reference one or more known analyses");continue
  relevant=[item for item in aids if role_by_analysis.get(item)!="EXPLORATORY"]
  if not relevant:f.reference_fail("CLAIM_RESULT_ANALYSES",f"claim_results[{i}].analysis_ids","exploratory analyses cannot be the sole support for a frozen claim");continue
  values=[derived_by_analysis[item] for item in relevant]
  primary_failed=any(role_by_analysis.get(item)=="PRIMARY" and derived_by_analysis[item]=="NOT_SUPPORTED" for item in relevant)
  safety_failed=any(role_by_analysis.get(item)=="SAFETY" and derived_by_analysis[item]=="NOT_SUPPORTED" for item in relevant)
  expected_claim="NOT_SUPPORTED" if primary_failed or safety_failed else ("SUPPORTED" if all(item=="SUPPORTED" for item in values) else ("PARTIALLY_SUPPORTED" if "SUPPORTED" in values else ("NOT_SUPPORTED" if "NOT_SUPPORTED" in values else "INCONCLUSIVE")))
  if row.get("derived_verdict")!=expected_claim:f.fail("CLAIM_VERDICT_MISMATCH",f"claim_results[{i}].derived_verdict",f"mechanically derived claim verdict is {expected_claim}")
 if not claim_results:f.minimum_fail("SCIENTIFIC_MINIMUM","claim_results","result handoff requires at least one claim-level verdict")
 if claim_ids!=allowed_claim_ids:f.reference_fail("CLAIM_CLOSURE","claim_results","claim results must cover exactly the frozen Research Card claim IDs")
 state=b.get("status")
 safety_values=[derived_by_analysis[k] for k,v in role_by_analysis.items() if v=="SAFETY"]
 primary_values=[derived_by_analysis[k] for k,v in role_by_analysis.items() if v=="PRIMARY"]
 expected="NOT_SUPPORTED" if "NOT_SUPPORTED" in safety_values or "NOT_SUPPORTED" in primary_values else ("SUPPORTED" if primary_values and all(x=="SUPPORTED" for x in primary_values) else "INCONCLUSIVE")
 if state!=expected:f.fail("STATUS_DERIVATION","status",f"expected {expected}")
 if state not in VERDICTS:f.fail("STATUS","status","unsupported result state")
 return f.report("robotics-result-bundle.v2",state,state in VERDICTS)
def main():
 p=argparse.ArgumentParser();p.add_argument("bundle");p.add_argument("contract");p.add_argument("--ready",action="store_true");a=p.parse_args();r=validate(load_json(a.bundle),load_json(a.contract),Path(a.bundle).parent);print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(0 if (r["handoff_ready"] if a.ready else r["contract_consistent"]) else 1)
if __name__=="__main__":main()
