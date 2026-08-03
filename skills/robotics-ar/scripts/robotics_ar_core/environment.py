"""实现安全环境 manifest、ONLINE_VERIFIED 和 mock batch 执行。

Implement safe environment manifests, ONLINE_VERIFIED, and mock batch execution.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .atomic_io import atomic_write_json, contained_path, read_json
from .canonical import ensure_finite, sha256_obj
from .models import utc_now
from .process_registry import ProcessRegistry
from .receipts import file_sha256
from .schema_validation import SchemaValidationError, validate_artifact


class EnvironmentError(RuntimeError):
    """环境验证或执行失败。 / Raised for environment validation or execution failures."""


ALLOWED_EXECUTABLES = frozenset({"python", "python3", "python3.8", "python3.9", "python3.10", "python3.11", "python3.12"})


def validate_environment_receipt(receipt: Mapping[str, Any], *, require_online: bool = False) -> None:
    """Validate an environment receipt and its self-hash before binding it."""

    if not isinstance(receipt, Mapping):
        raise EnvironmentError("environment receipt must be an object")
    try:
        validate_artifact("robotics-ar-environment-receipt.v1", receipt)
    except SchemaValidationError as exc:
        raise EnvironmentError(str(exc)) from exc
    if require_online and receipt.get("status") != "ONLINE_VERIFIED":
        raise EnvironmentError("ONLINE_VERIFIED environment receipt required")
    fingerprint = str(receipt.get("fingerprint", ""))
    if not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
        raise EnvironmentError("environment receipt fingerprint must be a 64-hex digest")
    receipt_hash = receipt.get("receipt_sha256")
    if not isinstance(receipt_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", receipt_hash):
        raise EnvironmentError("environment receipt self-hash is missing or invalid")
    expected = sha256_obj({key: value for key, value in receipt.items() if key != "receipt_sha256"})
    if receipt_hash != expected:
        raise EnvironmentError("environment receipt hash mismatch")


def _load_text_manifest(path: Path) -> Dict[str, Any]:
    """读取 JSON，或读取有限 YAML 子集。 / Read JSON or a limited YAML subset."""

    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    try:
        import yaml  # type: ignore

        value = yaml.safe_load(text)
    except Exception as exc:
        raise EnvironmentError("manifest must be JSON or PyYAML-readable YAML") from exc
    if not isinstance(value, dict):
        raise EnvironmentError("manifest root must be an object")
    return value


def _resolve_under(root: Path, value: str) -> Path:
    """确保路径位于 root 下。 / Ensure a path remains under root."""

    try:
        return contained_path(root, value, allow_missing=True)
    except Exception as exc:
        raise EnvironmentError(str(exc)) from exc


class EnvironmentAdapter:
    """验证并执行一个 environment manifest。 / Validate and execute one environment manifest."""

    def __init__(self, manifest: Mapping[str, Any], *, manifest_path: Optional[Path | str] = None) -> None:
        self.manifest = dict(manifest)
        self.manifest_path = Path(manifest_path).resolve() if manifest_path else None
        self.root = Path(str(self.manifest.get("root", ""))).expanduser().resolve()
        self.process_registry = ProcessRegistry(self.root / ".robotics-ar-process-registry.json")

    @classmethod
    def from_file(cls, path: Path | str) -> "EnvironmentAdapter":
        """从 manifest 文件创建 adapter。 / Create an adapter from a manifest file."""

        target = Path(path).resolve()
        return cls(_load_text_manifest(target), manifest_path=target)

    def validate_manifest(self) -> Dict[str, Any]:
        """验证 schema、argv、allowlist 和路径 containment。

        Validate schema, argv arrays, allowlists, and path containment.
        """

        try:
            validate_artifact("robotics-ar-environment.v1", self.manifest)
        except SchemaValidationError as exc:
            raise EnvironmentError(str(exc)) from exc
        required = ("schema_version", "id", "kind", "root", "adapter", "commands", "io", "limits")
        missing = [key for key in required if key not in self.manifest]
        if missing:
            raise EnvironmentError(f"manifest missing: {missing}")
        if self.manifest["schema_version"] != "robotics-ar-environment.v1":
            raise EnvironmentError("unsupported environment schema")
        if self.manifest["kind"] not in {"simulation", "real_robot", "hybrid"}:
            raise EnvironmentError("invalid environment kind")
        if not self.root.exists() or not self.root.is_dir():
            raise EnvironmentError("environment root does not exist")
        adapter_path = _resolve_under(self.root, str(self.manifest["adapter"]["path"]))
        if not adapter_path.is_file():
            raise EnvironmentError("adapter path does not exist")
        expected_adapter_hash = self.manifest["adapter"].get("sha256")
        if not isinstance(expected_adapter_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_adapter_hash):
            raise EnvironmentError("adapter sha256 must be a complete 64-hex digest")
        if file_sha256(adapter_path) != expected_adapter_hash:
            raise EnvironmentError("adapter hash drift")
        commands = self.manifest["commands"]
        for name in ("capabilities", "health_check", "minimal_rollout", "collect_results", "stop"):
            argv = commands.get(name)
            if not isinstance(argv, list) or not argv or any(not isinstance(arg, str) for arg in argv):
                raise EnvironmentError(f"command must be argv array: {name}")
            self._validate_argv(argv, name=name)
        if commands.get("run_batch") is not None:
            argv = commands.get("run_batch")
            if not isinstance(argv, list) or not argv or any(not isinstance(arg, str) for arg in argv):
                raise EnvironmentError("command must be argv array: run_batch")
            self._validate_argv(argv, name="run_batch")
        for optional_name in ("reset", "baseline", "trial", "collect_metrics", "collect_artifacts"):
            if commands.get(optional_name) is not None:
                argv = commands[optional_name]
                if not isinstance(argv, list) or not argv or any(not isinstance(arg, str) for arg in argv):
                    raise EnvironmentError(f"command must be argv array: {optional_name}")
                self._validate_argv(argv, name=optional_name)
        io = self.manifest["io"]
        for name in ("request_dir", "result_dir", "artifact_dir"):
            _resolve_under(self.root, str(io[name])).mkdir(parents=True, exist_ok=True)
        limits = self.manifest["limits"]
        if int(limits.get("timeout_s", 0)) <= 0 or int(limits.get("max_parallel_runs", 0)) <= 0:
            raise EnvironmentError("limits must be positive")
        if limits.get("network") not in {"denied", "allowed"}:
            raise EnvironmentError("limits.network must be denied or allowed")
        return {"status": "PASS", "environment_id": self.manifest["id"]}

    def _validate_argv(self, argv: Sequence[str], *, name: str) -> None:
        """验证 executable、参数类型和相对路径。 / Validate executable, argument types, and relative paths."""

        executable = Path(argv[0]).name
        allowlist = set(self.manifest.get("limits", {}).get("executables", ALLOWED_EXECUTABLES))
        if executable not in allowlist:
            raise EnvironmentError(f"executable not allowlisted: {executable}")
        if Path(argv[0]).is_absolute():
            resolved = Path(argv[0]).resolve()
            actual = shutil.which(executable)
            if not actual or Path(actual).resolve() != resolved:
                raise EnvironmentError(f"executable path is not the approved binary: {argv[0]}")
        for argument in argv[1:]:
            if "\x00" in argument or "\n" in argument or "\r" in argument:
                raise EnvironmentError(f"invalid command argument in {name}")
            if argument.startswith("/"):
                # Absolute interpreter/library paths are not accepted as command arguments.
                try:
                    Path(argument).resolve().relative_to(self.root)
                except ValueError as exc:
                    raise EnvironmentError(f"command argument escapes environment root: {argument}") from exc
            if ".." in Path(argument).parts:
                raise EnvironmentError(f"command argument contains traversal: {argument}")

    def fingerprint(self) -> str:
        """返回 manifest + adapter 内容的 immutable fingerprint。

        Return an immutable fingerprint of the manifest and adapter content.
        """

        self.validate_manifest()
        adapter_path = _resolve_under(self.root, str(self.manifest["adapter"]["path"]))
        return sha256_obj({"manifest": self.manifest, "adapter_sha256": file_sha256(adapter_path)})

    def _sanitized_env(self) -> Dict[str, str]:
        """返回最小环境变量。 / Return a minimal sanitized environment."""

        selected = {"PATH": os.environ.get("PATH", "")}
        selected.update({str(key): str(value) for key, value in self.manifest.get("env", {}).items()})
        return selected

    def run_argv(self, argv: Sequence[str], *, label: str, timeout_s: Optional[float] = None) -> Dict[str, Any]:
        """安全运行 argv；超时只 stop，不自动重试。

        Safely run argv; timeout stops once and never retries automatically.
        """

        self.validate_manifest()
        if not argv or any(not isinstance(arg, str) for arg in argv):
            raise EnvironmentError("argv must be a non-empty string list")
        self._validate_argv(argv, name=label)
        timeout = float(timeout_s or self.manifest["limits"]["timeout_s"])
        started = time.time()
        process = subprocess.Popen(list(argv), cwd=self.root, env=self._sanitized_env(), shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
        self.process_registry.register(process.pid, list(argv), self.root)
        timed_out = False
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except (ProcessLookupError, OSError):
                pass
            try:
                stdout, stderr = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except (ProcessLookupError, OSError):
                    pass
                stdout, stderr = process.communicate()
        status = "TIMEOUT" if timed_out else ("PASS" if process.returncode == 0 else "FAIL")
        self.process_registry.mark_stopped(process.pid, status, stdout=stdout, stderr=stderr)
        return {"label": label, "argv": list(argv), "returncode": process.returncode, "stdout": stdout, "stderr": stderr, "status": status, "duration_s": round(time.time() - started, 6)}

    def _json_output(self, result: Mapping[str, Any], label: str) -> Dict[str, Any]:
        """解析有限 JSON 输出。 / Parse finite JSON output."""

        try:
            value = json.loads(str(result.get("stdout", "")))
        except json.JSONDecodeError as exc:
            raise EnvironmentError(f"{label} did not emit JSON") from exc
        ensure_finite(value)
        if not isinstance(value, dict):
            raise EnvironmentError(f"{label} output must be an object")
        return value

    def verify_online(self) -> Dict[str, Any]:
        """执行 capabilities、health、minimal rollout、collect 和 stop gate。

        Run capabilities, health, minimal rollout, collection, and stop gates.
        """

        self.validate_manifest()
        checks: Dict[str, Any] = {}
        for name in ("capabilities", "health_check", "minimal_rollout"):
            result = self.run_argv(self.manifest["commands"][name], label=name)
            try:
                output = self._json_output(result, name) if result["status"] == "PASS" else {}
            except EnvironmentError as exc:
                checks[name] = {"status": "INVALID_RESULT", "error": str(exc)}
                return self._receipt("BLOCKED_ENVIRONMENT", checks)
            checks[name] = {"status": result["status"], "output": output}
            if result["status"] != "PASS":
                return self._receipt("BLOCKED_ENVIRONMENT", checks)
        collected = self.run_argv(self.manifest["commands"]["collect_results"], label="collect_results")
        try:
            collected_output = self._json_output(collected, "collect_results") if collected["status"] == "PASS" else {}
        except EnvironmentError as exc:
            checks["collect_results"] = {"status": "INVALID_RESULT", "error": str(exc)}
            return self._receipt("BLOCKED_ENVIRONMENT", checks)
        checks["collect_results"] = {"status": collected["status"], "output": collected_output}
        if collected["status"] != "PASS":
            return self._receipt("BLOCKED_ENVIRONMENT", checks)
        io = self.manifest["io"]
        result_dir = _resolve_under(self.root, io["result_dir"])
        artifact_dir = _resolve_under(self.root, io["artifact_dir"])
        checks["artifacts"] = {"result_files": self._file_receipts(result_dir), "artifact_files": self._file_receipts(artifact_dir)}
        if not checks["artifacts"]["result_files"] or not checks["artifacts"]["artifact_files"]:
            return self._receipt("BLOCKED_ENVIRONMENT", checks)
        stop_first = self.run_argv(self.manifest["commands"]["stop"], label="stop-1")
        stop_second = self.run_argv(self.manifest["commands"]["stop"], label="stop-2")
        try:
            stop_first_output = self._json_output(stop_first, "stop-1") if stop_first["status"] == "PASS" else {}
            stop_second_output = self._json_output(stop_second, "stop-2") if stop_second["status"] == "PASS" else {}
        except EnvironmentError as exc:
            checks["stop"] = {"status": "INVALID_RESULT", "error": str(exc)}
            return self._receipt("BLOCKED_ENVIRONMENT", checks)
        checks["stop"] = [{"status": stop_first["status"], "output": stop_first_output}, {"status": stop_second["status"], "output": stop_second_output}]
        if stop_first["status"] != "PASS" or stop_second["status"] != "PASS":
            return self._receipt("BLOCKED_ENVIRONMENT", checks)
        return self._receipt("ONLINE_VERIFIED", checks)

    def capability_manifest(self) -> Dict[str, Any]:
        """Read the environment capability declaration through the approved adapter."""

        self.validate_manifest()
        result = self.run_argv(self.manifest["commands"]["capabilities"], label="capabilities")
        if result["status"] != "PASS":
            raise EnvironmentError("capability command failed")
        return self._json_output(result, "capabilities")

    def health_check(self) -> Dict[str, Any]:
        """Run a single health check and require a finite JSON object."""

        self.validate_manifest()
        result = self.run_argv(self.manifest["commands"]["health_check"], label="health-check")
        if result["status"] != "PASS":
            raise EnvironmentError("health check failed")
        return self._json_output(result, "health-check")

    def reset(self, reset_spec: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        """Reset once using an explicit reset command or the minimal rollout adapter."""

        command = self.manifest["commands"].get("reset") or self.manifest["commands"]["minimal_rollout"]
        request_path = _resolve_under(self.root, self.manifest["io"]["request_dir"]) / "reset-request.json"
        atomic_write_json(request_path, dict(reset_spec or {}))
        result = self.run_argv(command, label="reset")
        if result["status"] != "PASS":
            raise EnvironmentError("reset failed")
        return self._json_output(result, "reset")

    def reproduce_baseline(self, baseline_spec: Mapping[str, Any]) -> Dict[str, Any]:
        """Execute the approved baseline command once and return finite output."""

        command = self.manifest["commands"].get("baseline") or self.manifest["commands"].get("run_batch") or self.manifest["commands"]["minimal_rollout"]
        request_path = _resolve_under(self.root, self.manifest["io"]["request_dir"]) / "baseline-request.json"
        atomic_write_json(request_path, dict(baseline_spec))
        result = self.run_argv(command, label="baseline")
        if result["status"] != "PASS":
            raise EnvironmentError(f"baseline failed: {result['status']}")
        output = self._json_output(result, "baseline")
        return {"status": "PASS", "output": output, "request_path": request_path.as_posix(), "command": list(command)}

    def run_trial(self, trial_spec: Mapping[str, Any]) -> Dict[str, Any]:
        """Run exactly one trial; retries are the caller's explicit responsibility."""

        if self.manifest.get("kind") == "real_robot":
            raise EnvironmentError("real-robot trials require BatchController caution/token authorization")
        command = self.manifest["commands"].get("trial") or self.manifest["commands"].get("run_batch") or self.manifest["commands"]["minimal_rollout"]
        trial_id = str(trial_spec.get("trial_id", "trial"))
        request_path = _resolve_under(self.root, self.manifest["io"]["request_dir"]) / f"{trial_id}-request.json"
        atomic_write_json(request_path, dict(trial_spec))
        result = self.run_argv(command, label=f"trial-{trial_id}")
        if result["status"] != "PASS":
            raise EnvironmentError(f"trial failed: {result['status']}")
        output = self._json_output(result, f"trial-{trial_id}")
        artifacts = self.collect_artifacts(trial_id)
        raw_evidence = {"request": {"path": request_path.as_posix(), "sha256": file_sha256(request_path)}, "output_sha256": sha256_obj(output), "artifacts": artifacts, "environment_fingerprint": self.fingerprint()}
        if not artifacts.get("files"):
            raise EnvironmentError("trial produced no raw artifacts")
        return {"status": "PASS", "trial_id": trial_id, "output": output, "request_path": request_path.as_posix(), "command": list(command), "raw_evidence": raw_evidence}

    def collect_metrics(self, run_id: str) -> Dict[str, Any]:
        command = self.manifest["commands"].get("collect_metrics") or self.manifest["commands"]["collect_results"]
        result = self.run_argv(command, label=f"metrics-{run_id}")
        if result["status"] != "PASS":
            raise EnvironmentError("metric collection failed")
        return self._json_output(result, f"metrics-{run_id}")

    def collect_artifacts(self, run_id: str) -> Dict[str, Any]:
        command = self.manifest["commands"].get("collect_artifacts")
        artifact_dir = _resolve_under(self.root, self.manifest["io"]["artifact_dir"])
        if command is not None:
            result = self.run_argv(command, label=f"artifacts-{run_id}")
            if result["status"] != "PASS":
                raise EnvironmentError("artifact collection failed")
            value = self._json_output(result, f"artifacts-{run_id}")
            value.setdefault("run_id", run_id)
            # Collect after the adapter command so newly materialized raw
            # evidence is included in the receipt.
            value["files"] = self._file_receipts(artifact_dir)
            return value
        return {"run_id": run_id, "files": self._file_receipts(artifact_dir)}

    def stop(self, run_id: Optional[str] = None) -> Dict[str, Any]:
        """Perform one idempotent stop call; never retry automatically."""

        result = self.run_argv(self.manifest["commands"]["stop"], label=f"stop-{run_id or 'current'}")
        if result["status"] != "PASS":
            raise EnvironmentError("stop failed")
        return self._json_output(result, f"stop-{run_id or 'current'}")

    def verify_takeover(self) -> Dict[str, Any]:
        """Verify the stronger takeover contract, including reset and trial hooks."""

        base = self.verify_online()
        if base.get("status") != "ONLINE_VERIFIED":
            return base
        checks = dict(base.get("checks", {}))
        try:
            reset_one = self.reset({"probe": True, "reset_index": 1})
            reset_two = self.reset({"probe": True, "reset_index": 2})
            checks["reset"] = {"status": "PASS", "outputs": [reset_one, reset_two]}
            checks["metrics"] = {"status": "PASS", "output": self.collect_metrics("online-verification")}
            checks["artifacts"] = {"status": "PASS", "output": self.collect_artifacts("online-verification")}
        except EnvironmentError as exc:
            checks["reset"] = {"status": "BLOCKED", "error": str(exc)}
            return self._receipt("BLOCKED_ENVIRONMENT", checks)
        if not (self.manifest["commands"].get("trial") or self.manifest["commands"].get("run_batch")):
            checks["trial_binding"] = {"status": "BLOCKED", "error": "trial or run_batch command is missing"}
            return self._receipt("BLOCKED_ENVIRONMENT", checks)
        checks["trial_binding"] = {"status": "PASS", "command": self.manifest["commands"].get("trial") or self.manifest["commands"].get("run_batch"), "config_binding": "request_dir/trial_id"}
        receipt = self._receipt("ONLINE_VERIFIED", checks)
        receipt["takeover_capabilities"] = {"baseline": "baseline" in self.manifest["commands"] or "run_batch" in self.manifest["commands"], "trial": "trial" in self.manifest["commands"] or "run_batch" in self.manifest["commands"], "reset": True, "metrics": True, "artifacts": True, "stop": True}
        receipt.pop("receipt_sha256", None)
        receipt["receipt_sha256"] = sha256_obj(receipt)
        try:
            validate_artifact("robotics-ar-environment-receipt.v1", receipt)
        except SchemaValidationError as exc:
            raise EnvironmentError(str(exc)) from exc
        return receipt

    def _receipt(self, status: str, checks: Mapping[str, Any]) -> Dict[str, Any]:
        """生成 environment receipt。 / Build an environment receipt."""

        receipt = {"schema_version": "robotics-ar-environment-receipt.v1", "environment_id": self.manifest["id"], "environment_kind": self.manifest.get("kind"), "fingerprint": self.fingerprint(), "status": status, "checks": dict(checks), "created_at": utc_now()}
        receipt["receipt_sha256"] = sha256_obj(receipt)
        try:
            validate_artifact("robotics-ar-environment-receipt.v1", receipt)
        except SchemaValidationError as exc:
            raise EnvironmentError(str(exc)) from exc
        return receipt

    @staticmethod
    def ensure_execution_allowed(mode: str, receipt: Optional[Mapping[str, Any]]) -> None:
        """执行前检查 mode 和 ONLINE_VERIFIED receipt。 / Gate execution on mode and ONLINE_VERIFIED receipt."""

        if mode == "PLANNING_ONLY":
            raise EnvironmentError("PLANNING_ONLY cannot execute a batch")
        if not receipt or receipt.get("status") != "ONLINE_VERIFIED":
            raise EnvironmentError("ONLINE_VERIFIED receipt required")

    def run_batch(self, mode: str, receipt: Optional[Mapping[str, Any]], *, request: Mapping[str, Any]) -> Dict[str, Any]:
        """只运行已验证的 batch 命令。 / Run a batch only after verification."""

        self.ensure_execution_allowed(mode, receipt)
        if self.manifest.get("kind") == "real_robot":
            raise EnvironmentError("real-robot batches require BatchController caution/token authorization")
        if receipt.get("fingerprint") != self.fingerprint():
            raise EnvironmentError("environment fingerprint drift")
        request_path = _resolve_under(self.root, self.manifest["io"]["request_dir"]) / "batch-request.json"
        atomic_write_json(request_path, dict(request))
        command = self.manifest["commands"].get("run_batch") or self.manifest["commands"]["minimal_rollout"]
        result = self.run_argv(command, label="run-batch")
        if result["status"] != "PASS":
            raise EnvironmentError(f"batch failed: {result['status']}")
        output = self._json_output(result, "run-batch")
        return {"status": "PASS", "result": output, "request_path": request_path.as_posix()}

    @staticmethod
    def _file_receipts(root: Path) -> List[Dict[str, Any]]:
        """Return real file/hash receipts while refusing symlinked evidence."""

        receipts: List[Dict[str, Any]] = []
        for path in sorted(root.rglob("*")):
            if path.is_symlink():
                continue
            if path.is_file():
                receipts.append({"path": path.relative_to(root).as_posix(), "sha256": file_sha256(path), "bytes": path.stat().st_size})
        return receipts
