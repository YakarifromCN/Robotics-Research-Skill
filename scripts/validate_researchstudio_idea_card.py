"""CLI facade for the ResearchStudio Idea Card validator."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common.researchstudio_idea_validation import main, validate  # noqa: E402

__all__ = ["main", "validate"]


if __name__ == "__main__":
    raise SystemExit(main())
