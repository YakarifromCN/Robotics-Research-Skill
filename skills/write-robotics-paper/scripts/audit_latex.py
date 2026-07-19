#!/usr/bin/env python3
"""轻量 LaTeX 主张审计。 / Lightweight LaTeX claim audit."""
import argparse,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from common.canonical_json import load_json
TERMS=["robust","real-time","safe","lightweight","significant","generaliz","universal","first","comprehensive","鲁棒","实时","安全","轻量","显著","泛化","普适","首次","全面","任意环境"]
NUM=re.compile(r"(?<![A-Za-z])(?:\\num\{[^}]+\}|\\SI\{[^}]+\}\{[^}]+\}|[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)")
def audit(text,ledger):
 stripped=re.sub(r"%.*","",text);findings=[]
 for term in TERMS:
  if re.search(re.escape(term),stripped,re.I):findings.append({"level":"warn","code":"CLAIM_SCOPE_TERM","term":term})
 if "{{N" in stripped:findings.append({"level":"fail","code":"UNRENDERED_NUMBER"})
 known={str(n.get("value")) for n in ledger.get("numbers",[])}
 for token in NUM.findall(stripped):
  if token.startswith("\\"):continue
  if token not in known and not re.fullmatch(r"(?:19|20)\d{2}",token):findings.append({"level":"warn","code":"UNTRACKED_NUMBER","value":token})
 return findings
def main():
 p=argparse.ArgumentParser();p.add_argument("manuscript");p.add_argument("ledger");a=p.parse_args();f=audit(Path(a.manuscript).read_text(encoding="utf-8"),load_json(a.ledger));print(json.dumps({"valid":not any(x["level"]=="fail" for x in f),"findings":f},ensure_ascii=False,indent=2));raise SystemExit(1 if any(x["level"]=="fail" for x in f) else 0)
if __name__=="__main__":main()
