#!/usr/bin/env python3
"""交叉校验最小 Plan、Task、Report 与 Handoff 工程闭环。

Cross-validate the minimal Plan, Task, Report, and Handoff engineering loop.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any


STATUSES = {"DONE", "PARTIAL", "BLOCKED", "NO_CODE_CHANGE"}
EXPERT_KEYS = {
    "affected_call_path", "critical_interfaces", "invariants",
    "smallest_change_locus", "mandatory_safeguards", "minimal_tests", "blockers",
}


def load_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"missing YAML frontmatter: {path}")
    try:
        end = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration as exc:
        raise ValueError(f"unterminated YAML frontmatter: {path}") from exc
    data: dict[str, Any] = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"frontmatter must use top-level key: value entries: {path}")
        key, raw = line.split(":", 1)
        key = key.strip()
        raw = raw.strip()
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            value = raw
        data[key] = value
    return data, "\n".join(lines[end + 1 :])


def _strings(value: Any, *, allow_empty: bool = True) -> bool:
    return isinstance(value, list) and (allow_empty or bool(value)) and all(isinstance(item, str) and item.strip() for item in value)


def _safe_relative(path: str) -> bool:
    value = PurePosixPath(path)
    return not value.is_absolute() and ".." not in value.parts and bool(path.strip())


def _inside_allowed(path: str, allowed: list[str]) -> bool:
    return any(path == root.rstrip("/") or path.startswith(root.rstrip("/") + "/") for root in allowed)


def _test_commands(rows: Any, *, require_results: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    if not isinstance(rows, list) or len(rows) > 3:
        return [], ["tests must be a list with at most 3 entries"]
    commands: list[str] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not isinstance(row.get("command"), str) or not row["command"].strip():
            errors.append(f"tests[{index}] requires a nonempty command")
            continue
        commands.append(row["command"])
        if require_results:
            if row.get("result") not in {"PASS", "FAIL"}:
                errors.append(f"tests[{index}].result must be PASS or FAIL; frozen tests cannot be NOT_RUN")
            if row.get("executed") is not True or type(row.get("exit_code")) is not int:
                errors.append(f"tests[{index}] requires executed=true and an integer exit_code")
            expected_result = "PASS" if row.get("exit_code") == 0 else "FAIL"
            if row.get("result") != expected_result:
                errors.append(f"tests[{index}].result does not match exit_code")
            payload = {"command": row.get("command"), "result": row.get("result"), "exit_code": row.get("exit_code")}
            expected_receipt = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            if row.get("receipt_sha256") != expected_receipt:
                errors.append(f"tests[{index}].receipt_sha256 does not bind command/result/exit_code")
    if len(commands) != len(set(commands)):
        errors.append("test commands must be unique")
    return commands, errors


def task_contract_sha256(task: dict[str, Any]) -> str:
    payload = {key: task.get(key) for key in (
        "task_id", "language", "axes", "development_modes", "risk_tier", "original_request",
        "allowed_paths", "forbidden_scope", "steps", "tests", "stop_conditions",
        "safeguards",
        "device_actions", "real_device_authorized", "expert_required", "expert_brief",
    )}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _meaningful_body(body: str) -> bool:
    lines = [line.strip() for line in body.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    return any(not (line.startswith("<") and line.endswith(">")) for line in lines)


def validate(plan: dict[str, Any], task: dict[str, Any], report: dict[str, Any], handoff: dict[str, Any], bodies: dict[str, str] | None = None) -> list[str]:
    errors: list[str] = []
    artifacts = (("plan", plan, "PLAN"), ("task", task, "TASK"), ("report", report, "REPORT"), ("handoff", handoff, "HANDOFF"))
    task_ids = {row.get("task_id") for _, row, _ in artifacts}
    if len(task_ids) != 1 or not next(iter(task_ids), None):
        errors.append("all artifacts must share one nonempty task_id")
    languages = {row.get("language") for _, row, _ in artifacts}
    if len(languages) != 1 or not next(iter(languages), None):
        errors.append("all artifacts must use one declared user language")
    if len({json.dumps(row.get("axes"), sort_keys=True) for _, row, _ in artifacts}) != 1:
        errors.append("all artifacts must preserve the same ordered axes")
    if len({row.get("risk_tier") for _, row, _ in artifacts}) != 1:
        errors.append("all artifacts must preserve the same risk tier")
    for name, row, expected in artifacts:
        if row.get("artifact") != expected:
            errors.append(f"{name}.artifact must be {expected}")
        axes = row.get("axes")
        if not _strings(axes, allow_empty=False) or not set(axes) <= set("EPCLDHAS"):
            errors.append(f"{name}.axes must be a nonempty E/P/C/L/D/H/A/S list")
        if row.get("risk_tier") not in {"T0", "T1", "T2", "T3"}:
            errors.append(f"{name}.risk_tier is invalid")
        if bodies is not None and not _meaningful_body(bodies.get(name, "")):
            errors.append(f"{name} Markdown body must contain non-placeholder recovery or decision context")
    if not isinstance(task.get("original_request"), str) or not task["original_request"].strip():
        errors.append("task.original_request is required")
    if not _strings(task.get("forbidden_scope"), allow_empty=False):
        errors.append("task.forbidden_scope must be a nonempty string list")
    if not _strings(task.get("stop_conditions"), allow_empty=False):
        errors.append("task.stop_conditions must be a nonempty string list")
    if not _strings(task.get("safeguards"), allow_empty=False):
        errors.append("task.safeguards must be a nonempty string list")
    expected_expert = task.get("risk_tier") == "T3" or (task.get("risk_tier") == "T2" and isinstance(task.get("axes"), list) and len(task["axes"]) >= 2)
    if task.get("expert_required") is not expected_expert:
        errors.append("task.expert_required must follow T0/T1=no expert, multi-axis T2/T3=one expert")
    brief = task.get("expert_brief")
    if expected_expert:
        if not isinstance(brief, dict) or set(brief) != EXPERT_KEYS:
            errors.append(f"task.expert_brief must contain exactly {sorted(EXPERT_KEYS)}")
        else:
            for key in EXPERT_KEYS - {"blockers"}:
                if not _strings(brief.get(key), allow_empty=False):
                    errors.append(f"task.expert_brief.{key} must be a nonempty string list")
            if not _strings(brief.get("blockers")):
                errors.append("task.expert_brief.blockers must be a string list")
    elif brief is not None:
        errors.append("T0/T1 or non-complex tasks must not create an expert brief")
    steps = task.get("steps")
    if not _strings(steps, allow_empty=False) or not 3 <= len(steps) <= 7:
        errors.append("task.steps must contain 3-7 nonempty steps")
    allowed = task.get("allowed_paths")
    if not _strings(allowed, allow_empty=False) or any(not _safe_relative(item) for item in allowed):
        errors.append("task.allowed_paths must contain safe relative paths")
        allowed = []
    task_commands, test_errors = _test_commands(task.get("tests"), require_results=False)
    errors.extend(f"task.{item}" for item in test_errors)
    if expected_expert and isinstance(brief, dict):
        if brief.get("minimal_tests") != task_commands:
            errors.append("Task frozen tests must exactly inherit expert_brief.minimal_tests")
        if not set(brief.get("mandatory_safeguards", [])) <= set(task.get("safeguards", [])):
            errors.append("Task safeguards must inherit every expert mandatory safeguard")
        if not set(brief.get("blockers", [])) <= set(task.get("stop_conditions", [])):
            errors.append("Task stop conditions must inherit every expert blocker")
    report_commands, test_errors = _test_commands(report.get("tests"), require_results=True)
    errors.extend(f"report.{item}" for item in test_errors)
    if task_commands != report_commands:
        errors.append("Report tests must reproduce Task frozen commands in the same order")
    if handoff.get("tests") != report.get("tests"):
        errors.append("Handoff tests must equal the executed Report receipts")
    binding = task_contract_sha256(task)
    if report.get("task_contract_sha256") != binding or handoff.get("task_contract_sha256") != binding:
        errors.append("Report and Handoff must bind the exact frozen Task contract")
    status = report.get("status")
    if status not in STATUSES or handoff.get("status") != status:
        errors.append("Report and Handoff must share a valid terminal status")
    changed = report.get("changed_files")
    if not _strings(changed):
        errors.append("report.changed_files must be a string list")
        changed = []
    if any(not _safe_relative(item) or not _inside_allowed(item, allowed) for item in changed):
        errors.append("every changed file must be a safe path inside Task allowed_paths")
    if handoff.get("changed_files") != changed:
        errors.append("Handoff changed_files must equal Report changed_files")
    if status == "DONE" and changed and any(row.get("result") != "PASS" for row in report.get("tests", [])):
        errors.append("DONE cannot contain failed or unrun frozen tests")
    if status == "DONE" and task_commands and not changed:
        errors.append("DONE with frozen implementation tests requires changed files; otherwise use NO_CODE_CHANGE")
    resume = handoff.get("resume_command")
    if status in {"PARTIAL", "BLOCKED"} and (not isinstance(resume, str) or not resume.strip()):
        errors.append("PARTIAL/BLOCKED requires a nonempty resume_command")
    if status in {"DONE", "NO_CODE_CHANGE"} and resume not in {None, ""}:
        errors.append("DONE/NO_CODE_CHANGE resume_command must be null")
    device_actions = task.get("device_actions", [])
    if not isinstance(device_actions, list) or any(item not in {"real_robot_run", "flash", "erase"} for item in device_actions):
        errors.append("task.device_actions must be a list containing only real_robot_run, flash, or erase")
    elif device_actions and task.get("real_device_authorized") is not True:
        errors.append("real-device actions require explicit real_device_authorized=true")
    return errors


def validate_paths(plan_path: Path, task_path: Path, report_path: Path, handoff_path: Path) -> dict[str, Any]:
    try:
        plan, plan_body = load_frontmatter(plan_path)
        task, task_body = load_frontmatter(task_path)
        report, report_body = load_frontmatter(report_path)
        handoff, handoff_body = load_frontmatter(handoff_path)
        errors = validate(plan, task, report, handoff, {"plan": plan_body, "task": task_body, "report": report_body, "handoff": handoff_body})
    except (OSError, ValueError) as exc:
        errors = [str(exc)]
    return {"valid": not errors, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("plan", type=Path)
    parser.add_argument("task", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("handoff", type=Path)
    args = parser.parse_args()
    result = validate_paths(args.plan, args.task, args.report, args.handoff)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
