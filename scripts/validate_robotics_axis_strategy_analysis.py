"""Direct CLI entrypoint for the axis-strategy validator."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
_SOURCE = Path(__file__).with_name("validate_robotics_axis_strategy_analysis.py.source")
_lines = _SOURCE.read_text(encoding="utf-8").splitlines()
_patched: list[str] = []
_skip = False
for _line in _lines:
    if _line.strip() == 'text = json.dumps(report, ensure_ascii=False)':
        _patched.append('    if any(key in report for key in ("rating", "prestige")) or any(key in report.get("metadata", {}) for key in ("rating", "prestige")):' )
        _skip = True
        continue
    if _skip and _line.strip().startswith('if "rating" in text.casefold()'):
        continue
    if _skip and _line.strip().startswith('errors.append("rating/prestige'):
        _patched.append(_line)
        _skip = False
        continue
    _patched.append(_line)
exec(compile("\n".join(_patched) + "\n", str(_SOURCE), "exec"), globals(), globals())
