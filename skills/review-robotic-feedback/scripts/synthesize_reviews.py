#!/usr/bin/env python3
"""安全合并独立评审并生成 Meta Review 与修改路线。

Safely synthesize independent reviews into a traceable Meta Review and roadmap.
The script refuses incomplete panels or snapshot drift and writes JSON/Markdown
atomically so a failed render cannot masquerade as a completed review.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import json
import os
import re
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

try:
    from common.canonical_json import JsonIntegrityError, load_json, sha256_file, write_json
except ModuleNotFoundError:  # 独立安装兼容 / standalone installed Skill
    from review_runtime import JsonIntegrityError, load_json, sha256_file, write_json
from review_language import language_mode, normalize_language
from validate_review_report import normalize_report, validate, validate_report_set


SEVERITY_ORDER = {"CRITICAL": 0, "MAJOR": 1, "MINOR": 2}


class SynthesisFailure(RuntimeError):
    def __init__(self, stage: str, message: str, details: Any = None):
        super().__init__(message)
        self.stage = stage
        self.details = details


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def norm(value: Any) -> str:
    return re.sub(r"\W+", " ", str(value or "").lower(), flags=re.UNICODE).strip()


def tokens(value: Any) -> set[str]:
    return {item for item in norm(value).split() if len(item) > 1}


def similarity(left: Any, right: Any) -> float:
    a, b = tokens(left), tokens(right)
    jaccard = len(a & b) / len(a | b) if a and b else 0.0
    sequence = difflib.SequenceMatcher(None, norm(left), norm(right)).ratio()
    return max(jaccard, sequence)


def source_report_id(report: dict[str, Any]) -> str:
    value = report.get("report_id") or report.get("reviewer_id")
    return str(value or "UNIDENTIFIED_REPORT")


def source_finding_id(report: dict[str, Any], finding: dict[str, Any]) -> str:
    return f"{source_report_id(report)}/{finding.get('finding_id') or 'UNIDENTIFIED_FINDING'}"


def context_root(context: dict[str, Any], context_path: Path) -> Path:
    value = context.get("paper", {}).get("root")
    return Path(value).resolve() if value else context_path.parent.resolve()


def verify_snapshot(context: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for item in context.get("artifact_manifest", []):
        if not isinstance(item, dict) or not item.get("exists"):
            continue
        path = Path(str(item.get("path"))).resolve()
        if not path.is_file():
            errors.append(f"missing after discovery: {path}")
        elif item.get("sha256") and sha256_file(path) != item.get("sha256"):
            errors.append(f"digest mismatch after discovery: {path}")
    return errors


def adjudicate_critical(finding: dict[str, Any]) -> tuple[str, str]:
    state = finding.get("state")
    evidence = finding.get("evidence_state")
    if state == "resolved":
        return "rejected_with_reason", "source reviewer marked this finding resolved"
    if evidence == "NOT_SUPPORTED":
        return "rejected_with_reason", "source evidence state is NOT_SUPPORTED"
    if evidence in {"INCONCLUSIVE", "EVIDENCE_GAPS", "UNASSESSED"}:
        return "not_assessable", f"source evidence state is {evidence}"
    if state in {"open", "uncertain"} and evidence in {"SUPPORTED", "PARTIALLY_SUPPORTED"}:
        return "validated", f"source state={state} with evidence_state={evidence}"
    return "unresolved", "source critical finding needs adjudication"


def same_group(finding: dict[str, Any], group: dict[str, Any]) -> bool:
    if norm(finding.get("issue")) == norm(group.get("issue")):
        return True
    if finding.get("category") != group.get("category"):
        return False
    shared_claim = set(finding.get("claim_ids") or []) & set(group.get("claim_ids") or [])
    finding_file = (finding.get("location") or {}).get("file")
    shared_file = finding_file and finding_file in group.get("location_files", set())
    shared_anchor = norm((finding.get("evidence_anchor") or {}).get("value")) in group.get("anchor_values", set())
    score = similarity(finding.get("issue"), group.get("issue"))
    return score >= 0.78 or (score >= 0.36 and (shared_claim or shared_file or shared_anchor))


def collect_groups(reports: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups: list[dict[str, Any]] = []
    strengths: list[dict[str, Any]] = []
    for report in reports:
        report_source = source_report_id(report)
        for strength in report.get("strengths", []):
            statement = strength.get("statement")
            existing = next((item for item in strengths if similarity(statement, item["statement"]) >= 0.82), None)
            source = {"report_id": report_source, "reviewer_id": report.get("reviewer_id"), "strength_id": strength.get("strength_id")}
            if existing:
                existing["sources"].append(source)
                existing["claim_ids"].update(strength.get("claim_ids") or [])
            else:
                strengths.append({"strength_id": strength.get("strength_id"), "category": strength.get("category"), "statement": statement, "evidence_anchor": strength.get("evidence_anchor"), "claim_ids": set(strength.get("claim_ids") or []), "sources": [source]})
        for finding in report.get("findings", []):
            if finding.get("state") == "resolved" and finding.get("action_kind") == "preserve":
                continue
            group = next((item for item in groups if same_group(finding, item)), None)
            source = {"report_id": report_source, "reviewer_id": report.get("reviewer_id"), "finding_id": finding.get("finding_id"), "source_finding_id": source_finding_id(report, finding), "role": finding.get("role", "primary")}
            if group is None:
                group = {
                    "severity": finding.get("severity"),
                    "category": finding.get("category"),
                    "issue": finding.get("issue"),
                    "impact": finding.get("impact"),
                    "actions": [],
                    "sources": [],
                    "claim_ids": set(),
                    "evidence_states": set(),
                    "evidence_claim_relations": set(),
                    "objection_burdens": [],
                    "states": set(),
                    "location_files": set(),
                    "anchor_values": set(),
                    "critical_adjudications": [],
                }
                groups.append(group)
            if SEVERITY_ORDER.get(finding.get("severity"), 9) < SEVERITY_ORDER.get(group.get("severity"), 9):
                group["severity"] = finding.get("severity")
            group["sources"].append(source)
            group["actions"].append(finding.get("action"))
            group["claim_ids"].update(finding.get("claim_ids") or [])
            group["evidence_states"].add(finding.get("evidence_state"))
            group["evidence_claim_relations"].add(finding.get("evidence_claim_relation"))
            if finding.get("objection_burden"):
                group["objection_burdens"].append(finding.get("objection_burden"))
            group["states"].add(finding.get("state"))
            group["location_files"].add((finding.get("location") or {}).get("file"))
            group["anchor_values"].add(norm((finding.get("evidence_anchor") or {}).get("value")))
            if finding.get("severity") == "CRITICAL":
                status, reason = adjudicate_critical(finding)
                group["critical_adjudications"].append({"source_finding_id": source["source_finding_id"], "report_id": source["report_id"], "reviewer_id": source["reviewer_id"], "finding_id": source["finding_id"], "issue": finding.get("issue"), "adjudication": status, "reason": reason})
    return groups, strengths


def json_safe_group(group: dict[str, Any]) -> dict[str, Any]:
    return {
        "severity": group["severity"],
        "category": group["category"],
        "issue": group["issue"],
        "impact": group["impact"],
        "recommended_action": next((item for item in group["actions"] if item), None),
        "corroboration": len(group["sources"]),
        "primary_source_count": sum(item.get("role") == "primary" for item in group["sources"]),
        "corroborating_source_count": sum(item.get("role") == "corroborating" for item in group["sources"]),
        "sources": group["sources"],
        "claim_ids": sorted(item for item in group["claim_ids"] if item),
        "evidence_states": sorted(item for item in group["evidence_states"] if item),
        "evidence_claim_relations": sorted(item for item in group["evidence_claim_relations"] if item),
        "objection_burdens": group["objection_burdens"],
        "evidence_anchor_values": sorted(item for item in group["anchor_values"] if item),
        "status": "open" if {"open", "uncertain"} & group["states"] else "resolved",
    }


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def atomic_pair_write(first: Path, first_content: str, second: Path, second_content: str) -> None:
    """Stage both outputs before replacing either destination.

    Filesystems cannot provide a cross-file transaction here, but staging both
    products prevents renderer failures from leaving a newly written half-pair.
    """
    first.parent.mkdir(parents=True, exist_ok=True)
    second.parent.mkdir(parents=True, exist_ok=True)
    first_tmp = first.with_name(f".{first.name}.{os.getpid()}.tmp")
    second_tmp = second.with_name(f".{second.name}.{os.getpid()}.tmp")
    try:
        first_tmp.write_text(first_content, encoding="utf-8")
        second_tmp.write_text(second_content, encoding="utf-8")
        if not first_tmp.read_text(encoding="utf-8").strip() or not second_tmp.read_text(encoding="utf-8").strip():
            raise SynthesisFailure("atomic_stage", "staged synthesis output is empty")
        os.replace(first_tmp, first)
        os.replace(second_tmp, second)
    finally:
        for temporary in (first_tmp, second_tmp):
            if temporary.exists():
                temporary.unlink()


def output_paths(context: dict[str, Any], context_path: Path, json_arg: str | None, markdown_arg: str | None) -> tuple[Path, Path, Path]:
    root = context_root(context, context_path)
    json_dir = context_path.parent.resolve()
    review_dir = json_dir.parent
    if json_dir.name != "jsons" or not review_dir.name.startswith("review-") or review_dir.parent != root / "reviews":
        raise SynthesisFailure("output_guard", "context must live under reviews/review-<timestamp>/jsons")
    markdown_dir = (review_dir / "markdowns").resolve()
    json_path = Path(json_arg).resolve() if json_arg else json_dir / "meta-review.json"
    markdown_path = Path(markdown_arg).resolve() if markdown_arg else markdown_dir / "robotic-revision-roadmap.md"
    for path, expected in ((json_path, json_dir), (markdown_path, markdown_dir)):
        if expected not in path.parents:
            raise SynthesisFailure("output_guard", f"review output must stay under {expected}: {path}")
    status_path = json_dir / "synthesis-status.json"
    return json_path, markdown_path, status_path


def render_markdown(meta: dict[str, Any]) -> str:
    decision = meta["decision"]
    summary = meta["score_summary"]
    lines = [
        "# 机器人论文总修改建议 / Robotics Revision Roadmap",
        "",
        f"决策 / Decision: **{decision}**",
        f"评审语言 / Review language: **{meta.get('review_language')}**",
        f"编排模式 / Execution mode: **{meta.get('execution_mode') or 'UNSPECIFIED'}**",
        f"适用评审数 / Applicable reviewers: {summary['applicable_reviewers']}",
        f"分数 / Scores: mean={summary['mean']}, median={summary['median']}, range={summary['minimum']}–{summary['maximum']}",
        "",
        "## 共识 / Consensus",
        "",
    ]
    if not meta["consensus"]:
        lines.append("- 暂无达到共识阈值的项目 / no item reached the consensus threshold")
    for item in meta["consensus"]:
        lines.append(f"- [{item['type']}] {item.get('issue') or item.get('statement')}（corroboration={item.get('corroboration', 0)}）")
    lines.extend(["", "## 受保护强项 / Protected strengths", ""])
    for item in meta["protected_strengths"]:
        sources = ", ".join(str(source.get("report_id")) + "/" + str(source.get("strength_id")) for source in item["sources"])
        lines.append(f"- {item['statement']}（corroboration={len(item['sources'])}; sources={sources}）")
    if not meta["protected_strengths"]:
        lines.append("- 未记录可保护强项 / no protected strength recorded")
    lines.extend(["", "## 修改项 / Revision items", ""])
    for item in meta["revision_roadmap"]:
        sources = ", ".join(str(source.get("report_id")) + "/" + str(source.get("finding_id")) for source in item["sources"])
        lines.extend([
            f"### {item['priority']}. [{item['severity']}] {item['category']} ({item['root_cause_id']})",
            f"- 问题 / Issue: {item['issue']}",
            f"- 影响 / Impact: {item['impact']}",
            f"- Evidence–claim relation: {', '.join(item.get('evidence_claim_relations', []))}",
            f"- 行动 / Action: {item['recommended_action']}",
            f"- corroboration: {item['corroboration']}; sources: {sources}",
            "",
        ])
    if not meta["revision_roadmap"]:
        lines.append("- 暂无开放修改项 / no open revision item")
    lines.extend(["", "## CRITICAL gate", ""])
    gate = meta["critical_gate"]
    lines.append(f"- source critical={gate['total']}; validated={gate['validated_source_critical_count']}; unresolved={gate['unresolved_source_critical_count']}; open root causes={gate['open_root_cause_count']}")
    for item in gate["items"]:
        lines.append(f"- {item['source_finding_id']}: {item['adjudication']} — {item['reason']}")
    if meta["evidence_gaps"]:
        lines.extend(["", "## 证据缺口 / Evidence gaps", ""])
        for item in meta["evidence_gaps"]:
            lines.append(f"- {item['source_id']}: {item['description']}")
    if meta["disagreements"]:
        lines.extend(["", "## 分歧 / Dissent", ""])
        for item in meta["disagreements"]:
            lines.append(f"- {item['type']}: {item['detail']}")
    return "\n".join(lines) + "\n"


def load_closure_map(path: str | None, reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not path:
        return []
    payload = load_json(path)
    if not isinstance(payload, list):
        raise SynthesisFailure("closure_map", "closure map must be an array")
    known = {source_finding_id(report, finding) for report in reports for finding in report.get("findings", [])}
    errors = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict) or set(item) != {"source_finding_id", "claimed_status", "new_evidence_anchor"}:
            errors.append(f"closure_map[{index}] must contain source_finding_id, claimed_status, new_evidence_anchor")
        elif item["source_finding_id"] not in known:
            errors.append(f"closure_map[{index}] unknown source_finding_id: {item['source_finding_id']}")
        elif not item.get("new_evidence_anchor"):
            errors.append(f"closure_map[{index}] needs new_evidence_anchor")
    if errors:
        raise SynthesisFailure("closure_map", "; ".join(errors), errors)
    return payload


def synthesize(context_path: Path, report_paths: list[Path], json_arg: str | None, markdown_arg: str | None, closure_map_path: str | None) -> tuple[Any, ...]:
    try:
        context = load_json(context_path)
    except (OSError, ValueError, JsonIntegrityError) as exc:
        raise SynthesisFailure("context_load", str(exc)) from exc
    if not isinstance(context, dict):
        raise SynthesisFailure("context_load", "review context must be an object")
    try:
        review_language = normalize_language(context.get("review_language") or context.get("paper", {}).get("output_language"))
    except ValueError as exc:
        raise SynthesisFailure("language_gate", str(exc)) from exc
    drift = verify_snapshot(context)
    if drift:
        raise SynthesisFailure("snapshot_lock", "discovery snapshot changed", drift)
    run_state_path = context_path.parent / "run-state.json"
    execution_mode = None
    if run_state_path.is_file():
        try:
            run_state = load_json(run_state_path)
            expected_context_hash = run_state.get("context_sha256")
            actual_context_hash = sha256_file(context_path)
            if expected_context_hash and expected_context_hash != actual_context_hash:
                raise SynthesisFailure("run_state_lock", "run-state context hash does not match review context")
            agents = run_state.get("agents", {})
            execution_mode = run_state.get("execution_mode")
            incomplete = [reviewer for reviewer, item in agents.items() if item.get("status") != "COMPLETE" or item.get("validation") != "PASS"]
            if incomplete:
                raise SynthesisFailure("run_state_gate", "panel agents are not terminal and validated", incomplete)
        except SynthesisFailure:
            raise
        except (OSError, ValueError, JsonIntegrityError) as exc:
            raise SynthesisFailure("run_state_load", str(exc)) from exc
    raw_reports = []
    for path in report_paths:
        try:
            raw_reports.append(load_json(path))
        except (OSError, ValueError, JsonIntegrityError) as exc:
            raise SynthesisFailure("report_load", f"{path}: {exc}") from exc
    report_set = validate_report_set(context, raw_reports)
    if not report_set["valid"]:
        raise SynthesisFailure("report_set", "; ".join(report_set["errors"]), report_set)
    reports = report_set["normalized_reports"]
    for report in reports:
        check = validate(report)
        if not check["contract_consistent"]:
            raise SynthesisFailure("report_validation", f"invalid report {source_report_id(report)}", check)
    closure_map = load_closure_map(closure_map_path, reports)
    groups, strength_groups = collect_groups(reports)
    groups.sort(key=lambda item: (SEVERITY_ORDER.get(item["severity"], 9), -len(item["sources"])))
    roadmap = []
    root_counter = 0
    for group in groups:
        if not ({"open", "uncertain"} & group["states"]):
            continue
        root_counter += 1
        root_id = f"ROOT-{root_counter:03d}"
        if group["severity"] == "CRITICAL":
            root_id = f"CRIT-ROOT-{root_counter:03d}"
        item = json_safe_group(group)
        item.update({"root_cause_id": root_id, "roadmap_id": f"RM-{len(roadmap)+1:03d}", "priority": len(roadmap) + 1})
        roadmap.append(item)
        for critical in group["critical_adjudications"]:
            critical["root_cause_id"] = root_id

    critical_items = [critical for group in groups for critical in group["critical_adjudications"]]
    validated_critical = [item for item in critical_items if item["adjudication"] == "validated"]
    unresolved_critical = [item for item in critical_items if item["adjudication"] in {"unresolved", "not_assessable"}]
    open_critical_roots = {item.get("root_cause_id") for item in unresolved_critical + validated_critical if item.get("root_cause_id")}
    protected_strengths = []
    for item in strength_groups:
        protected_strengths.append({"strength_id": item["strength_id"], "category": item["category"], "statement": item["statement"], "evidence_anchor": item["evidence_anchor"], "claim_ids": sorted(item["claim_ids"]), "sources": item["sources"], "corroboration": len(item["sources"])})
    consensus = []
    for item in roadmap:
        if item["corroboration"] >= 2:
            consensus.append({"type": "finding", "root_cause_id": item["root_cause_id"], "issue": item["issue"], "corroboration": item["corroboration"], "sources": item["sources"]})
    for item in protected_strengths:
        if item["corroboration"] >= 2:
            consensus.append({"type": "strength", "strength_id": item["strength_id"], "statement": item["statement"], "corroboration": item["corroboration"], "sources": item["sources"]})

    applicable = [report for report in reports if report.get("applicability", {}).get("applicable") is True and isinstance(report.get("score", {}).get("overall"), int)]
    scores = [report["score"]["overall"] for report in applicable]
    mean = statistics.mean(scores) if scores else None
    median = statistics.median(scores) if scores else None
    minimum = min(scores) if scores else None
    maximum = max(scores) if scores else None
    recommendations = Counter(report.get("recommendation") for report in applicable)
    disagreements = []
    if scores and maximum != minimum:
        disagreements.append({"type": "score_spread", "detail": f"scores span {minimum}–{maximum}", "reviewers": [report.get("reviewer_id") for report in applicable]})
    if len(recommendations) > 1:
        disagreements.append({"type": "recommendation_split", "detail": ", ".join(f"{key}={value}" for key, value in sorted(recommendations.items())), "reviewers": [report.get("reviewer_id") for report in applicable]})
    for item in roadmap:
        relations = set(item.get("evidence_claim_relations", []))
        if "OVER_CEILING" in relations and "BELOW_CEILING" in relations:
            disagreements.append({"type": "calibration_conflict", "detail": f"{item['root_cause_id']} was classified as both over- and below-ceiling", "reviewers": [source.get("reviewer_id") for source in item["sources"]]})
        for strength in protected_strengths:
            strength_anchor = norm((strength.get("evidence_anchor") or {}).get("value"))
            if strength_anchor and strength_anchor in set(item.get("evidence_anchor_values", [])):
                disagreements.append({"type": "preserve_revise_conflict", "detail": f"{item['root_cause_id']} requests revision at an anchor protected by {strength['strength_id']}", "reviewers": [source.get("reviewer_id") for source in item["sources"] + strength["sources"]]})

    evidence_gaps = []
    for report in reports:
        sid = source_report_id(report)
        for gap in report.get("evidence_gaps", []):
            evidence_gaps.append({"source_id": sid, **gap})
        for item in report.get("not_assessable", []):
            evidence_gaps.append({"source_id": sid, "gap_id": item.get("item_id"), "category": "not_assessable", "description": item.get("reason"), "impact": "该维度无法评估", "action": "补充材料或保留不可评估状态", "evidence_state": "UNASSESSED"})
    has_evidence_gap = bool(evidence_gaps) or any(state in {"EVIDENCE_GAPS", "INCONCLUSIVE", "UNASSESSED"} for group in groups for state in group.get("evidence_states", set()))
    has_major = any(item["severity"] in {"CRITICAL", "MAJOR"} for item in roadmap)
    if not applicable:
        decision = "NOT_ASSESSABLE"
    elif unresolved_critical:
        decision = "EVIDENCE_GAPS" if has_evidence_gap else "REBUILD_OR_REFRAME"
    elif roadmap and has_major:
        decision = "MAJOR_REVISION"
    elif roadmap:
        decision = "READY_WITH_MINOR_REVISIONS" if mean is not None and mean >= 4 else "MAJOR_REVISION"
    else:
        decision = "READY_TO_SUBMIT" if mean is not None and mean >= 4 else "NOT_ASSESSABLE"

    source_registry = {}
    for report in reports:
        source_registry[source_report_id(report)] = {
            "report_id": source_report_id(report),
            "reviewer_id": report.get("reviewer_id"),
            "original_report_id": report.get("normalization_audit", {}).get("original_report_id"),
            "normalization_warnings": report.get("normalization_audit", {}).get("warnings", []),
        }
    meta = {
        "schema_version": "robotics-meta-review.v1",
        "meta_review_id": "META-" + context.get("review_id", "UNKNOWN"),
        "review_id": context.get("review_id"),
        "review_language": review_language,
        "review_language_mode": language_mode(review_language),
        "execution_mode": execution_mode,
        "source_reports": [source_report_id(report) for report in reports],
        "source_registry": source_registry,
        "score_summary": {"applicable_reviewers": len(applicable), "mean": mean, "median": median, "minimum": minimum, "maximum": maximum, "spread": (maximum - minimum if scores else None), "low_confidence_reviewers": [report.get("reviewer_id") for report in applicable if report.get("score", {}).get("confidence", 0) <= 2], "by_reviewer": {report.get("reviewer_id"): {"score": report["score"]["overall"], "confidence": report["score"]["confidence"], "recommendation": report.get("recommendation")} for report in applicable}},
        "consensus": consensus,
        "protected_strengths": protected_strengths,
        "disagreements": disagreements,
        "critical_gate": {"total": len(critical_items), "validated_source_critical_count": len(validated_critical), "unresolved_source_critical_count": len(unresolved_critical), "open_root_cause_count": len(open_critical_roots), "items": critical_items},
        "evidence_gaps": evidence_gaps,
        "revision_roadmap": roadmap,
        "decision": decision,
        "closure_map": closure_map,
        "run_state": None,
        "notes": [],
    }
    json_path, markdown_path, status_path = output_paths(context, context_path, json_arg, markdown_arg)
    if run_state_path.is_file():
        try:
            meta["run_state"] = load_json(run_state_path)
        except (OSError, ValueError, JsonIntegrityError):
            meta["notes"].append("run-state.json exists but could not be loaded")
    markdown = render_markdown(meta)
    serialized = json.dumps(meta, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if not serialized.strip() or not markdown.strip():
        raise SynthesisFailure("render", "empty synthesis output")
    if "None/" in markdown or "None/None" in markdown:
        raise SynthesisFailure("render", "null source identity reached Markdown renderer")
    return meta, json_path, markdown_path, status_path, serialized, markdown


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("context")
    parser.add_argument("reports", nargs="+")
    parser.add_argument("--json-out")
    parser.add_argument("--markdown-out")
    parser.add_argument("--closure-map")
    args = parser.parse_args()
    context_path = Path(args.context).resolve()
    status_path = None
    try:
        result = synthesize(context_path, [Path(path).resolve() for path in args.reports], args.json_out, args.markdown_out, args.closure_map)
        meta, json_path, markdown_path, status_path, serialized, markdown = result
        # Validate both render products before replacing either destination.
        if not isinstance(meta, dict) or meta.get("schema_version") != "robotics-meta-review.v1":
            raise SynthesisFailure("render_validate", "invalid meta-review structure")
        atomic_pair_write(json_path, serialized, markdown_path, markdown)
        write_json(status_path, {"schema_version": "robotics-synthesis-status.v1", "status": "COMPLETED", "stage": "complete", "updated_at": now_iso(), "json_path": str(json_path), "markdown_path": str(markdown_path)})
        run_state_path = context_path.parent / "run-state.json"
        if run_state_path.is_file():
            run_state = load_json(run_state_path)
            run_state.setdefault("synthesis", {})["status"] = "COMPLETE"
            run_state["synthesis"]["updated_at"] = now_iso()
            write_json(run_state_path, run_state)
    except SynthesisFailure as exc:
        try:
            context = load_json(context_path)
            _, _, status_path = output_paths(context, context_path, args.json_out, args.markdown_out)
            write_json(status_path, {"schema_version": "robotics-synthesis-status.v1", "status": "FAILED", "stage": exc.stage, "error": str(exc), "details": exc.details, "updated_at": now_iso()})
            run_state_path = context_path.parent / "run-state.json"
            if run_state_path.is_file():
                run_state = load_json(run_state_path)
                run_state.setdefault("synthesis", {})["status"] = "FAILED"
                run_state["synthesis"]["stage"] = exc.stage
                run_state["synthesis"]["updated_at"] = now_iso()
                write_json(run_state_path, run_state)
        except Exception:
            pass
        print(json.dumps({"status": "FAILED", "stage": exc.stage, "error": str(exc), "details": exc.details}, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(1)
    except Exception as exc:
        try:
            context = load_json(context_path)
            _, _, status_path = output_paths(context, context_path, args.json_out, args.markdown_out)
            write_json(status_path, {"schema_version": "robotics-synthesis-status.v1", "status": "FAILED", "stage": "unexpected", "error": str(exc), "updated_at": now_iso()})
        except Exception:
            pass
        print(json.dumps({"status": "FAILED", "stage": "unexpected", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
