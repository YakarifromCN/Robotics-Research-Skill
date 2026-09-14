"""定义不含领域必需字段的研究对象和预算。

Define research objects and budgets without domain-required fields.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import itertools
from typing import Any, Dict, Mapping, MutableMapping, Optional

from .canonical import ensure_finite


FORBIDDEN_CORE_FIELDS = frozenset(
    {
        "robot",
        "controller",
        "simulator",
        "policy",
        "reward",
        "success_rate",
        "force",
        "accuracy",
        "loss",
        "p_value",
        "venue",
        "paper",
        "baseline",
        "ablation",
    }
)

_COUNTERS = itertools.count(1)


def utc_now() -> str:
    """返回 UTC ISO 时间。 / Return a UTC ISO timestamp."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _new_id(prefix: str) -> str:
    """生成进程内可读 ID。 / Generate a readable process-local ID."""

    return f"{prefix}-{next(_COUNTERS):06d}"


def validate_core_object(value: Mapping[str, Any]) -> None:
    """验证 generic object 的顶层字段和有限数。

    Validate generic top-level fields and finite JSON values.
    """

    if not isinstance(value, Mapping):
        raise ValueError("core object must be an object")
    forbidden = FORBIDDEN_CORE_FIELDS.intersection(value.keys())
    if forbidden:
        raise ValueError(f"forbidden core fields: {sorted(forbidden)}")
    for required in ("schema_version", "object_type", "object_id", "domain_payload"):
        if required not in value:
            raise ValueError(f"missing generic field: {required}")
    if not isinstance(value["domain_payload"], Mapping):
        raise ValueError("domain_payload must be an object")
    ensure_finite(dict(value))


def make_object(object_type: str, *, statement: str = "", domain_payload: Optional[Mapping[str, Any]] = None, **fields: Any) -> Dict[str, Any]:
    """构造通用研究对象；领域值只进入 domain_payload。

    Construct a generic research object; domain values belong in domain_payload.
    """

    if not object_type or not isinstance(object_type, str):
        raise ValueError("object_type must be a non-empty string")
    if FORBIDDEN_CORE_FIELDS.intersection(fields.keys()):
        raise ValueError("domain-specific fields must be nested in domain_payload")
    result: Dict[str, Any] = {
        "schema_version": "robotics-ar-kernel-object.v1",
        "object_type": object_type,
        "object_id": _new_id(object_type.upper()),
        "created_at": utc_now(),
        "domain_payload": dict(domain_payload or {}),
    }
    if statement:
        result["statement"] = statement
    result.update(fields)
    validate_core_object(result)
    return result


def make_research_question(statement: str, *, domain_payload: Optional[Mapping[str, Any]] = None, **fields: Any) -> Dict[str, Any]:
    """创建研究问题。 / Create a research question."""

    return make_object("ResearchQuestion", statement=statement, domain_payload=domain_payload, **fields)


def make_charter(statement: str, *, domain_payload: Optional[Mapping[str, Any]] = None, **fields: Any) -> Dict[str, Any]:
    """创建研究章程。 / Create a charter."""

    return make_object("Charter", statement=statement, domain_payload=domain_payload, **fields)


def make_hypothesis(statement: str, *, domain_payload: Optional[Mapping[str, Any]] = None, **fields: Any) -> Dict[str, Any]:
    """创建假设。 / Create a hypothesis."""

    return make_object("Hypothesis", statement=statement, domain_payload=domain_payload, **fields)


def make_unknown(statement: str, *, domain_payload: Optional[Mapping[str, Any]] = None, **fields: Any) -> Dict[str, Any]:
    """创建未知量。 / Create an unknown."""

    return make_object("Unknown", statement=statement, domain_payload=domain_payload, **fields)


def make_candidate_action(statement: str, *, domain_payload: Optional[Mapping[str, Any]] = None, **fields: Any) -> Dict[str, Any]:
    """创建候选行动。 / Create a candidate action."""

    return make_object("CandidateAction", statement=statement, domain_payload=domain_payload, **fields)


