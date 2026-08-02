"""Canonical runtime-first router with ResearchStudio strategy context."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common.researchstudio_ideation import build_strategy_context  # noqa: E402
from common.robotics_research_context import build_research_context  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare the runtime-first robotics + ResearchStudio research context.")
    parser.add_argument("profile")
    parser.add_argument("--stage", choices=("idea", "experiment", "writing", "review"), default="idea")
    parser.add_argument("--venue")
    parser.add_argument("--per-axis", type=int, default=4)
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.per_axis < 1:
        parser.error("--per-axis must be positive")
    profile = json.loads(Path(args.profile).read_text(encoding="utf-8"))
    context = build_research_context(profile, stage=args.stage, target_venue=args.venue, per_axis=args.per_axis)
    context["researchstudio_strategy_context"] = build_strategy_context(context, profile, target_venue=args.venue)
    context["routing_contract"] = {
        "order": ["compact robotics runtime artifact", "eight-axis context", "ResearchStudio axis-pattern cards", "stage adapter", "official venue scope"],
        "raw_corpus_loaded": context["first_core_reference"]["raw_corpus_loaded"],
        "outcome_semantics": "pattern and corpus outcomes are audit context only; acceptance probability is NOT_ESTIMABLE",
    }
    payload = json.dumps(context, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload, encoding="utf-8")
        print(target.resolve())
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
