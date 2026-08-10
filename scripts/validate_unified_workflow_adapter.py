#!/usr/bin/env python3
"""Validate unified external-workflow learning and four-Skill injection."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = (
    "develop-robotics-idea",
    "design-robotics-experiment",
    "write-robotics-paper",
    "review-robotic-feedback",
)
TARGETS = (
    "通用 AI conference",
    "通用工程技术 journal",
    "Science Robotics",
    "IJRR",
    "T-RO",
    "HRI",
    "CoRL",
    "RSS",
    "IROS",
    "ICRA",
)


def main() -> int:
    adapter_path = ROOT / "references/unified-venue-workflow-adapter.v1.md"
    adapter = adapter_path.read_text(encoding="utf-8")
    assert "不创建新的 `skills/<venue>/`" in adapter
    assert "研究流形轴解析" in adapter
    assert "贡献中心 / 证据形状 / 失败边界" in adapter
    assert "acceptance probability" not in adapter.casefold() or "NOT_ESTIMABLE" in adapter
    for target in TARGETS:
        assert f"| {target} |" in adapter, target
    runtime_section = adapter.split("## 模拟归纳后注入的运行时问题", 1)[1].split(
        "## 统一学习到四个 skill 的核心能力", 1
    )[0]
    numbered_questions = [
        line
        for line in runtime_section.splitlines()
        if line[:2] in {f"{n}." for n in range(1, 9)}
    ]
    assert len(numbered_questions) == 8

    for skill in SKILLS:
        text = (ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
        lowered = text.casefold()
        assert "at most two references" in lowered
        assert "do not preload sibling skills" in lowered
        assert "统一 workflow 能力" in text

    receipt = json.loads(
        (ROOT / "references/external-workflow-source-receipt.v1.json").read_text(encoding="utf-8")
    )
    assert "ten new internal venue workflows" in receipt["integration_boundary"]["do_not_create"]
    assert len(receipt["target_resolution"]) == 10
    print("UNIFIED_WORKFLOW_ADAPTER: PASS targets=10 skills=4 runtime_questions=8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
