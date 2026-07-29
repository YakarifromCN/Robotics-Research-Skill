"""Run the corpus-first and ResearchStudio-aware validation chain."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> None:
    print("+", " ".join(command), flush=True)
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode:
        raise SystemExit(result.returncode)


def main() -> int:
    python = sys.executable
    run([python, "-B", "scripts/run_all_checks_v2.py"])
    run([python, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_robotics_research_context.py", "-v"])
    run([python, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_researchstudio_infrastructure.py", "-v"])
    run([python, "-B", "scripts/run_researchstudio_robotics_pipeline.py"])
    run([python, "-B", "scripts/validate_researchstudio_pattern_library.py"])
    run([python, "-B", "scripts/validate_robotics_axis_strategy_analysis.py"])
    run([python, "-B", "scripts/route_robotics_research.py", "skills/develop-robotics-idea/assets/research-card.template.json", "--stage", "idea", "--venue", "conf-icra", "--per-axis", "2"])
    print("ALL_CHECKS_CORPUS_FIRST_RESEARCHSTUDIO: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
