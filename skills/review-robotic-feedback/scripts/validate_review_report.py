#!/usr/bin/env python3
"""规范化并校验机器人评审报告。

Normalize and validate robotics review reports before any synthesis happens.
The normalizer is intentionally conservative: it can migrate legacy nullable
IDs and legacy section names, but it never invents scientific evidence.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

try:
    from common.canonical_json import JsonIntegrityError, load_json
    from common.contract_core import Findings, validate_finite_tree
except ModuleNotFoundError:  # 独立安装兼容 / standalone installed Skill
    from review_runtime import JsonIntegrityError, Findings, load_json, validate_finite_tree


REVIEWERS = {
    "manuscript-proofreading",
    "contribution-calibration-review",
    "robotics-contribution-review",
    "control-optimization-review",
    "robot-learning-review",
    "hardware-review",
    "evidence-artifact-audit",
    "venue-compliance-review",
}
SEVERITIES = {"CRITICAL", "MAJOR", "MINOR"}
STATES = {"open", "uncertain", "resolved"}
EVIDENCE = {"SUPPORTED", "PARTIALLY_SUPPORTED", "NOT_SUPPORTED", "INCONCLUSIVE", "EVIDENCE_GAPS", "UNASSESSED"}
RECOMMENDATIONS = {
    "READY_TO_SUBMIT",
    "READY_WITH_MINOR_REVISIONS",
    "MAJOR_REVISION",
    "REBUILD_OR_REFRAME",
    "EVIDENCE_GAPS",
    "NOT_ASSESSABLE",
}
ROLES = {"primary", "corroborating"}
ACTION_KINDS = {"revise", "preserve", "monitor", "none"}
EVIDENCE_CLAIM_RELATIONS = {"OVER_CEILING", "AT_CEILING", "BELOW_CEILING", "MISALIGNED"}
CRITICAL_BASES = {
    "DESIGN_LOCK_BREACH",
    "CHANGE_REQUEST_TO_IDEA",
    "EVIDENCE_INTEGRITY",
    "SAFETY",
    "REPRODUCIBILITY",
    "CLAIM_EVIDENCE_MISMATCH",
    "VENUE_BLOCKER",
    "OTHER_DOCUMENTED",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def anchor(value: Any, fallback: str) -> dict[str, str]:
    if isinstance(value, dict) and nonempty(value.get("type")) and nonempty(value.get("value")):
        return {"type": str(value["type"]), "value": str(value["value"])}
    return {"type": "migration_fallback", "value": fallback}


def location(value: Any, fallback: str = "unknown") -> dict[str, str]:
    if isinstance(value, dict) and nonempty(value.get("file")) and nonempty(value.get("anchor")):
        return {"file": str(value["file"]), "anchor": str(value["anchor"])}
    return {"file": "unknown", "anchor": fallback}


def normalize_strength(value: Any, index: int, warnings: list[str]) -> dict[str, Any]:
    if isinstance(value, dict):
        result = copy.deepcopy(value)
        result.setdefault("strength_id", f"STR-{index:03d}")
        result.setdefault("category", "unspecified_strength")
        result.setdefault("statement", result.get("issue") or result.get("description") or "未命名强项 / unnamed strength")
        result["evidence_anchor"] = anchor(result.get("evidence_anchor"), result["statement"])
        result["claim_ids"] = result.get("claim_ids") if isinstance(result.get("claim_ids"), list) else []
        canonical = {"strength_id", "category", "statement", "evidence_anchor", "claim_ids"}
        result = {key: result.get(key) for key in canonical}
    else:
        result = {
            "strength_id": f"STR-{index:03d}",
            "category": "legacy_strength",
            "statement": str(value),
            "evidence_anchor": anchor(None, str(value)),
            "claim_ids": [],
        }
        warnings.append("legacy strength string normalized to review-strength.v1")
    return result


def normalize_gap(value: Any, index: int, warnings: list[str]) -> dict[str, Any]:
    if isinstance(value, dict):
        result = {
            "gap_id": value.get("gap_id") or f"GAP-{index:03d}",
            "category": value.get("category") or "unspecified_gap",
            "location": location(value.get("location"), "gap location unavailable"),
            "description": value.get("description") or value.get("issue") or "未说明的证据缺口 / unspecified evidence gap",
            "impact": value.get("impact") or "影响无法评估",
            "action": value.get("action") or "补充可审计材料或收窄主张",
            "evidence_state": value.get("evidence_state") or "EVIDENCE_GAPS",
        }
    else:
        result = {
            "gap_id": f"GAP-{index:03d}",
            "category": "legacy_gap",
            "location": location(None, "legacy evidence gap"),
            "description": str(value),
            "impact": "影响无法评估",
            "action": "补充可审计材料或收窄主张",
            "evidence_state": "EVIDENCE_GAPS",
        }
        warnings.append("legacy evidence gap normalized to one object schema")
    return result


def normalize_not_assessable(value: Any, index: int, warnings: list[str]) -> dict[str, str]:
    if isinstance(value, dict):
        result = {
            "item_id": value.get("item_id") or f"NA-{index:03d}",
            "scope": value.get("scope") or value.get("category") or "unspecified",
            "reason": value.get("reason") or value.get("description") or "材料不足，无法评估",
        }
    else:
        result = {"item_id": f"NA-{index:03d}", "scope": "unspecified", "reason": str(value)}
        warnings.append("legacy unassessed item normalized to not_assessable object")
    return result


def normalize_finding(value: Any, index: int, warnings: list[str]) -> dict[str, Any]:
    raw = value if isinstance(value, dict) else {"issue": str(value)}
    result = copy.deepcopy(raw)
    result.setdefault("finding_id", f"F-{index:03d}")
    result.setdefault("severity", "MINOR")
    result.setdefault("category", "unspecified")
    result["location"] = location(result.get("location"), "finding location unavailable")
    result["evidence_anchor"] = anchor(result.get("evidence_anchor"), str(result.get("issue") or "finding evidence unavailable"))
    result.setdefault("issue", "未说明的问题 / unspecified issue")
    result.setdefault("impact", "影响未说明 / impact unspecified")
    result.setdefault("action", "检查并记录处理决定 / inspect and record disposition")
    result.setdefault("state", "open")
    result["claim_ids"] = result.get("claim_ids") if isinstance(result.get("claim_ids"), list) else []
    result.setdefault("evidence_state", "INCONCLUSIVE")
    result["role"] = result.get("role") or result.get("finding_role") or "primary"
    result["critical_basis"] = result.get("critical_basis")
    result["action_kind"] = result.get("action_kind") or ("preserve" if result.get("state") == "resolved" else "revise")
    result["resolution_note"] = result.get("resolution_note")
    if "evidence_claim_relation" not in result:
        result["evidence_claim_relation"] = None
    burden = result.get("objection_burden")
    if burden is not None and isinstance(burden, dict):
        burden_keys = {"target_claim_id", "claimed_scope", "specific_gap", "why_this_gap_invalidates_or_weakens_the_claim", "required_action"}
        burden = {key: burden.get(key) for key in burden_keys}
    result["objection_burden"] = burden
    required = {
        "finding_id", "severity", "category", "location", "evidence_anchor", "issue", "impact", "action",
        "state", "claim_ids", "evidence_state", "role", "critical_basis", "action_kind", "resolution_note",
        "evidence_claim_relation", "objection_burden",
    }
    result = {key: result.get(key) for key in required}
    if isinstance(value, dict) and "role" not in value:
        warnings.append(f"finding {result['finding_id']} received default role=primary")
    return result


def normalize_report(report: Any) -> tuple[dict[str, Any], list[str]]:
    """Return a canonical report and migration warnings.

    ``report_id`` is never allowed to remain null.  A legacy nullable value is
    retained in ``normalization_audit`` while synthesis uses the deterministic
    ``review_id::reviewer_id`` fallback.
    """

    if not isinstance(report, dict):
        return {"_invalid": report}, ["report is not an object"]
    x = copy.deepcopy(report)
    warnings: list[str] = []
    reviewer = x.get("reviewer_id")
    review_id = x.get("review_id") or "UNSPECIFIED_REVIEW"
    original_id = x.get("report_id")
    if not nonempty(original_id):
        if nonempty(reviewer):
            x["report_id"] = f"{review_id}::{reviewer}"
        else:
            x["report_id"] = f"{review_id}::UNSPECIFIED_REVIEWER"
        warnings.append("nullable or missing report_id normalized to deterministic fallback")
    if "applicability" not in x or not isinstance(x.get("applicability"), dict):
        x["applicability"] = {"applicable": True, "reason": "legacy report did not state applicability"}
        warnings.append("missing applicability normalized")
    elif x["applicability"].get("applicable") is True and not nonempty(x["applicability"].get("reason")):
        x["applicability"]["reason"] = "适用范围由当前评审配置覆盖；旧报告未提供理由 / applicable by configured review scope"
        warnings.append("applicability.reason was missing and was normalized")
    x.setdefault("assessed_scope", [])
    x.setdefault("mode", "full")
    x.setdefault("summary", "未提供摘要 / summary unavailable")
    x.setdefault("score", {"overall": None, "confidence": 1, "dimensions": {}})
    x.setdefault("generated_at", now_iso())
    if not x.get("generated_at"):
        x["generated_at"] = now_iso()
        warnings.append("missing generated_at normalized")

    legacy_raw = x.get("positive_findings") or []
    if isinstance(legacy_raw, str):
        legacy_strengths = [legacy_raw]
        warnings.append("string positive_findings normalized to a one-item list")
    else:
        legacy_strengths = list(legacy_raw) if isinstance(legacy_raw, list) else []
    raw_strengths = x.get("strengths") or []
    if isinstance(raw_strengths, str):
        raw_strengths = [raw_strengths]
        warnings.append("string strengths normalized to a one-item list")
    strengths = list(raw_strengths) if isinstance(raw_strengths, list) else []
    strengths += legacy_strengths
    x["strengths"] = [normalize_strength(item, index + 1, warnings) for index, item in enumerate(strengths)]
    if legacy_strengths:
        warnings.append("deprecated positive_findings merged into strengths")

    findings: list[dict[str, Any]] = []
    raw_findings = x.get("findings") or []
    if isinstance(raw_findings, dict):
        raw_findings = [raw_findings]
        warnings.append("object findings normalized to a one-item list")
    elif isinstance(raw_findings, str):
        raw_findings = [raw_findings]
        warnings.append("string findings normalized to a one-item list")
    elif not isinstance(raw_findings, list):
        raw_findings = []
        warnings.append("unsupported findings shape normalized to an empty list")
    for index, item in enumerate(raw_findings, 1):
        normalized = normalize_finding(item, index, warnings)
        # Older runs sometimes encoded a positive, already-resolved strength as
        # a MINOR finding.  Preserve it as a strength, never as an open defect.
        if normalized["state"] == "resolved" and normalized["severity"] != "CRITICAL" and normalized["action_kind"] == "preserve":
            x["strengths"].append(normalize_strength({
                "strength_id": f"STR-LEGACY-{index:03d}",
                "category": normalized["category"],
                "statement": normalized["issue"],
                "evidence_anchor": normalized["evidence_anchor"],
                "claim_ids": normalized["claim_ids"],
            }, len(x["strengths"]) + 1, warnings))
            warnings.append(f"resolved finding {normalized['finding_id']} moved to protected strengths")
        else:
            findings.append(normalized)
    x["findings"] = findings

    raw_gaps = x.get("evidence_gaps")
    if raw_gaps is None:
        raw_gaps = []
        if "evidence_gaps" in x:
            warnings.append("null evidence_gaps normalized to an empty list")
    if isinstance(raw_gaps, str):
        raw_gaps = [raw_gaps]
        warnings.append("string evidence_gaps normalized to a one-item list")
    elif isinstance(raw_gaps, dict):
        raw_gaps = [raw_gaps]
        warnings.append("object evidence_gaps normalized to a one-item list")
    elif not isinstance(raw_gaps, list):
        raw_gaps = []
        warnings.append("unsupported evidence_gaps shape normalized to an empty list")
    x["evidence_gaps"] = [normalize_gap(item, index + 1, warnings) for index, item in enumerate(raw_gaps)]
    legacy_unassessed = x.pop("unassessed", []) or []
    if isinstance(legacy_unassessed, str) or isinstance(legacy_unassessed, dict):
        legacy_unassessed = [legacy_unassessed]
        warnings.append("scalar unassessed normalized to a one-item list")
    raw_na_value = x.get("not_assessable") or []
    if isinstance(raw_na_value, (str, dict)):
        raw_na_value = [raw_na_value]
        warnings.append("scalar not_assessable normalized to a one-item list")
    raw_na = (list(raw_na_value) if isinstance(raw_na_value, list) else []) + (list(legacy_unassessed) if isinstance(legacy_unassessed, list) else [])
    x["not_assessable"] = [normalize_not_assessable(item, index + 1, warnings) for index, item in enumerate(raw_na)]
    if legacy_unassessed:
        warnings.append("deprecated unassessed merged into not_assessable")
    x["normalization_audit"] = {
        "original_report_id": original_id,
        "warnings": warnings,
    }
    return x, warnings


def validate(x: Any) -> dict[str, Any]:
    findings = Findings()
    validate_finite_tree(x, findings)
    normalized, warnings = normalize_report(x)
    if not isinstance(x, dict):
        findings.fail("SCHEMA", "$", "report must be a JSON object")
        return findings.report("robotics-review-report.v1", None, False)
    if normalized.get("schema_version") != "robotics-review-report.v1":
        findings.fail("SCHEMA", "schema_version", "expected robotics-review-report.v1")
    if not nonempty(normalized.get("report_id")):
        findings.fail("REPORT_ID", "report_id", "must be a non-empty string after normalization")
    if normalized.get("reviewer_id") not in REVIEWERS:
        findings.fail("REVIEWER_ID", "reviewer_id", "unknown specialist reviewer")
    if not nonempty(normalized.get("review_id")):
        findings.fail("REVIEW_ID", "review_id", "must be a non-empty string")
    app = normalized.get("applicability")
    if not isinstance(app, dict) or set(app) != {"applicable", "reason"} or type(app.get("applicable")) is not bool or not nonempty(app.get("reason")):
        findings.fail("APPLICABILITY", "applicability", "must contain Boolean applicable and a non-empty reason")
    score = normalized.get("score")
    if not isinstance(score, dict) or set(score) != {"overall", "confidence", "dimensions"}:
        findings.fail("SCORE", "score", "must contain overall, confidence, dimensions")
    else:
        overall = score.get("overall")
        if app.get("applicable") is True and (type(overall) is not int or not 1 <= overall <= 5):
            findings.fail("SCORE", "score.overall", "applicable reports need integer 1–5")
        if app.get("applicable") is False and overall is not None:
            findings.fail("SCORE", "score.overall", "non-applicable reports must use null overall")
        if type(score.get("confidence")) is not int or not 1 <= score["confidence"] <= 5:
            findings.fail("SCORE", "score.confidence", "must be integer 1–5")
        if not isinstance(score.get("dimensions"), dict):
            findings.fail("SCORE", "score.dimensions", "must be an object")
    if not isinstance(normalized.get("assessed_scope"), list) or any(not nonempty(item) for item in normalized["assessed_scope"]):
        findings.fail("SCOPE", "assessed_scope", "must be a list of non-empty strings")
    if not nonempty(normalized.get("summary")):
        findings.fail("CONTENT", "summary", "must be a non-empty string")

    required = {
        "finding_id", "severity", "category", "location", "evidence_anchor", "issue", "impact", "action",
        "state", "claim_ids", "evidence_state", "role", "critical_basis", "action_kind", "resolution_note",
        "evidence_claim_relation", "objection_burden",
    }
    for index, item in enumerate(normalized.get("findings", [])):
        path = f"findings[{index}]"
        if not isinstance(item, dict) or set(item) != required:
            findings.fail("FINDING", path, f"must contain exactly {sorted(required)}")
            continue
        if item["severity"] not in SEVERITIES:
            findings.fail("FINDING", f"{path}.severity", "unsupported severity")
        if item["state"] not in STATES:
            findings.fail("FINDING", f"{path}.state", "unsupported finding state")
        if item["evidence_state"] not in EVIDENCE:
            findings.fail("FINDING", f"{path}.evidence_state", "unsupported evidence state")
        if item["role"] not in ROLES:
            findings.fail("FINDING", f"{path}.role", "must be primary or corroborating")
        if item["action_kind"] not in ACTION_KINDS:
            findings.fail("FINDING", f"{path}.action_kind", "unsupported action kind")
        if item["evidence_claim_relation"] not in EVIDENCE_CLAIM_RELATIONS:
            findings.fail("CALIBRATION", f"{path}.evidence_claim_relation", "unsupported evidence–claim relation")
        if not nonempty(item["finding_id"]) or not nonempty(item["category"]) or not nonempty(item["issue"]) or not nonempty(item["impact"]) or not nonempty(item["action"]):
            findings.fail("FINDING", path, "IDs, category, issue, impact, and action must be non-empty")
        if not isinstance(item["claim_ids"], list) or any(not nonempty(value) for value in item["claim_ids"]):
            findings.fail("FINDING", f"{path}.claim_ids", "must be a list of strings")
        loc = item["location"]
        if not isinstance(loc, dict) or set(loc) != {"file", "anchor"} or not nonempty(loc.get("file")) or not nonempty(loc.get("anchor")):
            findings.fail("ANCHOR", f"{path}.location", "must contain non-empty file and anchor")
        evidence = item["evidence_anchor"]
        if not isinstance(evidence, dict) or set(evidence) != {"type", "value"} or not nonempty(evidence.get("type")) or not nonempty(evidence.get("value")):
            findings.fail("ANCHOR", f"{path}.evidence_anchor", "typed non-empty anchor required")
        if item["severity"] == "CRITICAL" and (item["critical_basis"] not in CRITICAL_BASES or not nonempty(evidence.get("value"))):
            findings.fail("CRITICAL", path, "CRITICAL needs a documented basis and evidence anchor")
        if item["severity"] in {"MAJOR", "CRITICAL"}:
            burden = item.get("objection_burden")
            burden_keys = {"target_claim_id", "claimed_scope", "specific_gap", "why_this_gap_invalidates_or_weakens_the_claim", "required_action"}
            if not isinstance(burden, dict) or set(burden) != burden_keys or not all(nonempty(burden.get(key)) for key in burden_keys):
                findings.fail("OBJECTION_BURDEN", f"{path}.objection_burden", "MAJOR/CRITICAL must identify the threatened claim, scope, gap, logical impact, and required action")
            elif burden["target_claim_id"] not in item["claim_ids"]:
                findings.fail("OBJECTION_BURDEN", f"{path}.objection_burden.target_claim_id", "target claim must occur in finding claim_ids")
        if item["category"] == "OPTIONAL_EXTENSION" and not (
            item["severity"] == "MINOR" and item["state"] == "resolved" and item["action_kind"] == "monitor"
            and item["evidence_claim_relation"] == "AT_CEILING" and nonempty(item.get("resolution_note"))
        ):
            findings.fail("OPTIONAL_EXTENSION", path, "unrelated desirable work must be resolved MINOR/monitor at the current ceiling")
        if item["state"] == "resolved" and item["action_kind"] == "revise":
            findings.fail("STATE_ACTION", path, "resolved finding cannot still require revision")
        if item["state"] == "resolved" and not nonempty(item["resolution_note"]):
            findings.fail("STATE_ACTION", path, "resolved finding needs a resolution_note")

    for index, item in enumerate(normalized.get("strengths", [])):
        path = f"strengths[{index}]"
        required_strength = {"strength_id", "category", "statement", "evidence_anchor", "claim_ids"}
        if not isinstance(item, dict) or set(item) != required_strength:
            findings.fail("STRENGTH", path, f"must contain exactly {sorted(required_strength)}")
            continue
        if not all(nonempty(item.get(key)) for key in ("strength_id", "category", "statement")):
            findings.fail("STRENGTH", path, "strength fields must be non-empty")
        if not isinstance(item.get("claim_ids"), list):
            findings.fail("STRENGTH", f"{path}.claim_ids", "must be a list")
    for field, required_keys in (("evidence_gaps", {"gap_id", "category", "location", "description", "impact", "action", "evidence_state"}), ("not_assessable", {"item_id", "scope", "reason"})):
        values = normalized.get(field)
        if not isinstance(values, list):
            findings.fail("SECTION", field, "must be an array")
            continue
        for index, item in enumerate(values):
            if not isinstance(item, dict) or set(item) != required_keys:
                findings.fail("SECTION", f"{field}[{index}]", f"must contain exactly {sorted(required_keys)}")
    recommendation = normalized.get("recommendation")
    if recommendation not in RECOMMENDATIONS:
        findings.fail("RECOMMENDATION", "recommendation", "unsupported recommendation")
    if recommendation in {"READY_TO_SUBMIT", "READY_WITH_MINOR_REVISIONS"} and any(item.get("severity") == "CRITICAL" and item.get("state") in {"open", "uncertain"} for item in normalized.get("findings", [])):
        findings.fail("CRITICAL_GATE", "recommendation", "READY recommendation is invalid with unresolved CRITICAL finding")
    report_findings = normalized.get("findings", [])
    if report_findings and all(item.get("category") == "OPTIONAL_EXTENSION" for item in report_findings) and recommendation in {"MAJOR_REVISION", "REBUILD_OR_REFRAME", "EVIDENCE_GAPS"}:
        findings.fail("OPTIONAL_EXTENSION", "recommendation", "optional extensions cannot force a major, rebuild, or evidence-gap recommendation")
    report = findings.report("robotics-review-report.v1", recommendation, recommendation in RECOMMENDATIONS)
    report["normalization_warnings"] = warnings
    return report


def configured_reviewers(context: dict[str, Any]) -> list[str]:
    raw = context.get("reviewer_configuration")
    if not isinstance(raw, list) or not raw:
        return sorted(REVIEWERS)
    result = []
    for item in raw:
        result.append(item.get("reviewer_id") if isinstance(item, dict) else item)
    return [str(item) for item in result if nonempty(item)]


def validate_report_set(context: dict[str, Any], reports: list[dict[str, Any]]) -> dict[str, Any]:
    expected = configured_reviewers(context)
    normalized = [normalize_report(item)[0] for item in reports]
    reviewer_ids = [item.get("reviewer_id") for item in normalized]
    report_ids = [item.get("report_id") for item in normalized]
    errors: list[str] = []
    missing = sorted(set(expected) - set(reviewer_ids))
    unexpected = sorted(set(reviewer_ids) - set(expected))
    duplicates = sorted({item for item in reviewer_ids if reviewer_ids.count(item) > 1 and item})
    duplicate_reports = sorted({item for item in report_ids if report_ids.count(item) > 1 and item})
    if missing:
        errors.append("missing reviewers: " + ", ".join(missing))
    if unexpected:
        errors.append("unexpected reviewers: " + ", ".join(unexpected))
    if duplicates:
        errors.append("duplicate reviewer_id: " + ", ".join(duplicates))
    if duplicate_reports:
        errors.append("duplicate report_id: " + ", ".join(duplicate_reports))
    finding_keys: list[tuple[str, str]] = []
    for report in normalized:
        for finding in report.get("findings", []):
            finding_keys.append((str(report.get("reviewer_id")), str(finding.get("finding_id"))))
    duplicate_findings = sorted({item for item in finding_keys if finding_keys.count(item) > 1})
    if duplicate_findings:
        errors.append("duplicate reviewer/finding_id: " + ", ".join(f"{a}/{b}" for a, b in duplicate_findings))
    report_checks = [validate(item) for item in normalized]
    invalid = [check for check in report_checks if not check["contract_consistent"]]
    if invalid:
        errors.append(f"invalid reports: {len(invalid)}")
    return {"valid": not errors, "expected_reviewers": expected, "present_reviewers": sorted(set(reviewer_ids)), "missing_reviewers": missing, "unexpected_reviewers": unexpected, "errors": errors, "reports": report_checks, "normalized_reports": normalized}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("reports", nargs="+")
    parser.add_argument("--strict", action="store_true", help="将迁移警告视为失败")
    args = parser.parse_args()
    output = []
    ok = True
    for raw in args.reports:
        try:
            source = load_json(raw)
            checked = validate(source)
            if args.strict and checked.get("normalization_warnings"):
                checked["contract_consistent"] = False
                checked["schema_valid"] = False
                checked["handoff_ready"] = False
                checked.setdefault("findings", []).append({"level": "fail", "code": "STRICT_MIGRATION", "path": "$", "message": "normalization warnings present"})
        except (OSError, ValueError, JsonIntegrityError) as exc:
            checked = {"schema": "robotics-review-report.v1", "schema_valid": False, "contract_consistent": False, "handoff_ready": False, "terminal_state": None, "findings": [{"level": "fail", "code": "JSON", "path": "$", "message": str(exc)}]}
        checked["path"] = str(raw)
        output.append(checked)
        ok = ok and bool(checked.get("contract_consistent"))
    print(__import__("json").dumps({"valid": bool(ok), "reports": output}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
