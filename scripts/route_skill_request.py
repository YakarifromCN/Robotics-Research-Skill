#!/usr/bin/env python3
"""Fail-closed top-level router for the six robotics Skills."""

from __future__ import annotations

import argparse
import json
import re
from typing import Any


SKILLS = (
    "develop-robotics-idea",
    "design-robotics-experiment",
    "develop-robotics-engineering",
    "write-robotics-paper",
    "review-robotic-feedback",
    "robotics-ar",
)


def _has(text: str, *tokens: str) -> bool:
    return any(token in text for token in tokens)


def route(request: str) -> dict[str, Any]:
    text = re.sub(r"\s+", " ", request.casefold()).strip()
    if not text:
        return {"decision": "ABSTAIN", "skill": None, "reason": "empty request"}

    autonomous = _has(text, "long-running", "overnight", "autonomous loop", "自动执行", "长时间", "无人值守", "持续运行")
    engineering_object = _has(text, "ros", "controller", "控制器", "solver", "优化器", "firmware", "固件", "subscriber", "node", "节点", "deployment", "部署", "training code", "训练代码", "timeout", "driver", "驱动", "gain", "增益", "调参", "tuning", "cmake", "实现", "修复", "开发")
    engineering_action = _has(text, "implement", "fix", "debug", "modify", "patch", "tune", "tuning", "add parameter", "按照已有 plan", "按照现有 plan", "实现", "修复", "修改", "开发", "调参", "加一个")
    experiment = _has(text, "experiment", "实验", "negative control", "负控制", "metric", "指标", "estimand", "统计分析", "trial design", "验证 claim", "验证主张")
    writing = _has(text, "write the paper", "manuscript", "latex", "paper draft", "写进论文", "写论文", "论文组织", "润色", "camera-ready")
    review = _has(text, "peer review", "reviewer", "审稿", "评审", "够不够支持", "evidence sufficient", "审查这个结果")
    idea = _has(text, "idea", "prior art", "已有工作", "科研贡献", "research contribution", "novelty", "研究问题", "研究方向")

    if autonomous:
        skill, reason = "robotics-ar", "explicit autonomous or long-running execution"
    elif engineering_object and engineering_action:
        skill, reason = "develop-robotics-engineering", "scoped code or robotics implementation request"
    elif review:
        skill, reason = "review-robotic-feedback", "independent evidence or manuscript review"
    elif writing:
        skill, reason = "write-robotics-paper", "evidence-constrained manuscript work"
    elif experiment:
        skill, reason = "design-robotics-experiment", "scientific experiment or claim-validation design"
    elif idea:
        skill, reason = "develop-robotics-idea", "research object, novelty, or prior-art question"
    else:
        return {"decision": "ABSTAIN", "skill": None, "reason": "no stable routing signal"}
    return {"decision": "ROUTE", "skill": skill, "reason": reason, "allowed_skills": list(SKILLS)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("request")
    args = parser.parse_args()
    print(json.dumps(route(args.request), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
