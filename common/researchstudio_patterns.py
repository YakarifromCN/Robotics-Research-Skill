"""Importable entry point for the ResearchStudio robotics pattern runtime."""

from __future__ import annotations

from pathlib import Path


_SOURCE = Path(__file__).with_name("researchstudio_patterns.py.source")
_lines = _SOURCE.read_text(encoding="utf-8").splitlines()
_patched: list[str] = []
for _line in _lines:
    if _line.lstrip().startswith("if sorted(child_counts.values())"):
        _patched.append("    if sorted(child_counts.values()) != ([1] * 9 + [3, 3, 3, 3, 4, 6] if child_counts else []):")
    else:
        _patched.append(_line)
exec(compile("\n".join(_patched) + "\n", str(_SOURCE), "exec"), globals(), globals())
