#!/usr/bin/env python3
"""校验 V2 Research Card。 / Validate a V2 Research Card."""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; sys.path.insert(0,str(ROOT))
from common.canonical_json import JsonIntegrityError, load_json
from common.contract_core import (Findings, IDEA_MODES, compute_claim_digest, meaningful,
 validate_change_envelope, validate_claim_dimensions, validate_domain_packs,
 validate_finite_tree, validate_obligations)
from common.evidence_profile import validate_requirement

AXES={"problem_framing","core_mechanism","key_insight","application_or_evaluation"}
THREATS={"LOW","MEDIUM","HIGH"}

def valid_collision_audit(audit):
 if not isinstance(audit,dict) or re.fullmatch(r"[0-9a-f]{64}",str(audit.get("candidate_sha256",""))) is None:return False
 queries=audit.get("queries");sources=audit.get("sources");axes=audit.get("comparison_axes")
 if not isinstance(queries,list) or not queries or any(not meaningful(x) for x in queries):return False
 if not isinstance(sources,list) or not sources or any(not meaningful(x) for x in sources):return False
 if audit.get("closest_threat_id") not in sources:return False
 if not isinstance(axes,dict) or set(axes)!=AXES:return False
 for row in axes.values():
  if not isinstance(row,dict) or set(row)!={"closest_overlap","candidate_delta","source_ids","threat_level"}:return False
  if not meaningful(row.get("closest_overlap")) or not meaningful(row.get("candidate_delta")):return False
  ids=row.get("source_ids")
  if not isinstance(ids,list) or not ids or not set(ids)<=set(sources) or any(not meaningful(x) for x in ids):return False
  if row.get("threat_level") not in THREATS:return False
 return audit.get("verdict") in {"CLEAR","PARTIAL_COLLISION"} and meaningful(audit.get("uncovered_delta"))

def validate_mode_provenance(card,f):
 mode=card.get("mode")
 if mode=="ADOPT_LOCKED_IDEA":
  p=card.get("adoption_provenance")
  if not isinstance(p,dict) or set(p)!={"source_document_ids","adopted_claim_digest","adoption_authority","allowed_change_envelope","unresolved_evidence"}:
   f.minimum_fail("ADOPTION_PROVENANCE","adoption_provenance","ADOPT_LOCKED_IDEA requires complete adoption provenance");return
  if not isinstance(p.get("source_document_ids"),list) or not p["source_document_ids"] or any(not meaningful(x) for x in p["source_document_ids"]):f.minimum_fail("ADOPTION_PROVENANCE","adoption_provenance.source_document_ids","source documents are required")
  if re.fullmatch(r"[0-9a-f]{64}",str(p.get("adopted_claim_digest",""))) is None:f.minimum_fail("ADOPTION_PROVENANCE","adoption_provenance.adopted_claim_digest","a frozen source claim digest is required")
  if not meaningful(p.get("adoption_authority")):f.minimum_fail("ADOPTION_PROVENANCE","adoption_provenance.adoption_authority","adoption authority is required")
  if not isinstance(p.get("allowed_change_envelope"),list) or not p["allowed_change_envelope"] or any(not meaningful(x) for x in p["allowed_change_envelope"]):f.minimum_fail("ADOPTION_PROVENANCE","adoption_provenance.allowed_change_envelope","allowed changes are required")
  if not isinstance(p.get("unresolved_evidence"),list):f.minimum_fail("ADOPTION_PROVENANCE","adoption_provenance.unresolved_evidence","unresolved evidence must be recorded as a list")
 if mode=="MIGRATE_LEGACY_PROJECT":
  p=card.get("migration_provenance")
  if not isinstance(p,dict) or set(p)!={"legacy_artifact_paths","migration_snapshot","retrospective_prospective_boundary","existing_results_provenance","unresolved_lock_ambiguities"}:
   f.minimum_fail("MIGRATION_PROVENANCE","migration_provenance","MIGRATE_LEGACY_PROJECT requires complete migration provenance");return
  for key in ("legacy_artifact_paths","existing_results_provenance"):
   if not isinstance(p.get(key),list) or not p[key] or any(not meaningful(x) for x in p[key]):f.minimum_fail("MIGRATION_PROVENANCE",f"migration_provenance.{key}",f"{key} requires at least one source")
  for key in ("migration_snapshot","retrospective_prospective_boundary"):
   if not meaningful(p.get(key)):f.minimum_fail("MIGRATION_PROVENANCE",f"migration_provenance.{key}",f"{key} is required")
  if not isinstance(p.get("unresolved_lock_ambiguities"),list):f.minimum_fail("MIGRATION_PROVENANCE","migration_provenance.unresolved_lock_ambiguities","lock ambiguities must be recorded as a list")

