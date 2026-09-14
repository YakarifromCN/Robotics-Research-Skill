#!/usr/bin/env python3
"""从安装位置解析共享路由。 / Resolve the shared router from the installation."""
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
if __name__ == "__main__":
    runpy.run_path(str(ROOT / "scripts" / "route_robotics_research.py"), run_name="__main__")
