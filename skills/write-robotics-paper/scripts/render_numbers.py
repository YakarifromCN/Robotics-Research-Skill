#!/usr/bin/env python3
"""由 Ledger 渲染冻结数字。 / Render frozen numbers from the ledger."""
import argparse,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from common.canonical_json import load_json,finite_number
def render(text,ledger):
 values={n["number_id"]:n for n in ledger.get("numbers",[]) if finite_number(n.get("value"))}
 def sub(m):
  key=m.group(1)
  if key not in values:raise ValueError(f"unknown number token {key}")
  n=values[key];digits=n.get("precision",3);value=f"{n['value']:.{digits}f}";return value+(f" {n['unit']}" if n.get("unit") else "")
 out=re.sub(r"\{\{(N\d{3,})\}\}",sub,text)
 remain=re.findall(r"\{\{N\d{3,}\}\}",out)
 if remain:raise ValueError(f"unrendered tokens: {remain}")
 return out
def main():
 p=argparse.ArgumentParser();p.add_argument("manuscript");p.add_argument("ledger");p.add_argument("--output",required=True);a=p.parse_args();Path(a.output).write_text(render(Path(a.manuscript).read_text(encoding="utf-8"),load_json(a.ledger)),encoding="utf-8")
if __name__=="__main__":main()
