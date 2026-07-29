"""Direct CLI entrypoint for the ResearchStudio Idea Card validator."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
_SOURCE = Path(__file__).with_name("validate_researchstudio_idea_card.py.source")
_lines = _SOURCE.read_text(encoding="utf-8").splitlines()
_patched: list[str] = []
for _line in _lines:
    if _line.strip() == 'if len(card.get("selected_patterns", [])) > 3:':
        _patched.extend([
            '    selected_parent_ids = {item.get("pattern_id") for item in card.get("selected_patterns", []) if isinstance(item, dict)}',
            '    for sub_id in card.get("selected_subpatterns", []):',
            '        if sub_id in subs and subs[sub_id].get("parent_pattern_id") not in selected_parent_ids:',
            '            errors.append(f"subpattern parent mismatch: {sub_id}")',
            _line,
        ])
    else:
        _patched.append(_line)
exec(compile("\n".join(_patched) + "\n", str(_SOURCE), "exec"), globals(), globals())
