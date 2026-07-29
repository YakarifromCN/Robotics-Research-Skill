"""Run the retrieval-first, pattern-guided robotics Idea chain."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common.researchstudio_ideation import run_ideation_chain  # noqa: E402
from common.robotics_research_context import build_research_context  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the ResearchStudio-inspired robotics ideation chain.")
    parser.add_argument("profile")
    parser.add_argument("--output")
    parser.add_argument("--venue")
    args = parser.parse_args()
    profile = json.loads(Path(args.profile).read_text(encoding="utf-8"))
    base = build_research_context(profile, stage="idea", target_venue=args.venue)
    result = run_ideation_chain(profile, base)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
        print(output.resolve())
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
