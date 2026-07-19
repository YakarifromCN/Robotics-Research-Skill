"""非序数机器人证据画像及逐分量充分性比较。

Nonordinal robotics evidence profiles and component-wise sufficiency checks.
"""

from __future__ import annotations

from typing import Any


REGIMES = {
    "derivation",
    "simulation",
    "hardware_in_loop",
    "isolated_bench",
    "real_robot",
    "human_study",
    "field_operation",
}
COVERAGE = {
    "in_distribution",
    "held_out_object",
    "held_out_task",
    "held_out_environment",
    "cross_platform",
    "stress_condition",
    "failure_boundary",
}
DURATIONS = {"single_run", "single_session", "multi_session", "extended_operation"}
INDEPENDENCE = {"same_run", "same_lab", "independent_team", "independent_site", "multi_site"}
UNITS = {
    "derivation",
    "seed",
    "object",
    "task",
    "trajectory",
    "specimen",
    "robot",
    "participant",
    "demonstration",
    "session",
    "site",
}


def validate_profile(profile: Any) -> list[str]:
    """返回证据画像的结构错误。

    Return structural errors for an evidence profile.
    """

    errors: list[str] = []
    required = {
        "regime",
        "coverage",
        "duration",
        "independence",
        "experimental_unit",
        "unit_count",
        "sites",
    }
    if not isinstance(profile, dict) or set(profile) != required:
        return [f"profile must contain exactly {sorted(required)}"]
    if profile.get("regime") not in REGIMES:
        errors.append("regime is not canonical")
    coverage = profile.get("coverage")
    if not isinstance(coverage, list) or len(coverage) != len(set(coverage)) or not set(coverage) <= COVERAGE:
        errors.append("coverage must be a unique canonical list")
    if profile.get("duration") not in DURATIONS:
        errors.append("duration is not canonical")
    if profile.get("independence") not in INDEPENDENCE:
        errors.append("independence is not canonical")
    if profile.get("experimental_unit") not in UNITS:
        errors.append("experimental_unit is not canonical")
    for field in ("unit_count", "sites"):
        value = profile.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            errors.append(f"{field} must be a nonnegative integer")
    return errors


def validate_requirement(requirement: Any) -> list[str]:
    """返回非序数证据要求的结构错误。

    Return structural errors for a nonordinal evidence requirement.
    """

    errors: list[str] = []
    required = {
        "requirement_id",
        "allowed_regimes",
        "required_coverage",
        "allowed_durations",
        "allowed_independence",
        "experimental_unit",
        "min_units",
        "min_sites",
    }
    if not isinstance(requirement, dict) or set(requirement) != required:
        return [f"requirement must contain exactly {sorted(required)}"]
    for field, allowed in (
        ("allowed_regimes", REGIMES),
        ("required_coverage", COVERAGE),
        ("allowed_durations", DURATIONS),
        ("allowed_independence", INDEPENDENCE),
    ):
        values = requirement.get(field)
        if not isinstance(values, list) or not values or len(values) != len(set(values)) or not set(values) <= allowed:
            errors.append(f"{field} must be a nonempty unique canonical list")
    if requirement.get("experimental_unit") not in UNITS:
        errors.append("experimental_unit is not canonical")
    for field in ("min_units", "min_sites"):
        value = requirement.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            errors.append(f"{field} must be a nonnegative integer")
    return errors


def satisfies(requirement: dict[str, Any], profile: dict[str, Any]) -> tuple[bool, list[str]]:
    """逐分量比较证据，不建立跨属性总顺序。

    Compare evidence component by component without a cross-attribute total order.
    """

    reasons: list[str] = []
    if profile.get("regime") not in requirement.get("allowed_regimes", []):
        reasons.append("regime")
    if not set(requirement.get("required_coverage", [])) <= set(profile.get("coverage", [])):
        reasons.append("coverage")
    if profile.get("duration") not in requirement.get("allowed_durations", []):
        reasons.append("duration")
    if profile.get("independence") not in requirement.get("allowed_independence", []):
        reasons.append("independence")
    if profile.get("experimental_unit") != requirement.get("experimental_unit"):
        reasons.append("experimental_unit")
    if profile.get("unit_count", -1) < requirement.get("min_units", 0):
        reasons.append("unit_count")
    if profile.get("sites", -1) < requirement.get("min_sites", 0):
        reasons.append("sites")
    return not reasons, reasons

