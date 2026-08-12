#!/usr/bin/env python3
"""校验双向证据约束修订工件。 / Validate bidirectional evidence-bound revision artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from common.canonical_json import load_json
from common.contract_core import Findings, meaningful, validate_finite_tree

CLASSIFICATIONS = {f"D{i}" for i in range(1, 9)} | {f"K{i}" for i in range(1, 5)}
DISPOSITIONS = {"KEEP", "TIGHTEN", "REFRAME", "RELOCATE", "DEDUPLICATE", "CUT", "QUERY"}
RHETORICAL_DELTAS = {"STRONGER", "SAME", "WEAKER"}
SEMANTIC_RELATIONS = {"WITHIN_CEILING", "NARROWER", "BROADER", "MISALIGNED"}
MODES = {"DIAGNOSTIC", "AUTHORIZED_REVISION"}
STATUSES = {"DIAGNOSED", "READY_TO_REVISE", "REVISED", "BLOCKED"}
REGRESSION_KEYS = {
    "claim_ceiling_preserved", "evidence_status_preserved", "scope_coverage_preserved",
    "citation_role_preserved", "conceptual_hierarchy_preserved", "contribution_visibility_checked",
}
DECISION_KEYS = {
    "decision_id", "source_anchor", "replacement_anchor", "classification", "disposition",
    "executed", "claim_ids", "evidentiary_function", "rhetorical_strength_delta",
    "semantic_claim_relation", "source_status_preserved", "scope_preserved",
    "citation_role_preserved", "source_result_ids", "source_number_ids",
    "source_citation_ids", "preserved_in_anchor", "preserved_by_decision_id",
}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _ids(rows: Any, key: str) -> set[str]:
    return {row.get(key) for row in rows or [] if isinstance(row, dict) and meaningful(row.get(key))}


def _after_refs(text: str) -> tuple[set[str], set[str], set[str]]:
    results = set(re.findall(r"\\resultref\{([^}]+)\}", text))
    numbers = set(re.findall(r"\\numref\{([^}]+)\}", text))
    citations = {item.strip() for group in re.findall(r"\\cite(?:[A-Za-z]*)?\{([^}]+)\}", text) for item in group.split(",") if item.strip()}
    return results, numbers, citations


def validate(audit: Any, ledger: Any = None, before_text: str | None = None, after_text: str | None = None) -> dict[str, Any]:
    f = Findings(); validate_finite_tree(audit, f)
    if not isinstance(audit, dict) or audit.get("schema_version") != "robotics-evidence-bound-revision.v1":
        f.schema_fail("SCHEMA", "schema_version", "expected robotics-evidence-bound-revision.v1")
        return f.report("robotics-evidence-bound-revision.v1", None, False)
    if audit.get("mode") not in MODES: f.schema_fail("MODE", "mode", "unsupported mode")
    if audit.get("status") not in STATUSES: f.schema_fail("STATUS", "status", "unsupported status")
    if not meaningful(audit.get("audit_id")): f.schema_fail("ID", "audit_id", "non-empty audit ID required")

    contract = audit.get("contribution_contract")
    if not isinstance(contract, dict) or set(contract) != {"core_claim_ids", "contribution_first", "qualification_in_place"}:
        f.schema_fail("CONTRIBUTION_CONTRACT", "contribution_contract", "exact contribution contract required")
        contract = {}
    if contract.get("contribution_first") is not True or contract.get("qualification_in_place") is not True:
        f.minimum_fail("CONTRIBUTION_ORDER", "contribution_contract", "contribution-first and qualification-in-place are required")
    if not isinstance(contract.get("core_claim_ids"), list) or not contract.get("core_claim_ids"):
        f.minimum_fail("CORE_CLAIM", "contribution_contract.core_claim_ids", "at least one core claim ID required")

    authority = audit.get("authority")
    if not isinstance(authority, dict) or set(authority) != {"authorized", "allowed", "forbidden", "reason"}:
        f.schema_fail("AUTHORITY", "authority", "exact authority object required")
        authority = {}
    for field in ("allowed", "forbidden"):
        if not isinstance(authority.get(field), list) or any(not meaningful(x) for x in authority.get(field, [])):
            f.schema_fail("AUTHORITY", f"authority.{field}", "must be a list of non-empty values")
    if not meaningful(authority.get("reason")): f.minimum_fail("AUTHORITY", "authority.reason", "authority reason required")
    authorized = authority.get("authorized") is True
    if audit.get("mode") == "AUTHORIZED_REVISION" and not authorized:
        f.minimum_fail("AUTHORITY", "authority.authorized", "authorized revision requires explicit authority")
    if not authorized and (audit.get("status") in {"READY_TO_REVISE", "REVISED"} or audit.get("manuscript_after_sha256")):
        f.fail("UNAUTHORIZED_EDIT", "status", "diagnostic authority cannot produce or approve edited prose")

    if audit.get("status") != "BLOCKED" and not isinstance(ledger, dict):
        f.reference_fail("LEDGER", "claim_ledger_id", "a revision audit must bind the Claim Ledger")
    if audit.get("status") != "BLOCKED" and before_text is None:
        f.minimum_fail("MANUSCRIPT_SNAPSHOT", "manuscript_before_sha256", "a revision audit requires the source manuscript snapshot")

    known_claims = known_results = known_numbers = known_citations = set()
    if isinstance(ledger, dict):
        known_claims = _ids(ledger.get("claims"), "claim_id")
        known_results = {item for row in ledger.get("claims", []) if isinstance(row, dict) for field in ("support_result_ids", "boundary_result_ids") for item in row.get(field, [])}
        known_results |= _ids(ledger.get("external_evidence_registry"), "external_evidence_id")
        known_numbers = _ids(ledger.get("numbers"), "number_id")
        known_citations = _ids(ledger.get("citations"), "citation_id")
        if audit.get("claim_ledger_id") != ledger.get("ledger_id"):
            f.reference_fail("LEDGER", "claim_ledger_id", "ledger ID mismatch")
        digest = (ledger.get("research_card") or {}).get("claim_digest")
        if not meaningful(digest) or audit.get("claim_digest") != digest:
            f.reference_fail("CLAIM_CEILING", "claim_digest", "audit must bind the frozen Claim Ledger digest")
        if authority.get("allowed") != (ledger.get("change_envelope") or {}).get("allowed") or authority.get("forbidden") != (ledger.get("change_envelope") or {}).get("forbidden"):
            f.reference_fail("AUTHORITY", "authority", "authority must reproduce the Claim Ledger change envelope")
        if not set(contract.get("core_claim_ids", [])) <= known_claims:
            f.reference_fail("CORE_CLAIM", "contribution_contract.core_claim_ids", "unknown core claim ID")

    decisions = audit.get("decisions")
    if not isinstance(decisions, list): f.schema_fail("DECISIONS", "decisions", "must be a list"); decisions = []
    decision_ids = {row.get("decision_id") for row in decisions if isinstance(row, dict)}
    if len(decision_ids) != len(decisions) or None in decision_ids:
        f.schema_fail("DECISION_ID", "decisions", "decision IDs must be non-empty and unique")
    after_results, after_numbers, after_citations = _after_refs(after_text or "")
    for index, row in enumerate(decisions):
        path = f"decisions[{index}]"
        if not isinstance(row, dict) or set(row) != DECISION_KEYS:
            f.schema_fail("DECISION", path, f"must contain exactly {sorted(DECISION_KEYS)}"); continue
        if row["classification"] not in CLASSIFICATIONS or row["disposition"] not in DISPOSITIONS:
            f.schema_fail("CLASSIFICATION", path, "unsupported classification or disposition")
        if row["rhetorical_strength_delta"] not in RHETORICAL_DELTAS or row["semantic_claim_relation"] not in SEMANTIC_RELATIONS:
            f.schema_fail("CALIBRATION", path, "unsupported rhetorical or semantic relation")
        if row["executed"] is True and not authorized: f.fail("UNAUTHORIZED_EDIT", path, "executed decision requires authority")
        if row["executed"] is True and row["semantic_claim_relation"] in {"BROADER", "MISALIGNED"}:
            f.fail("CLAIM_CEILING", path, "executed revision must remain within ceiling or narrow")
        for flag in ("source_status_preserved", "scope_preserved", "citation_role_preserved"):
            if row["executed"] is True and row[flag] is not True: f.fail("PRESERVATION", f"{path}.{flag}", "executed revision must preserve this function")
        if not isinstance(row["claim_ids"], list) or (ledger and not set(row["claim_ids"]) <= known_claims):
            f.reference_fail("CLAIM_REF", f"{path}.claim_ids", "unknown or malformed claim IDs")
        for field, known in (("source_result_ids", known_results), ("source_number_ids", known_numbers), ("source_citation_ids", known_citations)):
            values = row[field]
            if not isinstance(values, list) or len(values) != len(set(values)) or (ledger and not set(values) <= known):
                f.reference_fail("STABLE_REF", f"{path}.{field}", "stable IDs must be unique and resolve in the ledger")
        carries = bool(row["source_result_ids"] or row["source_number_ids"] or row["source_citation_ids"])
        preservation_link = meaningful(row["replacement_anchor"]) or meaningful(row["preserved_in_anchor"]) or meaningful(row["preserved_by_decision_id"])
        if row["executed"] is True and carries and not preservation_link:
            f.fail("TOKEN_CONSERVATION", path, "stable evidence objects need a preservation anchor")
        if row["executed"] is True and row["classification"].startswith("K") and row["disposition"] in {"CUT", "DEDUPLICATE", "RELOCATE"} and not preservation_link:
            f.fail("FUNCTION_COVERAGE", path, "K-class function removal needs a replacement or preserving decision")
        if row["preserved_by_decision_id"] and row["preserved_by_decision_id"] not in decision_ids:
            f.reference_fail("DECISION_REF", f"{path}.preserved_by_decision_id", "unknown preserving decision")
        if row["executed"] is True and row["disposition"] == "CUT" and not row["classification"].startswith("K") and row["evidentiary_function"] != "RHETORICAL_ONLY" and not preservation_link:
            f.fail("CUT_GATE", path, "CUT may remove rhetoric, not an unpreserved evidentiary function")
        if row["executed"] is True and after_text is not None:
            if not set(row["source_result_ids"]) <= after_results: f.fail("TOKEN_CONSERVATION", f"{path}.source_result_ids", "result reference missing after revision")
            if not set(row["source_number_ids"]) <= after_numbers: f.fail("TOKEN_CONSERVATION", f"{path}.source_number_ids", "number reference missing after revision")
            if not set(row["source_citation_ids"]) <= after_citations: f.fail("TOKEN_CONSERVATION", f"{path}.source_citation_ids", "citation reference missing after revision")

    queries = audit.get("open_queries")
    if not isinstance(queries, list): f.schema_fail("QUERIES", "open_queries", "must be a list"); queries = []
    for index, query in enumerate(queries):
        if not isinstance(query, dict) or set(query) != {"query_id", "decision_id", "status", "resolution"}:
            f.schema_fail("QUERY", f"open_queries[{index}]", "exact query object required"); continue
        if query["decision_id"] not in decision_ids: f.reference_fail("QUERY", f"open_queries[{index}].decision_id", "unknown decision")
        if query["status"] not in {"OPEN", "RESOLVED"}: f.schema_fail("QUERY", f"open_queries[{index}].status", "unsupported query status")
        if query["status"] == "OPEN" and any(row.get("decision_id") == query["decision_id"] and row.get("executed") for row in decisions):
            f.fail("QUERY_GATE", f"open_queries[{index}]", "unresolved meaning cannot be edited")

    if before_text is not None and audit.get("manuscript_before_sha256") != sha256_text(before_text):
        f.reference_fail("MANUSCRIPT_HASH", "manuscript_before_sha256", "before manuscript hash mismatch")
    if after_text is not None and audit.get("manuscript_after_sha256") != sha256_text(after_text):
        f.reference_fail("MANUSCRIPT_HASH", "manuscript_after_sha256", "after manuscript hash mismatch")
    if audit.get("status") == "REVISED":
        regression = audit.get("regression")
        if not isinstance(regression, dict) or set(regression) != REGRESSION_KEYS or not all(regression.values()):
            f.minimum_fail("REGRESSION", "regression", "all whole-manuscript regression gates must pass")
        if not authorized or before_text is None or after_text is None:
            f.minimum_fail("REVISION_EVIDENCE", "status", "REVISED requires authority and both manuscript snapshots")
    ready = audit.get("status") in {"DIAGNOSED", "READY_TO_REVISE", "REVISED"}
    return f.report("robotics-evidence-bound-revision.v1", audit.get("status"), ready)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("audit"); parser.add_argument("--ledger"); parser.add_argument("--before"); parser.add_argument("--after"); parser.add_argument("--ready", action="store_true")
    args = parser.parse_args()
    before = Path(args.before).read_text(encoding="utf-8") if args.before else None
    after = Path(args.after).read_text(encoding="utf-8") if args.after else None
    report = validate(load_json(args.audit), load_json(args.ledger) if args.ledger else None, before, after)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if (report["handoff_ready"] if args.ready else report["contract_consistent"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
