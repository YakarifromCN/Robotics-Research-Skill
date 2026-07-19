#!/usr/bin/env python3
"""规范双语检查器的薄封装。 / Thin wrapper around the canonical bilingual checker."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).resolve().parents[1]/"scripts/check_bilingual_layout.py"),run_name="__main__")
