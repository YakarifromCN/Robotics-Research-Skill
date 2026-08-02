"""Online ResearchStudio-style ideation chain for robotics research.

This is an orchestration contract, not a claim that the local runtime can
retrieve papers by itself.  Grounding and mechanism-collision evidence must be
supplied by the configured literature tools or by explicit user records.
Missing evidence therefore produces an honest stop state.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

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


def _failure_matches(profile: dict[str, Any], selected_patterns: list[dict[str, Any]], library: dict[str, Any]) -> list[dict[str, Any]]:
    matches = profile.get("failure_audit", [])
    result = [item for item in matches if isinstance(item, dict)] if isinstance(matches, list) else []
    parent_map = {item.get("pattern_id"): item for item in library.get("main_patterns", []) if isinstance(item, dict)}
    for pattern in selected_patterns:
        card = parent_map.get(pattern.get("pattern_id"))
        if card:
            result.append({
                "pattern_id": card["pattern_id"],
                "pattern_name": card["name"],
                "known_failure_modes": card.get("failure_modes", []),
                "status": "requires_candidate_specific_audit",
            })
    return result


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
    return {
        "schema_version": "researchstudio-robotics-strategy-context.v1",
        "active_axes": active_axes,
        "axis_strategy_patterns": per_axis,
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
    collision = _collision_records(profile)
    gap = strategy_context["gap_text"]
    selected = strategy_context["pattern_fit"][:3]
    candidate_input = profile.get("candidate") if isinstance(profile.get("candidate"), dict) else {}
    candidate = deepcopy(candidate_input)
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
        "status": "PASS" if selected else "STOP",
        "selected_patterns": selected,
        "composition_default": 2,
        "reason": None if selected else "No active axis and gap terms support a structural pattern fit.",
    }
    subpattern_ids = profile.get("subpattern_ids", []) if isinstance(profile.get("subpattern_ids"), list) else []
    phases["instantiate"] = {
        "status": "PASS" if selected and candidate else "REQUIRES_LLM_OR_USER_CANDIDATE",
        "candidate": candidate,
        "subpattern_ids": subpattern_ids,
        "citation_gate": "pending_deterministic_validation",
    }
    exact_collision = [item for item in collision if item.get("exact_mechanism_overlap") is True or item.get("subsumes_claim") is True]
    phases["collision_audit"] = {
        "status": "ABANDON" if exact_collision else ("PASS" if collision else "STOP"),
        "records": collision,
        "exact_mechanism_threats": exact_collision,
        "reason": "Exact mechanism overlap is a hard floor." if exact_collision else (None if collision else "Mechanism-level collision search evidence is required."),
    }
    phases["failure_audit"] = {
        "status": "PASS" if selected else "STOP",
        "checks": _failure_matches(profile, selected, library),
        "reason": None if selected else "No selected pattern is available for failure-mode audit.",
    }
    hard_stop = bool(exact_collision) or not evidence or not gap
    needs_revision = bool(profile.get("revision_required")) or any(item.get("status") == "match_without_mitigation" for item in phases["failure_audit"]["checks"] if isinstance(item, dict))
    decision = "ABANDON" if exact_collision else ("DO_NOT_GENERATE" if hard_stop else ("REVISE" if needs_revision else "ADVANCE"))
    phases["decide"] = {
        "status": decision,
        "hard_floor": bool(exact_collision),
        "revision_targets": profile.get("revision_targets", []) if needs_revision else [],
        "reason": "Evidence or a concrete gap is missing." if hard_stop and not exact_collision else ("Exact mechanism collision." if exact_collision else None),
    }
    idea_card = {
        "schema_version": "researchstudio-robotics-idea-card.v1",
        "status": decision,
        "title": candidate.get("title"),
        "motivation": candidate.get("motivation") or candidate.get("problem_statement"),
        "method_flow": candidate.get("method_flow", []),
        "core_claim": candidate.get("core_claim"),
        "falsification_prediction": locked["falsification_prediction"],
        "compute_budget": locked["compute_budget"],
        "load_bearing_variable": candidate.get("load_bearing_variable"),
        "selected_patterns": selected,
        "selected_subpatterns": subpattern_ids,
        "evidence_ids": [item.get("paper_id") or item.get("id") for item in evidence],
        "collision_ids": [item.get("paper_id") or item.get("id") for item in collision],
        "open_author_decisions": candidate.get("open_author_decisions", []),
        "venue_context": base_context.get("fixed_venue_fit"),
        "acceptance_probability": {"status": "NOT_ESTIMABLE"},
    }
    phases["validate"] = {
        "status": "PENDING_DETERMINISTIC_VALIDATOR",
        "locked_fields": locked,
        "checks": ["subpattern citation consistency", "kill-switch integrity", "evidence provenance", "claim completeness"],
    }
    return {
        "schema_version": "researchstudio-robotics-ideation-run.v1",
        "decision": decision,
        "strategy_context": strategy_context,
        "phases": phases,
        "idea_card": idea_card,
        "honesty_boundary": "The chain stops rather than filling missing literature, collision evidence or implementability details from model memory.",
    }
