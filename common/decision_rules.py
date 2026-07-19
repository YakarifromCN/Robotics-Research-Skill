"""结构化实验判定规则及三态机械求值。

Structured experimental decision rules and deterministic three-state evaluation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .canonical_json import finite_number, load_json, sha256_file


GATE_TYPES = {
    "lower_bound_greater_than",
    "upper_bound_less_than",
    "estimate_greater_than",
    "estimate_less_than",
    "noninferiority",
    "estimate_within_bounds",
}


def validate_estimate(item: Any) -> list[str]:
    """校验结构化估计值。

    Validate a structured metric estimate.
    """

    errors: list[str] = []
    required = {"metric_id", "estimand", "estimate", "unit", "interval", "sample_size"}
    if not isinstance(item, dict) or set(item) != required:
        return [f"estimate must contain exactly {sorted(required)}"]
    if not isinstance(item.get("metric_id"), str) or not item["metric_id"]:
        errors.append("metric_id is required")
    if not isinstance(item.get("estimand"), str) or not item["estimand"]:
        errors.append("estimand is required")
    if not finite_number(item.get("estimate")):
        errors.append("estimate must be finite")
    if not isinstance(item.get("unit"), str) or not item["unit"]:
        errors.append("unit is required")
    interval = item.get("interval")
    if not isinstance(interval, dict) or set(interval) != {"type", "lower", "upper"}:
        errors.append("interval must contain type, lower, upper")
    else:
        if not isinstance(interval.get("type"), str) or not interval["type"]:
            errors.append("interval.type is required")
        if not finite_number(interval.get("lower")) or not finite_number(interval.get("upper")):
            errors.append("interval bounds must be finite")
        elif interval["lower"] > interval["upper"]:
            errors.append("interval lower exceeds upper")
    sample_size = item.get("sample_size")
    if not isinstance(sample_size, int) or isinstance(sample_size, bool) or sample_size < 0:
        errors.append("sample_size must be a nonnegative integer")
    return errors


def validate_rule(rule: Any) -> list[str]:
    """校验内置组合规则或外部分析规则。

    Validate a built-in composite rule or an external-analysis rule.
    """

    if not isinstance(rule, dict) or "rule_type" not in rule:
        return ["decision_rule must be an object with rule_type"]
    if rule["rule_type"] == "all":
        if set(rule) != {"rule_type", "gates"}:
            return ["all rule must contain exactly rule_type and gates"]
        gates = rule.get("gates")
        if not isinstance(gates, list) or not gates:
            return ["all rule needs at least one gate"]
        errors: list[str] = []
        for index, gate in enumerate(gates):
            if not isinstance(gate, dict) or gate.get("type") not in GATE_TYPES or not isinstance(gate.get("metric_id"), str):
                errors.append(f"gate {index} has invalid type or metric_id")
                continue
            gate_type = gate["type"]
            expected = {"type", "metric_id", "threshold"}
            if gate_type == "noninferiority":
                expected = {"type", "metric_id", "margin"}
            elif gate_type == "estimate_within_bounds":
                expected = {"type", "metric_id", "lower", "upper"}
            if set(gate) != expected:
                errors.append(f"gate {index} has wrong fields")
                continue
            for field in expected - {"type", "metric_id"}:
                if not finite_number(gate.get(field)):
                    errors.append(f"gate {index}.{field} must be finite")
            if gate_type == "estimate_within_bounds" and finite_number(gate.get("lower")) and finite_number(gate.get("upper")) and gate["lower"] > gate["upper"]:
                errors.append(f"gate {index} lower exceeds upper")
        return errors
    if rule["rule_type"] == "external_analysis":
        required = {"rule_type", "script_path", "script_sha256", "output_artifact", "output_sha256"}
        if set(rule) != required:
            return [f"external_analysis must contain exactly {sorted(required)}"]
        if any(not isinstance(rule.get(field), str) or not rule[field] for field in required - {"rule_type"}):
            return ["external_analysis paths and hashes must be nonempty strings"]
        for field in ("script_path", "output_artifact"):
            candidate = Path(rule[field])
            if candidate.is_absolute() or ".." in candidate.parts:
                return [f"{field} must be a safe relative path"]
        return []
    return ["unsupported rule_type"]


def _gate_state(gate: dict[str, Any], estimate: dict[str, Any] | None) -> str:
    if estimate is None or validate_estimate(estimate):
        return "inconclusive"
    value = estimate["estimate"]
    lower = estimate["interval"]["lower"]
    upper = estimate["interval"]["upper"]
    kind = gate["type"]
    if kind == "lower_bound_greater_than":
        if lower > gate["threshold"]:
            return "pass"
        if upper <= gate["threshold"]:
            return "fail"
        return "inconclusive"
    if kind == "upper_bound_less_than":
        if upper < gate["threshold"]:
            return "pass"
        if lower >= gate["threshold"]:
            return "fail"
        return "inconclusive"
    if kind == "estimate_greater_than":
        return "pass" if value > gate["threshold"] else "fail"
    if kind == "estimate_less_than":
        return "pass" if value < gate["threshold"] else "fail"
    if kind == "noninferiority":
        if lower > gate["margin"]:
            return "pass"
        if upper <= gate["margin"]:
            return "fail"
        return "inconclusive"
    if kind == "estimate_within_bounds":
        return "pass" if gate["lower"] <= value <= gate["upper"] else "fail"
    return "inconclusive"


def evaluate_rule(rule: dict[str, Any], estimates: list[dict[str, Any]], base_dir: str | Path) -> tuple[str, list[dict[str, Any]]]:
    """机械求值并返回三态判定与门级轨迹。

    Deterministically evaluate a rule and return a three-state verdict plus gate trace.
    """

    errors = validate_rule(rule)
    if errors:
        return "INCONCLUSIVE", [{"state": "inconclusive", "reason": error} for error in errors]
    if rule["rule_type"] == "external_analysis":
        root = Path(base_dir)
        script = (root / rule["script_path"]).resolve()
        output = (root / rule["output_artifact"]).resolve()
        trace: list[dict[str, Any]] = []
        if not script.is_file() or sha256_file(script) != rule["script_sha256"]:
            trace.append({"state": "inconclusive", "reason": "external script missing or hash mismatch"})
        if not output.is_file() or sha256_file(output) != rule["output_sha256"]:
            trace.append({"state": "inconclusive", "reason": "external output missing or hash mismatch"})
        if trace:
            return "INCONCLUSIVE", trace
        payload = load_json(output)
        verdict = payload.get("verdict") if isinstance(payload, dict) else None
        if verdict not in {"SUPPORTED", "NOT_SUPPORTED", "INCONCLUSIVE"}:
            return "INCONCLUSIVE", [{"state": "inconclusive", "reason": "external verdict is invalid"}]
        return verdict, [{"state": "external", "output_artifact": rule["output_artifact"]}]
    by_metric = {item.get("metric_id"): item for item in estimates if isinstance(item, dict)}
    trace = []
    states = []
    for gate in rule["gates"]:
        state = _gate_state(gate, by_metric.get(gate["metric_id"]))
        states.append(state)
        trace.append({"metric_id": gate["metric_id"], "type": gate["type"], "state": state})
    if "fail" in states:
        return "NOT_SUPPORTED", trace
    if states and all(state == "pass" for state in states):
        return "SUPPORTED", trace
    return "INCONCLUSIVE", trace
