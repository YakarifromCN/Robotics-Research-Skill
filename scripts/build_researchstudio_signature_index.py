"""Entry-point shim for the ResearchStudio signature adapter.

The implementation snapshot is kept in the adjacent ``.source`` file so the
workspace's source-preservation convention is respected while this entry
point remains importable by tests and orchestration scripts.
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
_SOURCE = Path(__file__).with_name("build_researchstudio_signature_index.py.source")
exec(compile(_SOURCE.read_text(encoding="utf-8"), str(_SOURCE), "exec"), globals(), globals())
