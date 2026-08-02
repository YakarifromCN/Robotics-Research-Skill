#!/usr/bin/env python3
"""运行 corpus-first 路由，或在独立安装中给出透明降级上下文。

Run corpus-first routing, or emit an explicit degraded context for a standalone
installation.  The fallback never claims that the public corpus was loaded.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
AXIS_TERMS = {
    "E": ("robot", "embodied", "morphology", "contact", "hardware", "具身", "形态", "接触"),
    "P": ("perception", "sensing", "state estimation", "vision", "tactile", "感知", "状态估计"),
    "C": ("control", "dynamics", "stability", "optimization", "feedback", "控制", "动力学", "稳定"),
    "L": ("learning", "policy", "training", "imitation", "reinforcement", "学习", "策略", "训练"),
    "D": ("planning", "decision", "coordination", "multi-agent", "规划", "决策", "协同"),
    "H": ("human", "hri", "teleoperation", "haptic", "participant", "人机", "触觉", "参与者"),
    "A": ("autonomy", "deployment", "field", "navigation", "现场", "部署", "自主"),
    "S": ("system", "real-time", "software", "middleware", "ros", "实时", "系统", "软件"),
}


def find_full_repo() -> Path | None:
    """寻找含完整 corpus/router 的仓库根目录。 / Find a full repository root."""
    for candidate in (SKILL_ROOT, *SKILL_ROOT.parents):
        if (
            (candidate / "corpus" / "robotics-research-runtime.v1.json").is_file()
            and (candidate / "scripts" / "route_robotics_research.py").is_file()
        ):
            return candidate
    return None


def fallback_context(profile: dict[str, Any], venue: str | None, stage: str, per_axis: int) -> dict[str, Any]:
    tags = " ".join(str(item) for item in profile.get("topic_tags", [])).casefold()
    axes = profile.get("submanifold_axes") if isinstance(profile.get("submanifold_axes"), dict) else {}
    active = [axis for axis, value in axes.items() if axis in AXIS_TERMS and isinstance(value, (int, float)) and value >= 2]
    for axis, terms in AXIS_TERMS.items():
        if axis not in active and any(term.casefold() in tags for term in terms):
            active.append(axis)
    active = sorted(set(active), key="EPCLDHAS".index)
    return {
        "schema_version": "robotics-review-routing-fallback.v1",
        "routing_status": "LOCAL_FALLBACK_NO_CORPUS",
        "runtime_artifact_loaded": False,
        "stage": stage,
        "target_venue": venue,
        "active_axes": active,
        "project_profile": profile,
        "per_axis": per_axis,
        "reference_files": [
            "references/active-corpus-first-reference.md",
            "references/unified-venue-workflow-adapter.v1.md",
            "references/robotics-submanifold-routing.md",
        ],
        "limitations": [
            "The compact robotics runtime and official venue catalog were not available in this standalone installation.",
            "This context may select review questions but cannot support runtime-derived collision or venue conclusions.",
            "Acceptance probability remains NOT_ESTIMABLE.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Route a robotics review through the full corpus or an explicit standalone fallback.")
    parser.add_argument("profile")
    parser.add_argument("--stage", choices=("idea", "experiment", "writing", "review"), default="review")
    parser.add_argument("--venue")
    parser.add_argument("--per-axis", type=int, default=4)
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.per_axis < 1:
        parser.error("--per-axis must be positive")
    profile = json.loads(Path(args.profile).read_text(encoding="utf-8"))
    if not isinstance(profile, dict):
        parser.error("profile must be a JSON object")
    repo = find_full_repo()
    if repo is not None and (repo / "scripts" / "route_robotics_research.py").resolve() != Path(__file__).resolve():
        command = [sys.executable, str(repo / "scripts" / "route_robotics_research.py"), args.profile, "--stage", args.stage, "--per-axis", str(args.per_axis)]
        if args.venue:
            command.extend(["--venue", args.venue])
        if args.output:
            command.extend(["--output", args.output])
        return subprocess.run(command, check=False).returncode
    payload = fallback_context(profile, args.venue, args.stage, args.per_axis)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        print(output.resolve())
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
