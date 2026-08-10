"""Online ResearchStudio-style ideation chain for robotics research.

This is an orchestration contract, not a claim that the local runtime can
retrieve papers by itself.  Grounding and mechanism-collision evidence must be
supplied by the configured literature tools or by explicit user records.
Missing evidence therefore produces an honest stop state.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .canonical_json import sha256_value
from .robotics_research_runtime import DEFAULT_RUNTIME, load_runtime
from .researchstudio_patterns import (
    DEFAULT_LIBRARY,
    fit_gap_to_patterns,
    load_pattern_library,
)


STAGES = ("retrieve", "diagnose", "fit_pattern", "instantiate", "collision_audit", "failure_audit", "decide", "validate")


def _active_axes(base_context: dict[str, Any]) -> list[str]:
    vector = base_context.get("project_vector", {}).get("vector", {})
    return [axis for axis, value in vector.items() if isinstance(value, int) and value >= 2]


def _evidence_records(profile: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("evidence_bundle", "retrieved_papers", "literature_records"):
        value = profile.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _collision_records(profile: dict[str, Any]) -> list[dict[str, Any]]:
    value = profile.get("collision_evidence", profile.get("prior_art", []))
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _failure_matches(profile: dict[str, Any], selected_patterns: list[dict[str, Any]], library: dict[str, Any], candidate_sha256: str | None, evidence_ids: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    matches = profile.get("failure_audit", [])
    supplied = [item for item in matches if isinstance(item, dict)] if isinstance(matches, list) else []
    knowledge: list[dict[str, Any]] = []
    parent_map = {item.get("pattern_id"): item for item in library.get("main_patterns", []) if isinstance(item, dict)}
    for pattern in selected_patterns:
        card = parent_map.get(pattern.get("pattern_id"))
        if card:
            knowledge.append({
                "pattern_id": card["pattern_id"],
                "pattern_name": card["name"],
                "known_failure_modes": card.get("failure_modes", []),
                "status": "FAILURE_KNOWLEDGE_LOADED",
            })
    bound = [item for item in supplied if _valid_failure_record(item, candidate_sha256, evidence_ids)]
    return knowledge, bound


_COLLISION_AXES = {"problem_framing", "core_mechanism", "key_insight", "application_or_evaluation"}


def _valid_collision_record(record: dict[str, Any], candidate_sha256: str | None, evidence_ids: set[str]) -> bool:
    axes = record.get("comparison_axes")
    sources = record.get("sources")
    rows_valid = isinstance(axes, dict) and set(axes) == _COLLISION_AXES and all(
        isinstance(row, dict)
        and set(row) == {"closest_overlap", "candidate_delta", "source_ids", "threat_level"}
        and all(isinstance(row.get(field), str) and row[field].strip() for field in ("closest_overlap", "candidate_delta"))
        and isinstance(row.get("source_ids"), list)
        and bool(row["source_ids"])
        and set(row["source_ids"]) <= set(sources or [])
        and row.get("threat_level") in {"LOW", "MEDIUM", "HIGH"}
        for row in axes.values()
    )
    return bool(
        candidate_sha256
        and record.get("candidate_sha256") == candidate_sha256
        and isinstance(record.get("queries"), list)
        and record.get("queries")
        and isinstance(sources, list)
        and sources
        and set(sources) <= evidence_ids
        and record.get("closest_prior_id", record.get("closest_threat_id")) in sources
        and rows_valid
        and record.get("verdict") in {"CLEAR", "PARTIAL_COLLISION", "EXACT_COLLISION", "INSUFFICIENT_EVIDENCE"}
    )


def _valid_failure_record(record: dict[str, Any], candidate_sha256: str | None, known_evidence_ids: set[str]) -> bool:
    evidence_ids = record.get("evidence_ids")
    return bool(
        candidate_sha256
        and record.get("candidate_sha256") == candidate_sha256
        and isinstance(record.get("pattern_id"), str)
        and record["pattern_id"]
        and isinstance(record.get("failure_mode_checked"), str)
        and record["failure_mode_checked"].strip()
        and isinstance(record.get("finding"), str)
        and record["finding"].strip()
        and isinstance(evidence_ids, list)
        and evidence_ids
        and all(isinstance(item, str) and item.strip() for item in evidence_ids)
        and set(evidence_ids) <= known_evidence_ids
        and isinstance(record.get("mitigation_or_boundary"), str)
        and record["mitigation_or_boundary"].strip()
        and record.get("status") in {"PASS", "REVISE", "FAIL"}
    )


def build_strategy_context(base_context: dict[str, Any], profile: dict[str, Any], *, target_venue: str | None = None) -> dict[str, Any]:
    """Attach axis strategy cards and pattern-fit guidance to a stage context."""

    library = load_pattern_library(DEFAULT_LIBRARY)
    runtime = load_runtime(DEFAULT_RUNTIME)
    active_axes = _active_axes(base_context)
    gap = str(profile.get("structural_gap") or profile.get("bottleneck") or profile.get("research_gap") or "")
    gap_fit = fit_gap_to_patterns(gap, active_axes, library) if gap and active_axes else []
    per_axis = {
        axis: row
        for axis, row in runtime.get("axis_strategy_by_axis", {}).items()
        if axis in active_axes
    }
    subpatterns = {item.get("subpattern_id"): item for item in library.get("subpatterns", []) if isinstance(item, dict)}
    tactical_ids = []
    for axis in active_axes:
        tactical_ids.extend(library.get("axis_profiles", {}).get(axis, {}).get("preferred_subpattern_ids", []))
    tactical_cards = []
    for item in dict.fromkeys(tactical_ids):
        if item not in subpatterns or subpatterns[item].get("status") not in {"runtime_active", "tactical_card_v2"}:
            continue
        card = deepcopy(subpatterns[item])
        # Stable runtime names are explicit even though the offline induction
        # artifact retains its historical field names.
        card["step_by_step_recipe"] = deepcopy(card.get("five_step_recipe"))
        card["evidence_requirement"] = deepcopy(card.get("required_evidence_profile"))
        tactical_cards.append(card)
    return {
        "schema_version": "researchstudio-robotics-strategy-context.v1",
        "active_axes": active_axes,
        "axis_strategy_patterns": per_axis,
        "tactical_cards": tactical_cards,
        "gap_text": gap,
        "pattern_fit": gap_fit,
        "target_venue": target_venue,
        "selection_rule": "fit the structural gap to one or two pattern operators; do not select by pattern frequency, award status or acceptance signal",
        "outcome_context": "descriptive audit only; acceptance probability is not estimable",
        "online_chain": list(STAGES),
    }


def run_ideation_chain(profile: dict[str, Any], base_context: dict[str, Any]) -> dict[str, Any]:
    """Run deterministic gates around an LLM/retrieval-compatible Idea Card."""

    library = load_pattern_library(DEFAULT_LIBRARY)
    strategy_context = build_strategy_context(base_context, profile)
    evidence = _evidence_records(profile)
    evidence_ids = {str(item.get("id")) for item in evidence if item.get("id")}
    collision = _collision_records(profile)
    gap = strategy_context["gap_text"]
    selected = strategy_context["pattern_fit"][:3]
    candidate_input = profile.get("candidate") if isinstance(profile.get("candidate"), dict) else {}
    candidate = deepcopy(candidate_input)
    candidate_sha256 = sha256_value(candidate) if candidate else None
    locked = {
        "falsification_prediction": candidate.get("falsification_prediction") or profile.get("falsification_prediction"),
        "compute_budget": candidate.get("compute_budget") or profile.get("compute_budget"),
    }
    phases: dict[str, dict[str, Any]] = {}
    phases["retrieve"] = {
        "status": "PASS" if evidence else "STOP",
        "records": len(evidence),
        "required": "multi-source literature records plus a small full-text cache",
        "reason": None if evidence else "No evidence bundle supplied; do not write a bottleneck from model memory.",
    }
    phases["diagnose"] = {
        "status": "PASS" if evidence and gap else "STOP",
        "structural_gap": gap or None,
        "method_lineage": profile.get("method_lineage", []),
        "reason": None if evidence and gap else "A concrete evidence-grounded structural gap is required.",
    }
    phases["fit_pattern"] = {
        "status": "PASS" if selected else "ABSTAIN",
        "selected_patterns": selected,
        "composition_default": 2,
        "reason": None if selected else "No active axis and gap terms support a structural pattern fit.",
    }
    subpattern_ids = profile.get("subpattern_ids", []) if isinstance(profile.get("subpattern_ids"), list) else []
    phases["instantiate"] = {
        "status": "PASS" if selected and candidate else "REQUIRES_CANDIDATE",
        "candidate": candidate,
        "subpattern_ids": subpattern_ids,
        "citation_gate": "pending_deterministic_validation",
    }
    bound_collision = [item for item in collision if _valid_collision_record(item, candidate_sha256, evidence_ids)]
    exact_collision = [item for item in bound_collision if item.get("verdict") == "EXACT_COLLISION"]
    phases["collision_audit"] = {
        "status": "ABANDON" if exact_collision else ("PASS" if bound_collision and all(item.get("verdict") in {"CLEAR", "PARTIAL_COLLISION"} for item in bound_collision) else "DO_NOT_ADVANCE"),
        "records": collision,
        "candidate_sha256": candidate_sha256,
        "bound_records": len(bound_collision),
        "exact_mechanism_threats": exact_collision,
        "reason": "Exact mechanism overlap is a hard floor." if exact_collision else (None if bound_collision else "Candidate-bound mechanism collision evidence is required."),
    }
    failure_knowledge, candidate_failure_checks = _failure_matches(profile, selected, library, candidate_sha256, evidence_ids)
    selected_ids = {item.get("pattern_id") for item in selected}
    audited_ids = {item.get("pattern_id") for item in candidate_failure_checks if item.get("status") == "PASS"}
    failure_pass = bool(candidate_sha256 and selected_ids and selected_ids <= audited_ids)
    phases["failure_audit"] = {
        "status": "PASS" if failure_pass else "REVISE",
        "knowledge": failure_knowledge,
        "candidate_checks": candidate_failure_checks,
        "checks": candidate_failure_checks,
        "reason": None if failure_pass else "Every selected pattern requires substantive candidate-bound failure evidence marked PASS.",
    }
    idea_card = {
        "schema_version": "researchstudio-robotics-idea-card.v1",
        "status": None,
        "title": candidate.get("title"),
        "motivation": candidate.get("motivation") or candidate.get("problem_statement"),
        "method_flow": candidate.get("method_flow", []),
        "core_claim": candidate.get("core_claim"),
        "falsification_prediction": locked["falsification_prediction"],
        "compute_budget": locked["compute_budget"],
        "load_bearing_variable": candidate.get("load_bearing_variable"),
        "selected_patterns": selected,
        "selected_subpatterns": subpattern_ids,
        "candidate_sha256": candidate_sha256,
        "evidence_ids": [item.get("paper_id") or item.get("id") for item in evidence],
        "collision_ids": [item.get("paper_id") or item.get("id") for item in collision],
        "open_author_decisions": candidate.get("open_author_decisions", []),
        "venue_context": base_context.get("fixed_venue_fit"),
        "acceptance_probability": {"status": "NOT_ESTIMABLE"},
    }
    required_card_fields = ("core_claim", "falsification_prediction", "compute_budget", "load_bearing_variable")
    deterministic_ready = all(isinstance(idea_card.get(field), str) and idea_card[field].strip() for field in required_card_fields)
    phases["validate"] = {
        "status": "PASS" if deterministic_ready else "PENDING_VALIDATION",
        "locked_fields": locked,
        "checks": ["subpattern citation consistency", "kill-switch integrity", "evidence provenance", "claim completeness"],
    }
    if exact_collision:
        decision = "ABANDON"
    elif phases["retrieve"]["status"] != "PASS" or phases["diagnose"]["status"] != "PASS":
        decision = "DO_NOT_GENERATE"
    elif phases["fit_pattern"]["status"] != "PASS":
        decision = "ABSTAIN"
    elif phases["instantiate"]["status"] != "PASS":
        decision = "REQUIRES_CANDIDATE"
    elif phases["collision_audit"]["status"] != "PASS":
        decision = "DO_NOT_ADVANCE"
    elif phases["failure_audit"]["status"] != "PASS" or profile.get("revision_required"):
        decision = "REVISE"
    elif phases["validate"]["status"] != "PASS":
        decision = "PENDING_VALIDATION"
    else:
        decision = "ADVANCE"
    idea_card["status"] = decision
    phases["decide"] = {
        "status": decision,
        "hard_floor": bool(exact_collision),
        "revision_targets": profile.get("revision_targets", []) if decision == "REVISE" else [],
        "reason": None,
    }
    result = {
        "schema_version": "researchstudio-robotics-ideation-run.v1",
        "decision": decision,
        "strategy_context": strategy_context,
        "phases": phases,
        "idea_card": idea_card,
        "honesty_boundary": "The chain stops rather than filling missing literature, collision evidence or implementability details from model memory.",
    }
    from .researchstudio_idea_validation import validate as validate_idea_run
    validation_errors = validate_idea_run(result, library)
    phases["validate"]["errors"] = validation_errors
    if decision == "ADVANCE" and validation_errors:
        decision = "PENDING_VALIDATION"
        phases["validate"]["status"] = "PENDING_VALIDATION"
        phases["decide"]["status"] = decision
        idea_card["status"] = decision
        result["decision"] = decision
    return result
