"""实现安全环境 manifest、ONLINE_VERIFIED 和 mock batch 执行。

Implement safe environment manifests, ONLINE_VERIFIED, and mock batch execution.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
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


class EnvironmentError(RuntimeError):
    """环境验证或执行失败。 / Raised for environment validation or execution failures."""


ALLOWED_EXECUTABLES = frozenset({"python", "python3", "python3.8", "python3.9", "python3.10", "python3.11", "python3.12"})


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
        if expected_adapter_hash and file_sha256(adapter_path) != expected_adapter_hash:
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
        checks["artifacts"] = {"result_files": sorted(path.relative_to(result_dir).as_posix() for path in result_dir.rglob("*") if path.is_file()), "artifact_files": sorted(path.relative_to(artifact_dir).as_posix() for path in artifact_dir.rglob("*") if path.is_file())}
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

    def _receipt(self, status: str, checks: Mapping[str, Any]) -> Dict[str, Any]:
        """生成 environment receipt。 / Build an environment receipt."""

        receipt = {"schema_version": "robotics-ar-environment-receipt.v1", "environment_id": self.manifest["id"], "fingerprint": self.fingerprint(), "status": status, "checks": dict(checks), "created_at": utc_now()}
        receipt["receipt_sha256"] = sha256_obj(receipt)
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
