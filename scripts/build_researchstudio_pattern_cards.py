"""Entry point for building the robotics ResearchStudio pattern library."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
_SOURCE = Path(__file__).with_name("build_researchstudio_pattern_cards.py.source")
_TEXT = _SOURCE.read_text(encoding="utf-8")
# Keep the preserved source readable while making omitted optional failure
# lists safe for the compact parent-card declarations.
_TEXT = _TEXT.replace("failure_modes: list[str],", "failure_modes: list[str] | None = None,")
_TEXT = _TEXT.replace('"failure_modes": failure_modes,', '"failure_modes": failure_modes or ["The proposed change is not load-bearing or its evidence cannot separate it from a simpler explanation."],')
exec(compile(_TEXT, str(_SOURCE), "exec"), globals(), globals())
