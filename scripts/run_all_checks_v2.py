#!/usr/bin/env python3
"""Compatibility wrapper for the extended repository checks."""

from __future__ import annotations

from run_all_checks import main


if __name__ == "__main__":
    raise SystemExit(main(["--profile", "extended"]))
