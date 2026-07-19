#!/usr/bin/env python3
"""把旧项目提取为 V2 待审草稿；不猜测科学语义。 / Extract legacy projects into V2 review drafts without guessing science."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from common.canonical_json import load_json,write_json
def main():
 p=argparse.ArgumentParser();p.add_argument("legacy");p.add_argument("--kind",choices=["idea","experiment","writing"],required=True);p.add_argument("--output",required=True);a=p.parse_args();old=load_json(a.legacy)
 template={"idea":ROOT/"skills/develop-robotics-idea/assets/research-card.template.json","experiment":ROOT/"skills/design-robotics-experiment/assets/experiment-contract.template.json","writing":ROOT/"skills/write-robotics-paper/assets/claim-ledger.template.json"}[a.kind]
 new=load_json(template);new["mode"]={"idea":"MIGRATE_LEGACY_PROJECT","experiment":"RETROSPECTIVE_AUDIT","writing":"WRITING_ONLY"}[a.kind];new["status"]="REVISE" if a.kind!="writing" else "EVIDENCE_GAPS";new["migration_note"]={"source_schema":old.get("schema_version"),"design_timing":"retrospective","unmapped_paths":sorted(old.keys()),"warning":"需要人工审计；不得称为预注册 / human audit required; not preregistered"};write_json(a.output,new)
if __name__=="__main__":main()
