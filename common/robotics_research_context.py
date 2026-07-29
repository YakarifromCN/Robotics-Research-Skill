"""First-core-reference context built from the public robotics paper corpus.

The corpus is an active research-design dependency.  This module turns its
paper-level axis vectors, extractable patterns, and do-not-infer boundaries
into a stage-neutral context that the Idea, Experiment, Writing, and Review
skills can consume before venue routing.  It does not copy paper text and does
not treat awards as quality weights.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .robotics_submanifold import AXIS_ORDER, analyze, load_json, project_vector, research_intensity


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = ROOT / "corpus" / "robotics-submanifold.v1.json"
DEFAULT_CATALOG = ROOT / "corpus" / "venue-catalog.v2.json"
DEFAULT_CORPUS = ROOT / "corpus" / "public-paper-index.json"
DEFAULT_CALIBRATION = ROOT / "corpus" / "robotics-submanifold-calibration.v1.json"


def _corpus_errors(corpus: dict[str, Any]) -> list[str]:
    # Importing the existing hard-gate validator keeps the single source of
    # truth for the 100-record, 50/50, award, oral, and balance constraints.
    from scripts.validate_public_paper_index import validate

    return validate(corpus)


def load_first_core_reference(
    *,
    model_path: str | Path = DEFAULT_MODEL,
    catalog_path: str | Path = DEFAULT_CATALOG,
    corpus_path: str | Path = DEFAULT_CORPUS,
    calibration_path: str | Path = DEFAULT_CALIBRATION,
) -> dict[str, Any]:
    """Load and hard-validate the corpus/model/catalog first reference."""

    model = load_json(model_path)
    catalog = load_json(catalog_path)
    corpus = load_json(corpus_path)
    calibration = load_json(calibration_path) if Path(calibration_path).exists() else {}
    errors = _corpus_errors(corpus)
    if errors:
        raise ValueError("first core reference corpus is invalid: " + "; ".join(errors))
    records = corpus.get("records", [])
    if not isinstance(records, list) or len(records) != 100:
        raise ValueError("first core reference requires exactly 100 records")
    return {
        "model": model,
        "catalog": catalog,
        "corpus": corpus,
        "calibration": calibration,
        "reference_status": "LOADED_AND_HARD_VALIDATED",
        "reference_contract": "The paper corpus must be read before stage-specific design or venue routing.",
    }


def _venue_weight_map(catalog: dict[str, Any]) -> dict[str, float]:
    result: dict[str, float] = {}
    for record in catalog.get("records", []):
        if isinstance(record, dict) and isinstance(record.get("name"), str):
            result[record["name"]] = float(record.get("directness_weight", 0.65))
    return result


def paper_reference_bundle(
    project_vector_result: dict[str, Any],
    reference: dict[str, Any],
    *,
    per_axis: int = 4,
) -> dict[str, Any]:
    """Select diverse paper exemplars for the active project axes."""

    if per_axis < 1:
        raise ValueError("per_axis must be positive")
    records = [record for record in reference["corpus"].get("records", []) if isinstance(record, dict)]
    venue_weights = _venue_weight_map(reference["catalog"])
    vector = project_vector_result["vector"]
    active_axes = [axis for axis in AXIS_ORDER if vector.get(axis, 0) >= 2]
    by_axis: dict[str, list[dict[str, Any]]] = {}
    pattern_summary: dict[str, dict[str, list[str]]] = {}
    for axis in active_axes:
        ranked = sorted(
            records,
            key=lambda record: (
                0 if record.get("primary_axis") == axis else 1,
                -int(record.get("submanifold_axes", {}).get(axis, 0)),
                -venue_weights.get(str(record.get("venue")), 0.65),
                str(record.get("paper_id")),
            ),
        )
        selected = ranked[:per_axis]
        by_axis[axis] = [
            {
                "paper_id": record.get("paper_id"),
                "title": record.get("title"),
                "year": record.get("year"),
                "venue": record.get("venue"),
                "venue_kind": record.get("venue_kind"),
                "primary_axis": record.get("primary_axis"),
                "submanifold_axes": record.get("submanifold_axes"),
                "pattern_tags": record.get("pattern_tags", []),
                "preprint_url": record.get("preprint", {}).get("url"),
                "final_publication_url": record.get("final_publication", {}).get("url"),
                "award_status": record.get("award", {}).get("status") if isinstance(record.get("award"), dict) else None,
            }
            for record in selected
        ]
        extracts = sorted({item for record in selected for item in record.get("extract", [])})
        limits = sorted({item for record in selected for item in record.get("do_not_infer", [])})
        pattern_summary[axis] = {"extract_patterns": extracts, "do_not_infer_boundaries": limits}

    return {
        "active_axes": active_axes,
        "paper_exemplars_by_axis": by_axis,
        "axis_pattern_summary": pattern_summary,
        "sampling_note": "Exemplars are selected from a balanced infrastructure corpus; they are pattern references, not prevalence or quality estimates.",
    }


def stage_adapters(active_axes: list[str]) -> dict[str, Any]:
    return {
        "idea": {
            "first_action": "read paper_exemplars_by_axis before drafting or accepting the Claim Lock",
            "use": "collision check, mechanism distinction, claim-altitude boundary",
            "must_not": "copy a paper's claim or infer generality from award/venue",
        },
        "experiment": {
            "first_action": "convert axis_pattern_summary into candidate conditions, contrasts, metrics, and failure logs",
            "use": "evidence obligation and negative-control planning",
            "must_not": "replace the project Design Lock with a corpus average",
        },
        "writing": {
            "first_action": "use paper patterns and do_not_infer boundaries to audit each load-bearing sentence",
            "use": "claim altitude, evidence-chain completeness, related-work positioning",
            "must_not": "turn corpus recognition or factor fit into an acceptance claim",
        },
        "review": {
            "first_action": "compare manuscript evidence against active-axis exemplars and their failure boundaries",
            "use": "panel focus, prior-art collision, evidence-gap diagnosis",
            "must_not": "use corpus awards or counts as reviewer scores",
        },
        "active_axes": active_axes,
    }


def build_research_context(
    profile: dict[str, Any],
    *,
    stage: str = "idea",
    target_venue: str | None = None,
    per_axis: int = 4,
    model_path: str | Path = DEFAULT_MODEL,
    catalog_path: str | Path = DEFAULT_CATALOG,
    corpus_path: str | Path = DEFAULT_CORPUS,
    calibration_path: str | Path = DEFAULT_CALIBRATION,
) -> dict[str, Any]:
    """Build the stage context with the paper corpus loaded first."""

    if stage not in {"idea", "experiment", "writing", "review"}:
        raise ValueError("stage must be idea, experiment, writing, or review")
    reference = load_first_core_reference(
        model_path=model_path,
        catalog_path=catalog_path,
        corpus_path=corpus_path,
        calibration_path=calibration_path,
    )
    project = project_vector(profile, reference["model"])
    intensity = research_intensity(project, reference["model"])
    route = analyze(profile, reference["catalog"], reference["model"], top_k=len(reference["catalog"].get("records", [])))
    target_fit = None
    if target_venue:
        target = target_venue.casefold()
        target_fit = next(
            (
                candidate
                for candidate in route["candidates"]
                if str(candidate.get("venue_id", "")).casefold() == target
                or str(candidate.get("name", "")).casefold() == target
            ),
            None,
        )
    exemplars = paper_reference_bundle(project, reference, per_axis=per_axis)
    return {
        "schema_version": "robotics-research-context.v1",
        "stage": stage,
        "first_core_reference": {
            "status": reference["reference_status"],
            "corpus_schema": reference["corpus"].get("schema_version"),
            "corpus_record_count": len(reference["corpus"]["records"]),
            "calibration_schema": reference["calibration"].get("schema_version"),
            "contract": reference["reference_contract"],
        },
        "project_vector": project,
        "research_intensity": intensity,
        "paper_reference_bundle": exemplars,
        "stage_adapter": stage_adapters(exemplars["active_axes"])[stage],
        "factor_fit_ranking": route["candidates"][:12],
        "fixed_venue_fit": target_fit,
        "venue_scope_status": "REFRESH_REQUIRED",
        "acceptance_probability": {"status": "NOT_ESTIMABLE"},
        "limitations": [
            "Paper exemplars are pattern references, not a statistical prevalence model.",
            "Corpus award status is recognition metadata, not evidence sufficiency.",
            "Venue fit is a routing proxy and requires current official-scope verification.",
        ],
    }
