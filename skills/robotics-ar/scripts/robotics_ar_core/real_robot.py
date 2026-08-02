"""实现真实机器人 caution 文档和一次性批准 token。

Implement real-robot caution documents and one-shot approval tokens.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from .atomic_io import atomic_write_json, atomic_write_bytes, read_json
from .canonical import sha256_obj
from .models import utc_now


class RealRobotGateError(RuntimeError):
    """真实设备门禁失败。 / Raised when the real-robot gate fails."""


CAUTION_FIELDS = (
    "robot",
    "experiment_id",
    "task",
    "controller_or_policy",
    "expected_motion",
    "expected_contact",
    "workspace_boundary",
    "velocity_limits",
    "acceleration_limits",
    "force_limits",
    "torque_limits",
    "episode_count",
    "operator_presence",
    "emergency_stop",
    "stop_conditions",
    "data_recording",
    "automatic_retry",
)


def build_caution_document(values: Mapping[str, Any]) -> Dict[str, Any]:
    """校验 caution 字段并强制关闭自动重试。

    Validate caution fields and force automatic retry off.
    """

    missing = [field for field in CAUTION_FIELDS if field not in values]
    if missing:
        raise RealRobotGateError(f"caution document missing: {missing}")
    if values.get("automatic_retry") not in {False, "DISABLED", "disabled", "false"}:
        raise RealRobotGateError("automatic retry must be disabled")
    if values.get("operator_presence") in {False, None, "absent", "ABSENT"}:
        raise RealRobotGateError("operator presence is required")
    if not values.get("emergency_stop"):
        raise RealRobotGateError("emergency stop is required")
    document = {
        "schema_version": "robotics-ar-real-robot-caution.v1",
        "title": "CAUTION — REAL ROBOT EXECUTION",
        "fields": {field: values[field] for field in CAUTION_FIELDS},
        "created_at": utc_now(),
    }
    document["caution_sha256"] = sha256_obj(document)
    return document


def render_caution_markdown(document: Mapping[str, Any]) -> str:
    """渲染中英双语 caution 文件。 / Render a bilingual caution file."""

    fields = document.get("fields", {})
    lines = [
        "# CAUTION — REAL ROBOT EXECUTION",
        "",
        "## 中文",
        "",
        "真实机器人仅允许一次批准的单一 batch；失败后必须停止、保存收据、暂停并等待用户决定。",
        "",
    ]
    labels = {
        "robot": "机器人 / Robot",
        "experiment_id": "实验 ID / Experiment ID",
        "task": "任务 / Task",
        "controller_or_policy": "控制器或策略 / Controller or policy",
        "expected_motion": "预期运动 / Expected motion",
        "expected_contact": "预期接触 / Expected contact",
        "workspace_boundary": "工作空间边界 / Workspace boundary",
        "velocity_limits": "速度限制 / Velocity limits",
        "acceleration_limits": "加速度限制 / Acceleration limits",
        "force_limits": "力限制 / Force limits",
        "torque_limits": "扭矩限制 / Torque limits",
        "episode_count": "回合数 / Episode count",
        "operator_presence": "操作员在场 / Operator presence",
        "emergency_stop": "急停 / Emergency stop",
        "stop_conditions": "停止条件 / Stop conditions",
        "data_recording": "数据记录 / Data recording",
        "automatic_retry": "自动重试 / Automatic retry",
    }
    for field in CAUTION_FIELDS:
        lines.append(f"- **{labels[field]}**: `{fields[field]}`")
    lines.extend([
        "",
        "## English",
        "",
        "Only one approved batch may run on a real robot; on failure, stop, save the receipt, pause, and ask the user.",
        "",
    ])
    for field in CAUTION_FIELDS:
        lines.append(f"- **{labels[field]}**: `{fields[field]}`")
    lines.extend(["", f"Caution SHA-256: `{document['caution_sha256']}`", ""])
    return "\n".join(lines)


class OneShotRealRobotToken:
    """绑定安全上下文、只能消费一次的真实机器人 token。 / One-use token bound to safety context."""

    def __init__(self, token: Mapping[str, Any]) -> None:
        self.token = dict(token)
        self._path: Optional[Path] = None

    @classmethod
    def issue(
        cls,
        *,
        task_sha256: str,
        environment_sha256: str,
        adapter_sha256: str,
        safety_limits_sha256: str,
        batch_id: str,
        operator_presence: str,
        token_id: Optional[str] = None,
    ) -> "OneShotRealRobotToken":
        """生成 single-use token。 / Issue a single-use token."""

        if not operator_presence or operator_presence.lower() in {"absent", "false", "no"}:
            raise RealRobotGateError("operator must be present")
        binding = {
            "task_sha256": task_sha256,
            "environment_sha256": environment_sha256,
            "adapter_sha256": adapter_sha256,
            "safety_limits_sha256": safety_limits_sha256,
            "batch_id": batch_id,
            "operator_presence": operator_presence,
        }
        token = {
            "schema_version": "robotics-ar-real-robot-token.v1",
            "token_id": token_id or f"RRT-{sha256_obj(binding)[:16]}",
            "binding": binding,
            "status": "unused",
            "issued_at": utc_now(),
        }
        token["token_sha256"] = sha256_obj(token)
        return cls(token)

    @property
    def token_id(self) -> str:
        """返回 token ID。 / Return the token ID."""

        return str(self.token["token_id"])

    def _assert_integrity(self) -> None:
        """验证 token 自身安全 hash。 / Verify the token's own safety hash."""

        expected = self.token.get("token_sha256")
        actual = sha256_obj({key: value for key, value in self.token.items() if key != "token_sha256"})
        if not expected or expected != actual:
            raise RealRobotGateError("real-robot token integrity mismatch")

    def save(self, path: Path | str) -> Path:
        """原子保存 token。 / Atomically save the token."""

        self._assert_integrity()
        target = Path(path)
        atomic_write_json(target, self.token)
        self._path = target
        return target

    @classmethod
    def load(cls, path: Path | str) -> "OneShotRealRobotToken":
        """读取 token。 / Load a token."""

        token = cls(read_json(path))
        token._assert_integrity()
        token._path = Path(path)
        return token

    def consume(self, *, binding: Mapping[str, Any], stop_status: str = "READY", retry_requested: bool = False) -> Dict[str, Any]:
        """验证绑定后消费一次；不执行设备命令。 / Validate binding and consume once without device I/O."""

        self._assert_integrity()
        if self.token.get("status") != "unused":
            raise RealRobotGateError("real-robot token replay rejected")
        expected = dict(self.token.get("binding", {}))
        for key, value in expected.items():
            if binding.get(key) != value:
                raise RealRobotGateError(f"real-robot binding drift: {key}")
        if not binding.get("operator_presence") or str(binding.get("operator_presence")).lower() in {"absent", "false", "no"}:
            raise RealRobotGateError("operator presence missing")
        if retry_requested:
            raise RealRobotGateError("automatic retry is disabled")
        if stop_status not in {"READY", "PASS", "STOPPED"}:
            raise RealRobotGateError("stop gate did not pass")
        self.token["status"] = "consumed"
        self.token["consumed_at"] = utc_now()
        self.token["consumed_binding_sha256"] = sha256_obj(dict(binding))
        self.token["token_sha256"] = sha256_obj({key: value for key, value in self.token.items() if key != "token_sha256"})
        if self._path is not None:
            atomic_write_json(self._path, self.token)
        return dict(self.token)


def failure_protocol(*, receipt_path: Path | str, report_path: Path | str, reason: str) -> Dict[str, str]:
    """返回真实设备失败后的固定动作，不连接设备。

    Return the fixed post-failure actions without connecting to a device.
    """

    receipt = {"schema_version": "robotics-ar-real-robot-failure.v1", "status": "STOP_SAVE_PAUSE_REPORT_USER_DECISION", "reason": reason, "created_at": utc_now()}
    receipt["receipt_sha256"] = sha256_obj(receipt)
    atomic_write_json(receipt_path, receipt)
    text = "# 真实设备失败报告\n\n## 中文\n\nSTOP → SAVE RECEIPT → PAUSE → REPORT → USER DECISION\n\n原因：" + reason + "\n\n# English\n\nSTOP → SAVE RECEIPT → PAUSE → REPORT → USER DECISION\n\nReason: " + reason + "\n"
    atomic_write_bytes(report_path, text.encode("utf-8"))
    return {"status": receipt["status"], "receipt_path": str(receipt_path), "report_path": str(report_path)}
