#!/usr/bin/env python3
"""提供 Robotics-AR 的确定性 CLI。

Provide the deterministic Robotics-AR command-line interface.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, Iterable, List, Mapping, Optional


SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from robotics_ar_core.environment import EnvironmentAdapter, EnvironmentError  # noqa: E402
from robotics_ar_core.reporting import write_handoff, write_report  # noqa: E402
from robotics_ar_core.session import SessionError, SessionManager  # noqa: E402
from robotics_ar_core.sibling_skill_adapter import SiblingAdapterError, SiblingSkillInvocationAdapter  # noqa: E402


class CLIError(RuntimeError):
    """CLI 参数或 gate 失败。 / Raised for CLI argument or gate failures."""


def _manager(args: argparse.Namespace) -> SessionManager:
    return SessionManager(args.project_root)


def _split(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _load_json(path: Path | str) -> Dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CLIError(f"cannot read JSON: {path}") from exc
    if not isinstance(value, dict):
        raise CLIError(f"JSON object required: {path}")
    return value


def _dry(args: argparse.Namespace, action: str, **extra: Any) -> Dict[str, Any]:
    return {"status": "DRY_RUN", "action": action, **extra}


def command_discover(args: argparse.Namespace) -> Dict[str, Any]:
    adapter = SiblingSkillInvocationAdapter(args.robotics_research_root)
    manifest = adapter.discover()
    path = Path(args.project_root).resolve() / ".robotics-ar" / "sibling-skills" / "manifest.json"
    if args.dry_run:
        return _dry(args, "discover", manifest=manifest, path=path.as_posix())
    adapter.write_manifest(path, manifest)
    return {"status": "PASS", "manifest_path": path.as_posix(), "manifest": manifest}


def command_init(args: argparse.Namespace) -> Dict[str, Any]:
    if args.dry_run:
        return _dry(args, "init", project_root=str(Path(args.project_root).resolve()), mode=args.mode)
    return _manager(args).initialize(mode=args.mode, interaction_language=args.interaction_language)


def command_status(args: argparse.Namespace) -> Dict[str, Any]:
    return _manager(args).state


def _manifest_path(args: argparse.Namespace) -> Path:
    return Path(args.manifest or (Path(args.project_root).resolve() / ".robotics-ar" / "sibling-skills" / "manifest.json"))


def command_validate_siblings(args: argparse.Namespace) -> Dict[str, Any]:
    adapter = SiblingSkillInvocationAdapter(args.robotics_research_root)
    path = _manifest_path(args)
    manifest = _load_json(path)
    adapter.validate_manifest(manifest, require_confirmed=not args.allow_unconfirmed)
    return {"status": "PASS", "manifest_path": path.as_posix(), "manifest_sha256": manifest.get("manifest_sha256")}


def command_prepare_stage(args: argparse.Namespace) -> Dict[str, Any]:
    adapter = SiblingSkillInvocationAdapter(args.robotics_research_root)
    manifest = _load_json(_manifest_path(args))
    request = adapter.prepare_invocation(manifest, args.stage, session_id=_manager(args).session_id, prompt=args.prompt, allowed_files=_split(args.allowed_files), input_sha256=args.input_sha256)
    path = Path(args.project_root).resolve() / ".robotics-ar" / "sibling-skills" / args.stage / "invocation-request.json"
    if args.dry_run:
        return _dry(args, "prepare-stage", request=request, path=path.as_posix())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    return {"status": "PASS", "request_path": path.as_posix(), "request": request}


def command_register_stage_result(args: argparse.Namespace) -> Dict[str, Any]:
    adapter = SiblingSkillInvocationAdapter(args.robotics_research_root)
    manifest = _load_json(_manifest_path(args))
    result = adapter.validate_native_artifact(args.stage, args.artifact, manifest=manifest)
    if result["status"] != "PASS":
        raise CLIError("native artifact failed owner validator")
    receipt = adapter.register_stage_result(args.stage, args.artifact, session_id=_manager(args).session_id, manifest=manifest, validation=result, handoff_status=args.handoff_status)
    path = Path(args.project_root).resolve() / ".robotics-ar" / "sibling-skills" / args.stage / "stage-receipt.json"
    if args.dry_run:
        return _dry(args, "register-stage-result", receipt=receipt, path=path.as_posix())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    return {"status": "PASS", "receipt_path": path.as_posix(), "receipt": receipt}


def command_approve(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    subject = Path(args.subject)
    if args.dry_run:
        return _dry(args, "approve", gate=args.gate, subject_path=subject.as_posix())
    return manager.approve_subject(args.gate, subject, scope=args.scope)


def command_compile_task(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    if args.dry_run:
        return _dry(args, "compile-task", allowed_paths=_split(args.allowed_paths), forbidden_paths=_split(args.forbidden_paths))
    return manager.compile_task(args.instruction, allowed_paths=_split(args.allowed_paths), forbidden_paths=_split(args.forbidden_paths), stop_conditions=_split(args.stop_conditions))


def command_approve_task(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    if args.dry_run:
        return _dry(args, "approve-task", approval=args.approval)
    approval = manager.consume_approval(args.approval)
    if manager.state["state"] == "AWAITING_TASK_APPROVAL":
        manager.transition("IMPLEMENTING", "TASK_APPROVED", {"approval_id": approval["approval_id"]})
    return {"status": "PASS", "approval": approval, "state": manager.state}


def command_validate_environment(args: argparse.Namespace) -> Dict[str, Any]:
    adapter = EnvironmentAdapter.from_file(args.environment_manifest)
    if args.dry_run:
        return _dry(args, "validate-environment", environment_id=adapter.manifest.get("id"))
    receipt = adapter.verify_online()
    path = Path(args.project_root).resolve() / ".robotics-ar" / "environment" / "validation-receipt.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    if receipt.get("status") != "ONLINE_VERIFIED":
        raise CLIError("environment is not ONLINE_VERIFIED")
    return {"status": "PASS", "receipt_path": path.as_posix(), "receipt": receipt}


def command_enable_execution(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    receipt = _load_json(args.receipt)
    if receipt.get("status") != "ONLINE_VERIFIED":
        raise CLIError("ONLINE_VERIFIED receipt required")
    if args.dry_run:
        return _dry(args, "enable-execution", fingerprint=receipt.get("fingerprint"))
    state = manager.enable_execution(receipt)
    return {"status": "PASS", "state": state, "environment_fingerprint": receipt["fingerprint"]}


def command_run_batch(args: argparse.Namespace) -> Dict[str, Any]:
    adapter = EnvironmentAdapter.from_file(args.environment_manifest)
    manager = _manager(args)
    receipt = _load_json(args.receipt)
    request = _load_json(args.request) if args.request else {"batch_id": args.batch_id}
    if args.dry_run:
        return _dry(args, "run-batch", batch_id=args.batch_id)
    result = adapter.run_batch(manager.state["mode"], receipt, request=request)
    return {"status": "PASS", "batch_id": args.batch_id, "result": result}


def command_pause(args: argparse.Namespace) -> Dict[str, Any]:
    if args.dry_run:
        return _dry(args, "pause", reason=args.reason)
    return _manager(args).pause(args.reason)


def command_resume(args: argparse.Namespace) -> Dict[str, Any]:
    if args.dry_run:
        return _dry(args, "resume")
    return _manager(args).resume()


def command_report(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    path = manager.paths.root / "report.md"
    if args.dry_run:
        return _dry(args, "report", path=path.as_posix())
    write_report(path, title="Robotics-AR report", state=manager.state["state"], summary=args.summary, actions=_split(args.actions))
    return {"status": "PASS", "report_path": path.as_posix()}


def command_handoff(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    path = manager.paths.root / "handoff.md"
    if args.dry_run:
        return _dry(args, "handoff", path=path.as_posix())
    write_handoff(path, state=manager.state["state"], session_id=manager.session_id, reason=args.reason)
    return {"status": "PASS", "handoff_path": path.as_posix()}


def command_reconstruct(args: argparse.Namespace) -> Dict[str, Any]:
    if args.dry_run:
        return _dry(args, "reconstruct-state")
    return _manager(args).reconstruct_state(persist=True)


COMMANDS = {
    "discover": command_discover,
    "init": command_init,
    "status": command_status,
    "validate-siblings": command_validate_siblings,
    "prepare-stage": command_prepare_stage,
    "register-stage-result": command_register_stage_result,
    "approve": command_approve,
    "compile-task": command_compile_task,
    "approve-task": command_approve_task,
    "validate-environment": command_validate_environment,
    "enable-execution": command_enable_execution,
    "run-batch": command_run_batch,
    "pause": command_pause,
    "resume": command_resume,
    "report": command_report,
    "handoff": command_handoff,
    "reconstruct-state": command_reconstruct,
}


def build_parser() -> argparse.ArgumentParser:
    """创建 CLI parser。 / Build the CLI parser."""

    parser = argparse.ArgumentParser(prog="robotics_ar.py")
    parser.add_argument("command", choices=sorted(COMMANDS))
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--robotics-research-root", default=".")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--mode", choices=["PLANNING_ONLY", "EXECUTION_ENABLED"], default="PLANNING_ONLY")
    parser.add_argument("--interaction-language", default="zh")
    parser.add_argument("--manifest")
    parser.add_argument("--allow-unconfirmed", action="store_true")
    parser.add_argument("--stage", choices=["idea", "experiment", "writing", "review"])
    parser.add_argument("--prompt", default="")
    parser.add_argument("--allowed-files", default="README.md")
    parser.add_argument("--input-sha256", default="")
    parser.add_argument("--artifact")
    parser.add_argument("--handoff-status", choices=["READY", "REVISE", "BLOCKED", "STOPPED"], default="READY")
    parser.add_argument("--gate", choices=["IDEA", "EXPERIMENT", "TASK", "EVIDENCE", "WRITING", "REVIEW_ROUTE", "REAL_ROBOT"])
    parser.add_argument("--subject")
    parser.add_argument("--scope", choices=["single-use", "persistent-until-drift"], default="single-use")
    parser.add_argument("--instruction", default="")
    parser.add_argument("--allowed-paths", default="src")
    parser.add_argument("--forbidden-paths", default="raw,research,claims")
    parser.add_argument("--stop-conditions", default="budget,critical-failure")
    parser.add_argument("--approval")
    parser.add_argument("--environment-manifest")
    parser.add_argument("--receipt")
    parser.add_argument("--request")
    parser.add_argument("--batch-id", default="batch-001")
    parser.add_argument("--reason", default="user-request")
    parser.add_argument("--summary", default="No summary supplied.")
    parser.add_argument("--actions", default="resume after validation")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """运行 CLI，只输出一个 JSON 对象。 / Run the CLI and emit one JSON object."""

    args = build_parser().parse_args(argv)
    try:
        result = COMMANDS[args.command](args)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 0
    except (CLIError, SessionError, SiblingAdapterError, EnvironmentError, OSError, ValueError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
