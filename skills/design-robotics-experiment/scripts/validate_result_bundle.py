#!/usr/bin/env python3
"""校验结果并机械重算三态结论。 / Validate results and recompute verdicts."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from common.canonical_json import load_json
from common.contract_core import Findings,VERDICTS,validate_finite_tree
from common.decision_rules import validate_estimate,evaluate_rule
from common.evidence_profile import validate_profile
def validate(b,c,base):
 f=Findings();validate_finite_tree(b,f)
 if not isinstance(b,dict) or b.get("schema_version")!="robotics-result-bundle.v2":f.fail("SCHEMA","schema_version","expected robotics-result-bundle.v2");return f.report("robotics-result-bundle.v2",None,False)
 ref=b.get("experiment_contract",{})
 if ref.get("id")!=c.get("experiment_id") or ref.get("design_digest")!=c.get("design_digest"):f.fail("DESIGN_LOCK","experiment_contract","experiment ID or design digest mismatch")
 estimates=b.get("metric_estimates",[])
 for i,e in enumerate(estimates):
  for err in validate_estimate(e):f.fail("ESTIMATE",f"metric_estimates[{i}]",err)
 actual={x.get("analysis_id"):x for x in b.get("analysis_results",[]) if isinstance(x,dict)}
 derived=[]
 for i,a in enumerate(c.get("analyses",[])):
  verdict,trace=evaluate_rule(a["decision_rule"],estimates,base);derived.append(verdict);row=actual.get(a.get("analysis_id"))
  if not row or row.get("derived_verdict")!=verdict:f.fail("VERDICT_MISMATCH",f"analysis_results[{a.get('analysis_id')}]",f"mechanically derived verdict is {verdict}")
  if row and row.get("gate_trace")!=trace:f.fail("TRACE_MISMATCH",f"analysis_results[{a.get('analysis_id')}].gate_trace","must equal deterministic trace")
 for i,p in enumerate(b.get("evidence_profiles",[])):
  for err in validate_profile(p):f.fail("EVIDENCE_PROFILE",f"evidence_profiles[{i}]",err)
 state=b.get("status")
 expected="NOT_SUPPORTED" if "NOT_SUPPORTED" in derived else ("SUPPORTED" if derived and all(x=="SUPPORTED" for x in derived) else "INCONCLUSIVE")
 if state!=expected:f.fail("STATUS_DERIVATION","status",f"expected {expected}")
 if state not in VERDICTS:f.fail("STATUS","status","unsupported result state")
 return f.report("robotics-result-bundle.v2",state,state in VERDICTS)
def main():
 p=argparse.ArgumentParser();p.add_argument("bundle");p.add_argument("contract");p.add_argument("--ready",action="store_true");a=p.parse_args();r=validate(load_json(a.bundle),load_json(a.contract),Path(a.bundle).parent);print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(0 if (r["handoff_ready"] if a.ready else r["contract_consistent"]) else 1)
if __name__=="__main__":main()
