#!/usr/bin/env python3
"""诊断本地 Skill 安装。 / Diagnose a local Skill installation."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from local_skill_install import main_doctor  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main_doctor())
