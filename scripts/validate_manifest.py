#!/usr/bin/env python3
"""校验确定性交接索引。 / Validate the deterministic handoff manifest."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from common.canonical_json import load_json,sha256_file
def inside(path,root):
 try:path.resolve().relative_to(root.resolve());return True
 except ValueError:return False
def main():
 p=argparse.ArgumentParser();p.add_argument("manifest");a=p.parse_args();path=Path(a.manifest);m=load_json(path);errors=[]
 for key in ("research_card","experiment_contract","result_bundle","claim_ledger","target_fit_snapshot"):
  ref=m.get(key)
  if ref is None:continue
  target=(path.parent/ref["path"]).resolve()
  if not inside(target,path.parent):errors.append(f"{key}: path escapes project")
  elif not target.is_file() or sha256_file(target)!=ref.get("sha256"):errors.append(f"{key}: missing or digest mismatch")
 print(json.dumps({"valid":not errors,"errors":errors},ensure_ascii=False,indent=2));raise SystemExit(bool(errors))
if __name__=="__main__":main()
