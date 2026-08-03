"""Validate the current 15/31 ResearchStudio pattern library."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from common.researchstudio_patterns import DEFAULT_LIBRARY, load_pattern_library, validate_pattern_library  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the robotics ResearchStudio pattern library.")
    parser.add_argument("--path", default=str(DEFAULT_LIBRARY))
    args = parser.parse_args()
    errors = validate_pattern_library(load_pattern_library(args.path))
    if errors:
        for error in errors:
            print("ERROR:", error)
        return 1
    print("RESEARCHSTUDIO_PATTERN_LIBRARY: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
