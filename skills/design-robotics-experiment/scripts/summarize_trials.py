#!/usr/bin/env python3
"""汇总试验注册表与长格式测量，不替代统计分析。 / Summarize registry and long measurements."""
from __future__ import annotations
import argparse,csv,json,math
from collections import Counter,defaultdict
REQUIRED_REGISTRY={"trial_id","experiment_id","condition_id","unit_id","session_id","block_id","pair_id","participant_id","demo_id","robot_id","hardware_batch","randomized_order","success","abort","excluded","failure_class","config_hash","log_uri"}
REQUIRED_MEAS={"trial_id","metric_id","phase_id","window_id","value","unit","aggregation","valid","missing_reason","source_log_hash"}
TRUE={"1","true","yes"}; FALSE={"0","false","no",""}
def flag(v):
 x=v.strip().lower()
 if x in TRUE:return True
 if x in FALSE:return False
 raise ValueError(f"invalid Boolean: {v}")
def read(path,required):
 with open(path,encoding="utf-8",newline="") as h:
  r=csv.DictReader(h)
  if set(r.fieldnames or [])!=required:raise ValueError(f"wrong columns in {path}")
  return list(r)
def summarize(registry,measurements,abort_policy,contract=None):
 rows=read(registry,REQUIRED_REGISTRY); meas=read(measurements,REQUIRED_MEAS)
 if contract is not None:
  if contract.get("abort_policy")!=abort_policy:raise ValueError("abort policy does not match the frozen experiment contract")
  experiment_id=contract.get("experiment_id");condition_ids={row.get("condition_id") for row in contract.get("conditions",[]) if isinstance(row,dict)};metric_ids={row.get("metric_id") for row in contract.get("metrics",[]) if isinstance(row,dict)}
  if any(row.get("experiment_id")!=experiment_id for row in rows):raise ValueError("trial registry experiment_id does not match the frozen contract")
  if any(row.get("condition_id") not in condition_ids for row in rows):raise ValueError("trial registry contains a condition outside the frozen contract")
  if any(row.get("metric_id") not in metric_ids for row in meas):raise ValueError("measurement log contains a metric outside the frozen contract")
  nesting=contract.get("nesting",{})
  keys=nesting.get("keys",[]) if isinstance(nesting,dict) else []
  if any(key not in REQUIRED_REGISTRY for key in keys):raise ValueError("nesting contains an unknown registry key")
  if any(not row.get(key) for row in rows for key in keys):raise ValueError("nested registry key is empty")
  if "participant_id" in keys and "demo_id" in keys:
   demo_owner=defaultdict(set)
   for row in rows:demo_owner[row["demo_id"]].add(row["participant_id"])
   if any(len(owners)!=1 for owners in demo_owner.values()):raise ValueError("each demonstration must belong to exactly one participant")
  if nesting.get("complete_conditions_per_demo"):
   by_demo=defaultdict(set)
   for row in rows:by_demo[row["demo_id"]].add(row["condition_id"])
   if any(seen!=condition_ids for seen in by_demo.values()):raise ValueError("each demonstration must contain every frozen condition")
 ids=[r["trial_id"] for r in rows]
 if not all(ids) or len(ids)!=len(set(ids)):raise ValueError("trial_id must be nonempty and unique")
 known=set(ids); by=defaultdict(lambda:{"trials":0,"denominator":0,"successes":0,"aborts":0,"excluded":0})
 for r in rows:
  b=by[r["condition_id"]];b["trials"]+=1;ab=flag(r["abort"]);ex=flag(r["excluded"]);ok=flag(r["success"])
  if ab:b["aborts"]+=1
  if ex:b["excluded"]+=1;continue
  if ab and abort_policy=="excluded_only_if_predeclared_hardware_fault":
   if r["failure_class"]!="predeclared_hardware_fault":raise ValueError("abort exclusion lacks predeclared hardware-fault class")
   continue
  b["denominator"]+=1
  if ok and not ab:b["successes"]+=1
 for m in meas:
  if m["trial_id"] not in known:raise ValueError("measurement references unknown trial")
  if flag(m["valid"]):
   value=float(m["value"])
   if not math.isfinite(value):raise ValueError("measurement values must be finite")
 return {"abort_policy":abort_policy,"contract_binding":({"experiment_id":contract.get("experiment_id"),"design_digest":contract.get("design_digest")} if contract is not None else None),"conditions":{k:{**v,"success_rate":(v["successes"]/v["denominator"] if v["denominator"] else None)} for k,v in sorted(by.items())},"measurements":len(meas),"participants":len({r["participant_id"] for r in rows if r["participant_id"]}),"demonstrations":len({r["demo_id"] for r in rows if r["demo_id"]})}
def main():
 p=argparse.ArgumentParser();p.add_argument("registry");p.add_argument("measurements");p.add_argument("--abort-policy",required=True,choices=["count_as_failure","unscored_but_in_denominator","excluded_only_if_predeclared_hardware_fault"]);p.add_argument("--contract");a=p.parse_args();contract=json.load(open(a.contract,encoding="utf-8")) if a.contract else None;print(json.dumps(summarize(a.registry,a.measurements,a.abort_policy,contract),ensure_ascii=False,indent=2))
if __name__=="__main__":main()
