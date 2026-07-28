#!/usr/bin/env python3
"""校验单个或多个机器人评审报告。 / Validate one or more robotics review reports."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from common.canonical_json import JsonIntegrityError,load_json
from common.contract_core import Findings,validate_finite_tree
REVIEWERS={"manuscript-proofreading","robotics-contribution-review","control-optimization-review","robot-learning-review","hardware-review","evidence-artifact-audit","venue-compliance-review"}
SEVERITIES={"CRITICAL","MAJOR","MINOR"};STATES={"open","uncertain","resolved"};EVIDENCE={"SUPPORTED","PARTIALLY_SUPPORTED","NOT_SUPPORTED","INCONCLUSIVE","EVIDENCE_GAPS","UNASSESSED"};RECOMMENDATIONS={"READY_WITH_MINOR_REVISIONS","MAJOR_REVISION","REBUILD_OR_REFRAME","EVIDENCE_GAPS","NOT_ASSESSABLE"}
def validate(x):
 f=Findings();validate_finite_tree(x,f)
 if not isinstance(x,dict) or x.get("schema_version")!="robotics-review-report.v1":f.fail("SCHEMA","schema_version","expected robotics-review-report.v1");return f.report("robotics-review-report.v1",None,False)
 if x.get("reviewer_id") not in REVIEWERS:f.fail("REVIEWER_ID","reviewer_id","unknown specialist reviewer")
 app=x.get("applicability")
 if not isinstance(app,dict) or set(app)!={"applicable","reason"} or type(app.get("applicable")) is not bool:f.fail("APPLICABILITY","applicability","must contain Boolean applicable and reason")
 elif app["applicable"] is False and not isinstance(app.get("reason"),str):f.fail("APPLICABILITY","applicability.reason","required when not applicable")
 score=x.get("score")
 if not isinstance(score,dict) or set(score)!= {"overall","confidence","dimensions"}:f.fail("SCORE","score","must contain overall, confidence, dimensions")
 else:
  if app.get("applicable") is True and (type(score.get("overall")) is not int or not 1<=score["overall"]<=5):f.fail("SCORE","score.overall","applicable reports need integer 1–5")
  if type(score.get("confidence")) is not int or not 1<=score["confidence"]<=5:f.fail("SCORE","score.confidence","must be integer 1–5")
  if not isinstance(score.get("dimensions"),dict):f.fail("SCORE","score.dimensions","must be an object")
 for i,item in enumerate(x.get("findings",[])):
  path=f"findings[{i}]";required={"finding_id","severity","category","location","evidence_anchor","issue","impact","action","state","claim_ids","evidence_state"}
  if not isinstance(item,dict) or set(item)!=required:f.fail("FINDING",path,f"must contain exactly {sorted(required)}");continue
  if item["severity"] not in SEVERITIES:f.fail("FINDING",f"{path}.severity","unsupported severity")
  if item["state"] not in STATES:f.fail("FINDING",f"{path}.state","unsupported finding state")
  if item["evidence_state"] not in EVIDENCE:f.fail("FINDING",f"{path}.evidence_state","unsupported evidence state")
  if not isinstance(item["claim_ids"],list):f.fail("FINDING",f"{path}.claim_ids","must be a list")
  loc=item["location"];anchor=item["evidence_anchor"]
  if not isinstance(loc,dict) or set(loc)!={"file","anchor"}:f.fail("ANCHOR",f"{path}.location","must contain file and anchor")
  if not isinstance(anchor,dict) or set(anchor)!= {"type","value"} or not anchor.get("type") or not anchor.get("value"):f.fail("ANCHOR",f"{path}.evidence_anchor","typed nonempty anchor required")
 for field in ("summary","recommendation"):
  if field=="summary" and not isinstance(x.get(field),str):f.fail("CONTENT",field,"must be a string")
  if field=="recommendation" and x.get(field) not in RECOMMENDATIONS:f.fail("RECOMMENDATION",field,"unsupported recommendation")
 state=x.get("recommendation")
 return f.report("robotics-review-report.v1",state,False if not x.get("applicability",{}).get("applicable",True) else state in RECOMMENDATIONS)
def main():
 p=argparse.ArgumentParser();p.add_argument("reports",nargs="+");a=p.parse_args();out=[];ok=True
 for raw in a.reports:
  try:r=validate(load_json(raw))
  except (OSError,ValueError,JsonIntegrityError) as e:r={"schema":"robotics-review-report.v1","schema_valid":False,"contract_consistent":False,"handoff_ready":False,"terminal_state":None,"findings":[{"level":"fail","code":"JSON","path":"$","message":str(e)}]}
  r["path"]=str(raw);out.append(r);ok &= r["contract_consistent"]
 print(json.dumps({"valid":bool(ok),"reports":out},ensure_ascii=False,indent=2));raise SystemExit(0 if ok else 1)
if __name__=="__main__":main()
