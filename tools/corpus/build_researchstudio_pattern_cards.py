"""Stable CLI/API facade for the robotics ResearchStudio pattern library."""

from __future__ import annotations

try:  # package import / 包导入
    from ._pattern_cards import AXIS_PROFILES, DEFAULT_OUTPUT, PARENTS, SUBPATTERNS, build_library, main
except ImportError:  # direct CLI execution / 直接 CLI 执行
    from _pattern_cards import AXIS_PROFILES, DEFAULT_OUTPUT, PARENTS, SUBPATTERNS, build_library, main

__all__ = ["AXIS_PROFILES", "DEFAULT_OUTPUT", "PARENTS", "SUBPATTERNS", "build_library", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
