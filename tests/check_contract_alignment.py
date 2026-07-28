#!/usr/bin/env python3
"""V2 跨阶段静态对齐检查。 / V2 cross-stage static alignment check."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
paths={"card":ROOT/"skills/develop-robotics-idea/assets/research-card.template.json","contract":ROOT/"skills/design-robotics-experiment/assets/experiment-contract.template.json","result":ROOT/"skills/design-robotics-experiment/assets/result-bundle.template.json","ledger":ROOT/"skills/write-robotics-paper/assets/claim-ledger.template.json"}
expected={"card":"robotics-research-card.v2","contract":"robotics-experiment-contract.v2","result":"robotics-result-bundle.v2","ledger":"robotics-claim-ledger.v2"};errors=[]
for k,p in paths.items():
 x=json.loads(p.read_text())
 if x.get("schema_version")!=expected[k]:errors.append(f"{k}: wrong schema")
review_template=ROOT/"skills/review-robotic-feedback/assets/review-context.template.json"
if json.loads(review_template.read_text()).get("schema_version")!="robotics-review-context.v1":errors.append("review: wrong schema")
suffixes={".md",".py",".json",".yaml",".yml",".csv",".tex"}
blob="\n".join(p.read_text(encoding="utf-8") for p in ROOT.rglob("*") if p.is_file() and p.suffix in suffixes and ".git" not in p.parts and p.resolve()!=Path(__file__).resolve())
for forbidden in ("axis_floors","required_rung","reached_rung"):
 if forbidden in blob:errors.append(f"legacy routing token remains: {forbidden}")
print("CONTRACT_ALIGNMENT: "+("PASS" if not errors else "FAIL"))
for e in errors:print("- "+e)
raise SystemExit(bool(errors))
