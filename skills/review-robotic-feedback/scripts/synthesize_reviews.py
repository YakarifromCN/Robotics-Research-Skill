#!/usr/bin/env python3
"""合并独立评审并生成 Meta Review 与修改路线。 / Synthesize independent reviews."""
from __future__ import annotations
import argparse,json,re,statistics,sys
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from common.canonical_json import load_json
from validate_review_report import validate
def norm(text):return re.sub(r"\W+"," ",str(text).lower()).strip()[:180]
def main():
 p=argparse.ArgumentParser();p.add_argument("context");p.add_argument("reports",nargs="+");p.add_argument("--json-out",required=True);p.add_argument("--markdown-out",required=True);a=p.parse_args();context=load_json(a.context);reports=[load_json(x) for x in a.reports];bad=[(str(x),validate(load_json(x))) for x in a.reports if not validate(load_json(x))["contract_consistent"]]
 applicable=[r for r in reports if r.get("applicability",{}).get("applicable") is True and isinstance(r.get("score",{}).get("overall"),int)]
 scores=[r["score"]["overall"] for r in applicable];by={r["reviewer_id"]:{"score":r["score"]["overall"],"confidence":r["score"]["confidence"],"recommendation":r.get("recommendation")} for r in applicable}
 groups={};raw_critical=[]
 for report in reports:
  for finding in report.get("findings",[]):
   key=(finding.get("severity"),finding.get("category"),norm(finding.get("issue")))
   if key not in groups:groups[key]={"severity":finding.get("severity"),"category":finding.get("category"),"issue":finding.get("issue"),"impact":finding.get("impact"),"actions":[],"sources":[],"claim_ids":set(),"evidence_states":set(),"states":set()}
   g=groups[key];g["actions"].append(finding.get("action"));g["sources"].append({"report_id":report.get("report_id"),"reviewer_id":report.get("reviewer_id"),"finding_id":finding.get("finding_id")});g["claim_ids"].update(finding.get("claim_ids",[]));g["evidence_states"].add(finding.get("evidence_state"));g["states"].add(finding.get("state"))
   if finding.get("severity")=="CRITICAL":raw_critical.append({"report_id":report.get("report_id"),"reviewer_id":report.get("reviewer_id"),"finding_id":finding.get("finding_id"),"issue":finding.get("issue"),"adjudication":"unresolved"})
 roadmap=[];severity_order={"CRITICAL":0,"MAJOR":1,"MINOR":2}
 for i,g in enumerate(sorted(groups.values(),key=lambda x:(severity_order.get(x["severity"],9),-len(x["sources"])))):
  roadmap.append({"roadmap_id":f"RM-{i+1:03d}","priority":i+1,"severity":g["severity"],"category":g["category"],"issue":g["issue"],"impact":g["impact"],"recommended_action":g["actions"][0] if g["actions"] else None,"corroboration":len(g["sources"]),"sources":g["sources"],"claim_ids":sorted(g["claim_ids"]),"evidence_states":sorted(g["evidence_states"]),"status":"open" if "open" in g["states"] or "uncertain" in g["states"] else "resolved"})
 unresolved=len(raw_critical);mean=statistics.mean(scores) if scores else None;median=statistics.median(scores) if scores else None;minimum=min(scores) if scores else None;maximum=max(scores) if scores else None
 has_gap=any(bool(g["evidence_states"] & {"EVIDENCE_GAPS","INCONCLUSIVE"}) for g in groups.values())
 has_major=any(g["severity"]=="MAJOR" for g in groups.values())
 if not applicable:decision="NOT_ASSESSABLE"
 elif unresolved:decision="EVIDENCE_GAPS" if has_gap else "REBUILD_OR_REFRAME"
 elif mean is not None and mean>=4 and not has_major:decision="READY_WITH_MINOR_REVISIONS"
 elif mean is not None and mean>=3:decision="MAJOR_REVISION"
 else:decision="REBUILD_OR_REFRAME"
 meta={"schema_version":"robotics-meta-review.v1","meta_review_id":"META-001","review_id":context.get("review_id"),"source_reports":[r.get("report_id") for r in reports],"score_summary":{"applicable_reviewers":len(applicable),"mean":mean,"median":median,"minimum":minimum,"maximum":maximum,"spread":(maximum-minimum if scores else None),"by_reviewer":by},"consensus":[x for x in roadmap if x["corroboration"]>=2],"disagreements":[{"reviewers":[r.get("reviewer_id") for r in applicable],"type":"score_spread","spread":(maximum-minimum if scores else None)}] if scores and maximum!=minimum else [],"critical_gate":{"total":len(raw_critical),"unresolved":unresolved,"items":raw_critical},"evidence_gaps":[{"reviewer_id":r.get("reviewer_id"),"items":r.get("unassessed",[])} for r in reports if r.get("unassessed")],"revision_roadmap":roadmap,"decision":decision,"notes":[f"Invalid source reports: {len(bad)}"] if bad else []}
 Path(a.json_out).write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");lines=["# 机器人论文总修改建议 / Robotics Revision Roadmap","",f"决策 / Decision: **{decision}**",f"适用评审数 / Applicable reviewers: {len(applicable)}",f"分数 / Scores: mean={mean}, median={median}, range={minimum}–{maximum}","","## 修改项 / Revision items"]
 for item in roadmap:lines.extend([f"### {item['priority']}. [{item['severity']}] {item['category']}",f"- 问题 / Issue: {item['issue']}",f"- 影响 / Impact: {item['impact']}",f"- 行动 / Action: {item['recommended_action']}",f"- corroboration: {item['corroboration']}; sources: "+", ".join(x["report_id"]+"/"+x["finding_id"] for x in item["sources"]),""])
 if raw_critical:lines.extend(["## CRITICAL gate",""]+[f"- {x['report_id']}/{x['finding_id']}: {x['issue']} — {x['adjudication']}" for x in raw_critical])
 Path(a.markdown_out).write_text("\n".join(lines)+"\n",encoding="utf-8")
if __name__=="__main__":main()
