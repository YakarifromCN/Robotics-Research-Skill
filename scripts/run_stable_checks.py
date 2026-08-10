#!/usr/bin/env python3
"""Single CI entry point for the Stable-Use release gate."""

from __future__ import annotations

from run_all_checks import main


if __name__ == "__main__":
    raise SystemExit(main(["--profile", "corpus-first"]))
