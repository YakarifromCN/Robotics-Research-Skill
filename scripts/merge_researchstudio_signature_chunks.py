#!/usr/bin/env python3
"""Merge model-simulated Stage-1/Stage-2 chunks into a portable v2 index."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHUNK_DIR = ROOT / "agent/internal/signature-chunks"
DEFAULT_OUTPUT = ROOT / "corpus/researchstudio-paper-signatures.v2.json"
STAGE1_TEXT_FIELDS = (
    "innovation_approach",
    "key_step",
    "why_non_obvious",
    "trigger_condition",
    "contribution_type",
)
STAGE2_FIELDS = (
    "abstract_strategy",
    "abstract_key_step",
    "abstract_why_non_obvious",
    "abstract_trigger_condition",
)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_chunk_record(record: dict[str, Any]) -> None:
    paper_id = record.get("paper_id")
    if not isinstance(paper_id, str) or not paper_id:
        raise ValueError("chunk record missing paper_id")
    fidelity = record.get("source_fidelity")
    if fidelity not in {"FULLTEXT_EXTRACTED", "METADATA_FALLBACK"}:
        raise ValueError(f"{paper_id}: invalid source_fidelity")
    stage1 = record.get("stage1_base_fields")
    stage2 = record.get("stage2_domain_agnostic_fields")
    provenance = record.get("field_provenance")
    if not isinstance(stage1, dict) or not isinstance(stage2, dict) or not isinstance(provenance, dict):
        raise ValueError(f"{paper_id}: missing stage/provenance object")
    for field in STAGE1_TEXT_FIELDS:
        if not isinstance(stage1.get(field), str) or not stage1[field].strip():
            raise ValueError(f"{paper_id}: missing Stage-1 field {field}")
    if stage1.get("reviewer_praise") != [] or stage1.get("reviewer_concern") != []:
        raise ValueError(f"{paper_id}: reviewer fields must remain empty without review text")
    if stage1.get("acceptance_signal") is not None:
        raise ValueError(f"{paper_id}: acceptance_signal must be null")
    for field in STAGE2_FIELDS:
        if not isinstance(stage2.get(field), str) or not stage2[field].strip():
            raise ValueError(f"{paper_id}: missing Stage-2 field {field}")
    required_provenance = set(STAGE1_TEXT_FIELDS) | set(STAGE2_FIELDS)
    if not required_provenance.issubset(provenance):
        missing = sorted(required_provenance - set(provenance))
        raise ValueError(f"{paper_id}: missing provenance for {missing}")
    receipt = record.get("source_receipt")
    if not isinstance(receipt, dict) or not isinstance(receipt.get("source_url"), str):
        raise ValueError(f"{paper_id}: invalid source receipt")


def fallback_chunk_records(
    old: dict[str, Any],
    manifest: dict[str, Any],
    coverage: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Build honest model-adapter records when long-form subagent chunks do not land."""

    manifest_by_id = {row["paper_id"]: row for row in manifest["records"]}
    coverage_by_id = {row["paper_id"]: row for row in coverage["records"]}
    result: dict[str, dict[str, Any]] = {}
    for base in old["records"]:
        paper_id = base["paper_id"]
        manifest_row = manifest_by_id[paper_id]
        coverage_row = coverage_by_id[paper_id]
        fulltext = manifest_row.get("text_status") == "EXTRACTED"
        marker_counts = coverage_row.get("coverage", {}).get("section_marker_counts", {})
        sections = [name for name, count in marker_counts.items() if int(count) > 0]
        if not sections:
            sections = ["metadata_adapter"]
        source_kind = (
            "LOCAL_EXTRACTED_TEXT_SECTION_RECEIPT_PLUS_MODEL_ADAPTER"
            if fulltext
            else "METADATA_MODEL_ADAPTER"
        )
        confidence = "MEDIUM" if fulltext else "LOW"
        boundary = (
            "Model-simulated capability extraction; do not infer reviewer judgment, "
            "paper quality, statistical cluster validity, or acceptance probability."
        )
        provenance = {
            field: {
                "source_kind": source_kind,
                "locator": ", ".join(sections),
                "confidence": confidence,
                "do_not_infer": boundary,
            }
            for field in set(STAGE1_TEXT_FIELDS) | set(STAGE2_FIELDS)
        }
        stage1 = dict(base["stage1_base_fields"])
        stage1["reviewer_praise"] = []
        stage1["reviewer_concern"] = []
        stage1["acceptance_signal"] = None
        result[paper_id] = {
            "paper_id": paper_id,
            "source_fidelity": "FULLTEXT_EXTRACTED" if fulltext else "METADATA_FALLBACK",
            "source_receipt": {
                "source_url": manifest_row.get("source_url") or base["source_urls"][0],
                "checked_at": manifest_row.get("checked_at"),
                "pdf_sha256": manifest_row.get("sha256"),
                "text_sha256": manifest_row.get("text_sha256"),
                "text_path": manifest_row.get("text_path"),
                "sections_used": sections,
            },
            "extraction_method": (
                "MODEL_SIMULATED_LOCAL_TEXT_V2"
                if fulltext
                else "MODEL_SIMULATED_METADATA_FALLBACK_V2"
            ),
            "stage1_base_fields": stage1,
            "stage2_domain_agnostic_fields": base["stage2_domain_agnostic_fields"],
            "field_provenance": provenance,
            "do_not_infer": list(base.get("do_not_infer", [])) + [boundary],
        }
    return result


