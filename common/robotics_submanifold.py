"""机器人研究子流形的透明因子模型与 venue 对齐。\n\nTransparent semantic factorization and venue alignment for robotics research.\n\nThe model is deliberately not a statistical PCA implementation.  It exposes\nits axes, indicator groups, aggregation rule, and direct/strong-related prior\nso that every routing decision can be audited and replaced when paper-level\ndata become available.\n"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .canonical_json import sha256_value


AXIS_ORDER = ("E", "P", "C", "L", "D", "H", "A", "S")
LAYER_PRIOR = {
    "direct_robotics": 1.0,
    "robotics_strong_related": 0.65,
}
CENTERS = {
    "robotics_core",
    "embodiment_core",
    "perception_core",
    "vision_core",
    "control_core",
    "learning_core",
    "planning_core",
    "multi_agent_core",
    "hri_core",
    "haptics_core",
    "xr_core",
    "ai_core",
    "autonomy_core",
    "sensing_core",
    "systems_core",
    "realtime_core",
    "embedded_core",
    "industrial_core",
    "field_core",
    "graphics_core",
    "geometry_core",
    "theory_core",
    "social_computing_core",
    "biomedical_core",
}

CENTER_TO_TAGS = {
    "robotics_core": ["robotics", "embodied_systems"],
    "embodiment_core": ["embodied_systems", "mechatronics", "manipulation"],
    "perception_core": ["perception", "sensing"],
    "vision_core": ["computer_vision", "3d_perception"],
    "control_core": ["control", "dynamics"],
    "learning_core": ["machine_learning", "robot_learning"],
    "planning_core": ["planning", "task_motion_planning"],
    "multi_agent_core": ["multi_agent", "coordination"],
    "hri_core": ["hri", "human"],
    "haptics_core": ["haptics", "force_feedback"],
    "xr_core": ["virtual_reality", "augmented_reality"],
    "ai_core": ["artificial_intelligence", "reasoning"],
    "autonomy_core": ["autonomy", "autonomous_systems"],
    "sensing_core": ["sensing", "multisensor"],
    "systems_core": ["systems", "hardware_software"],
    "realtime_core": ["real_time", "embedded"],
    "embedded_core": ["embedded", "hardware_software"],
    "industrial_core": ["industrial_robotics", "manufacturing"],
    "field_core": ["field", "deployment"],
    "graphics_core": ["graphics", "visualization"],
    "geometry_core": ["geometry", "simulation"],
    "theory_core": ["theory", "learning_theory"],
    "social_computing_core": ["social_computing", "user_study"],
    "biomedical_core": ["biomedical_robotics", "rehabilitation_robotics"],
}


def load_json(path: str | Path) -> dict[str, Any]:
    """Load a UTF-8 JSON object."""

    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def catalog_digest(catalog: dict[str, Any]) -> str:
    """Return a stable digest for the catalog used in an analysis."""

    return sha256_value(catalog)


def model_digest(model: dict[str, Any]) -> str:
    """Return a stable digest for the factor model used in an analysis."""

    return sha256_value(model)


def validate_model(model: dict[str, Any], catalog: dict[str, Any] | None = None) -> list[str]:
    """Return structural errors without changing either input."""

    errors: list[str] = []
    if model.get("schema_version") != "robotics-submanifold.v1":
        errors.append("wrong model schema")
    axes = model.get("axes")
    if not isinstance(axes, list) or tuple(item.get("axis_id") for item in axes if isinstance(item, dict)) != AXIS_ORDER:
        errors.append(f"axes must preserve exactly {list(AXIS_ORDER)}")
    groups = model.get("tag_groups")
    if not isinstance(groups, list) or not groups:
        errors.append("tag_groups must be a non-empty array")
    else:
        for index, group in enumerate(groups):
            if not isinstance(group, dict):
                errors.append(f"tag_groups[{index}] must be an object")
                continue
            if group.get("axis_id") not in AXIS_ORDER:
                errors.append(f"tag_groups[{index}].axis_id unsupported")
            if group.get("weight") not in (1, 2, 3):
                errors.append(f"tag_groups[{index}].weight must be 1, 2, or 3")
            tags = group.get("tags")
            if not isinstance(tags, list) or not tags or len(tags) != len(set(tags)):
                errors.append(f"tag_groups[{index}].tags must be a unique nonempty list")
    if catalog is not None:
        records = catalog.get("records")
        if not isinstance(records, list) or not records:
            errors.append("catalog.records must be a non-empty array")
        else:
            ids: set[str] = set()
            for index, record in enumerate(records):
                if not isinstance(record, dict):
                    errors.append(f"catalog.records[{index}] must be an object")
                    continue
                venue_id = record.get("venue_id")
                if not isinstance(venue_id, str) or not venue_id:
                    errors.append(f"catalog.records[{index}].venue_id must be nonempty")
                elif venue_id in ids:
                    errors.append(f"duplicate venue_id: {venue_id}")
                else:
                    ids.add(venue_id)
                if record.get("layer") not in LAYER_PRIOR:
                    errors.append(f"catalog.records[{index}].layer unsupported")
                if not isinstance(record.get("topic_tags"), list):
                    errors.append(f"catalog.records[{index}].topic_tags must be an array")
    return errors


def _groups_by_axis(model: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    result = {axis: [] for axis in AXIS_ORDER}
    for group in model.get("tag_groups", []):
        if isinstance(group, dict) and group.get("axis_id") in result:
            result[group["axis_id"]].append(group)
    return result


def _aggregate_loadings(loadings: list[int]) -> int:
    """Collapse indicator hits into a 0–3 axis loading.

    A strong indicator establishes a substantive axis; multiple medium
    indicators can elevate an axis, but repeated labels cannot create an
    unbounded score.  This is a declared aggregation rule, not a learned
    weight.
    """

    if not loadings:
        return 0
    maximum = max(loadings)
    if maximum >= 3:
        return 3
    if maximum == 2 and len(loadings) >= 2:
        return 3
    return maximum


def vector_from_tags(tags: list[str] | set[str], model: dict[str, Any]) -> dict[str, Any]:
    """Compute an auditable venue/project vector from canonical tags."""

    tag_set = {str(tag) for tag in tags if isinstance(tag, str) and tag}
    matches: dict[str, list[str]] = {axis: [] for axis in AXIS_ORDER}
    loadings: dict[str, list[int]] = {axis: [] for axis in AXIS_ORDER}
    for group in model.get("tag_groups", []):
        if not isinstance(group, dict):
            continue
        axis = group.get("axis_id")
        if axis not in AXIS_ORDER:
            continue
        hit = sorted(tag_set & set(group.get("tags", [])))
        if hit:
            matches[axis].extend(hit)
            loadings[axis].extend([int(group["weight"])] * len(hit))
    vector = {axis: _aggregate_loadings(loadings[axis]) for axis in AXIS_ORDER}
    return {
        "vector": vector,
        "matched_indicators": {axis: sorted(set(matches[axis])) for axis in AXIS_ORDER if matches[axis]},
        "input_tags": sorted(tag_set),
        "active_axes": [axis for axis in AXIS_ORDER if vector[axis] >= 2],
    }


def project_tags(profile: dict[str, Any], model: dict[str, Any]) -> list[str]:
    """Derive canonical tags from an idea/profile without mutating its lock."""

    tags: set[str] = set()
    explicit = profile.get("topic_tags", [])
    if isinstance(explicit, list):
        tags.update(tag for tag in explicit if isinstance(tag, str))
    claim_shape = profile.get("claim_shape", {})
    if isinstance(claim_shape, dict):
        mapping = model.get("claim_shape_to_tags", {})
        for key, enabled in claim_shape.items():
            if enabled is True:
                tags.update(mapping.get(key, []))
    packs = profile.get("domain_packs", [])
    if isinstance(packs, list):
        mapping = model.get("domain_pack_to_tags", {})
        for pack in packs:
            tags.update(mapping.get(pack, []))
    center = profile.get("contribution_center")
    if isinstance(center, str):
        tags.update(CENTER_TO_TAGS.get(center, []))
    centers = profile.get("contribution_centers", [])
    if isinstance(centers, list):
        for item in centers:
            if isinstance(item, str):
                tags.update(CENTER_TO_TAGS.get(item, []))
    return sorted(tags)


def project_vector(profile: dict[str, Any], model: dict[str, Any]) -> dict[str, Any]:
    """Compute the project vector, preserving explicit human overrides."""

    tags = project_tags(profile, model)
    derived = vector_from_tags(tags, model)
    explicit = profile.get("submanifold_axes")
    if isinstance(explicit, dict):
        vector = dict(derived["vector"])
        for axis in AXIS_ORDER:
            value = explicit.get(axis)
            if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 3:
                vector[axis] = value
        derived["vector"] = vector
        derived["active_axes"] = [axis for axis in AXIS_ORDER if vector[axis] >= 2]
        derived["explicit_axes"] = {axis: explicit[axis] for axis in AXIS_ORDER if axis in explicit}
    return derived


def venue_vector(venue: dict[str, Any], model: dict[str, Any]) -> dict[str, Any]:
    """Compute a factor vector for one catalog record."""

    result = vector_from_tags(venue.get("topic_tags", []), model)
    result["venue_id"] = venue.get("venue_id")
    result["name"] = venue.get("name")
    result["kind"] = venue.get("kind")
    result["layer"] = venue.get("layer")
    result["directness_weight"] = LAYER_PRIOR.get(venue.get("layer"), 0.0)
    result["contribution_gate"] = venue.get("contribution_gate", [])
    return result


def research_intensity(project: dict[str, Any], model: dict[str, Any]) -> dict[str, Any]:
    """Summarize factor breadth/depth and propose, never silently lock, obligations."""

    vector = project["vector"]
    active = [axis for axis in AXIS_ORDER if vector[axis] >= 2]
    maximum = max(vector.values()) if vector else 0
    breadth = len(active)
    if not active:
        level = "UNSPECIFIED"
    elif maximum <= 1:
        level = "LOCAL_COMPONENT"
    elif breadth <= 2:
        level = "MECHANISM_OR_SINGLE_SYSTEM"
    elif breadth <= 4:
        level = "INTEGRATED_SYSTEM"
    else:
        level = "CROSS_AXIS_SYSTEM"
    pressure_map = model.get("evidence_pressure_map", {})
    pressures = sorted({item for axis in active for item in pressure_map.get(axis, [])})
    return {
        "level": level,
        "active_axes": active,
        "maximum_axis_loading": maximum,
        "axis_breadth": breadth,
        "proposed_evidence_pressures": pressures,
        "claim_altitude_status": "PROPOSED_FOR_EXPLICIT_REVIEW",
        "rule": "Use this summary to propose evidence obligations and claim boundaries; never silently rewrite Claim Lock or Design Lock.",
    }


def compare_vectors(project: dict[str, Any], venue: dict[str, Any], model: dict[str, Any]) -> dict[str, Any]:
    """Compare project and venue factors component by component."""

    vv = venue_vector(venue, model)
    pv = project["vector"]
    axis_rows = []
    shared = 0
    demand = 0
    supported_axes = 0
    for axis in AXIS_ORDER:
        project_loading = pv[axis]
        venue_loading = vv["vector"][axis]
        shared_loading = min(project_loading, venue_loading)
        if project_loading >= 2:
            demand += project_loading
            shared += shared_loading
            if venue_loading >= 2:
                supported_axes += 1
        if project_loading == 0 and venue_loading == 0:
            relation = "inactive"
        elif venue_loading >= project_loading and project_loading > 0:
            relation = "supported"
        elif venue_loading > 0 and project_loading > 0:
            relation = "partial"
        elif project_loading > 0:
            relation = "venue_gap"
        else:
            relation = "venue_specialty"
        axis_rows.append({"axis_id": axis, "project": project_loading, "venue": venue_loading, "shared": shared_loading, "relation": relation})
    overlap = round(shared / demand, 4) if demand else 0.0
    kind_ok = not project.get("target_kind") or project.get("target_kind") in {venue.get("kind"), "either"}
    center = project.get("contribution_center")
    gate = set(venue.get("contribution_gate", []))
    gate_status = "UNKNOWN" if not center else ("PASS" if center in gate else "CONDITIONAL")
    if not kind_ok:
        route = "NOT_ROUTED"
    elif not project.get("active_axes"):
        route = "DISCOVERY_ONLY"
    elif overlap >= 0.65 and gate_status in {"PASS", "UNKNOWN"}:
        route = "PRIMARY_CANDIDATE"
    elif overlap >= 0.25 and gate_status != "CONDITIONAL":
        route = "CONDITIONAL_CANDIDATE"
    elif overlap >= 0.25:
        route = "CONDITIONAL_CANDIDATE"
    else:
        route = "NOT_ROUTED"
    weighted_fit = round(overlap * vv["directness_weight"], 4)
    return {
        "venue_id": vv["venue_id"],
        "name": vv["name"],
        "kind": vv["kind"],
        "layer": vv["layer"],
        "directness_weight": vv["directness_weight"],
        "factor_overlap": overlap,
        "weighted_fit": weighted_fit,
        "supported_active_axes": supported_axes,
        "active_project_axes": len(project.get("active_axes", [])),
        "contribution_gate": {"status": gate_status, "project_center": center, "venue_centers": sorted(gate)},
        "axis_comparison": axis_rows,
        "route": route,
        "evidence_status": "REQUIRES_PROJECT_EVIDENCE_PROFILE",
        "note": "This is a factor-fit candidate, not an acceptance probability or a final submission decision.",
    }


def analyze(profile: dict[str, Any], catalog: dict[str, Any], model: dict[str, Any], top_k: int = 12) -> dict[str, Any]:
    """Return the complete submanifold analysis and ranked factor candidates."""

    errors = validate_model(model, catalog)
    if errors:
        raise ValueError("invalid robotics submanifold inputs: " + "; ".join(errors))
    project = project_vector(profile, model)
    intensity = research_intensity(project, model)
    candidates = [compare_vectors(project, venue, model) for venue in catalog["records"]]
    candidates.sort(key=lambda item: ({"PRIMARY_CANDIDATE": 0, "CONDITIONAL_CANDIDATE": 1, "DISCOVERY_ONLY": 2, "NOT_ROUTED": 3}[item["route"]], -item["weighted_fit"], item["name"]))
    target_kind = profile.get("target_kind")
    if target_kind not in (None, "either"):
        candidates = [item for item in candidates if item["kind"] == target_kind or item["route"] == "NOT_ROUTED"]
    return {
        "schema_version": "robotics-submanifold-analysis.v1",
        "model_id": model.get("model_id"),
        "model_digest": model_digest(model),
        "catalog_id": catalog.get("catalog_id"),
        "catalog_digest": catalog_digest(catalog),
        "profile": profile,
        "project_vector": project,
        "research_intensity": intensity,
        "candidates": candidates[:top_k],
        "infrastructure_status": "EXPERT_CODED_SEMANTIC_FACTOR_MODEL",
        "limitations": [
            "The axes are semantic latent dimensions distilled from the supplied venue set, not PCA components.",
            "Venue fit does not estimate acceptance probability without paper-level and outcome-level data.",
            "Evidence pressures are proposals that require explicit project-level adjudication.",
        ],
    }
