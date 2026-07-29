"""Direct CLI entrypoint for the pattern-library validator."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
_SOURCE = Path(__file__).with_name("validate_researchstudio_pattern_library.py.source")
exec(compile(_SOURCE.read_text(encoding="utf-8"), str(_SOURCE), "exec"), globals(), globals())