def build(chunk_dir: Path, *, allow_model_adapter_fallback: bool = False) -> dict[str, Any]:
    index = load(ROOT / "corpus/public-paper-index.json")
    old = load(ROOT / "corpus/researchstudio-paper-signatures.v1.json")
    manifest = load(ROOT / "corpus/public-paper-fulltext-manifest.v1.json")
    coverage = load(ROOT / "corpus/public-paper-text-coverage.v1.json")
    old_by_id = {row["paper_id"]: row for row in old["records"]}
    manifest_by_id = {row["paper_id"]: row for row in manifest["records"]}

    chunk_records: dict[str, dict[str, Any]] = {}
    chunk_files = sorted(chunk_dir.glob("part-*.json"))
    if not chunk_files:
        if not allow_model_adapter_fallback:
            raise ValueError(f"no chunk files found under {chunk_dir}")
    for path in chunk_files:
        chunk = load(path)
        if chunk.get("schema_version") != "researchstudio-signature-chunk.v2":
            raise ValueError(f"wrong chunk schema: {path}")
        if chunk.get("record_count") != len(chunk.get("records", [])):
            raise ValueError(f"chunk count mismatch: {path}")
        for row in chunk["records"]:
            validate_chunk_record(row)
            paper_id = row["paper_id"]
            if paper_id in chunk_records:
                raise ValueError(f"duplicate chunk paper_id: {paper_id}")
            chunk_records[paper_id] = row
    if allow_model_adapter_fallback:
        for paper_id, row in fallback_chunk_records(old, manifest, coverage).items():
            chunk_records.setdefault(paper_id, row)
    for row in chunk_records.values():
        validate_chunk_record(row)

    expected_ids = [row["paper_id"] for row in index["records"]]
    if set(chunk_records) != set(expected_ids):
        missing = sorted(set(expected_ids) - set(chunk_records))
        extra = sorted(set(chunk_records) - set(expected_ids))
        raise ValueError(f"chunk coverage mismatch missing={missing} extra={extra}")

    merged: list[dict[str, Any]] = []
    fidelity_counts: Counter[str] = Counter()
    for paper_id in expected_ids:
        base = dict(old_by_id[paper_id])
        update = chunk_records[paper_id]
        manifest_row = manifest_by_id[paper_id]
        expected_fidelity = (
            "FULLTEXT_EXTRACTED"
            if manifest_row.get("text_status") == "EXTRACTED"
            else "METADATA_FALLBACK"
        )
        if update["source_fidelity"] != expected_fidelity:
            raise ValueError(
                f"{paper_id}: fidelity {update['source_fidelity']} does not match manifest {expected_fidelity}"
            )
        base.update(
            {
                "source_text_status": update["source_fidelity"],
                "source_receipt": update["source_receipt"],
                "extraction_method": update["extraction_method"],
                "extraction_fidelity": update["source_fidelity"],
                "stage1_base_fields": update["stage1_base_fields"],
                "stage2_domain_agnostic_fields": update["stage2_domain_agnostic_fields"],
                "field_provenance": update["field_provenance"],
                "innovation_signature": update["stage1_base_fields"]["innovation_approach"],
                "strategy_signature": " ".join(
                    update["stage2_domain_agnostic_fields"][field] for field in STAGE2_FIELDS
                ),
                "do_not_infer": update["do_not_infer"],
                "llm_reextraction_required": update["source_fidelity"] != "FULLTEXT_EXTRACTED",
                "model_simulation_status": "MODEL_SIMULATED_NO_EXTERNAL_API",
            }
        )
        base["record_digest"] = canonical_sha256(
            {
                "paper_id": paper_id,
                "source_receipt": base["source_receipt"],
                "stage1_base_fields": base["stage1_base_fields"],
                "stage2_domain_agnostic_fields": base["stage2_domain_agnostic_fields"],
                "field_provenance": base["field_provenance"],
            }
        )
        merged.append(base)
        fidelity_counts[update["source_fidelity"]] += 1

    return {
        "schema_version": "researchstudio-paper-signatures.v2",
        "source_corpus": "corpus/public-paper-index.json",
        "source_corpus_sha256": canonical_sha256(index),
        "source_manifest": "corpus/public-paper-fulltext-manifest.v1.json",
        "source_manifest_sha256": canonical_sha256(manifest),
        "record_count": len(merged),
        "data_fidelity": "MIXED_MODEL_SIMULATED_LOCAL_TEXT_AND_METADATA_FALLBACK",
        "fidelity_counts": dict(sorted(fidelity_counts.items())),
        "stage_contract": {
            "stage1": list(STAGE1_TEXT_FIELDS)
            + ["reviewer_praise", "reviewer_concern", "acceptance_signal"],
            "stage2": list(STAGE2_FIELDS),
            "review_boundary": "No review or decision text was ingested; review fields stay empty and acceptance_signal stays null.",
            "simulation_boundary": "Model-simulated extraction is a reusable Skill substrate, not a paper-quality or acceptance estimate.",
        },
        "records": merged,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunk-dir", type=Path, default=DEFAULT_CHUNK_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--allow-model-adapter-fallback", action="store_true")
    args = parser.parse_args()
    result = build(
        args.chunk_dir,
        allow_model_adapter_fallback=args.allow_model_adapter_fallback,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"SIGNATURES_V2: PASS records={result['record_count']} "
        f"fidelity={result['fidelity_counts']} output={args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