def make_evidence(statement: str, *, domain_payload: Optional[Mapping[str, Any]] = None, status: str = "UNVERIFIED", **fields: Any) -> Dict[str, Any]:
    """创建 evidence 记录。 / Create an evidence record."""

    return make_object("Evidence", statement=statement, status=status, domain_payload=domain_payload, **fields)


def make_decision(statement: str, *, domain_payload: Optional[Mapping[str, Any]] = None, verdict: str = "NOT_APPLICABLE", **fields: Any) -> Dict[str, Any]:
    """创建通用 decision。 / Create a generic decision."""

    return make_object("Decision", statement=statement, verdict=verdict, domain_payload=domain_payload, **fields)


@dataclass
class Budget:
    """两个正交预算轴的确定性消费器。

    Deterministic consumer for the two orthogonal budget axes.
    """

    max_candidates: int = 4
    max_expert_rounds: int = 2
    max_debug_rounds: int = 2
    max_batches: int = 1
    max_trials: int = 30
    max_wall_time_minutes: int = 480
    max_gpu_hours: float = 0.0
    max_disk_gb: float = 20.0
    max_parallel_jobs: int = 1
    candidates_used: int = 0
    expert_rounds_used: int = 0
    debug_rounds_used: int = 0
    batches_used: int = 0
    trials_used: int = 0
    wall_time_used_minutes: float = 0.0
    gpu_hours_used: float = 0.0
    disk_gb_used: float = 0.0
    parallel_jobs_used: int = 0

    def consume(self, name: str, amount: int = 1) -> None:
        """消费预算，超限时拒绝。 / Consume budget and reject exhaustion."""

        if type(amount) not in (int, float):
            raise ValueError("amount must be numeric")
        ensure_finite(amount)
        if amount < 0:
            raise ValueError("amount must be non-negative")
        used_name = f"{name}_used"
        max_name = f"max_{name}"
        if not hasattr(self, used_name) or not hasattr(self, max_name):
            raise ValueError(f"unknown budget: {name}")
        used = getattr(self, used_name)
        maximum = getattr(self, max_name)
        if used + amount > maximum:
            raise RuntimeError(f"budget exhausted: {name}")
        setattr(self, used_name, used + amount)

    def to_dict(self) -> Dict[str, int]:
        """序列化预算。 / Serialize the budget."""

        return {
            "max_candidates": self.max_candidates,
            "max_expert_rounds": self.max_expert_rounds,
            "max_debug_rounds": self.max_debug_rounds,
            "max_batches": self.max_batches,
            "max_trials": self.max_trials,
            "max_wall_time_minutes": self.max_wall_time_minutes,
            "max_gpu_hours": self.max_gpu_hours,
            "max_disk_gb": self.max_disk_gb,
            "max_parallel_jobs": self.max_parallel_jobs,
            "candidates_used": self.candidates_used,
            "expert_rounds_used": self.expert_rounds_used,
            "debug_rounds_used": self.debug_rounds_used,
            "batches_used": self.batches_used,
            "trials_used": self.trials_used,
            "wall_time_used_minutes": self.wall_time_used_minutes,
            "gpu_hours_used": self.gpu_hours_used,
            "disk_gb_used": self.disk_gb_used,
            "parallel_jobs_used": self.parallel_jobs_used,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Budget":
        """从映射重建预算。 / Reconstruct a budget from a mapping."""

        # 保留资源小数预算，拒绝非有限和隐式截断。 / Preserve fractional resources; reject nonfinite values and truncation.
        fractional = {"max_gpu_hours", "max_disk_gb", "gpu_hours_used", "disk_gb_used", "wall_time_used_minutes"}
        allowed = {}
        for field in cls.__dataclass_fields__:
            number = value.get(field, getattr(cls(), field))
            if type(number) not in (int, float):
                raise ValueError(f"budget {field} must be numeric")
            ensure_finite(number)
            if field not in fractional and number != int(number):
                raise ValueError(f"budget {field} must be an integer")
            allowed[field] = float(number) if field in fractional else int(number)
        if any(number < 0 for number in allowed.values()):
            raise ValueError("budget values must be non-negative")
        return cls(**allowed)
