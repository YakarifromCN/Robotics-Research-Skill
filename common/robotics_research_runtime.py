"""Load the compact, versioned robotics research runtime artifact.

The full 100-paper corpus is an offline build/audit input.  Runtime Skills use
only this derived artifact and therefore do not need the paper corpus on every
invocation.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME = ROOT / "corpus" / "robotics-research-runtime.v1.json"
AXES = ("E", "P", "C", "L", "D", "H", "A", "S")


def load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"runtime artifact must be a JSON object: {path}")
    return value


def validate_runtime(runtime: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if runtime.get("schema_version") != "robotics-research-runtime.v1":
        errors.append("schema_version must be robotics-research-runtime.v1")
    if runtime.get("artifact_status") != "DERIVED_RUNTIME_ONLY":
        errors.append("artifact_status must be DERIVED_RUNTIME_ONLY")

    source = runtime.get("source")
    if not isinstance(source, dict):
        errors.append("source must be an object")
        source = {}
    if source.get("record_count") != 100:
        errors.append("source.record_count must be 100")
    if source.get("raw_corpus_loaded_at_runtime") is not False:
        errors.append("source.raw_corpus_loaded_at_runtime must be false")
    if not isinstance(source.get("corpus_sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", source["corpus_sha256"]):
        errors.append("source.corpus_sha256 must be a lowercase 64-character SHA-256 digest")

    exemplars = runtime.get("paper_exemplars_by_axis")
    if not isinstance(exemplars, dict):
        errors.append("paper_exemplars_by_axis must be an object")
        exemplars = {}
    for axis in AXES:
        rows = exemplars.get(axis)
        if not isinstance(rows, list) or not rows:
            errors.append(f"paper_exemplars_by_axis.{axis} must be a non-empty array")
        elif any(not isinstance(row, dict) or not isinstance(row.get("paper_id"), str) for row in rows):
            errors.append(f"paper_exemplars_by_axis.{axis} contains an invalid exemplar")

    strategies = runtime.get("axis_strategy_by_axis")
    if not isinstance(strategies, dict) or set(strategies) != set(AXES):
        errors.append("axis_strategy_by_axis must contain exactly E/P/C/L/D/H/A/S")
    else:
        for axis in AXES:
            row = strategies[axis]
            if not isinstance(row, dict) or row.get("axis_id") != axis:
                errors.append(f"axis_strategy_by_axis.{axis} has an invalid axis row")

    pattern_system = runtime.get("pattern_system")
    if not isinstance(pattern_system, dict):
        errors.append("pattern_system must be an object")
    else:
        if pattern_system.get("parent_cards") != 15:
            errors.append("pattern_system.parent_cards must be 15")
        if pattern_system.get("subpattern_cards") != 31:
            errors.append("pattern_system.subpattern_cards must be 31")

    runtime_contract = runtime.get("runtime_contract")
    if not isinstance(runtime_contract, dict) or not isinstance(runtime_contract.get("exemplar_count_per_axis"), int) or runtime_contract["exemplar_count_per_axis"] < 1:
        errors.append("runtime_contract.exemplar_count_per_axis must be a positive integer")

    if runtime.get("outcome_contract", {}).get("acceptance_probability") != "NOT_ESTIMABLE":
        errors.append("outcome_contract.acceptance_probability must be NOT_ESTIMABLE")
    return errors


def load_runtime(path: str | Path = DEFAULT_RUNTIME) -> dict[str, Any]:
    runtime = load_json(path)
    errors = validate_runtime(runtime)
    if errors:
        raise ValueError("invalid robotics runtime artifact: " + "; ".join(errors))
    return runtime
