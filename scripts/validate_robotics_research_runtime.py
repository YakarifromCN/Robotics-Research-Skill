"""Validate the tracked compact runtime artifact without loading the corpus."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common.robotics_research_runtime import DEFAULT_RUNTIME, load_runtime  # noqa: E402


def main() -> int:
    runtime = load_runtime(DEFAULT_RUNTIME)
    print(
        "ROBOTICS_RUNTIME: PASS "
        f"source_records={runtime['source']['record_count']} "
        f"raw_corpus_loaded_at_runtime={runtime['source']['raw_corpus_loaded_at_runtime']} "
        f"exemplars_per_axis={runtime['runtime_contract']['exemplar_count_per_axis']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