def validate(card):
 f=Findings(); validate_finite_tree(card,f)
 if not isinstance(card,dict) or card.get("schema_version")!="robotics-research-card.v2":
  f.schema_fail("SCHEMA","schema_version","expected robotics-research-card.v2"); return f.report("robotics-research-card.v2",None,False)
 if card.get("mode") not in IDEA_MODES: f.fail("MODE","mode","unsupported mode")
 validate_change_envelope(card.get("change_envelope"),f)
 validate_claim_dimensions(card.get("claim_shape"),f,"claim_shape")
 validate_obligations(card.get("evidence_obligations"),f)
 validate_domain_packs(card.get("domain_packs"),f)
 for section,keys in (("claim_contract",("claim_id","task","system_boundary","core_claim","claim_boundary")),("mechanism_contract",("mechanism_id","mechanism","load_bearing_variable_id","load_bearing_variable","retained_invariant")),("falsification_contract",("decisive_test_id","falsification_target","stop_state_if_failed"))):
  obj=card.get(section)
  if not isinstance(obj,dict) or set(obj)!=set(keys): f.fail("SECTION",section,f"must contain exactly {list(keys)}")
  elif any(not meaningful(obj.get(k)) for k in keys): f.fail("CONTENT",section,"all fields must contain a decision")
 reqs=card.get("evidence_requirements")
 if not isinstance(reqs,list): f.fail("EVIDENCE_REQUIREMENTS","evidence_requirements","must be a list")
 else:
  for i,req in enumerate(reqs):
   for err in validate_requirement(req): f.fail("EVIDENCE_REQUIREMENT",f"evidence_requirements[{i}]",err)
 expected=compute_claim_digest(card)
 if card.get("claim_digest")!=expected: f.fail("CLAIM_DIGEST","claim_digest",f"expected {expected}")
 state=card.get("status")
 if state not in {"READY","REVISE","DO_NOT_GENERATE","ABANDON"}: f.fail("STATUS","status","unsupported terminal state")
 if state=="READY":
  if not any(card.get("claim_shape",{}).values()): f.minimum_fail("SCIENTIFIC_MINIMUM","claim_shape","READY requires at least one active claim dimension")
  mode=card.get("mode")
  validate_mode_provenance(card,f)
  if mode in {"EXPLORE_NEW","AUDIT_EXISTING_IDEA"}:
   if not card.get("evidence_requirements") and not card.get("deferred_evidence"): f.minimum_fail("SCIENTIFIC_MINIMUM","evidence_requirements","READY requires an evidence requirement or an explicit deferred-evidence record")
   if not valid_collision_audit(card.get("collision_audit")): f.minimum_fail("SCIENTIFIC_MINIMUM","collision_audit","READY requires substantive candidate-bound comparisons on all four axes")
 return f.report("robotics-research-card.v2",state,state=="READY")

def main():
 p=argparse.ArgumentParser(); p.add_argument("card"); p.add_argument("--ready",action="store_true"); a=p.parse_args()
 try: report=validate(load_json(a.card))
 except (OSError,ValueError,JsonIntegrityError) as e: report={"schema":"robotics-research-card.v2","schema_valid":False,"contract_consistent":False,"handoff_ready":False,"terminal_state":None,"findings":[{"level":"fail","code":"JSON","path":"$","message":str(e)}]}
 print(json.dumps(report,ensure_ascii=False,indent=2)); raise SystemExit(0 if (report["handoff_ready"] if a.ready else report["contract_consistent"]) else 1)
if __name__=="__main__": main()
