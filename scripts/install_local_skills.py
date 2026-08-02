#!/usr/bin/env python3
"""安装并列机器人科研 Skill。 / Install the sibling robotics research Skills."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from local_skill_install import main_install  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main_install())
