"""V2 科学合同的公共常量、发现项与基础校验。

Shared constants, findings, and base validation for V2 scientific contracts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .canonical_json import finite_number, sha256_value


CLAIM_DIMENSIONS = (
    "embodied_system",
    "learning",
    "mechanism",
    "human",
    "soft_material",
    "practice",
    "cross_context",
)
OBLIGATIONS = (
    "multi_condition",
    "mechanism_boundary",
    "generalization",
    "deployment_practice",
    "independent_convergence",
)
DOMAIN_PACKS = {
    "learning",
    "soft-body",
    "morphology",
    "human-interaction",
    "clinical",
    "industrial",
    "field",
    "multi-robot",
}
VERDICTS = {"SUPPORTED", "NOT_SUPPORTED", "INCONCLUSIVE"}
IDEA_MODES = {"EXPLORE_NEW", "AUDIT_EXISTING_IDEA", "ADOPT_LOCKED_IDEA", "MIGRATE_LEGACY_PROJECT"}
EXPERIMENT_MODES = {
    "PROSPECTIVE_DESIGN",
    "PILOT_AMENDMENT",
    "RETROSPECTIVE_AUDIT",
    "MICRO_ADJUSTMENT",
    "PACKAGE_EXISTING_RESULTS",
}
WRITING_MODES = {"FULL_DRAFT", "WRITING_ONLY", "REVISION_ONLY", "REBUTTAL", "CLAIM_AUDIT"}
DESIGN_TIMINGS = {"prospective", "amended_before_unblinding", "retrospective"}


def meaningful(value: Any) -> bool:
    """判断值是否含非占位信息。

    Return whether a value contains non-placeholder information.
    """

    if not isinstance(value, str):
        return False
    text = value.strip()
    return bool(text) and not (text.startswith("<") and text.endswith(">"))


@dataclass
class Findings:
    """收集机器可读发现项。

    Collect machine-readable findings.
    """

    items: list[dict[str, Any]] = field(default_factory=list)

    def add(self, level: str, code: str, path: str, message: str) -> None:
        self.items.append({"level": level, "code": code, "path": path, "message": message})

    def fail(self, code: str, path: str, message: str) -> None:
        self.add("fail", code, path, message)

    def warn(self, code: str, path: str, message: str) -> None:
        self.add("warn", code, path, message)

    def info(self, code: str, path: str, message: str) -> None:
        self.add("info", code, path, message)

    def count(self, level: str) -> int:
        return sum(item["level"] == level for item in self.items)

    @property
    def consistent(self) -> bool:
        return self.count("fail") == 0

    def report(self, schema: str, terminal_state: str | None, handoff_ready: bool) -> dict[str, Any]:
        return {
            "schema": schema,
            "schema_valid": self.consistent,
            "contract_consistent": self.consistent,
            "handoff_ready": handoff_ready and self.consistent,
            "terminal_state": terminal_state,
            "counts": {level: self.count(level) for level in ("fail", "warn", "info")},
            "findings": self.items,
        }


def validate_change_envelope(value: Any, findings: Findings, path: str = "change_envelope") -> None:
    """校验既有项目的允许与禁止修改边界。

    Validate allowed and forbidden changes for an existing project.
    """

    required = {"allowed", "forbidden", "reason"}
    if not isinstance(value, dict) or set(value) != required:
        findings.fail("CHANGE_ENVELOPE", path, f"must contain exactly {sorted(required)}")
        return
    for field_name in ("allowed", "forbidden"):
        entries = value.get(field_name)
        if not isinstance(entries, list) or len(entries) != len(set(entries)) or any(not meaningful(item) for item in entries):
            findings.fail("CHANGE_ENVELOPE", f"{path}.{field_name}", "must be a unique list of nonempty strings")
    if not meaningful(value.get("reason")):
        findings.fail("CHANGE_ENVELOPE", f"{path}.reason", "must explain the project constraint")
    if isinstance(value.get("allowed"), list) and isinstance(value.get("forbidden"), list):
        overlap = set(value["allowed"]) & set(value["forbidden"])
        if overlap:
            findings.fail("CHANGE_ENVELOPE_CONFLICT", path, f"items cannot be both allowed and forbidden: {sorted(overlap)}")


def validate_claim_dimensions(value: Any, findings: Findings, path: str) -> None:
    """校验七维 Claim Shape；它不是派生向量集合。

    Validate the seven-dimensional Claim Shape; it is not a set of derived vectors.
    """

    if not isinstance(value, dict) or tuple(value) != CLAIM_DIMENSIONS:
        findings.fail("CLAIM_DIMENSIONS", path, f"must preserve exactly {list(CLAIM_DIMENSIONS)}")
        return
    if any(type(flag) is not bool for flag in value.values()):
        findings.fail("CLAIM_DIMENSIONS", path, "every dimension must be Boolean")


def validate_obligations(value: Any, findings: Findings, path: str = "evidence_obligations") -> None:
    """校验显式证据义务，不从轴分数触发。

    Validate explicit evidence obligations without routing from axis scores.
    """

    if not isinstance(value, dict) or tuple(value) != OBLIGATIONS:
        findings.fail("EVIDENCE_OBLIGATIONS", path, f"must preserve exactly {list(OBLIGATIONS)}")
        return
    for name in OBLIGATIONS:
        item = value.get(name)
        item_path = f"{path}.{name}"
        required = {"required", "reason", "decisive_test_ids", "claim_boundary"}
        if not isinstance(item, dict) or set(item) != required:
            findings.fail("EVIDENCE_OBLIGATION", item_path, f"must contain exactly {sorted(required)}")
            continue
        if type(item.get("required")) is not bool:
            findings.fail("EVIDENCE_OBLIGATION", f"{item_path}.required", "must be Boolean")
        if not meaningful(item.get("reason")):
            findings.fail("EVIDENCE_OBLIGATION", f"{item_path}.reason", "must explain inclusion or exclusion")
        tests = item.get("decisive_test_ids")
        if not isinstance(tests, list) or len(tests) != len(set(tests)) or any(not meaningful(test) for test in tests):
            findings.fail("EVIDENCE_OBLIGATION", f"{item_path}.decisive_test_ids", "must be a unique string list")
        if item.get("required") is True and not tests:
            findings.fail("EVIDENCE_OBLIGATION", f"{item_path}.decisive_test_ids", "a required obligation needs a decisive test ID")
        if item.get("required") is False and not meaningful(item.get("claim_boundary")):
            findings.fail("EVIDENCE_OBLIGATION", f"{item_path}.claim_boundary", "an omitted obligation needs a claim boundary")


def validate_domain_packs(value: Any, findings: Findings, path: str = "domain_packs") -> None:
    """校验按需加载的领域包。

    Validate conditionally loaded domain packs.
    """

    if not isinstance(value, list) or len(value) != len(set(value)) or not set(value) <= DOMAIN_PACKS:
        findings.fail("DOMAIN_PACKS", path, f"must be a unique subset of {sorted(DOMAIN_PACKS)}")


def claim_digest_payload(card: dict[str, Any]) -> dict[str, Any]:
    """提取 Claim Lock 的规范摘要负载。

    Extract the canonical digest payload for the Claim Lock.
    """

    return {
        "claim_contract": card.get("claim_contract"),
        "mechanism_contract": card.get("mechanism_contract"),
        "falsification_contract": card.get("falsification_contract"),
        "evidence_obligations": card.get("evidence_obligations"),
        "deferred_evidence": card.get("deferred_evidence"),
        "domain_packs": card.get("domain_packs"),
    }


def compute_claim_digest(card: dict[str, Any]) -> str:
    return sha256_value(claim_digest_payload(card))


def design_digest_payload(contract: dict[str, Any]) -> dict[str, Any]:
    """提取 Design Lock 的规范摘要负载。

    Extract the canonical digest payload for the Design Lock.
    """

    return {
        "design_timing": contract.get("design_timing"),
        "unit_hierarchy": contract.get("unit_hierarchy"),
        "conditions": contract.get("conditions"),
        "metrics": contract.get("metrics"),
        "contrasts": contract.get("contrasts"),
        "analyses": contract.get("analyses"),
        "exclusions": contract.get("exclusions"),
        "abort_policy": contract.get("abort_policy"),
    }


def compute_design_digest(contract: dict[str, Any]) -> str:
    return sha256_value(design_digest_payload(contract))


def validate_finite_tree(value: Any, findings: Findings, path: str = "$") -> None:
    """递归拒绝内存对象中的非有限浮点数。

    Recursively reject non-finite floats in an in-memory object.
    """

    if isinstance(value, float) and not finite_number(value):
        findings.fail("NONFINITE_NUMBER", path, "numeric values must be finite")
    elif isinstance(value, dict):
        for key, child in value.items():
            validate_finite_tree(child, findings, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_finite_tree(child, findings, f"{path}[{index}]")
