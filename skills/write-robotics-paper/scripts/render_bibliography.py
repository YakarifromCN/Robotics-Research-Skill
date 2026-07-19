#!/usr/bin/env python3
"""从已核验 Ledger 引文生成最小 BibTeX。 / Render minimal BibTeX from verified ledger citations."""
import argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from common.canonical_json import load_json
def main():
 p=argparse.ArgumentParser();p.add_argument("ledger");p.add_argument("--output",required=True);a=p.parse_args();entries=[]
 for c in load_json(a.ledger).get("citations",[]):
  if not c.get("verified"):raise ValueError(f"citation {c.get('citation_id')} is not verified")
  entries.append(f"@article{{{c['citation_id']},\n  title={{{c['title']}}},\n  author={{{c['authors']}}},\n  year={{{c['year']}}},\n  doi={{{c.get('doi','')}}}\n}}")
 Path(a.output).write_text("\n\n".join(entries)+"\n",encoding="utf-8")
if __name__=="__main__":main()
