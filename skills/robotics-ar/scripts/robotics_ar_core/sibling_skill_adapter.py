"""适配四个并列 Skill 的入口、validator、hash 和通用 receipt。

Adapt the four sibling Skill entry points, validators, hashes, and generic receipts.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional

from .atomic_io import atomic_write_json, read_json
from .canonical import sha256_obj
from .receipts import file_sha256


class SiblingAdapterError(RuntimeError):
    """并列 Skill 适配失败。 / Raised for sibling adapter failures."""


@dataclass(frozen=True)
class SiblingSpec:
    """一个 sibling 的公开接口。 / Public interface for one sibling."""

    key: str
    skill: str
    validator: str
    native_artifact: str
    result_validator: Optional[str] = None
    template: Optional[str] = None


SIBLING_SPECS = (
    SiblingSpec("idea", "skills/develop-robotics-idea/SKILL.md", "skills/develop-robotics-idea/scripts/validate_research_card.py", "research-card.json", template="skills/develop-robotics-idea/assets/research-card.template.json"),
    SiblingSpec("experiment", "skills/design-robotics-experiment/SKILL.md", "skills/design-robotics-experiment/scripts/validate_experiment_contract.py", "experiment-contract.json", result_validator="skills/design-robotics-experiment/scripts/validate_result_bundle.py", template="skills/design-robotics-experiment/assets/experiment-contract.template.json"),
    SiblingSpec("writing", "skills/write-robotics-paper/SKILL.md", "skills/write-robotics-paper/scripts/validate_claim_ledger.py", "claim-ledger.json", template="skills/write-robotics-paper/assets/claim-ledger.template.json"),
    SiblingSpec("review", "skills/review-robotic-feedback/SKILL.md", "skills/review-robotic-feedback/scripts/validate_review_report.py", "meta-review.json", template="skills/review-robotic-feedback/assets/meta-review.template.json"),
)


def _spec_dict(root: Path, spec: SiblingSpec) -> Dict[str, Any]:
    """为 spec 计算路径和 hash。 / Resolve paths and hashes for a spec."""

    result: Dict[str, Any] = {
        "skill": spec.skill,
        "validator": spec.validator,
        "native_artifact": spec.native_artifact,
        "skill_sha256": file_sha256(root / spec.skill),
        "validator_sha256": file_sha256(root / spec.validator),
    }
    if spec.result_validator:
        result["result_validator"] = spec.result_validator
        result["result_validator_sha256"] = file_sha256(root / spec.result_validator)
    if spec.template:
        result["template"] = spec.template
        result["template_sha256"] = file_sha256(root / spec.template)
    return result


class SiblingSkillInvocationAdapter:
    """发现、冻结和验证 sibling，不执行隐式调用。 / Discover, freeze, and validate siblings without implicit calls."""

    def __init__(self, robotics_research_root: Path | str) -> None:
        self.root = Path(robotics_research_root).resolve()

    def discover(self) -> Dict[str, Any]:
        """生成未确认 candidate manifest。 / Build an unconfirmed candidate manifest."""

        siblings: Dict[str, Any] = {}
        missing: List[str] = []
        for spec in SIBLING_SPECS:
            required = [spec.skill, spec.validator]
            if spec.result_validator:
                required.append(spec.result_validator)
            if spec.template:
                required.append(spec.template)
            if any(not (self.root / relative).is_file() for relative in required):
                missing.append(spec.key)
                continue
            siblings[spec.key] = _spec_dict(self.root, spec)
        manifest = {"schema_version": "robotics-ar-sibling-skills-manifest.v1", "name": "robotics-research-sibling-skills", "root": self.root.as_posix(), "confirmed_by_user": False, "siblings": siblings, "missing": missing}
        manifest["manifest_sha256"] = self.manifest_hash(manifest)
        return manifest

    @staticmethod
    def manifest_hash(manifest: Mapping[str, Any]) -> str:
        """计算不含自身字段的 manifest hash。 / Hash a manifest without its own hash."""

        copy = dict(manifest)
        copy.pop("manifest_sha256", None)
        return sha256_obj(copy)

    def write_manifest(self, path: Path | str, manifest: Mapping[str, Any]) -> Path:
        """写入 candidate/confirmed manifest。 / Write a candidate or confirmed manifest."""

        value = dict(manifest)
        value["manifest_sha256"] = self.manifest_hash(value)
        atomic_write_json(path, value)
        return Path(path)

    def confirm_manifest(self, path: Path | str, expected_hash: str) -> Dict[str, Any]:
        """由用户 hash 确认 manifest 并冻结。 / Freeze a manifest after user hash confirmation."""

        manifest = read_json(path)
        actual = self.manifest_hash(manifest)
        if actual != expected_hash or manifest.get("manifest_sha256") != actual:
            raise SiblingAdapterError("manifest hash mismatch")
        if manifest.get("missing"):
            raise SiblingAdapterError(f"missing siblings: {manifest['missing']}")
        manifest["confirmed_by_user"] = True
        manifest["confirmed_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        manifest["manifest_sha256"] = self.manifest_hash(manifest)
        atomic_write_json(path, manifest)
        return manifest

    def validate_manifest(self, manifest: Mapping[str, Any], *, require_confirmed: bool = True) -> None:
        """验证路径、hash 和确认状态。 / Validate paths, hashes, and confirmation."""

        if require_confirmed and not manifest.get("confirmed_by_user"):
            raise SiblingAdapterError("manifest is not confirmed")
        if manifest.get("root") != self.root.as_posix():
            raise SiblingAdapterError("manifest root drift")
        if manifest.get("manifest_sha256") != self.manifest_hash(manifest):
            raise SiblingAdapterError("manifest self-hash drift")
        for key, entry in manifest.get("siblings", {}).items():
            for field in ("skill", "validator", "template"):
                relative = entry.get(field)
                if relative:
                    try:
                        (self.root / relative).resolve().relative_to(self.root)
                    except ValueError as exc:
                        raise SiblingAdapterError(f"path escapes root: {relative}") from exc
            if file_sha256(self.root / entry["skill"]) != entry.get("skill_sha256"):
                raise SiblingAdapterError(f"skill hash drift: {key}")
            if file_sha256(self.root / entry["validator"]) != entry.get("validator_sha256"):
                raise SiblingAdapterError(f"validator hash drift: {key}")
            if entry.get("result_validator") and file_sha256(self.root / entry["result_validator"]) != entry.get("result_validator_sha256"):
                raise SiblingAdapterError(f"result validator hash drift: {key}")
            if entry.get("template") and file_sha256(self.root / entry["template"]) != entry.get("template_sha256"):
                raise SiblingAdapterError(f"template hash drift: {key}")

    def prepare_invocation(self, manifest: Mapping[str, Any], stage: str, *, session_id: str, prompt: str, allowed_files: Iterable[str], input_sha256: str = "") -> Dict[str, Any]:
        """生成实际 runtime 使用的 invocation request。 / Prepare the request consumed by an actual runtime."""

        self.validate_manifest(manifest)
        if stage not in manifest.get("siblings", {}):
            raise SiblingAdapterError(f"stage is missing: {stage}")
        allowed = []
        for relative in allowed_files:
            target = (self.root / relative).resolve()
            try:
                target.relative_to(self.root)
            except ValueError as exc:
                raise SiblingAdapterError(f"allowed file escapes root: {relative}") from exc
            allowed.append(Path(relative).as_posix())
        request = {"schema_version": "robotics-ar-invocation-request.v1", "session_id": session_id, "stage": stage, "prompt": prompt, "prompt_sha256": sha256_obj({"prompt": prompt}), "allowed_files": sorted(set(allowed)), "input_sha256": input_sha256, "manifest_sha256": manifest["manifest_sha256"], "runtime_status": "REQUEST_ONLY"}
        request["request_sha256"] = sha256_obj(request)
        return request

    @staticmethod
    def runtime_status(stage: str, *, fresh_runtime: bool, manual_review_import: bool = False) -> str:
        """诚实表示当前 Agent runtime 能力。 / Honestly represent runtime capability."""

        if fresh_runtime:
            return "FRESH_RUNTIME"
        if stage == "review" and not manual_review_import:
            return "BLOCKED_DEPENDENCY"
        if stage == "review" and manual_review_import:
            return "MANUAL_REVIEW_IMPORT"
        return "SINGLE_AGENT_MODE"

    def validate_native_artifact(self, stage: str, artifact_path: Path | str, *, manifest: Mapping[str, Any], repair: Optional[Callable[[], None]] = None) -> Dict[str, Any]:
        """调用 owner validator；失败时最多运行一次修复再验证。

        Invoke the owner validator; on failure, repair and retry at most once.
        """

        self.validate_manifest(manifest)
        entry = manifest.get("siblings", {}).get(stage)
        if not entry:
            raise SiblingAdapterError(f"unknown stage: {stage}")
        artifact = Path(artifact_path).resolve()
        try:
            artifact.relative_to(self.root)
        except ValueError as exc:
            raise SiblingAdapterError(f"artifact escapes sibling root: {artifact}") from exc
        if not artifact.is_file():
            raise SiblingAdapterError(f"artifact does not exist: {artifact}")
        command = [sys.executable, str(self.root / entry["validator"]), str(artifact)]
        attempts = 0
        result = subprocess.run(command, cwd=self.root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30, check=False)
        attempts += 1
        if result.returncode != 0 and repair is not None:
            repair()
            result = subprocess.run(command, cwd=self.root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30, check=False)
            attempts += 1
        status = "PASS" if result.returncode == 0 else "FAIL"
        return {"status": status, "attempts": attempts, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr, "validator": entry["validator"], "path": artifact.as_posix()}

    def register_stage_result(self, stage: str, artifact_path: Path | str, *, session_id: str, manifest: Mapping[str, Any], validation: Mapping[str, Any], handoff_status: str = "READY", domain_payload: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        """把原生工件包进 generic StageReceipt。 / Wrap a native artifact in a generic StageReceipt."""

        if validation.get("status") != "PASS":
            raise SiblingAdapterError("native artifact did not pass owner validator")
        artifact = Path(artifact_path)
        try:
            artifact.resolve().relative_to(self.root)
        except ValueError as exc:
            raise SiblingAdapterError(f"artifact escapes sibling root: {artifact}") from exc
        if not artifact.is_file():
            raise SiblingAdapterError(f"artifact does not exist: {artifact}")
        receipt = {"schema_version": "robotics-ar-stage-receipt.v1", "session_id": session_id, "stage": stage, "native_artifact": {"path": artifact.as_posix(), "sha256": file_sha256(artifact), "validator": validation.get("validator"), "validation_status": "PASS"}, "handoff_status": handoff_status, "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"), "domain_payload": dict(domain_payload or {})}
        receipt["receipt_sha256"] = sha256_obj(receipt)
        return receipt
