"""Run the original Skill checks plus the v2 submanifold/corpus checks."""

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
    run([python, "-B", "scripts/run_all_checks.py"])
    run([python, "-B", "scripts/validate_venue_catalog_v2.py"])
    run([python, "-B", "scripts/validate_robotics_submanifold.py", "--catalog", "corpus/venue-catalog.v2.json"])
    run([python, "-B", "scripts/validate_public_paper_index.py"])
    run([python, "-B", "scripts/check_portable_corpus_paths.py"])
    run([python, "-B", "scripts/calibrate_robotics_submanifold.py"])
    run([python, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_public_paper_index.py", "-v"])
    run([python, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_venue_catalog_v2.py", "-v"])
    print("ALL_CHECKS_V2: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
