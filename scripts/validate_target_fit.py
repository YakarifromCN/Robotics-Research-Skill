#!/usr/bin/env python3
"""校验独立投稿适配快照。 / Validate a separate target-fit snapshot."""
import argparse,datetime as dt,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from common.canonical_json import load_json
def main():
 p=argparse.ArgumentParser();p.add_argument("snapshot");p.add_argument("--fresh",action="store_true");a=p.parse_args();x=load_json(a.snapshot);errors=[]
 if x.get("schema_version")!="robotics-target-fit.v2":errors.append("wrong schema")
 if not x.get("sources"):errors.append("official sources required")
 if a.fresh:
  try:
   expiry=dt.datetime.fromisoformat(x["expires_at"].replace("Z","+00:00"));now=dt.datetime.now(dt.timezone.utc)
   if expiry<now:errors.append("snapshot expired")
  except Exception:errors.append("invalid expires_at")
 print(json.dumps({"valid":not errors,"errors":errors},ensure_ascii=False,indent=2));raise SystemExit(bool(errors))
if __name__=="__main__":main()
