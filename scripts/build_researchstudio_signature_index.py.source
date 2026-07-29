"""Adapt the balanced public robotics corpus to the ResearchStudio signature contract.

The current 100-paper corpus contains metadata, tags and short extraction
prompts rather than complete abstracts/reviews.  This adapter therefore emits
explicitly labelled metadata-only Stage-1/Stage-2 placeholders.  It is useful
for infrastructure smoke tests and axis strategy baselines, but a future
full-text run must replace these fields before claiming induced clusters or
outcome contrasts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.build_researchstudio_pattern_cards import AXIS_PROFILES


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "corpus" / "public-paper-index.json"
DEFAULT_OUTPUT = ROOT / "corpus" / "researchstudio-paper-signatures.v1.json"


def _portable_source_reference(input_path: str | Path) -> tuple[str, str]:
    """Return a repository-portable source reference and content digest.

    生成产物不得记录本机绝对路径；仓库内文件使用相对 POSIX 路径，外部
    输入只保留内容摘要。 / Generated artifacts must not record host-specific
    absolute paths; repository inputs use a relative POSIX path, while external
    inputs retain only a content digest.
    """
    path = Path(input_path).resolve()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    try:
        reference = path.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        reference = f"external-corpus-sha256:{digest}"
    return reference, digest


def _contribution_type(record: dict[str, Any]) -> str:
    tags = " ".join(str(item) for item in record.get("pattern_tags", [])).casefold()
    axis = str(record.get("primary_axis"))
    if "benchmark" in tags or "dataset" in tags or "testbed" in tags:
        return "benchmark"
    if axis in {"E", "S", "A"}:
        return "system"
    if axis in {"C", "D"}:
        return "theoretical" if any(term in tags for term in ("optimality", "observability", "barrier", "bound", "formal")) else "methodological"
    return "methodological"


def _outcome_signal(record: dict[str, Any]) -> dict[str, Any]:
    presentation = record.get("presentation") if isinstance(record.get("presentation"), dict) else {}
    award = record.get("award") if isinstance(record.get("award"), dict) else {}
    return {
        "label": presentation.get("level") or "journal_record",
        "recognition_status": award.get("status"),
        "source_urls": [item for item in (presentation.get("source_url"), award.get("source_url")) if item],
        "semantics": "descriptive_public_trace_only; not a decision outcome and not an acceptance probability",
    }


def _make_record(record: dict[str, Any]) -> dict[str, Any]:
    axis = str(record.get("primary_axis"))
    profile = AXIS_PROFILES[axis]
    tags = [str(item) for item in record.get("pattern_tags", [])]
    extracts = [str(item) for item in record.get("extract", [])]
    boundaries = [str(item) for item in record.get("do_not_infer", [])]
    title = str(record.get("title", ""))
    key_step = extracts[0] if extracts else "the load-bearing mechanism"
    bottleneck = extracts[1] if len(extracts) > 1 else "the unresolved axis-specific constraint"
    failure = extracts[2] if len(extracts) > 2 else "the deployment boundary"
    base = {
        "innovation_approach": f"Metadata adapter for {title}: make {key_step} operational and test it against {failure}.",
        "key_step": f"Expose {key_step} as the intervention that links the research object to the robot outcome.",
        "why_non_obvious": f"The load-bearing {bottleneck} is entangled with the rest of the robot loop and is easy to mistake for an implementation detail.",
        "trigger_condition": f"When {bottleneck} limits the {axis} research axis, apply the axis strategy signature to achieve a measurable downstream outcome.",
        "reviewer_praise": [],
        "reviewer_concern": [],
        "acceptance_signal": "No reviewer or decision text is present in the 100-paper metadata corpus; retain public presentation/recognition as a descriptive trace only.",
        "contribution_type": _contribution_type(record),
    }
    abstract = {
        "abstract_strategy": profile["strategy_signature_template"],
        "abstract_key_step": f"Name the axis-specific load-bearing object ({key_step}), isolate it, and test the downstream robot consequence.",
        "abstract_why_non_obvious": "The field often treats the relevant body, state, loop, interface or system constraint as a fixed background rather than a controllable research object.",
        "abstract_trigger_condition": f"When the {profile['axis_name_zh']} bottleneck is structural rather than a missing application feature, apply the matched operator and its negative control.",
    }
    return {
        "paper_id": record.get("paper_id"),
        "title": title,
        "year": record.get("year"),
        "venue": record.get("venue"),
        "venue_kind": record.get("venue_kind"),
        "primary_axis": axis,
        "submanifold_axes": record.get("submanifold_axes", {}),
        "source_urls": [item for item in (record.get("preprint", {}).get("url"), record.get("final_publication", {}).get("url")) if item],
        "source_text_status": "metadata_only_no_full_text_ingested",
        "extraction_method": "researchstudio_metadata_adapter_v1",
        "extraction_fidelity": "METADATA_ONLY",
        "stage1_base_fields": base,
        "stage2_domain_agnostic_fields": abstract,
        "innovation_signature": base["innovation_approach"],
        "strategy_signature": " ".join(abstract.values()),
        "problem_bottleneck": bottleneck,
        "key_method": tags,
        "do_not_infer": boundaries,
        "outcome_signal": _outcome_signal(record),
        "pattern_tags": tags,
        "llm_reextraction_required": True,
        "llm_reextraction_contract": "Supply title + abstract/introduction + available reviews; return non-empty Stage-1 review lists and four Stage-2 rewrites before production clustering.",
    }


def build(input_path: str | Path = DEFAULT_INPUT) -> dict[str, Any]:
    data = json.loads(Path(input_path).read_text(encoding="utf-8"))
    records = data.get("records", [])
    signatures = [_make_record(record) for record in records if isinstance(record, dict)]
    source_reference, source_digest = _portable_source_reference(input_path)
    return {
        "schema_version": "researchstudio-paper-signatures.v1",
        "source_corpus": source_reference,
        "source_corpus_sha256": source_digest,
        "record_count": len(signatures),
        "stage_contract": {
            "stage1_fields": ["innovation_approach", "key_step", "why_non_obvious", "trigger_condition", "reviewer_praise", "reviewer_concern", "acceptance_signal", "contribution_type"],
            "stage2_embedded_fields": ["abstract_strategy", "abstract_key_step", "abstract_why_non_obvious", "abstract_trigger_condition"],
            "embedding_input": "field-prefixed concatenation of the four Stage-2 domain-agnostic fields",
            "outcome_usage": "Oral/HC/Reject comparisons are disabled until decision-aligned labels and provenance are present.",
        },
        "data_fidelity": "METADATA_ONLY",
        "records": signatures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build ResearchStudio-compatible robotics paper signatures.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(build(args.input), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
